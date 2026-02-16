"""
Utility helper functions.
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file.
    
    Works both in development and when packaged with PyInstaller.
    PyInstaller creates a temp folder and stores the path in sys._MEIPASS.
    
    Args:
        relative_path: Path relative to the application root.
        
    Returns:
        Absolute path to the resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_app_data_path() -> str:
    """
    Get the application data directory.
    Windows: %LOCALAPPDATA%/pyCol (Consistent with SettingsManager & Logger)
    Linux: ~/.local/share/pyCol
    """
    if sys.platform == "win32":
        # Use LOCALAPPDATA because Roaming is for roaming profiles, 
        # but our logger and settings currently use LOCALAPPDATA.
        # Consistency is key.
        base = os.environ.get("LOCALAPPDATA")
        if not base:
             # Fallback
             base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "pyCol")
    else:
        path = os.path.expanduser("~/.local/share/pyCol")
        
    if not os.path.exists(path):
        os.makedirs(path)
        
    return path
