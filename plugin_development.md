# pyCol Plugin Development Guide

This guide explains how to create plugins for **pyCol** to extend its functionality.

## 1. Plugin Structure

Plugins are Python packages located in:
*   **Built-in:** `src/plugins/`
*   **User (External):** `%LOCALAPPDATA%/pyCol/plugins/` (Windows) or `~/.local/share/pyCol/plugins/` (Linux)

A minimal plugin folder looks like this:
```text
my_plugin/
├── __init__.py      # Entry point (Required)
├── manager.py       # Logic (Optional but recommended)
└── panel.py         # UI (Optional)
```

## 2. The `__init__.py` Entry Point

Every plugin **must** implement a class that inherits from `PluginInterface` in its `__init__.py`.

```python
from core.plugin_interface import PluginInterface
from .manager import MyManager
from .panel import MyPanel

class MyPlugin(PluginInterface):
    @property
    def name(self) -> str:
        """Unique internal ID (snake_case)."""
        return "my_awesome_plugin"

    @property
    def display_name(self) -> str:
        """User-facing name."""
        return "My Awesome Plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, context) -> bool:
        """
        Called on startup.
        'context' is a dictionary with access to core systems.
        """
        self.context = context
        # Example: Access Camera Thread
        # self.camera = context.get('camera_thread')
        
        self.manager = MyManager(context)
        return True

    def get_sidebar_panel(self):
        """Return a QWidget to show in the sidebar (optional)."""
        return MyPanel(self)

    def process_frame(self, frame, metadata):
        """
        Real-time frame processing hook.
        Return modified frame or None to do nothing.
        """
        # output_frame = self.manager.process(frame)
        # return output_frame
        return None
```

## 3. The `context` Dictionary

The `initialize` method receives a `context` dictionary. This is your gateway to the pyCol core.

| Key | Type | Description |
| :--- | :--- | :--- |
| `'camera_thread'` | `CameraThread` | Access to camera controls, settings, and signals. |
| `'main_window'` | `MainWindow` | Reference to the main UI window. |
| `'settings_manager'` | `SettingsManager` | Access to load/save settings. |
| `'app_data_path'` | `str` | Path to the application data directory. |

### Common Actions via `camera_thread`

*   **Change Settings:** `thread.set_exposure(-5)`, `thread.set_zoom(2.0)`
*   **Signals:** `thread.change_pixmap_signal`, `thread.camera_error_signal`
*   **Global Offset:** `thread.set_global_offset_x(10.5)`

## 5. Storage & Settings (Managed)

Plugins should **not** manage their own files. Use the built-in settings API.
Data is stored automatically in `settings.json` (and handles Profiles!).

```python
# Save a value
self.save_setting("threshold", 120)

# Load a value (with default)
val = self.get_setting("threshold", 100)
```

## 4. UI Development (Qt / PySide6)

pyCol uses **PySide6** (Qt) for its UI.
Your sidebar panel should inherit from `ui.widgets.CollapsibleSection` or just be a `QWidget`.

```python
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout
from ui.widgets import CollapsibleSection

class MyPanel(CollapsibleSection):
    def __init__(self, plugin):
        super().__init__("My Plugin", parent=None)
        self.plugin = plugin
        
        lbl = QLabel("Hello World")
        btn = QPushButton("Click Me")
        
        self.addWidget(lbl)
        self.addWidget(btn)
```

## 6. Deployment

To install a plugin, simply copy the folder to the user's plugin directory:
*   **Windows:** press `Win+R` -> `%LOCALAPPDATA%\pyCol\plugins`

The `PluginManager` will automatically discover and load it on the next start.
