#!/usr/bin/env python3
"""
pyCol - Optical Collimation Tool

Application entrypoint.
"""
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import apply_dark_theme


def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
