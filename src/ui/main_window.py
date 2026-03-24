"""
Main Window UI Component.

The main application window containing the sidebar and camera view.
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QScrollArea, QListWidgetItem, QToolBar, QPushButton, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt, Slot, QTimer, QSize, Signal
from PySide6.QtGui import QPixmap, QImage, QColor, QIcon, QAction, QKeySequence, QShortcut
from core import CameraThread, SettingsManager, PluginManager, init_logging, get_logger
from ui.widgets import ZoomImageLabel
from ui.panels import CameraPanel, OverlayPanel, SettingsPanel
from ui.panels.config_panel import ConfigPanel
from utils import resource_path, get_app_data_path
from __version__ import __version__, __app_name__
import sys
import os
if sys.platform == "win32":
    from ctypes import windll, c_int, byref


class MainWindow(QMainWindow):
    """
    Main application window for pyCol.
    
    Contains:
    - Sidebar with collapsible panels (Camera, Measurement, Overlay)
    - Main camera view area with zoom support
    - Settings persistence on close
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setWindowIcon(QIcon(resource_path("icon.png")))
        
        # Core Components
        self.settings_manager = SettingsManager(settings_file=os.path.join(get_app_data_path(), "settings.json"))
        self.settings = self.settings_manager.load_settings()
        
        # Initialize Logger first
        log_level = self.settings.get('log_level', 'INFO')
        log_max_size = self.settings.get('log_max_size_mb', 5)
        log_backup_count = self.settings.get('log_backup_count', 3)
        init_logging(level=log_level, max_size_mb=log_max_size, backup_count=log_backup_count)
        
        self.logger = get_logger('main')
        self.logger.info(f"{__app_name__} v{__version__} starting")
        
        # Log hardware/system info
        self._log_system_info()
        
        # Install global exception handler
        self._install_exception_handler()
        
        # Session tracking
        import time
        self._session_start = time.time()
        self._overlay_count = 0
        
        # Restore Window Geometry (if available)
        self._geometry_restored = False
        if 'window_geometry' in self.settings:
            try:
                from PySide6.QtCore import QByteArray
                geometry_data = QByteArray.fromBase64(self.settings['window_geometry'].encode('utf-8'))
                self.restoreGeometry(geometry_data)
                self._geometry_restored = True
            except Exception as e:
                self.logger.warning(f"Failed to restore window geometry: {e}")
                self.resize(1200, 800)
        else:
            self.resize(1200, 800)
        
        # Apply Windows Dark Title Bar
        if sys.platform == "win32":
            try:
                hwnd = self.winId()
                windll.dwmapi.DwmSetWindowAttribute(
                    c_int(int(hwnd)),
                    c_int(20),
                    byref(c_int(1)),
                    c_int(4)
                )
            except Exception as e:
                self.logger.debug(f"Failed to set dark title bar: {e}")

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.plugin_context = {
            'main_window': self,
            'settings_manager': self.settings_manager,
            'app_data_path': get_app_data_path()
        }
        self.plugin_manager = PluginManager(self.plugin_context)
        
        # Camera Thread
        self.thread = CameraThread(camera_id=0, plugin_manager=self.plugin_manager) # ID will be updated from settings
        self.plugin_context['camera_thread'] = self.thread # Add to context

        # --- Sidebar ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setFixedWidth(320)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Linux: Force scrollbar visibility to prevent layout shifts.
        if sys.platform.startswith("linux"):
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.scroll_area.setStyleSheet("""
                QScrollArea { border: none; background-color: #202020; }
                QScrollBar:vertical {
                    background: #202020;
                    width: 8px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #555;
                    min-height: 20px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #777;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: #202020;
                }
            """)
            sidebar_margins = (5, 5, 5, 5)
        else:
            self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #202020; }")
            sidebar_margins = (5, 5, 5, 5)

        self.sidebar_content = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        self.sidebar_layout.setContentsMargins(*sidebar_margins)
        self.sidebar_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.sidebar_content)
        self.layout.addWidget(self.scroll_area)

        # --- Toggle Button ---
        self.btn_toggle = QPushButton()
        self.btn_toggle.setFixedWidth(15)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #333;
                border: none;
                color: #888;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #444;
                color: white;
            }
            QPushButton:checked {
                background-color: #222;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        self.btn_toggle.setText("❮") # Initial state (Sidebar visible)
        self.btn_toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.layout.addWidget(self.btn_toggle)

        # --- Panels ---
        self.sec_camera = CameraPanel(self.thread, self)
        self.sidebar_layout.addWidget(self.sec_camera)

        # sec_measure removed (moved to plugin)
        
        self.sec_overlay = OverlayPanel(self.thread, self)
        self.sidebar_layout.addWidget(self.sec_overlay)
        
        self.sec_config = ConfigPanel(self.settings_manager, self)
        self.sidebar_layout.addWidget(self.sec_config)
        
        self.sec_settings = SettingsPanel(self.settings_manager, self)
        self.sidebar_layout.addWidget(self.sec_settings)
        
        # Load Plugins
        self.plugin_manager.load_plugins()
        for panel in self.plugin_manager.get_sidebar_panels():
            if hasattr(panel, 'set_expanded'): # If it follows our collapsable pattern
                # Load state
                is_expanded = self.settings.get("ui_state", {}).get(f"{panel.title}_expanded", False)
                panel.set_expanded(is_expanded)
            
            # Apply Plugin Theme (Green)
            if hasattr(panel, 'set_accent_color'):
                panel.set_accent_color("#98c379") # Green for Plugins

            self.sidebar_layout.addWidget(panel)
            
        self.sidebar_layout.addStretch()
        
        # --- Bottom Toolbar (Snapshot) ---
        self.layout_bottom = QHBoxLayout()
        self.layout_bottom.setSpacing(5)
        
        self.btn_snapshot = QPushButton("📸 Snapshot")
        self.btn_snapshot.setStyleSheet("background-color: #2a82da; color: white; padding: 5px; font-weight: bold;")
        self.btn_snapshot.clicked.connect(self.take_snapshot)
        
        self.btn_open_snap_folder = QPushButton("📂")
        self.btn_open_snap_folder.setToolTip("Open Snapshot Folder")
        self.btn_open_snap_folder.setStyleSheet("background-color: #444; color: white; padding: 5px;")
        self.btn_open_snap_folder.setFixedWidth(40)
        self.btn_open_snap_folder.clicked.connect(self.open_snapshot_folder)
        
        # Pan Mode Toggle
        self.btn_pan_mode = QPushButton("✋")
        self.btn_pan_mode.setCheckable(True)
        self.btn_pan_mode.setToolTip("Toggle Pan Mode (for Touchpads)")
        self.btn_pan_mode.setStyleSheet("""
            QPushButton { background-color: #444; color: white; padding: 5px; }
            QPushButton:checked { background-color: #2a82da; }
        """)
        self.btn_pan_mode.setFixedWidth(40)
        
        self.layout_bottom.addWidget(self.btn_snapshot, 1)
        self.layout_bottom.addWidget(self.btn_open_snap_folder)
        self.layout_bottom.addWidget(self.btn_pan_mode)
        
        self.sidebar_layout.addLayout(self.layout_bottom)
        
        self.sidebar_layout.addSpacing(5)

        # --- Camera View ---
        self.image_label = ZoomImageLabel(self)
        self.layout.addWidget(self.image_label, 1)
        
        # Connect Pan Mode Button
        self.btn_pan_mode.toggled.connect(self.image_label.set_pan_mode)
        self.image_label.pan_mode_changed.connect(self.update_pan_button)

        # Connect signals and start thread
        self.thread.change_pixmap_signal.connect(self.update_image)
        # update_centroid_signal removed (handled by plugin)
        # Use QueuedConnection to ensure error dialog runs on main thread
        self.thread.camera_error_signal.connect(self.on_camera_error, Qt.QueuedConnection)
        self.thread.camera_capabilities_signal.connect(self.sec_camera.update_capabilities, Qt.QueuedConnection)
        self.thread.camera_info_signal.connect(self.sec_camera.update_camera_info, Qt.QueuedConnection)
        self.thread.snapshot_saved_signal.connect(self.on_snapshot_saved, Qt.QueuedConnection)
        self.thread.start()

        # Apply Saved Pan Behavior
        interaction_cfg = self.settings.get('interaction', {})
        interaction_cfg = self.settings.get('interaction', {})
        space_behavior = interaction_cfg.get('space_behavior', 'toggle')
        self.image_label.set_pan_behavior(space_behavior)
        
        # Internal State
        self.last_centroid = None
        self._was_maximized = False

        
        # Shortcuts
        self.shortcut_fullscreen = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        
        # Apply Saved Settings
        # Check for default profile
        default_profile = self.settings_manager.get_default_profile()
        profile_loaded = False
        
        if default_profile:
             data = self.settings_manager.load_profile(default_profile)
             if data:
                 self.logger.info(f"Loading Default Profile: {default_profile}")
                 self.apply_settings(data, clear_existing=False)
                 self.set_active_profile(default_profile)
                 # Ensure settings dict is in sync for next save
                 self.settings["active_profile"] = default_profile
                 profile_loaded = True
             else:
                 self.logger.warning(f"Default profile '{default_profile}' not found, falling back.")
        
        if not profile_loaded:
            self.logger.info("Loading Last Session Settings")
            self.apply_settings()
            
            # Restore active profile name from settings
            if self.settings and "active_profile" in self.settings:
                 restored_name = self.settings["active_profile"]
                 if self.settings_manager.load_profile(restored_name):
                      self.set_active_profile(restored_name)
                 else:
                      self.active_profile_name = ""
            else:
                 self.active_profile_name = ""

        # Track Active Profile (verified state)
        if self.active_profile_name:
             self.logger.info(f"Current Active Profile: {self.active_profile_name}")
        
        # Track Active Profile (Duplicated logic removed)

    def set_active_profile(self, name: str):
        """Update active profile name for metadata."""
        self.active_profile_name = name
        self.logger.info(f"Active Profile Set: {name}")
        
        # Update Window Title
        if name:
            self.setWindowTitle(f"{__app_name__} v{__version__} - [{name}]")
        else:
            self.setWindowTitle(f"{__app_name__} v{__version__}")

    def update_pan_button(self, enabled: bool):
        """Update pan button state without triggering signals (loop prevention)."""
        self.btn_pan_mode.blockSignals(True)
        self.btn_pan_mode.setChecked(enabled)
        self.btn_pan_mode.blockSignals(False)

    def toggle_fullscreen(self):
        """Toggle between fullscreen and normal mode."""
        if self.isFullScreen():
            if self._was_maximized:
                self.showMaximized()
            else:
                self.showNormal()
        else:
            self._was_maximized = self.isMaximized()
            self.showFullScreen()
            
    def take_snapshot(self):
        """Trigger snapshot save."""
        # Get settings
        cfg = self.sec_settings.get_snapshot_settings()
        path = cfg['path']
        prefix = cfg['prefix']
        pattern = cfg.get('subfolder_pattern', "")
        meta = cfg['metadata']
        
        # Determine profile name
        profile_name = self.active_profile_name or "Default"
        
        # Resolve Subfolder Pattern
        if pattern:
            import datetime
            now = datetime.datetime.now()
            
            # 1. Replace Profile Variable
            # We do this BEFORE strftime to avoid issues with % characters in profile names (unlikely but safe)
            # or if we wanted to support profile-specific time formats later.
            subfolder = pattern.replace("{profile}", profile_name)
            
            # 2. Apply Python strftime formatting (allows %Y, %m, %d, %H, etc.)
            # Also support legacy {date} style for backward compatibility if desired,
            # or just switch fully. Let's keep {date} as a helper alias?
            # User request was specifically for python notation.
            # We'll map the old variables to strftime equivalents just in case,
            # but rely on strftime for the heavy lifting.
            subfolder = subfolder.replace("{date}", "%Y-%m-%d")
            subfolder = subfolder.replace("{year}", "%Y")
            subfolder = subfolder.replace("{month}", "%m")
            subfolder = subfolder.replace("{day}", "%d")
            
            try:
                subfolder = now.strftime(subfolder)
            except Exception as e:
                self.logger.error(f"Error formatting snapshot path: {e}")
                # Fallback to mostly raw string but safe
                pass
            
            # Construct new full path
            import os
            path = os.path.join(path, subfolder)
             
        # Resolve Profile in Filename Pattern (formerly Prefix)
        # We do this here because CameraThread shouldn't know about profiles/GUI state
        # Parsing for strftime % happens in CameraThread
        if "{profile}" in prefix:
             prefix = prefix.replace("{profile}", profile_name)
             
        self.thread.request_snapshot(path, prefix, meta, profile_name)
        
    def on_snapshot_saved(self, path):
        """Handle successful snapshot save."""
        # Visual feedback on button instead of status bar
        self.btn_snapshot.setText("✅ Saved!")
        self.btn_snapshot.setStyleSheet("background-color: #28a745; color: white; padding: 5px; font-weight: bold;")
        
        # Reset after 2 seconds
        QTimer.singleShot(1000, self.reset_snapshot_btn)
        
    def reset_snapshot_btn(self):
        """Reset snapshot button style."""
        self.btn_snapshot.setText("📸 Snapshot")
        self.btn_snapshot.setStyleSheet("background-color: #2a82da; color: white; padding: 5px; font-weight: bold;")

    def open_snapshot_folder(self):
        """Open the snapshot folder in system explorer."""
        cfg = self.sec_settings.get_snapshot_settings()
        path = cfg['path']
        
        import os
        import subprocess
        
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                pass
                
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            self.logger.error(f"Failed to open folder: {e}")


    def _log_system_info(self):
        """Log system and hardware info at startup (INFO level)."""
        import platform
        import cv2
        from PySide6 import __version__ as pyside_version
        
        self.logger.info(f"System: {platform.system()} {platform.release()}")
        self.logger.info(f"Python: {platform.python_version()}, OpenCV: {cv2.__version__}, PySide6: {pyside_version}")
        
        # Redirect OpenCV errors to logger
        def cv_log_callback(*args):
            try:
                func_name = args[1] if len(args) > 1 else "Unknown"
                err_msg = args[2] if len(args) > 2 else "Unknown error"
                file = args[3] if len(args) > 3 else ""
                line = args[4] if len(args) > 4 else 0
                self.logger.warning(f"OpenCV Native: {func_name} - {err_msg} ({file}:{line})")
            except Exception:
                pass
            return 0 # Allow default behavior? Or 1 to suppress?
            
        cv2.redirectError(cv_log_callback)
        
        # Log available cameras
        from PySide6.QtMultimedia import QMediaDevices
        cameras = QMediaDevices.videoInputs()
        if cameras:
            cam_names = [cam.description() for cam in cameras]
            self.logger.info(f"Cameras: {', '.join(cam_names)}")
        else:
            self.logger.info("Cameras: None detected via Qt, using OpenCV probing")
    
    def _install_exception_handler(self):
        """Install global exception handler for unhandled errors (CRITICAL level)."""
        import sys
        import traceback
        
        def exception_handler(exc_type, exc_value, exc_tb):
            # Don't log KeyboardInterrupt
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            self.logger.critical(f"Unhandled exception:\n{tb_str}")
            
            # Still call default handler for console output
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        
        sys.excepthook = exception_handler

    def handle_zoom_scroll(self, delta: int, rel_x: float = 0.5, rel_y: float = 0.5):
        """Handle mouse scroll for zoom adjustment.
        
        Args:
            delta: Scroll wheel delta (positive = zoom in)
            rel_x: Cursor X position relative to image (0-1)
            rel_y: Cursor Y position relative to image (0-1)
        """
        current_val = self.sec_camera.slider_zoom.value()
        
        # Multiplicative zoom is more natural
        factor = 1.2
        if delta > 0:
            new_val = min(10.0, current_val * factor)
        else:
            new_val = max(1.0, current_val / factor)
        
        # Calculate new focus point to keep mouse position stable
        # Formula: new_f = old_f + (mouse - 0.5) * (1/old_z - 1/new_z)
        if current_val > 0 and new_val > 0:
            term = (1.0 / current_val) - (1.0 / new_val)
            
            curr_fx = self.thread.zoom_focus_x
            curr_fy = self.thread.zoom_focus_y
            
            new_fx = curr_fx + (rel_x - 0.5) * term
            new_fy = curr_fy + (rel_y - 0.5) * term
            
            # Update focus FIRST, then zoom level
            self.thread.set_zoom_focus(new_fx, new_fy)
        
        self.sec_camera.slider_zoom.setValue(new_val)
    
    def handle_pan(self, delta_x: float, delta_y: float):
        """Handle pan movement from mouse drag.
        
        Args:
            delta_x: Relative X movement (-1 to 1 range)
            delta_y: Relative Y movement (-1 to 1 range)
        """
        if self.thread.zoom_val > 1.0:
            # Apply pan to zoom focus point
            new_x = self.thread.zoom_focus_x + delta_x
            new_y = self.thread.zoom_focus_y + delta_y
            self.thread.set_zoom_focus(new_x, new_y)

    @Slot(QImage)
    def update_image(self, qt_img: QImage):
        """Update the camera view with a new frame."""
        if not qt_img or qt_img.isNull():
            return
            
        try:
            self.image_label.set_image(qt_img)
        except Exception as e:
            self.logger.error(f"Error updating image: {e}")
        
    # update_centroid slot removed (moved to plugin)

    def _requery_camera_capabilities(self):
        """Re-query camera capabilities after startup to handle race conditions (Thread-Safe)."""
        if self.thread.isRunning():
            self.thread.request_capabilities_update()
            self.logger.debug("Requested camera capability update (threaded)")

    @Slot(str)
    def on_camera_error(self, error_message: str):
        """Handle camera errors by showing a message box."""
        self.logger.warning(f"Camera error: {error_message}")
        QMessageBox.warning(
            self,
            "Camera Error",
            error_message + "\n\nPlease select a different camera.",
            QMessageBox.Ok
        )

    def apply_settings(self, settings_data=None, clear_existing=False):
        """
        Apply settings/profile to UI.
        
        Args:
            settings_data: Dict with settings. If None, uses self.settings (loaded at start).
            clear_existing: If True, clears current partial state (e.g. overlays) before applying. 
        """
        if settings_data is None:
            data = self.settings
        else:
            data = settings_data
        
        # Always apply UI state defaults (panels collapsed on first start)
        ui = data.get("ui_state", {}) if data else {}
        self.sec_camera.set_expanded(ui.get("camera_expanded", False))
        # sec_measure state restore removed
        self.sec_overlay.set_expanded(ui.get("overlay_expanded", False))
        self.sec_config.set_expanded(ui.get("config_expanded", False))
        self.sec_settings.set_expanded(ui.get("settings_expanded", False))
            
        if not data: 
            self.logger.debug("No settings to apply")
            return
        
        self.logger.debug("Applying settings")
        
        # 0. Clear logic for profile loading
        if clear_existing:
            self.logger.debug("Clearing existing state for profile load")
            # Clear Overlays
            self.thread.collimator.clear_overlays()
            self.sec_overlay.list_circles.clear()
            # Reset active index
            self.thread.collimator.active_overlay_index = -1
        
        # 1. Camera settings
        cam = data.get("camera", {})
        if "id" in cam:
            self.sec_camera.combo_camera.blockSignals(True)
            idx = self.sec_camera.combo_camera.findData(cam["id"])
            if idx >= 0:
                self.sec_camera.combo_camera.setCurrentIndex(idx)
                if cam["id"] != 0:
                    self.thread.switch_camera(cam["id"])
            self.sec_camera.combo_camera.blockSignals(False)
            
        if "format" in cam:
            self.sec_camera.combo_format.blockSignals(True)
            idx = self.sec_camera.combo_format.findText(cam["format"])
            if idx >= 0:
                self.sec_camera.combo_format.setCurrentIndex(idx)
            self.sec_camera.combo_format.blockSignals(False)
            self.thread.set_format(cam["format"])
            
        if "exposure" in cam:
            self.sec_camera.slider_exposure.setValue(cam["exposure"])
        if "focus" in cam:
            self.sec_camera.slider_focus.setValue(cam["focus"])
        # Zoom is not restored (always start at 1.0)
        if "contrast" in cam:
            self.sec_camera.slider_contrast.setValue(cam["contrast"])
        if "brightness" in cam:
            self.sec_camera.slider_brightness.setValue(cam["brightness"])
        if "saturation" in cam:
            self.sec_camera.slider_saturation.setValue(cam["saturation"])
        
        # Restore Flip / Mirror State
        if "flip_h" in cam:
            self.sec_camera.check_flip_h.setChecked(cam["flip_h"])
            self.thread.set_flip_h(cam["flip_h"])
        if "flip_v" in cam:
            self.sec_camera.check_flip_v.setChecked(cam["flip_v"])
            self.thread.set_flip_v(cam["flip_v"])
        
        # Restore Focus Favorites
        if "focus_favorites" in cam:
            self.sec_camera.slider_focus.set_favorites(cam["focus_favorites"])
            
        # 2. Calibration settings
        cal = data.get("calibration", {})
        if "offset_x" in cal:
            self.sec_overlay._stored_offset_x = cal["offset_x"]
            self.thread.set_global_offset_x(cal["offset_x"])
            self.sec_overlay.slider_off_x.setValue(cal["offset_x"])
        if "offset_y" in cal:
            self.sec_overlay._stored_offset_y = cal["offset_y"]
            self.thread.set_global_offset_y(cal["offset_y"])
            self.sec_overlay.slider_off_y.setValue(cal["offset_y"])
        if "offset_enabled" in cal:
            enabled = cal["offset_enabled"]
            self.sec_overlay.chk_global_offset.setChecked(enabled)
            if not enabled:
                self.sec_overlay.toggle_global_offset(0)  # Apply disabled state
        # Calibration settings are now only Global Offset (threshold/invert moved to plugin)

        # 4. Overlays
        overlays = data.get("overlays", [])
        self.logger.debug(f"Restoring {len(overlays)} overlays")
        for ov in overlays:
            stype = ov.get("type", "circle")
            arms = ov.get("arms", 4)
            
            idx = self.thread.add_overlay_shape(stype, arms=arms)
            self.logger.debug(f"Added overlay {stype} at index {idx}")
            
            self.thread.collimator.set_active_index(idx)
            # Apply individual overlay props
            if "radius" in ov:
                self.thread.collimator.update_active_circle_radius(ov["radius"])
            if "thickness" in ov:
                self.thread.collimator.update_active_circle_thickness(ov["thickness"])
            if "angle" in ov and stype != "circle":
                self.thread.collimator.update_active_angle(ov["angle"])
            if "color" in ov:
                self.thread.collimator.update_active_circle_color(tuple(ov["color"]))
            if "offset_x" in ov:
                self.thread.collimator.update_active_circle_offset_x(ov["offset_x"])
            if "offset_y" in ov:
                self.thread.collimator.update_active_circle_offset_y(ov["offset_y"])

            # Add to UI List
            stored_name = ov.get("name", "")
            count = self.sec_overlay.list_circles.count() + 1
            
            if stored_name:
                name = stored_name
            elif stype == "circle":
                name = f"Circle {count}"
            elif stype in ('radial', 'crosshair'):
                name = f"Crosshair {count}"
            else:
                name = f"{stype.capitalize()} {count}"
            
            # Update backend with name if it was generated/missing
            self.thread.collimator.overlays[idx]['name'] = name
            
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsEditable) # Make editable
            
            if "color" in ov:
                bgr = ov["color"]
                rgb = (bgr[2], bgr[1], bgr[0])
                item.setForeground(QColor(*rgb))
                
            self.sec_overlay.list_circles.addItem(item)
            
        # 5. Plugin Settings (Apply from Profile)
        if "plugins" in data and self.plugin_manager:
            self.logger.debug("Applying plugin settings from profile")
            self.plugin_manager.apply_profile_settings(data["plugins"])

    def get_current_settings(self):
        """Collect current application state into a dictionary."""
        # Get logging settings from settings panel
        logging_settings = self.sec_settings.get_settings()
        
        return {
            "active_profile": self.active_profile_name,
            "camera": {
                "id": self.sec_camera.combo_camera.currentData(),
                "format": self.thread.format_val,
                "exposure": self.thread.exposure_val,
                # Zoom is not saved
                "focus": self.thread.focus_val,
                "contrast": self.thread.contrast_val,
                "brightness": self.thread.brightness_val,
                "saturation": self.thread.saturation_val,
                "flip_h": self.thread.flip_h,
                "flip_v": self.thread.flip_v,
                "focus_favorites": self.sec_camera.slider_focus.get_favorites()
            },
            "calibration": {
                "offset_x": self.sec_overlay._stored_offset_x,
                "offset_y": self.sec_overlay._stored_offset_y,
                "offset_enabled": self.sec_overlay.chk_global_offset.isChecked(),
                "threshold": self.thread.collimator.threshold,
                "invert": self.thread.collimator.invert
            },
            "ui_state": {
                "camera_expanded": self.sec_camera.is_expanded(),
                # measure_expanded removed
                "overlay_expanded": self.sec_overlay.is_expanded(),
                "config_expanded": False, # Never save as expanded
                "settings_expanded": self.sec_settings.is_expanded()
            },
            "overlays": self.thread.collimator.overlays,
            "window_geometry": self.saveGeometry().toBase64().data().decode('utf-8'),
            "window_state": self.saveState().toBase64().data().decode('utf-8'),
            # Logging settings
            "log_level": logging_settings['log_level'],
            "log_max_size_mb": logging_settings['log_max_size_mb'],
            "log_backup_count": logging_settings['log_backup_count'],
            "snapshot": logging_settings.get('snapshot', {}),
            "interaction": logging_settings.get('interaction', {})
        }

    def toggle_sidebar(self):
        """Toggle the visibility of the sidebar."""
        visible = not self.scroll_area.isVisible()
        self.scroll_area.setVisible(visible)
        
        # Update styling or text
        if visible:
            self.btn_toggle.setText("❮")
        else:
            self.btn_toggle.setText("❯")

    def showEvent(self, event):
        """Validate window position when shown."""
        super().showEvent(event)
        
        # Only check once after geometry was restored
        if hasattr(self, '_geometry_restored') and self._geometry_restored:
            self._geometry_restored = False  # Don't check again
            
            from PySide6.QtWidgets import QApplication
            
            # Check if window center is on any connected screen
            window_center = self.geometry().center()
            screen_found = False
            for screen in QApplication.screens():
                if screen.geometry().contains(window_center):
                    screen_found = True
                    break
            
            if not screen_found:
                self.logger.warning("Window position off-screen, resetting to primary monitor")
                self.resize(1200, 800)
                primary = QApplication.primaryScreen()
                if primary:
                    screen_geo = primary.availableGeometry()
                    self.move(screen_geo.x() + 50, screen_geo.y() + 50)

    def closeEvent(self, event):
        """Save settings and cleanup on window close."""
        # Session summary (DEBUG)
        import time
        duration_min = (time.time() - self._session_start) / 60
        overlay_count = len(self.thread.collimator.overlays)
        self.logger.debug(f"Session ended. Duration: {duration_min:.1f}min, Overlays: {overlay_count}")
        
        self.logger.info("Closing application, saving settings")
        data = self.get_current_settings()
        self.settings_manager.save_settings(data)
        
        self.thread.stop()
        self.thread.wait()
        event.accept()
