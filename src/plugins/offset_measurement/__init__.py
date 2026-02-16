from core.plugin_interface import PluginInterface
from .offset_manager import OffsetManager
from .panel import OffsetPanel

class OffsetMeasurementPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "offset_measurement"

    @property
    def display_name(self) -> str:
        return "Offset Measurement"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, context) -> bool:
        super().initialize(context) # Important to init base for context
        self.manager = OffsetManager(self) 
        return True

    def process_frame(self, frame, metadata):
        return self.manager.process_frame(frame)

    def on_settings_change(self, settings):
        """Update manager and UI when settings change."""
        # Update Manager
        if "threshold" in settings:
            self.manager.threshold = int(settings["threshold"])
        if "invert" in settings:
            self.manager.invert = bool(settings["invert"])
            
        # Update UI (if panel created)
        # We need a reference to the panel. PluginInterface doesn't store it by default?
        # PluginManager stores the result of get_sidebar_panel in UI layout, 
        # but we can store it in self during creation.
        
        # However, to be safe, let's rely on manager state and panel polling?
        # OffsetPanel polls manager 10Hz for centroid, but not for slider values.
        # So we should push to panel.
        
        if hasattr(self, 'panel') and self.panel:
             self.panel.slider_threshold.blockSignals(True)
             self.panel.slider_threshold.setValue(self.manager.threshold)
             self.panel.slider_threshold.blockSignals(False)
             
             self.panel.btn_invert.blockSignals(True)
             self.panel.btn_invert.setChecked(self.manager.invert)
             if self.manager.invert:
                 self.panel.btn_invert.setText("Mode: Dark Spot")
             else:
                 self.panel.btn_invert.setText("Mode: Laser (Bright)")
             self.panel.btn_invert.blockSignals(False)
        pass

    def get_sidebar_panel(self):
        self.panel = OffsetPanel(self) # Store reference
        return self.panel
