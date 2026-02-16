from core.plugin_interface import PluginInterface
from .calibration_manager import CalibrationManager
from .panel import CalibrationPanel

class LensCalibrationPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "lens_calibration"

    @property
    def display_name(self) -> str:
        return "Lens Calibration"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, context) -> bool:
        self.context = context
        # Initialize Manager
        # We use managed settings now, so we pass self (plugin)
        self.manager = CalibrationManager(self)
        
        # We need access to the CameraThread to hook UNDISTORT?
        # Actually, process_frame is called by thread. So we apply it there.
        return True

    def get_sidebar_panel(self):
        return CalibrationPanel(self)

    def process_frame(self, frame, metadata):
        # This is where the magic happens!
        if self.manager.active:
            return self.manager.get_undistorted_frame(frame)
        return frame
