import os
import sys
import importlib.util
import traceback
from typing import Dict, List, Any
from .plugin_interface import PluginInterface
from .logger import get_logger
from utils import get_app_data_path

_logger = get_logger('plugin_mgr')

class PluginManager:
    """
    Manages loading, unloading, and execution of plugins.
    Scans both built-in 'src/plugins' and User AppData plugins.
    """
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        # Add self to context so plugins can call back
        self.context['plugin_manager'] = self
        
        self.plugins: List[PluginInterface] = []
        self.active_plugins: List[PluginInterface] = []
        
        # Paths
        # 1. Built-in: ../../plugins relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.builtin_path = os.path.abspath(os.path.join(current_dir, '..', 'plugins'))
        
        # 2. User: %APPDATA%/pyCol/plugins
        self.user_path = os.path.join(get_app_data_path(), 'plugins')
        if not os.path.exists(self.user_path):
            os.makedirs(self.user_path)

    def load_plugins(self):
        """Discover and load all plugins."""
        self.plugins.clear()
        self.active_plugins.clear()
        
        _logger.info("Starting plugin discovery...")
        
        # Scan built-in
        _logger.info(f"Scanning Built-in Plugins: {self.builtin_path}")
        self._scan_directory(self.builtin_path, is_builtin=True)
        
        # Scan user
        _logger.info(f"Scanning User Plugins: {self.user_path}")
        self._scan_directory(self.user_path, is_builtin=False)
        
        _logger.info(f"Plugin load complete. Active: {len(self.active_plugins)}")

    def _scan_directory(self, base_path, is_builtin):
        if not os.path.exists(base_path): return
        
        for name in os.listdir(base_path):
            plugin_dir = os.path.join(base_path, name)
            if os.path.isdir(plugin_dir):
                # Expect __init__.py
                init_file = os.path.join(plugin_dir, '__init__.py')
                if os.path.exists(init_file):
                    self._load_plugin_from_dir(plugin_dir, name)

    def _load_plugin_from_dir(self, path, name):
        try:
            # Create a unique module name for external plugins to avoid conflicts
            # and ensure relative imports work.
            # We use 'pyCol_plugins.{name}' as the global module name.
            module_name = f"pyCol_plugins.{name}"
            
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(path, '__init__.py'))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                
                # IMPORTANT: Set __package__ to enable relative imports (from . import x)
                module.__package__ = module_name
                
                spec.loader.exec_module(module)
                
                # Find PluginInterface implementation
                found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, PluginInterface) and attr is not PluginInterface:
                        # Instantiate
                        try:
                            instance = attr()
                            if instance.initialize(self.context):
                                self.plugins.append(instance)
                                self.active_plugins.append(instance)
                                _logger.info(f"Initialized plugin: {instance.display_name} ({instance.version})")
                                found = True
                            else:
                                _logger.error(f"Plugin {name} failed to initialize")
                        except Exception as e:
                            _logger.error(f"Error initializing plugin {name}: {e}")
                            _logger.debug(traceback.format_exc())
                
                if not found:
                    _logger.warning(f"No PluginInterface implementation found in {name}")
                    
        except Exception as e:
            _logger.error(f"Failed to load plugin {name}: {e}")
            _logger.debug(traceback.format_exc())

    def get_sidebar_panels(self) -> List[Any]:
        """Collect UI panels from all active plugins."""
        panels = []
        for p in self.active_plugins:
            try:
                panel = p.get_sidebar_panel()
                if panel:
                    panels.append(panel)
            except Exception as e:
                _logger.error(f"Error getting panel from {p.name}: {e}")
        return panels

    def process_frame(self, frame):
        """Apply all plugin visual effects in order."""
        processed = frame
        for p in self.active_plugins:
            try:
                res = p.process_frame(processed, {})
                if res is not None:
                    processed = res
            except Exception as e:
                _logger.error(f"Error in {p.name}.process_frame: {e}")
                # Disable plugin? Or just log? For now log.
        return processed
        
    def get_plugin_setting(self, plugin_name, key, default=None):
        """Retrieve a specific setting for a plugin via SettingsManager."""
        return self.context['settings_manager'].get_plugin_setting(plugin_name, key, default)

    def save_plugin_setting(self, plugin_name, key, value):
        """Save a specific setting for a plugin via SettingsManager."""
        self.context['settings_manager'].set_plugin_setting(plugin_name, key, value)

    def get_all_plugin_settings(self) -> Dict[str, Dict]:
        """
        Collect current settings from all active plugins for Profile saving.
        Plugins should implement `get_settings()` in their interface.
        If not implemented, we assume they manage state via set_plugin_setting exclusively,
        and we might need to read from disk (global state) as a fallback?
        
        Better: We read the *current* global disk state for each active plugin.
        Because plugins write to disk immediately.
        So 'current state' == 'contents of plugins/<name>.json'.
        """
        all_settings = {}
        for p in self.active_plugins:
            # Load from their individual file
            settings = self.context['settings_manager'].load_plugin_settings(p.name)
            if settings:
                all_settings[p.name] = settings
        return all_settings

    def apply_profile_settings(self, profile_plugins_data: Dict[str, Dict]):
        """
        Apply settings from a loaded profile to all plugins.
        This overrides the current state with the profile's state.
        
        Note: This does NOT overwrite the global JSON files.
        Plugins will receive these values via method calls or re-init/reload if supported.
        
        Issue: Plugins usually read settings during init.
        We need a way to tell them "Here are new settings, please update".
        
        We will rely on `plugin.on_settings_change(new_settings)` if it exists,
        OR just update the file (risky/wrong for temporary profiles)
        OR (Simplest for now): 
        Just save these to the global JSONs?
            NO -> That makes the profile permanent.
            
        Better Strategy detailed in Plan:
            Plugins access settings via `get_plugin_setting`.
            We need an in-memory override layer in SettingsManager?
            Or we just tell plugins to update.
            
        Revised Strategy:
        1. We DO write to the global JSONs.
           Why? Because "Loading a Profile" implies "Setting the machine to this state".
           If I load "Telescope A", I want "Telescope A" settings to persist until I change them.
           This fits the user's workflow: "Das Default Profil würde dann die Global Settings überschreiben? Ja."
           
        So:
        1. Iterate profile_plugins_data.
        2. For each plugin, overwrite its global JSON.
        3. Notify plugin to reload (if method exists).
        """
        for plugin_name, data in profile_plugins_data.items():
            # 1. Overwrite global storage (Persist the profile application)
            self.context['settings_manager'].save_plugin_settings(plugin_name, data)
            
            # 2. Notify Plugin (Find instance)
            for p in self.active_plugins:
                if p.name == plugin_name:
                    # Optional: defined in PluginInterface?
                    if hasattr(p, 'on_settings_change'):
                        try:
                            p.on_settings_change(data)
                        except Exception as e:
                            _logger.error(f"Error notifying {p.name} of settings change: {e}")
                    elif hasattr(p, 'load_settings'):
                        # Fallback: Ask it to reload
                        try:
                             # Some plugins might not accept args, check signature?
                             # Unsafe. Let's assume standard interface from now on.
                             # For now, most plugins load in process_frame or init.
                             pass
                        except: pass
                    break
