"""
Settings Panel UI Component.

Provides application settings including logging configuration.
"""
import os
import subprocess
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QSpinBox, QPushButton,
                               QGroupBox, QLineEdit, QCheckBox, QFileDialog)
from PySide6.QtCore import Qt
from ui.widgets import CollapsibleSection
from core import get_log_folder, set_log_level, set_rotation_settings

class SettingsPanel(CollapsibleSection):
    """
    Panel for application settings (logging, etc.).
    """
    
    def __init__(self, settings_manager, main_window, parent=None):
        super().__init__("Settings", parent)
        self.settings_manager = settings_manager
        self.main_window = main_window
        
        # --- Snapshot Group ---
        self.grp_snapshot = QGroupBox("Snapshots")
        self.layout_snap = QVBoxLayout(self.grp_snapshot)
        self.layout_snap.setSpacing(5)
        
        # Path
        self.layout_snap_path = QHBoxLayout()
        self.txt_snap_path = QLineEdit()
        self.txt_snap_path.setReadOnly(True) 
        self.btn_browse_snap = QPushButton("...")
        self.btn_browse_snap.setFixedWidth(30)
        self.btn_browse_snap.clicked.connect(self.browse_snapshot_path)
        self.layout_snap_path.addWidget(QLabel("Path:"))
        self.layout_snap_path.addWidget(self.txt_snap_path)
        self.layout_snap_path.addWidget(self.btn_browse_snap)
        self.layout_snap.addLayout(self.layout_snap_path)
        
        # Subfolder Pattern
        self.layout_snap_subfolder = QHBoxLayout()
        self.txt_snap_subfolder = QLineEdit()
        self.txt_snap_subfolder.setPlaceholderText(r"{profile}/%Y-%m-%d")
        self.txt_snap_subfolder.setToolTip("Variables: {profile}\nTime Codes: %Y, %m, %d, %H, %M, %S\nLegacy: {date}, {year}")
        self.layout_snap_subfolder.addWidget(QLabel("Subfolder:"))
        self.layout_snap_subfolder.addWidget(self.txt_snap_subfolder)
        self.layout_snap.addLayout(self.layout_snap_subfolder)
        
        # Filename Pattern (formerly Prefix)
        self.layout_snap_prefix = QHBoxLayout()
        self.txt_snap_prefix = QLineEdit()
        self.txt_snap_prefix.setPlaceholderText("pyCol_%Y-%m-%d_%H-%M-%S")
        self.txt_snap_prefix.setToolTip("Full filename pattern. If no '%' is used, timestamp is appended automatically.")
        self.layout_snap_prefix.addWidget(QLabel("Filename:"))
        self.layout_snap_prefix.addWidget(self.txt_snap_prefix)
        self.layout_snap.addLayout(self.layout_snap_prefix)
        
        # --- Metadata Sub-Group ---
        self.grp_meta = QGroupBox("Burn-in Metadata")
        # self.grp_meta.setCheckable(True) # Redundant
        # self.grp_meta.setChecked(True)
        # self.grp_meta.toggled.connect(self.save_snapshot_settings)
        self.layout_meta = QVBoxLayout(self.grp_meta)
        self.layout_meta.setSpacing(5)
        
        # 1. Date/Time
        self.layout_meta_time = QHBoxLayout()
        self.chk_meta_time = QCheckBox("Date/Time")
        self.chk_meta_time.setChecked(True)
        self.chk_meta_time.stateChanged.connect(self.toggle_meta_fields)
        self.txt_meta_time_fmt = QLineEdit("%Y-%m-%d - %H:%M:%S")
        self.txt_meta_time_fmt.setPlaceholderText("Format (e.g. %Y-%m-%d)")
        self.txt_meta_time_fmt.textChanged.connect(self.save_snapshot_settings)
        self.layout_meta_time.addWidget(self.chk_meta_time)
        self.layout_meta_time.addWidget(self.txt_meta_time_fmt)
        self.layout_meta.addLayout(self.layout_meta_time)
        
        # 2. Profile
        self.chk_meta_profile = QCheckBox("Profile Name")
        self.chk_meta_profile.setChecked(True)
        self.chk_meta_profile.stateChanged.connect(self.save_snapshot_settings)
        self.layout_meta.addWidget(self.chk_meta_profile)
        
        # 3. Note
        self.layout_meta_note = QHBoxLayout()
        self.chk_meta_note = QCheckBox("Note")
        self.chk_meta_note.stateChanged.connect(self.toggle_meta_fields)
        self.txt_meta_note = QLineEdit()
        self.txt_meta_note.setPlaceholderText("Custom text...")
        self.txt_meta_note.textChanged.connect(self.save_snapshot_settings)
        self.layout_meta_note.addWidget(self.chk_meta_note)
        self.layout_meta_note.addWidget(self.txt_meta_note)
        self.layout_meta.addLayout(self.layout_meta_note)
        
        self.layout_snap.addWidget(self.grp_meta)
        
        self.addWidget(self.grp_snapshot)
        self.addSpacing(10)
        
        # --- Interaction Group ---
        self.grp_interaction = QGroupBox("Interaction")
        self.layout_interaction = QVBoxLayout(self.grp_interaction)
        self.layout_interaction.setSpacing(5)
        
        self.layout_space = QHBoxLayout()
        self.layout_space.addWidget(QLabel("Space Key Behavior:"))
        self.combo_space = QComboBox()
        self.combo_space.addItems(["Toggle (Press to On/Off)", "Hold (Press & Hold)"])
        self.combo_space.currentIndexChanged.connect(self.on_space_behavior_changed)
        self.layout_space.addWidget(self.combo_space, 1)
        self.layout_interaction.addLayout(self.layout_space)
        
        self.addWidget(self.grp_interaction)
        self.addSpacing(10)
        
        # --- Logging Group ---
        self.grp_logging = QGroupBox("Logging")
        self.layout_logging = QVBoxLayout(self.grp_logging)
        self.layout_logging.setContentsMargins(10, 15, 10, 10)
        self.layout_logging.setSpacing(8)
        
        # Log Level
        self.layout_level = QHBoxLayout()
        self.lbl_level = QLabel("Log Level:")
        self.combo_level = QComboBox()
        self.combo_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.combo_level.setCurrentText("INFO")
        self.combo_level.currentTextChanged.connect(self.on_level_changed)
        self.layout_level.addWidget(self.lbl_level)
        self.layout_level.addWidget(self.combo_level, 1)
        self.layout_logging.addLayout(self.layout_level)
        
        # Max File Size
        self.layout_size = QHBoxLayout()
        self.lbl_size = QLabel("Max File Size:")
        self.spin_size = QSpinBox()
        self.spin_size.setRange(1, 50)
        self.spin_size.setValue(5)
        self.spin_size.setSuffix(" MB")
        self.spin_size.valueChanged.connect(self.on_rotation_changed)
        self.layout_size.addWidget(self.lbl_size)
        self.layout_size.addWidget(self.spin_size, 1)
        self.layout_logging.addLayout(self.layout_size)
        
        # Backup Count
        self.layout_backup = QHBoxLayout()
        self.lbl_backup = QLabel("Backup Files:")
        self.spin_backup = QSpinBox()
        self.spin_backup.setRange(1, 10)
        self.spin_backup.setValue(3)
        self.spin_backup.valueChanged.connect(self.on_rotation_changed)
        self.layout_backup.addWidget(self.lbl_backup)
        self.layout_backup.addWidget(self.spin_backup, 1)
        self.layout_logging.addLayout(self.layout_backup)
        
        # Open Log Folder Button
        self.btn_open_folder = QPushButton("📂 Open Log Folder")
        self.btn_open_folder.clicked.connect(self.open_log_folder)
        self.layout_logging.addWidget(self.btn_open_folder)
        
        self.addWidget(self.grp_logging)
        
        # Push content to top
        self.addStretch(1)
        
        # Load saved settings
        self.load_settings()
    
    def load_settings(self):
        """Load logging settings from settings manager."""
        settings = self.settings_manager.load_settings()
        
        log_level = settings.get('log_level', 'INFO')
        log_max_size = settings.get('log_max_size_mb', 5)
        log_backup_count = settings.get('log_backup_count', 3)
        
        snap_config = settings.get('snapshot', {})
        default_path = os.path.join(os.path.expanduser("~"), "Pictures", "pyCol")
        snap_path = snap_config.get('path', default_path)
        snap_prefix = snap_config.get('prefix', "pyCol_")
        snap_subfolder = snap_config.get('subfolder_pattern', "")
        
        # Handle new metadata structure
        # 'metadata' can be bool (legacy) or dict (new)
        raw_meta = snap_config.get('metadata', True)
        meta_cfg = {}
        
        if isinstance(raw_meta, bool):
             # Legacy migration
             meta_cfg = {'time': True, 'profile': True, 'note': False}
        elif isinstance(raw_meta, dict):
             meta_cfg = raw_meta
        else:
             # Default fallback
             meta_cfg = {'time': True, 'profile': True, 'note': False}
             
        # snap_meta_enabled = meta_cfg.get('enabled', True) # Removed
        snap_time = meta_cfg.get('time', True)
        snap_time_fmt = meta_cfg.get('time_fmt', "%Y-%m-%d - %H:%M:%S")
        snap_profile = meta_cfg.get('profile', True)
        snap_note = meta_cfg.get('note', False)
        snap_note_text = meta_cfg.get('note_text', "")
        
        # Interaction
        interaction_cfg = settings.get('interaction', {})
        space_behavior = interaction_cfg.get('space_behavior', 'toggle') # 'toggle' or 'hold'
        
        # Block signals
        self.txt_snap_prefix.blockSignals(True)
        self.txt_snap_subfolder.blockSignals(True)
        self.grp_meta.blockSignals(True)
        self.chk_meta_time.blockSignals(True)
        self.txt_meta_time_fmt.blockSignals(True)
        self.chk_meta_profile.blockSignals(True)
        self.chk_meta_note.blockSignals(True)
        self.txt_meta_note.blockSignals(True)
        self.combo_level.blockSignals(True)
        self.spin_size.blockSignals(True)
        self.spin_backup.blockSignals(True)
        self.combo_space.blockSignals(True)
        
        self.spin_size.setValue(log_max_size)
        self.spin_backup.setValue(log_backup_count)
        
        # Set Space Behavior
        idx = 0 if space_behavior == 'toggle' else 1
        self.combo_space.setCurrentIndex(idx)
        
        self.txt_snap_path.setText(snap_path)
        self.txt_snap_prefix.setText(snap_prefix)
        self.txt_snap_subfolder.setText(snap_subfolder)
        
        # Set Metadata UI
        # self.grp_meta.setChecked(snap_meta_enabled) # Removed
        self.chk_meta_time.setChecked(snap_time)
        self.txt_meta_time_fmt.setText(snap_time_fmt)
        self.chk_meta_profile.setChecked(snap_profile)
        self.chk_meta_note.setChecked(snap_note)
        self.txt_meta_note.setText(snap_note_text)
        
        self.toggle_meta_fields() # Set visibility based on checked state
        
        self.combo_level.blockSignals(False)
        self.txt_snap_prefix.blockSignals(False)
        self.txt_snap_subfolder.blockSignals(False)
        self.grp_meta.blockSignals(False)
        self.chk_meta_time.blockSignals(False)
        self.txt_meta_time_fmt.blockSignals(False)
        self.chk_meta_profile.blockSignals(False)
        self.chk_meta_note.blockSignals(False)
        self.txt_meta_note.blockSignals(False)
        self.spin_size.blockSignals(False)
        self.spin_backup.blockSignals(False)
        self.combo_space.blockSignals(False)
    
    def on_level_changed(self, level: str):
        """Handle log level change."""
        set_log_level(level)
        self.save_logging_settings()
    
    def on_rotation_changed(self):
        """Handle rotation settings change."""
        set_rotation_settings(self.spin_size.value(), self.spin_backup.value())
        self.save_logging_settings()
    
    def save_logging_settings(self):
        """Save current logging settings."""
        settings = self.settings_manager.load_settings()
        settings['log_level'] = self.combo_level.currentText()
        settings['log_max_size_mb'] = self.spin_size.value()
        settings['log_backup_count'] = self.spin_backup.value()
        self.settings_manager.save_settings(settings)

    def browse_snapshot_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Snapshot Folder", self.txt_snap_path.text())
        if folder:
            self.txt_snap_path.setText(folder)
            self.save_snapshot_settings()

    def toggle_meta_fields(self):
        """Enable/Disable format/text fields based on checkbox."""
        self.txt_meta_time_fmt.setEnabled(self.chk_meta_time.isChecked())
        self.txt_meta_note.setEnabled(self.chk_meta_note.isChecked())
        # Only save if signals are NOT blocked (means user interaction)
        if not self.chk_meta_time.signalsBlocked():
            self.save_snapshot_settings()

    def save_snapshot_settings(self):
        """Save snapshot configuration."""
        settings = self.settings_manager.load_settings()
        
        meta_cfg = {
            # 'enabled': self.grp_meta.isChecked(), # Removed
            'time': self.chk_meta_time.isChecked(),
            'time_fmt': self.txt_meta_time_fmt.text(),
            'profile': self.chk_meta_profile.isChecked(),
            'note': self.chk_meta_note.isChecked(),
            'note_text': self.txt_meta_note.text()
        }
        
        settings['snapshot'] = {
            'path': self.txt_snap_path.text(),
            'prefix': self.txt_snap_prefix.text(),
            'subfolder_pattern': self.txt_snap_subfolder.text(),
            'metadata': meta_cfg
        }
        self.settings_manager.save_settings(settings)
    
    def get_snapshot_settings(self):
        return {
            'path': self.txt_snap_path.text(),
            'prefix': self.txt_snap_prefix.text(),
            'subfolder_pattern': self.txt_snap_subfolder.text(),
            # Return full config dict for CameraThread
            'metadata': {
                # 'enabled': self.grp_meta.isChecked(), # Removed
                'time': self.chk_meta_time.isChecked(),
                'time_fmt': self.txt_meta_time_fmt.text(),
                'profile': self.chk_meta_profile.isChecked(),
                'note': self.chk_meta_note.isChecked(),
                'note_text': self.txt_meta_note.text()
            }
        }
    
    def on_space_behavior_changed(self):
        self.save_interaction_settings()
        # Update Main Window live
        behavior = 'toggle' if self.combo_space.currentIndex() == 0 else 'hold'
        if hasattr(self.main_window, 'image_label'):
             self.main_window.image_label.set_pan_behavior(behavior)

    def save_interaction_settings(self):
        settings = self.settings_manager.load_settings()
        behavior = 'toggle' if self.combo_space.currentIndex() == 0 else 'hold'
        
        settings['interaction'] = {
            'space_behavior': behavior
        }
        self.settings_manager.save_settings(settings)

    def open_log_folder(self):
        """Open the log folder in the system file manager."""
        log_folder = get_log_folder()
        
        if sys.platform == 'win32':
            os.startfile(str(log_folder))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(log_folder)])
        else:
            subprocess.run(['xdg-open', str(log_folder)])
    
    def get_settings(self) -> dict:
        """Get current logging settings for saving."""
        return {
            'log_level': self.combo_level.currentText(),
            'log_max_size_mb': self.spin_size.value(),
            'log_backup_count': self.spin_backup.value(),
            'snapshot': self.get_snapshot_settings(),
            'interaction': {
                'space_behavior': 'toggle' if self.combo_space.currentIndex() == 0 else 'hold'
            }
        }
