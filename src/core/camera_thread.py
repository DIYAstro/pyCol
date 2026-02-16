import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition, Qt
from PySide6.QtGui import QImage
from .collimator import Collimator
from .logger import get_logger
from __version__ import __version__

# Module logger
_logger = get_logger('camera')

class CameraThread(QThread):
    change_pixmap_signal = Signal(QImage)
    update_centroid_signal = Signal(tuple) # Emit (x, y) of detected spot
    camera_error_signal = Signal(str) # Emit error message when camera fails
    camera_capabilities_signal = Signal(dict) # Emit supported features {'focus': bool, 'exposure': bool}
    snapshot_saved_signal = Signal(str) # Emit path when snapshot saved
    global_offset_changed = Signal(float, float) # Emit (offset_x, offset_y) when global offsets change

    def __init__(self, camera_id=0, plugin_manager=None):
        super().__init__()
        self.camera_id = camera_id
        self.plugin_manager = plugin_manager
        self._run_flag = True
        self.cap = None
        
        self.collimator = Collimator()
        
        # Camera Settings
        self.exposure_val = -5 # Default log2 value
        self.gain_val = 0
        self.focus_val = 0
        self.zoom_val = 1.0
        
        # Software Image Adjustments
        self.contrast_val = 1.0 # Alpha (1.0 = no change)
        self.brightness_val = 0 # Beta (0 = no change)
        self.saturation_val = 1.0 # 1.0 = no change
        
        # Zoom focus point (0-1 range, 0.5 = center)
        self.zoom_focus_x = 0.5
        self.zoom_focus_y = 0.5
        
        # Detection Toggle
        self.detection_active = False
        
        # Flag to signal camera needs reinitialization
        self._camera_needs_init = True
        
        # Image Flip Flags (Mirroring)
        self.flip_h = False
        self.flip_v = False
        
        # Snapshot Request State
        self._snapshot_request = None # Dict with path, prefix, etc.
        
        # Capability Update Request
        self._req_caps_update = False

    def request_capabilities_update(self):
        """Request a re-check of camera capabilities in the next loop iteration."""
        self._req_caps_update = True

    def _init_camera(self):
        """Try to initialize the current camera. Returns True on success."""
        _logger.info(f"Initializing camera {self.camera_id}")
        
        if self.cap:
            self.cap.release()
            self.cap = None
            
        try:
            # Platform-specific backend selection
            import sys
            if sys.platform == 'win32':
                backend = cv2.CAP_DSHOW
            elif sys.platform == 'linux':
                backend = cv2.CAP_V4L2
            else:
                backend = cv2.CAP_ANY

            self.cap = cv2.VideoCapture(self.camera_id, backend)
        except Exception as e:
            _logger.error(f"Failed to open camera {self.camera_id}: {e}")
            self.camera_error_signal.emit(f"Failed to open camera {self.camera_id}: {e}")
            return False
        
        if not self.cap or not self.cap.isOpened():
            _logger.warning(f"Camera {self.camera_id} could not be opened")
            self.camera_error_signal.emit(f"Camera {self.camera_id} could not be opened. It may be in use or incompatible.")
            if self.cap:
                self.cap.release()
                self.cap = None
            return False
        
        # Try to read a test frame to verify camera works
        try:
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                _logger.warning(f"Camera {self.camera_id} cannot read frames (possibly IR camera)")
                self.camera_error_signal.emit(f"Camera {self.camera_id} opened but cannot read frames. It may be an IR or special-purpose camera.")
                self.cap.release()
                self.cap = None
                return False
        except Exception as e:
             _logger.error(f"Error reading test frame from camera {self.camera_id}: {e}")
             self.cap.release()
             self.cap = None
             return False
        
        # Set high res
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        
        # Get actual resolution
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        _logger.info(f"Camera {self.camera_id} ready ({actual_w}x{actual_h})")
        
        # Check capabilities (Focus/Exposure support)
        caps = self.get_capabilities()
        self.camera_capabilities_signal.emit(caps)
        _logger.info(f"Camera capabilities: {caps}")

        self.update_camera_settings()
        return True

    def get_capabilities(self):
        """Probe camera for supported features."""
        caps = {
            'focus': False,
            'exposure': False,
            'zoom': True # Digital zoom is always supported by software
        }
        
        if not self.cap or not self.cap.isOpened():
            return caps
            
        try:
            # Check Focus
            # Try to disable autofocus (0). If this returns True, manual focus is likely supported.
            if self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0):
                caps['focus'] = True
            else:
                # Fallback 1: Check if we can read a valid focus value
                val = self.cap.get(cv2.CAP_PROP_FOCUS)
                caps['focus'] = (val != -1)
                
                # Fallback 2: Check if Auto Focus property is readable
                if not caps['focus']:
                    af_val = self.cap.get(cv2.CAP_PROP_AUTOFOCUS)
                    if af_val != -1:
                        caps['focus'] = True
                        _logger.debug(f"Focus capability detected via AUTOFOCUS property (val={af_val})")

            # Check Exposure
            # Check if we can read exposure. 
            # Note: Many webcams return -1 if not supported.
            # 0 can be a valid exposure value (e.g. very short).
            # We also check if we can disable Auto Exposure, which is key for manual control.
            
            # 1. Check Auto Exposure Support (Try to set to Manual)
            # DSHOW: 0.25 = Manual, 0.75 = Auto
            # V4L2: 1 = Manual, 3 = Auto
            # We try both common manual flags? 
            # Actually, simpliest check: if get(CAP_PROP_EXPOSURE) returns valid number (!= -1).
            
            val = self.cap.get(cv2.CAP_PROP_EXPOSURE)
            
            # Some cameras return -1, -2, or other negative codes for "Auto" or "Not Supported"
            # But log2 exposure values are negative (e.g. -5).
            # So checking != -1 is risky if -1 is a valid exposure (0.5s).
            # However, typically -1 as an error code is distinct from -1.0 float.
            # Let's assume ANY return value implies support, unless explicitly indicating failure?
            # Actually, OpenCV DSHOW backend often returns -1 for unsupported properties.
            
            # Better check: Try to set it to current value? No.
            
            # User reported regression. Previous code was likely more permissive or different.
            # Let's just allow 0.
            
            # Fallback 1: Check Auto Exposure property (Passive)
            if not caps['exposure']:
                 ae_val = self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
                 if ae_val != -1:
                     caps['exposure'] = True
                     _logger.debug(f"Exposure capability detected via AUTO_EXPOSURE property (val={ae_val})")
            
            # Fallback 2: Active Probing (Try to SET Auto Exposure to Manual)
            # DSHOW: 0.25 = Manual, 0.75 = Auto
            if not caps['exposure']:
                _logger.info("Attempting Active Probing for Exposure (DSHOW Manual=0.25)...")
                if self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25):
                    caps['exposure'] = True
                    _logger.info("Exposure capability detected via Active Set (DSHOW 0.25)")
                # Also try V4L2/Other standard (1 = Manual)
                elif self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
                    caps['exposure'] = True
                    _logger.info("Exposure capability detected via Active Set (Standard 1)")
            
        except Exception as e:
            _logger.warning(f"Error checking capabilities: {e}")
            
        return caps

    def run(self):
        import time
        consecutive_failures = 0
        max_failures = 30
        
        # FPS tracking
        frame_count = 0
        fps_start_time = time.time()
        fps_log_interval = 30  # Log FPS every 30 seconds

        while self._run_flag:
            # Check if camera needs (re)initialization
            if self._camera_needs_init:
                self._camera_needs_init = False
                self._init_camera()
                fps_start_time = time.time()
                frame_count = 0
            
            # If no valid camera, just sleep and wait for switch_camera call
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)  # Avoid busy loop
                continue
                
            try:
                ret, cv_img = self.cap.read()
                if not ret or cv_img is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.camera_error_signal.emit(f"Camera {self.camera_id} stopped responding after {max_failures} failed reads.")
                        self.cap.release()
                        self.cap = None
                    continue
                
                
                # Check for Capability Update Request (Thread-Safe)
                if self._req_caps_update:
                    self._req_caps_update = False
                    try:
                        caps = self.get_capabilities()
                        self.camera_capabilities_signal.emit(caps)
                        _logger.info(f"Re-queried camera capabilities: {caps}")
                    except Exception as e:
                        _logger.error(f"Error re-querying capabilities: {e}")
                
                consecutive_failures = 0
                frame_count += 1
                
                # Log FPS periodically (DEBUG)
                elapsed = time.time() - fps_start_time
                if elapsed >= fps_log_interval:
                    fps = frame_count / elapsed
                    _logger.debug(f"Camera performance: {fps:.1f} FPS (avg over {elapsed:.0f}s)")
                    fps_start_time = time.time()
                    frame_count = 0

                
                # 0. Apply Flip / Mirroring (FIRST step to ensure coordinates align)
                if self.flip_h and self.flip_v:
                    cv_img = cv2.flip(cv_img, -1) # Both
                elif self.flip_h:
                    cv_img = cv2.flip(cv_img, 1)  # Horizontal
                elif self.flip_v:
                    cv_img = cv2.flip(cv_img, 0)  # Vertical

                # 1. Plugin Processing (e.g. Lens Calibration, Auto Focus Analysis)
                if self.plugin_manager:
                    cv_img = self.plugin_manager.process_frame(cv_img)

                # 2. Apply Software Adjustments (Contrast/Brightness/Saturation)
                if self.contrast_val != 1.0 or self.brightness_val != 0:
                    cv_img = cv2.convertScaleAbs(cv_img, alpha=self.contrast_val, beta=self.brightness_val)
                
                # Apply Saturation adjustment
                if self.saturation_val != 1.0:
                    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV).astype(np.float32)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * self.saturation_val, 0, 255)
                    cv_img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

                # 1. Measurement / Centroid Finding (MOVED TO PLUGIN)
                # Detection and Calibration is now handled by 'offset_measurement' plugin.
                # The plugin hooks into process_frame above.

                # 2. Digital Zoom & Crop (FIRST)
                zoom_params = None
                
                if self.zoom_val > 1.0:
                    h_orig, w_orig = cv_img.shape[:2]
                    
                    # Calculate Crop
                    new_h, new_w = int(h_orig / self.zoom_val), int(w_orig / self.zoom_val)
                    
                    # Zoom focus center
                    zoom_cx = int(w_orig * self.zoom_focus_x)
                    zoom_cy = int(h_orig * self.zoom_focus_y)
                    
                    top = zoom_cy - new_h // 2
                    left = zoom_cx - new_w // 2
                    
                    # Clamp
                    if top < 0: top = 0
                    if left < 0: left = 0
                    if top + new_h > h_orig: top = h_orig - new_h
                    if left + new_w > w_orig: left = w_orig - new_w
                    # Apply Crop
                    cv_img = cv_img[top:top+new_h, left:left+new_w]
                    
                    # Upscale back to original size (Nearest Neighbor to keep pixel look)
                    # This enables "High Res Vector Overlay" on top of "Blocky Zoomed Pixels"
                    cv_img = cv2.resize(cv_img, (w_orig, h_orig), interpolation=cv2.INTER_NEAREST)
                    
                    # Prepare zoom params for overlay drawing
                    zoom_params = {
                        'zoom': self.zoom_val,
                        'left': left,
                        'top': top,
                        'orig_w': w_orig,
                        'orig_h': h_orig
                    }
                
                # 3. Draw Overlays (AFTER Zoom, using coordinate transform)
                # This draws Crosshair, Shapes, Calibration Trail, and Measurement Points
                cv_img = self.collimator.draw_overlays(cv_img, zoom_params=zoom_params)

                # 4. Handle Snapshot Request
                if self._snapshot_request:
                     self._save_snapshot(cv_img)

                # --- LEGACY CODE REMOVED HERE ---
                
                rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Debug logging (temporary)
                _logger.debug(f"Emitting frame: {w}x{h}, {convert_to_qt_format.sizeInBytes()} bytes, null={convert_to_qt_format.isNull()}")
                
                self.change_pixmap_signal.emit(convert_to_qt_format)

            except cv2.error as e:
                _logger.warning(f"OpenCV error during frame processing: {e}")
                consecutive_failures += 1
                continue
            except Exception as e:
                _logger.error(f"Unexpected error during frame processing: {e}")
                consecutive_failures += 1
                continue
            
            # Apply settings if changed (simple polling for now)
            self.update_camera_settings()
            
    # Calibration wrappers removed (moved to plugin)
            
    def update_camera_settings(self):
        if not self.cap: return

        # Exposure (only set if changed)
        current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
        if current_exposure != self.exposure_val:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure_val)

        # Focus (disable autofocus first, then set manual value, only if changed)
        if self.focus_val >= 0:
            current_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
            # Use tolerance for float comparison to avoid infinite loop spam
            if abs(current_focus - self.focus_val) > 0.1:
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_val)
             
    def set_exposure(self, val):
        self.exposure_val = val

    def set_focus(self, val):
        self.focus_val = val
        
    def set_zoom(self, val):
        self.zoom_val = val
        
    def set_zoom_focus(self, x: float, y: float):
        """Set zoom focus point (0-1 range, 0.5 = center)."""
        self.zoom_focus_x = max(0, min(1, x))
        self.zoom_focus_y = max(0, min(1, y))

    def set_flip_h(self, flip: bool):
        """Set horizontal flip (mirror) state."""
        self.flip_h = flip
        
    def set_flip_v(self, flip: bool):
        """Set vertical flip (mirror) state."""
        self.flip_v = flip
        
    def request_snapshot(self, path, prefix, include_metadata=True, profile_name=""):
        """Queue a snapshot request."""
        self._snapshot_request = {
            'path': path,
            'prefix': prefix,
            'metadata': include_metadata,
            'profile': profile_name
        }

    def _save_snapshot(self, frame):
        """Internal method to save snapshot with metadata."""
        try:
            req = self._snapshot_request
            self._snapshot_request = None # Reset flag
            
            save_path = req['path']
            prefix = req['prefix']
            
            import os
            import datetime
            
                
            if not os.path.exists(save_path):
                os.makedirs(save_path)
                
            now = datetime.datetime.now()
            
            # Dynamic Filename Logic
            if "%" in prefix:
                 # It's a pattern (e.g. pyCol_%Y-%m-%d). Use strftime.
                 filename = now.strftime(prefix)
                 # Ensure extension
                 if not filename.lower().endswith(".png"):
                      filename += ".png"
            else:
                 # Legacy: It's a simple prefix. Append timestamp.
                 timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
                 filename = f"{prefix}{timestamp}.png"
                 
            full_path = os.path.join(save_path, filename)
            
            output_frame = frame.copy()
            
            # Draw Metadata (OSD)
            # Metadata can be bool (legacy) or dict (new)
            osd_cfg = req.get('metadata', False)
            show_osd = False
            
            if isinstance(osd_cfg, bool):
                # Legacy behavior
                show_osd = osd_cfg
                osd_time = True
                osd_time_fmt = "%Y-%m-%d_%H-%M-%S"
                osd_profile = True
                osd_note = False
                osd_note_text = ""
            elif isinstance(osd_cfg, dict):
                osd_time = osd_cfg.get('time', True)
                osd_time_fmt = osd_cfg.get('time_fmt', "%Y-%m-%d - %H:%M:%S")
                osd_profile = osd_cfg.get('profile', True)
                osd_note = osd_cfg.get('note', False)
                osd_note_text = osd_cfg.get('note_text', "")
                
                # Auto-detect if we should show OSD (if ANY field is active)
                # Or check 'enabled' key if present (backward compat)
                show_osd = osd_cfg.get('enabled', False) or osd_time or osd_profile or (osd_note and osd_note_text)
            else:
                show_osd = False

            if show_osd:
                # 1. Get dimensions & Create Banner
                h, w = output_frame.shape[:2]
                banner_height = 30
                
                # Add black banner at bottom
                banner = np.zeros((banner_height, w, 3), dtype=np.uint8)
                output_frame = np.vstack((output_frame, banner))

                # Build Text Parts first to see if we have anything to show
                parts = [f"pyCol v{__version__}"]
                
                if osd_time:
                    try:
                        ts = datetime.datetime.now().strftime(osd_time_fmt)
                        parts.append(ts)
                    except:
                        parts.append(datetime.datetime.now().strftime("%Y-%m-%d"))
                
                if osd_profile and req['profile']:
                    parts.append(f"Profile: {req['profile']}")
                    
                if osd_note and osd_note_text:
                    parts.append(f"Note: {osd_note_text}")
                
                text = " | ".join(parts)
                    
                cv2.putText(output_frame, text, (10, h + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.imwrite(full_path, output_frame)
            _logger.info(f"Snapshot saved: {full_path}")
            self.snapshot_saved_signal.emit(full_path)
            
        except Exception as e:
            _logger.error(f"Failed to save snapshot: {e}")
            self.camera_error_signal.emit(f"Snapshot failed: {e}")
        
    def set_contrast(self, val):
        self.contrast_val = val
        
    def set_brightness(self, val):
        self.brightness_val = val
        
    def set_saturation(self, val):
        self.saturation_val = val
        
    def set_threshold(self, val):
        self.collimator.threshold = val

    def set_invert(self, val):
        self.collimator.invert = val
        
    def set_global_offset_x(self, val):
        self.collimator.global_offset_x = val
        # Emit signal so UI can update
        self.global_offset_changed.emit(val, self.collimator.global_offset_y)
        
    def set_global_offset_y(self, val):
        self.collimator.global_offset_y = val
        # Emit signal so UI can update
        self.global_offset_changed.emit(self.collimator.global_offset_x, val)
        
    def set_active_radius(self, val):
        self.collimator.update_active_circle_radius(val)
        
    def set_active_angle(self, val):
        self.collimator.update_active_angle(val)

    def set_active_arms(self, val):
        self.collimator.update_active_arms(val)
        
    def set_active_offset_x(self, val):
        self.collimator.update_active_circle_offset_x(val)
        
    def set_active_offset_y(self, val):
        self.collimator.update_active_circle_offset_y(val)
        
    def add_overlay_shape(self, shape_type, arms=4):
        return self.collimator.add_overlay_shape(shape_type, arms=arms)
        
    def capture_p2(self, pos):
        # We need frame width/height to call calculate_center correctly
        # We can get it from self.cap settings
        w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.collimator.capture_p2(pos, w, h)
        # Emit signal to update UI sliders? 
        # We might need a new signal if algorithm changes global offset internally
        # Let's emit 'update_centroid_signal' or a new one?
        # A new one is cleaner.
        
    def stop(self):
        self._run_flag = False
        self.wait()
        if self.cap:
            self.cap.release()
            
    def switch_camera(self, camera_id):
        """Switch to a different camera. Thread-safe - triggers reinitialization in run loop."""
        self.camera_id = camera_id
        if self.cap:
            self.cap.release()
            self.cap = None
        self._camera_needs_init = True

    # set_detection_active removed (moved to plugin)
