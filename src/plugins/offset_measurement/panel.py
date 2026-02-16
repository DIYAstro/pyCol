from PySide6.QtWidgets import (QLabel, QPushButton, QCheckBox, QVBoxLayout)
from PySide6.QtCore import Slot, QTimer
from ui.widgets import CollapsibleSection, SliderSpinbox

class OffsetPanel(CollapsibleSection):
    """
    Panel for Offset Measurement plugin.
    Replaces the old MeasurePanel.
    """
    def __init__(self, plugin, parent=None):
        super().__init__("Offset Measurement", parent)
        self.plugin = plugin
        self.manager = plugin.manager
        
        # -- UI Components --
        
        # Centroid Display
        self.lbl_centroid = QLabel("Centroid: -")
        
        # Enable Toggle
        self.chk_detection = QCheckBox("Enable Live Detection")
        self.chk_detection.setChecked(False)
        self.chk_detection.toggled.connect(self.toggle_detection)
        
        # Threshold
        self.lbl_threshold = QLabel("Threshold:")
        self.slider_threshold = SliderSpinbox(0, 255, self.manager.threshold, decimals=0)
        self.slider_threshold.valueChanged.connect(self.update_threshold)
        
        # Mode
        self.btn_invert = QPushButton("Mode: Laser (Bright)")
        self.btn_invert.setCheckable(True)
        self.btn_invert.setChecked(self.manager.invert)
        if self.manager.invert:
             self.btn_invert.setText("Mode: Dark Spot")
             
        self.btn_invert.clicked.connect(self.toggle_invert)
        
        # Auto-Cal
        self.btn_auto_cal = QPushButton("Start Auto-Calibration")
        self.btn_auto_cal.setStyleSheet("background-color: #2a2a2a; color: white; padding: 5px;")
        self.btn_auto_cal.setEnabled(self.manager.detection_active)
        self.btn_auto_cal.clicked.connect(self.toggle_auto_calibration)
        
        # Layout
        self.addWidget(self.lbl_centroid)
        self.addWidget(self.chk_detection)
        self.addWidget(self.lbl_threshold)
        self.addWidget(self.slider_threshold)
        self.addWidget(self.btn_invert)
        self.addSpacing(10)
        self.addWidget(self.btn_auto_cal)
        
        # Timer to update UI from manager state (async update)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100) # 10Hz UI update
        
    def update_ui(self):
        """Poll manager for latest centroid."""
        if self.manager.detection_active and self.manager.last_centroid:
            c = self.manager.last_centroid
            self.lbl_centroid.setText(f"Centroid: ({c[0]:.2f}, {c[1]:.2f})")
        elif not self.manager.detection_active:
            self.lbl_centroid.setText("Centroid: -")
            
    def toggle_detection(self, checked):
        self.manager.detection_active = checked
        self.btn_auto_cal.setEnabled(checked)
        
    def update_threshold(self, val):
        self.manager.threshold = int(val)
        self.plugin.save_setting("threshold", int(val))
        
    def toggle_invert(self, checked):
        self.manager.invert = checked
        self.plugin.save_setting("invert", checked)
        if checked:
            self.btn_invert.setText("Mode: Dark Spot")
        else:
            self.btn_invert.setText("Mode: Laser (Bright)")
            
    def toggle_auto_calibration(self):
        from core import get_logger
        _logger = get_logger('offset_panel')
        
        _logger.debug(f"toggle_auto_calibration called, is_calibrating={self.manager.is_calibrating}")
        
        if not self.manager.is_calibrating:
            _logger.info("Starting calibration")
            self.manager.start_calibration()
            self.btn_auto_cal.setText("Finish && Solve")
            self.btn_auto_cal.setStyleSheet("background-color: #008000; color: white; padding: 5px;")
        else:
            _logger.info("Stopping calibration")
            # We need frame dimensions for solve
            # Get from camera thread via context
            thread = self.plugin._context.get('camera_thread')
            w = 1920 # Default
            h = 1080
            if thread and thread.cap:
                w = int(thread.cap.get(3))  # CAP_PROP_FRAME_WIDTH
                h = int(thread.cap.get(4))  # CAP_PROP_FRAME_HEIGHT
                _logger.debug(f"Frame dimensions: {w}x{h}")
            
            center = self.manager.stop_calibration(w, h)
            _logger.debug(f"Calibration result: {center}")
            
            self.btn_auto_cal.setText("Start Auto-Calibration")
            self.btn_auto_cal.setStyleSheet("background-color: #2a2a2a; color: white; padding: 5px;")
            
            if center:
                 self.lbl_centroid.setText(f"Solved: ({center[0]:.2f}, {center[1]:.2f})")
                 _logger.info(f"Calibration solved: {center}")
            else:
                 self.lbl_centroid.setText("Failed (< 10 pts)")
                 _logger.warning("Calibration failed - insufficient points")
