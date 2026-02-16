"""
Config Panel UI Component.

Provides a manager for saving and loading named configuration profiles.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QListWidget, 
                               QListWidgetItem, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from ui.widgets import CollapsibleSection

class ConfigPanel(CollapsibleSection):
    """
    Panel for managing configuration profiles.
    """
    
    def __init__(self, settings_manager, main_window, parent=None):
        super().__init__("Configuration Profiles", parent)
        self.settings_manager = settings_manager
        self.main_window = main_window
        
        # UI Elements
        
        # 1. Save New Profile
        self.layout_save = QHBoxLayout()
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Profile Name (e.g. Telescope A)")
        self.btn_save = QPushButton("Save Config")
        self.btn_save.clicked.connect(self.save_profile)
        
        self.layout_save.addWidget(self.txt_name)
        self.layout_save.addWidget(self.btn_save)
        
        self.addLayout(self.layout_save)
        
        # 2. Profile List
        self.lbl_list = QLabel("Saved Profiles:")
        self.list_profiles = QListWidget()
        # Use global theme instead of manual stylesheet
        # self.list_profiles.setStyleSheet("background-color: #333; color: white;") 
        self.list_profiles.setFixedHeight(120) # Slightly taller than overlay list
        self.list_profiles.itemChanged.connect(self.on_item_renamed)
        
        self.addWidget(self.lbl_list)
        self.addWidget(self.list_profiles)
        
        # 3. Actions (Load / Delete)
        self.layout_actions = QHBoxLayout()
        self.btn_load = QPushButton("Load Selected")
        self.btn_load.clicked.connect(self.load_selected)
        # Highlight Load button slightly
        self.btn_load.setStyleSheet("background-color: #2a82da; color: white; font-weight: bold;") 
        
        self.btn_delete = QPushButton("Delete")
        # Keep delete red but subtle
        self.btn_delete.setStyleSheet("background-color: #502020; color: #ffaaaa;") 
        self.btn_delete.clicked.connect(self.delete_selected)
        
        self.layout_actions.addWidget(self.btn_load)
        self.layout_actions.addWidget(self.btn_delete)
        
        self.addLayout(self.layout_actions)
        
        # 4. Default Profile Actions
        self.layout_defaults = QHBoxLayout()
        self.btn_set_default = QPushButton("Set Default")
        self.btn_set_default.clicked.connect(self.set_selected_default)
        self.btn_unset_default = QPushButton("Unset Default")
        self.btn_unset_default.clicked.connect(self.unset_selected_default)
        
        self.layout_defaults.addWidget(self.btn_set_default)
        self.layout_defaults.addWidget(self.btn_unset_default)
        self.addLayout(self.layout_defaults)

        # Initial Load
        self.refresh_list()
        
    def refresh_list(self):
        self.list_profiles.clear()
        profiles = self.settings_manager.get_profiles()
        default_profile = self.settings_manager.get_default_profile()
        
        for name in profiles.keys():
            display_text = name
            if name == default_profile:
                display_text += " [Default]"
                
            item = QListWidgetItem(display_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            # Store original name in hidden data to detect changes AND to know real name
            item.setData(Qt.UserRole, name)
            self.list_profiles.addItem(item)
            
        # Enable/Disable Unset button based on if default is set
        self.btn_unset_default.setEnabled(default_profile is not None)
            
    def save_profile(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a profile name.")
            return
            
        # Check for overwrite
        profiles = self.settings_manager.get_profiles()
        if name in profiles:
            reply = QMessageBox.question(self, "Confirm Overwrite", 
                                       f"Profile '{name}' already exists.\nDo you want to overwrite it?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            
        # Get current state from MainWindow
        full_data = self.main_window.get_current_settings()
        
        # Filter: Only save telescope-specific settings to profile
        # Global settings (window, items, snapshot, interaction) are in settings.json
        # Add Plugin Settings
        plugin_settings = {}
        if self.main_window.plugin_manager:
            plugin_settings = self.main_window.plugin_manager.get_all_plugin_settings()
            
        profile_data = {
            "camera": full_data.get("camera", {}),
            "calibration": full_data.get("calibration", {}),
            "overlays": full_data.get("overlays", []),
            "plugins": plugin_settings
        }
        
        self.settings_manager.save_profile(name, profile_data)
        self.txt_name.clear()
        self.refresh_list()
        
        # Update active profile tracker
        self.main_window.set_active_profile(name)
        
        # Feedback
        self.btn_save.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.btn_save.setText("Save Config"))
        
    def load_selected(self):
        item = self.list_profiles.currentItem()
        if not item:
            return
            
        # Use stored name (UserRole) to avoid issues with [Default] suffix or edits
        name = item.data(Qt.UserRole)
        # Fallback if UserRole empty (shouldn't happen)
        if not name:
             name = item.text().replace(" [Default]", "").strip()
             
        data = self.settings_manager.load_profile(name)
        
        if data:
            # Important: Clear existing state first?
            # apply_settings in MainWindow should handle this.
            # But apply_settings usually ADDS overlays. We need a "reset" flag or logic.
            self.main_window.apply_settings(data, clear_existing=True)
            self.main_window.set_active_profile(name)
            
            # Apply Plugin Settings is now handled inside verify_settings (apply_settings)

            
            self.btn_load.setText("Loaded!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.btn_load.setText("Load Selected"))
            
    def delete_selected(self):
        item = self.list_profiles.currentItem()
        if not item:
            return
            
        name = item.data(Qt.UserRole)
        if not name:
             name = item.text().replace(" [Default]", "").strip()
        
        # Confirm
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Delete profile '{name}'?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                   
        if reply == QMessageBox.Yes:
            self.settings_manager.delete_profile(name)
            
            # Check if we deleted the currently active profile
            if self.main_window.active_profile_name == name:
                 self.main_window.set_active_profile("")
            
            self.refresh_list()
            
    def on_item_renamed(self, item):
        """Handle renaming of profiles via list edit."""
        # Clean up input in case user left the suffix
        new_name_raw = item.text().strip()
        new_name = new_name_raw.replace(" [Default]", "")
        
        old_name = item.data(Qt.UserRole)
        
        # Validation
        if not new_name:
            # Revert empty name
            item.setText(old_name)
            QMessageBox.warning(self, "Rename Failed", "Profile name cannot be empty.")
            return

        if new_name == old_name:
            return # No change
            
        # Check if exists (handled by manager too, but good for UI feedback)
        profiles = self.settings_manager.get_profiles()
        if new_name in profiles:
             item.setText(old_name) # Revert
             QMessageBox.warning(self, "Rename Failed", f"Profile '{new_name}' already exists.")
             return
             
        # Perform Rename
        success = self.settings_manager.rename_profile(old_name, new_name)
        if success:
             # Update hidden data to match new state
             item.setData(Qt.UserRole, new_name)
             
             # Re-apply suffix if it was default (refresh_list catches this cleanly too, but this avoids full list rebuild if we want)
             # Easier: Just refresh list to ensure consistency
             self.list_profiles.blockSignals(True)
             self.refresh_list()
             self.list_profiles.blockSignals(False)
             
             # If it was active, update active tracker
             if self.main_window.active_profile_name == old_name:
                 self.main_window.set_active_profile(new_name)
                 
             self.btn_save.setText("Renamed!")
             QTimer.singleShot(2000, lambda: self.btn_save.setText("Save Config"))
        else:
             self.list_profiles.blockSignals(True)
             self.refresh_list() # Revert on failure (easiest way to restore suffix logic)
             self.list_profiles.blockSignals(False)

    def set_selected_default(self):
        item = self.list_profiles.currentItem()
        if not item:
            return
        
        name = item.data(Qt.UserRole)
        self.settings_manager.set_default_profile(name)
        self.refresh_list()
        
    def unset_selected_default(self):
        self.settings_manager.unset_default_profile()
        self.refresh_list()
