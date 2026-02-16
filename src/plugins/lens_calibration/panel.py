from PySide6.QtWidgets import (QLabel, QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout)
from ui.widgets import CollapsibleSection
from .wizard import CalibrationWizard # Relative import

class CalibrationPanel(CollapsibleSection):
    """
    Panel for Lens Calibration controls.
    """
    def __init__(self, plugin, parent=None):
        super().__init__("Lens Calibration", parent)
        self.plugin = plugin
        self.manager = self.plugin.manager
        self.thread = self.plugin.context.get('camera_thread')
        
        # Status Label
        self.lbl_status = QLabel("Status: Checking...")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        
        # Toggle Undistort
        self.chk_undistort = QCheckBox("Enable Distortion Correction")
        self.chk_undistort.setChecked(self.manager.active)
        self.chk_undistort.toggled.connect(self.toggle_undistort)
        
        # Wizard Button
        self.btn_wizard = QPushButton("Open Calibration Wizard...")
        self.btn_wizard.setStyleSheet("background-color: #2a82da; color: white; padding: 5px;")
        self.btn_wizard.clicked.connect(self.open_wizard)
        
        # Layout
        self.addWidget(self.lbl_status)
        self.addWidget(self.chk_undistort)
        self.addSpacing(10)
        self.addWidget(self.btn_wizard)
        
        self.update_ui_state()

    def toggle_undistort(self, checked):
        self.manager.active = checked
        self.plugin.save_setting("active", checked)
        
    def open_wizard(self):
        if not self.thread:
            return # Camera not ready
            
        wizard = CalibrationWizard(self.thread, self.manager, self)
        if wizard.exec():
            # If accepted (finished), reload/update state
            self.manager.load_calibration() # Reload to be sure
            self.update_ui_state()
            # Also ensure active state is synced if wizard enabled it?
            # Wizard finish saves calibration, but doesn't auto-enable active.
            
    def update_ui_state(self):
        """Update UI based on manager state."""
        has_calib = (self.manager.camera_matrix is not None)
        
        if has_calib:
            self.lbl_status.setText("Status: ✅ Calibrated")
            self.lbl_status.setStyleSheet("color: #00ff00; font-weight: bold;")
            self.chk_undistort.setEnabled(True)
        else:
            self.lbl_status.setText("Status: ❌ Not Calibrated")
            self.lbl_status.setStyleSheet("color: #ff5555; font-weight: bold;")
            self.chk_undistort.setEnabled(False)
            self.chk_undistort.setChecked(False)
