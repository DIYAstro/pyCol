"""
Camera Panel UI Component.

Provides camera selection and image adjustment controls.
"""
import os
import sys
import cv2
import cv2
from PySide6.QtWidgets import QLabel, QComboBox, QCheckBox, QHBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaDevices
from ui.widgets import CollapsibleSection, SliderSpinbox, TwoStageSlider
from core import get_logger

_logger = get_logger('camera')


class CameraPanel(CollapsibleSection):
    """
    Panel for camera settings in the sidebar.
    
    Provides controls for:
    - Camera selection (auto-detected via Qt or OpenCV)
    - Exposure adjustment (log2 scale)
    - Focus control (0 = Auto)
    - Digital zoom
    - Contrast and brightness adjustments
    
    Args:
        camera_thread: The CameraThread instance to control.
        main_window_redirect: Optional reference to main window for callbacks.
        parent: Optional parent widget.
    """
    
    def __init__(self, camera_thread, main_window_redirect=None, parent=None):
        super().__init__("Camera Settings", parent)
        self.thread = camera_thread
        self.main_window = main_window_redirect
        
        self.lbl_cam_select = QLabel("Select Camera:")
        self.combo_camera = QComboBox()
        
        # Auto-detect cameras (moved from main.py)
        cameras = QMediaDevices.videoInputs()
        if not cameras:
            # Fallback: Probe OpenCV indices
            _logger.debug("No Qt Media Devices found, probing OpenCV indices")
            
            # Suppress OpenCV warnings during probing
            os.environ["OPENCV_LOG_LEVEL"] = "OFF"
            
            # Try to open indices 0-5 to find working cameras
            for i in range(5):
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.combo_camera.addItem(f"Camera {i} (OpenCV)", i)
                    cap.release()
            
            if self.combo_camera.count() == 0:
                 self.combo_camera.addItem("No Camera Found", -1)
        else:
            for i, cam_device in enumerate(cameras):
                label = cam_device.description()
                self.combo_camera.addItem(label, i)
        
        self.combo_camera.currentIndexChanged.connect(self.change_camera)
        
        # Camera Info Label (shows active resolution + format)
        self.lbl_camera_info = QLabel("")
        self.lbl_camera_info.setStyleSheet("color: gray; font-size: 11px;")
        
        # Exposure: Integer -13 to 0
        # Exposure: Log2 scale (-13.0 to 0.0)
        self.lbl_exposure = QLabel("Exposure (Log2):")
        # Allow 0.1 steps
        self.slider_exposure = SliderSpinbox(-13.0, 0.0, -5.0, decimals=1, step=0.1)
        self.slider_exposure.valueChanged.connect(self.update_exposure)
        
        # Focus: 0.0 to 1000.0 (Manual) - Two-Stage Slider
        self.lbl_focus = QLabel("Focus:")
        self.slider_focus = TwoStageSlider(
            min_val=0,
            max_val=1000,
            default_val=0,
            coarse_step=100,
            fine_range=50
        )
        self.slider_focus.valueChanged.connect(self.update_focus)
        
        # Zoom: Decimal 1.0 to 10.0
        self.lbl_zoom = QLabel("Digital Zoom:")
        self.slider_zoom = SliderSpinbox(1.0, 10.0, 1.0, decimals=1)
        self.slider_zoom.valueChanged.connect(self.update_zoom)
        
        # Contrast: Decimal 0.5 to 3.0
        self.lbl_contrast = QLabel("Contrast:")
        self.slider_contrast = SliderSpinbox(0.5, 3.0, 1.0, decimals=1)
        self.slider_contrast.valueChanged.connect(self.update_contrast)

        # Brightness: -100.0 to 100.0
        self.lbl_brightness = QLabel("Brightness:")
        self.slider_brightness = SliderSpinbox(-100.0, 100.0, 0.0, decimals=1, step=0.1)
        self.slider_brightness.valueChanged.connect(self.update_brightness)
        
        # Saturation: Decimal 0.0 to 3.0
        self.lbl_saturation = QLabel("Saturation:")
        self.slider_saturation = SliderSpinbox(0.0, 3.0, 1.0, decimals=1)
        self.slider_saturation.valueChanged.connect(self.update_saturation)
        self.lbl_saturation = QLabel("Saturation:")
        self.slider_saturation = SliderSpinbox(0.0, 3.0, 1.0, decimals=1)
        self.slider_saturation.valueChanged.connect(self.update_saturation)
        
        # Mirror / Flip Controls
        self.layout_flip = QHBoxLayout()
        self.check_flip_h = QCheckBox("Flip H ↔")
        self.check_flip_v = QCheckBox("Flip V ↕")
        self.check_flip_h.stateChanged.connect(self.update_flip_h)
        self.check_flip_v.stateChanged.connect(self.update_flip_v)
        self.layout_flip.addWidget(self.check_flip_h)
        self.layout_flip.addWidget(self.check_flip_v)
        
        # Reset Button
        self.btn_reset = QPushButton("Reset Camera Settings")
        self.btn_reset.clicked.connect(self.reset_camera_settings)
        
        # Add widgets to content layout (layout inherited from CollapsibleSection)
        self.addWidget(self.lbl_cam_select)
        self.addWidget(self.combo_camera)
        self.addWidget(self.lbl_camera_info)
        self.addWidget(self.lbl_exposure)
        self.addWidget(self.slider_exposure)
        self.addWidget(self.lbl_focus)
        self.addWidget(self.slider_focus)
        self.addWidget(self.lbl_zoom)
        self.addWidget(self.slider_zoom)
        self.addWidget(self.lbl_contrast)
        self.addWidget(self.slider_contrast)
        self.addWidget(self.lbl_brightness)
        self.addWidget(self.slider_brightness)
        self.addWidget(self.lbl_saturation)
        self.addWidget(self.slider_saturation)
        
        # Create a container widget for flip layout to add it to main layout
        container = QWidget()
        container.setLayout(self.layout_flip)
        self.addWidget(container)
        self.addWidget(self.btn_reset)
        
        self.addStretch(1)
        
    def change_camera(self, index: int):
        """Switch to a different camera by combo box index."""
        if index >= 0:
            cam_idx = self.combo_camera.itemData(index)
            if cam_idx != -1:
                self.thread.switch_camera(cam_idx)

    def update_camera_info(self, info: str):
        """Update the camera info label with active resolution + format."""
        self.lbl_camera_info.setText(f"Active: {info}")

    def update_exposure(self, val: float):
        """Update camera exposure setting."""
        self.thread.set_exposure(float(val))
        
    def update_focus(self, val: float):
        """Update camera focus setting (0 = Auto)."""
        self.thread.set_focus(float(val))
        
    def update_zoom(self, val: float):
        """Update digital zoom level."""
        self.thread.set_zoom(val)

    def update_contrast(self, val: float):
        """Update image contrast."""
        self.thread.set_contrast(val)

    def update_brightness(self, val: float):
        """Update image brightness."""
        self.thread.set_brightness(float(val))

    def update_capabilities(self, caps: dict):
        """Update UI based on camera capabilities."""
        # Focus
        has_focus = caps.get('focus', False)
        self.lbl_focus.setEnabled(has_focus)
        self.slider_focus.setEnabled(has_focus)
        if not has_focus:
            self.slider_focus.setToolTip("Not supported by this camera")
        else:
            self.slider_focus.setToolTip("Adjust camera focus")

        # Exposure
        has_exposure = caps.get('exposure', False)
        self.slider_exposure.setEnabled(has_exposure)
        if not has_exposure:
            self.slider_exposure.setToolTip("Not supported by this camera")
        else:
            self.slider_exposure.setToolTip("Adjust camera exposure")

    def update_saturation(self, val: float):
        """Update image saturation."""
        self.thread.set_saturation(val)

    def update_flip_h(self, state):
        """Update horizontal flip."""
        self.thread.set_flip_h(bool(state))
        
    def update_flip_v(self, state):
        """Update vertical flip."""
        self.thread.set_flip_v(bool(state))
        
    def reset_camera_settings(self):
        """Reset all camera settings to default values."""
        # Reset sliders to default values
        self.slider_exposure.setValue(-5.0)
        self.slider_focus.setValue(0.0)
        self.slider_zoom.setValue(1.0)
        self.slider_contrast.setValue(1.0)
        self.slider_brightness.setValue(0.0)
        self.slider_saturation.setValue(1.0)
        
        # Reset flip checkboxes
        self.check_flip_h.setChecked(False)
        self.check_flip_v.setChecked(False)
        
        _logger.info("Camera settings reset to defaults")
