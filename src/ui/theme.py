"""
Dark theme setup for the application.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

def get_dark_palette():
    """Create and return a dark color palette."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    return palette

def get_dark_stylesheet():
    """Return the dark stylesheet for controls."""
    return """
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QGroupBox {
            border: 1px solid #3A3A3A;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            color: #E0E0E0;
        }
        QSlider::groove:horizontal {
            border: 1px solid #3A3A3A;
            height: 8px;
            background: #202020;
            margin: 2px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #2a82da;
            border: 1px solid #2a82da;
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        QListWidget {
            background-color: #202020;
            border: 1px solid #3A3A3A;
            border-radius: 4px;
        }
    """

def apply_dark_theme(app):
    """Apply dark theme to the application."""
    app.setStyle("Fusion")
    app.setPalette(get_dark_palette())
    app.setStyleSheet(get_dark_stylesheet())
