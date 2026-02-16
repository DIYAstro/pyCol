from core.plugin_interface import PluginInterface
from .manager import AutoDetectionManager
from .panel import DetectionPanel

class AutoDetectionPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "auto_detection"

    @property
    def display_name(self) -> str:
        return "Auto Detection"

    @property
    def version(self) -> str:
        return "0.1.0"

    def initialize(self, context) -> bool:
        super().initialize(context)
        self.manager = AutoDetectionManager(self)
        return True

    def process_frame(self, frame, metadata):
        return self.manager.process_frame(frame)

    def on_settings_change(self, settings):
        """Update manager and UI when settings change."""
        # Update Manager
        if "hough_dp" in settings: self.manager.dp = float(settings["hough_dp"])
        if "hough_minDist" in settings: self.manager.minDist = float(settings["hough_minDist"])
        if "hough_param1" in settings: self.manager.param1 = float(settings["hough_param1"])
        if "hough_param2" in settings: self.manager.param2 = float(settings["hough_param2"])
        if "hough_minRadius" in settings: self.manager.minRadius = int(settings["hough_minRadius"])
        if "hough_maxRadius" in settings: self.manager.maxRadius = int(settings["hough_maxRadius"])
        if "blur_size" in settings: self.manager.blur_size = int(settings["blur_size"])
        if "smoothing" in settings: self.manager.smoothing = int(settings["smoothing"])
        
        # Update UI (if panel created)
        if hasattr(self, 'panel') and self.panel:
             p = self.panel
             p.slider_dp.blockSignals(True)
             if "hough_dp" in settings: p.slider_dp.setValue(self.manager.dp)
             p.slider_dp.blockSignals(False)

             p.slider_md.blockSignals(True)
             if "hough_minDist" in settings: p.slider_md.setValue(self.manager.minDist)
             p.slider_md.blockSignals(False)

             p.slider_p1.blockSignals(True)
             if "hough_param1" in settings: p.slider_p1.setValue(self.manager.param1)
             p.slider_p1.blockSignals(False)
             
             p.slider_p2.blockSignals(True)
             if "hough_param2" in settings: p.slider_p2.setValue(self.manager.param2)
             p.slider_p2.blockSignals(False)
             
             p.slider_minR.blockSignals(True)
             if "hough_minRadius" in settings: p.slider_minR.setValue(self.manager.minRadius)
             p.slider_minR.blockSignals(False)

             p.slider_maxR.blockSignals(True)
             if "hough_maxRadius" in settings: p.slider_maxR.setValue(self.manager.maxRadius)
             p.slider_maxR.blockSignals(False)
             
             p.slider_blur.blockSignals(True)
             if "blur_size" in settings: p.slider_blur.setValue(self.manager.blur_size)
             p.slider_blur.blockSignals(False)
             
             p.slider_smooth.blockSignals(True)
             if "smoothing" in settings: p.slider_smooth.setValue(self.manager.smoothing)
             p.slider_smooth.blockSignals(False)
        pass

    def get_sidebar_panel(self):
        self.panel = DetectionPanel(self) # Store reference
        return self.panel
