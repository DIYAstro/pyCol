import json
import os
import logging

# Get logger - use basic logging since this module loads before init_logging
_logger = logging.getLogger('settings')
from utils import get_app_data_path

class SettingsManager:
    def __init__(self, app_name="pyCol", settings_file=None):
        if settings_file:
            self.config_file = settings_file
            self.config_dir = os.path.dirname(settings_file)
        else:
            # Use unified helper
            self.config_dir = get_app_data_path()
            self.config_file = os.path.join(self.config_dir, "settings.json")
            
        self.profiles_dir = os.path.join(self.config_dir, "profiles")
        self._ensure_config_dir()
        
    def _ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
                _logger.debug(f"Created config dir: {self.config_dir}")
            except Exception as e:
                _logger.error(f"Error creating config dir: {e}")
                
        if not os.path.exists(self.profiles_dir):
            try:
                os.makedirs(self.profiles_dir)
                _logger.debug(f"Created profiles dir: {self.profiles_dir}")
            except Exception as e:
                 _logger.error(f"Error creating profiles dir: {e}")

        # Ensure plugins dir exists for new architecture
        self.plugins_dir = os.path.join(self.config_dir, "plugins")
        if not os.path.exists(self.plugins_dir):
            try:
                os.makedirs(self.plugins_dir)
                _logger.debug(f"Created plugins dir: {self.plugins_dir}")
            except Exception as e:
                 _logger.error(f"Error creating plugins dir: {e}")
                
    def load_settings(self):
        if not os.path.exists(self.config_file):
            _logger.debug("Settings file does not exist, using defaults")
            return {}
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                _logger.debug(f"Loaded settings: {len(data)} keys")
                return data
        except Exception as e:
            _logger.error(f"Error loading settings: {e}")
            return {}
            
    def save_settings(self, data):
        try:
             # Clean up: Don't save 'profiles' into global settings anymore
             if "profiles" in data:
                 del data["profiles"]

             # Clean up: Don't save 'plugins' into global settings (moved to separate files)
             if "plugins" in data:
                 del data["plugins"]
                 
             # Preserve 'default_profile' from disk if not present in data
             # This prevents old in-memory snapshots (MainWindow.settings) from overwriting
             # a default profile set via ConfigPanel interactions.
             if "default_profile" not in data:
                 disk_data = self.load_settings()
                 if "default_profile" in disk_data:
                     data["default_profile"] = disk_data["default_profile"]
                     
             with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
             _logger.debug(f"Settings saved to {self.config_file}")
        except Exception as e:
            _logger.error(f"Error saving settings: {e}")

    # Profile Management
    def get_profiles(self):
        """Returns a dict of all saved profiles {name: path}."""
        profiles = {}
        if not os.path.exists(self.profiles_dir):
            return profiles
            
        for filename in os.listdir(self.profiles_dir):
            if filename.lower().endswith(".json"):
                name = os.path.splitext(filename)[0]
                profiles[name] = os.path.join(self.profiles_dir, filename)
        return profiles

    def save_profile(self, name, profile_data):
        """Save a specific configuration state as a named profile file."""
        # Sanitize filename (basic)
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_name:
             safe_name = "default_profile"
        
        path = os.path.join(self.profiles_dir, f"{safe_name}.json")
        try:
            with open(path, 'w') as f:
                json.dump(profile_data, f, indent=4)
            _logger.info(f"Profile '{safe_name}' saved to {path}")
        except Exception as e:
            _logger.error(f"Failed to save profile {name}: {e}")

    def load_profile(self, name):
        """Load a specific profile by name."""
        path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            _logger.error(f"Error loading profile {name}: {e}")
            return None

    def delete_profile(self, name):
        """Delete a named profile file."""
        path = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                _logger.info(f"Profile '{name}' deleted")
                
                # If deleted profile was default, unset it
                if self.get_default_profile() == name:
                    self.unset_default_profile()
                    
            except Exception as e:
                _logger.error(f"Error deleting profile {name}: {e}")

    def rename_profile(self, old_name, new_name):
        """Rename a profile file."""
        if old_name == new_name:
            return True
        
        old_path = os.path.join(self.profiles_dir, f"{old_name}.json")
        new_path = os.path.join(self.profiles_dir, f"{new_name}.json")
        
        if not os.path.exists(old_path):
             _logger.error(f"Cannot rename: {old_path} not found")
             return False
             
        if os.path.exists(new_path):
             _logger.error(f"Cannot rename: {new_path} already exists")
             return False
             
        try:
            os.rename(old_path, new_path)
            _logger.info(f"Renamed profile '{old_name}' -> '{new_name}'")
            
            # If renamed profile was default, update it
            if self.get_default_profile() == old_name:
                self.set_default_profile(new_name)
                
            return True
        except Exception as e:
            _logger.error(f"Rename failed: {e}")
            return False

    def set_default_profile(self, name):
        """Set a profile as the default to load on startup."""
        data = self.load_settings()
        data["default_profile"] = name
        self._write_to_file(data)
        _logger.info(f"Default profile set to '{name}'")
        
    def get_default_profile(self):
        """Get the name of the default profile (or None)."""
        data = self.load_settings()
        # Ensure we return None if key missing or JSON null
        return data.get("default_profile") 
        
    def unset_default_profile(self):
        """Unset the default profile."""
        data = self.load_settings()
        if "default_profile" in data:
            del data["default_profile"]
            self._write_to_file(data)
            _logger.info("Default profile unset")

    def _write_to_file(self, data):
        """Helper to write data to disk."""
        try:
             # Preserve 'default_profile' re-read logic or similar if needed?
             # Actually _write_to_file is used by set_default_profile directly on loaded data
             # which is fine.
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            _logger.error(f"Error writing settings: {e}")

    # Plugin Settings Management (New: Individual Files)
    def load_plugin_settings(self, plugin_name):
        """Load active settings for a specific plugin from its JSON file."""
        # Sanitize name
        safe_name = "".join([c for c in plugin_name if c.isalnum() or c in ('-', '_')]).strip()
        path = os.path.join(self.plugins_dir, f"{safe_name}.json")
        
        if not os.path.exists(path):
            return {}
            
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            _logger.error(f"Error loading settings for plugin {plugin_name}: {e}")
            return {}

    def save_plugin_settings(self, plugin_name, data):
        """Save settings for a specific plugin to its JSON file."""
        safe_name = "".join([c for c in plugin_name if c.isalnum() or c in ('-', '_')]).strip()
        path = os.path.join(self.plugins_dir, f"{safe_name}.json")
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            # _logger.debug(f"Saved settings for plugin {plugin_name}")
        except Exception as e:
             _logger.error(f"Error saving settings for plugin {plugin_name}: {e}")

    def get_plugin_setting(self, plugin_name, key, default=None):
        """
        Get a setting for a specific plugin.
        Now redirects to individual file loading.
        Efficiency note: Loading file on every get() is slow? 
        Plugins usually cache their settings in memory. This is mostly for init.
        """
        data = self.load_plugin_settings(plugin_name)
        return data.get(key, default)

    def set_plugin_setting(self, plugin_name, key, value):
        """Save a specific plugin setting to its individual file."""
        data = self.load_plugin_settings(plugin_name)
        data[key] = value
        self.save_plugin_settings(plugin_name, data)

