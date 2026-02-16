from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class PluginInterface(ABC):
    """
    Base class for all pyCol plugins.
    Defines the lifecycle and integration points.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique internal name (e.g. 'lens_calibration')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """User facing name (e.g. 'Lens Calibration')."""
        pass
    
    @property
    def version(self) -> str:
        """Plugin version (default 0.1.0)."""
        return "0.1.0"

    @abstractmethod
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        Called when the plugin is loaded.
        context: Dictionary containing core references (e.g. 'camera_thread', 'main_window').
        Return True if initialization succeeded.
        """
        self._context = context
        return True

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a setting for this plugin.
        Delegates to PluginManager via context.
        """
        if hasattr(self, '_context') and 'plugin_manager' in self._context:
            return self._context['plugin_manager'].get_plugin_setting(self.name, key, default)
        return default

    def save_setting(self, key: str, value: Any):
        """
        Save a setting for this plugin.
        Delegates to PluginManager via context.
        """
        if hasattr(self, '_context') and 'plugin_manager' in self._context:
            self._context['plugin_manager'].save_plugin_setting(self.name, key, value)

    def shutdown(self):
        """Called when plugin is unloaded or app closes."""
        pass

    def get_sidebar_panel(self) -> Optional[Any]: # Returns QWidget or None
        """
        Return a QWidget to be added to the main sidebar.
        Return None if no UI is needed.
        """
        return None

    def process_frame(self, frame, metadata: Dict[str, Any]) -> Any: # Returns modified frame or None
        """
        Hook to process or modify the video frame.
        frame: numpy array (BGR).
        metadata: dict with frame info.
        Return the modified frame, or None to keep original.
        """
        return None

    def draw_overlay(self, painter, rect, metadata: Dict[str, Any]):
        """
        Hook to draw on the video widget/pixmap.
        painter: QPainter instance.
        rect: QRect of the target area.
        """
        pass

    def on_settings_change(self, settings: Dict[str, Any]):
        """
        Called when settings for this plugin are updated externally (e.g. profile load).
        Plugins should update their internal state and UI components here.
        APP RESTART NOT REQUIRED usually.
        """
        pass
