from PySide6.QtWidgets import (QLabel, QPushButton, QCheckBox, QVBoxLayout, QWidget)
from ui.widgets import CollapsibleSection, SliderSpinbox

class DetectionPanel(CollapsibleSection):
    """
    Panel for controlling Auto Detection parameters.
    """
    def __init__(self, plugin, parent=None):
        super().__init__("Auto Detection", parent)
        self.plugin = plugin
        self.manager = plugin.manager
        
        # Enable Toggle
        self.chk_enable = QCheckBox("Enable Live Detection")
        self.chk_enable.setChecked(False)
        self.chk_enable.toggled.connect(self.toggle_enable)
        self.addWidget(self.chk_enable)
        
        # --- Presets ---
        self.addSpacing(10)
        self.layout_presets = QVBoxLayout()
        self.addWidget(QLabel("Presets:"))
        
        self.btn_preset_primary = QPushButton("Primary Mirror (Big)")
        self.btn_preset_primary.clicked.connect(self.apply_preset_primary)
        self.addWidget(self.btn_preset_primary)
        
        self.btn_preset_secondary = QPushButton("Secondary Mirror (Small)")
        self.btn_preset_secondary.clicked.connect(self.apply_preset_secondary)
        self.addWidget(self.btn_preset_secondary)
        
        # --- Expert Mode Toggle ---
        self.addSpacing(10)
        self.chk_expert = QCheckBox("Expert Settings")
        self.chk_expert.setChecked(False)
        self.chk_expert.toggled.connect(self.toggle_expert_mode)
        self.addWidget(self.chk_expert)
        
        # --- Advanced Container ---
        self.expert_widget = QWidget()
        self.expert_layout = QVBoxLayout(self.expert_widget)
        self.expert_layout.setContentsMargins(0, 0, 0, 0)
        self.addWidget(self.expert_widget)
        
        # Smoothing (Always visible or expert? Let's keep visible for now as it's useful)
        self.addWidget(QLabel("Smoothing (Frames):"))
        self.slider_smooth = SliderSpinbox(1, 30, self.manager.smoothing)
        self.slider_smooth.valueChanged.connect(lambda v: self.update_param("smoothing", v, "smoothing"))
        self.addWidget(self.slider_smooth)

        # --- Hough Parameters (Moved to Expert) ---
        self.hough_label = QLabel("Hough Parameters:")
        self.expert_layout.addWidget(self.hough_label)
        
        # DP (Inverse Ratio)
        self.expert_layout.addWidget(QLabel("Resolution (DP):"))
        self.slider_dp = SliderSpinbox(1.0, 3.0, self.manager.dp, step=0.1)
        self.slider_dp.valueChanged.connect(lambda v: self.update_param("hough_dp", v, "dp"))
        self.expert_layout.addWidget(self.slider_dp)
        
        # Min Dist
        self.expert_layout.addWidget(QLabel("Min Distance:"))
        self.slider_md = SliderSpinbox(10, 1000, self.manager.minDist)
        self.slider_md.valueChanged.connect(lambda v: self.update_param("hough_minDist", v, "minDist"))
        self.expert_layout.addWidget(self.slider_md)
        
        # Param 1 (Canny)
        self.expert_layout.addWidget(QLabel("Edge Thresh (Param1):"))
        self.slider_p1 = SliderSpinbox(10, 200, self.manager.param1)
        self.slider_p1.valueChanged.connect(lambda v: self.update_param("hough_param1", v, "param1"))
        self.expert_layout.addWidget(self.slider_p1)
        
        # Param 2 (Accumulator)
        self.expert_layout.addWidget(QLabel("Circle Thresh (Param2):"))
        self.slider_p2 = SliderSpinbox(10, 200, self.manager.param2)
        self.slider_p2.valueChanged.connect(lambda v: self.update_param("hough_param2", v, "param2"))
        self.expert_layout.addWidget(self.slider_p2)
        
        # Radii
        self.expert_layout.addWidget(QLabel("Min Radius:"))
        self.slider_minR = SliderSpinbox(5, 500, self.manager.minRadius)
        self.slider_minR.valueChanged.connect(lambda v: self.update_param("hough_minRadius", v, "minRadius"))
        self.expert_layout.addWidget(self.slider_minR)
        
        self.expert_layout.addWidget(QLabel("Max Radius:"))
        self.slider_maxR = SliderSpinbox(5, 1000, self.manager.maxRadius)
        self.slider_maxR.valueChanged.connect(lambda v: self.update_param("hough_maxRadius", v, "maxRadius"))
        self.expert_layout.addWidget(self.slider_maxR)
        
        # Blur
        self.expert_layout.addWidget(QLabel("Blur Size:"))
        self.slider_blur = SliderSpinbox(1, 21, self.manager.blur_size, step=2)
        self.slider_blur.valueChanged.connect(lambda v: self.update_param("blur_size", v, "blur_size"))
        self.expert_layout.addWidget(self.slider_blur)
        
        # Trigger initial visibility
        self.toggle_expert_mode(False)
        
        # Apply Button
        self.addSpacing(10)
        self.btn_apply = QPushButton("Apply to Overlays")
        self.btn_apply.setStyleSheet("background-color: #2a82da; color: white; padding: 5px;")
        self.btn_apply.clicked.connect(self.apply_to_overlays)
        self.addWidget(self.btn_apply)
        
        self.lbl_status = QLabel("")
        self.addWidget(self.lbl_status)

    def toggle_expert_mode(self, checked):
        self.expert_widget.setVisible(checked)
        
    def apply_preset_primary(self):
        """Set params for Primary Mirror (large, defined edge)."""
        self.slider_dp.setValue(1.5)
        self.slider_md.setValue(200)
        self.slider_p1.setValue(100)
        self.slider_p2.setValue(50) # Strict
        self.slider_minR.setValue(200)
        self.slider_maxR.setValue(600)
        self.slider_blur.setValue(5)
        self.slider_smooth.setValue(5)
        
    def apply_preset_secondary(self):
        """Set params for Secondary Mirror (medium)."""
        self.slider_dp.setValue(1.2)
        self.slider_md.setValue(100)
        self.slider_p1.setValue(60)
        self.slider_p2.setValue(40) 
        self.slider_minR.setValue(50)
        self.slider_maxR.setValue(250)
        self.slider_blur.setValue(7)
        self.slider_smooth.setValue(5)

    def toggle_enable(self, checked):
        self.manager.active = checked
        
    def update_param(self, setting_key, value, attr_name):
        # Update Manager attribute
        if attr_name == "blur_size":
            int_val = int(value)
            if int_val % 2 == 0: int_val += 1 # Ensure odd
            setattr(self.manager, attr_name, int_val)
            self.plugin.save_setting(setting_key, int_val)
            return

        setattr(self.manager, attr_name, value)
        self.plugin.save_setting(setting_key, value)
        
    def apply_to_overlays(self):
        count = self.manager.apply_detection_to_overlays()
        if count is not None:
            self.lbl_status.setText(f"Added {count} overlays")
            self.lbl_status.setStyleSheet("color: #00ff00;")
        else:
             self.lbl_status.setText("Error applying overlays")
