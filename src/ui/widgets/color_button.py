"""
Color Button Widget.

A small colored button used for color selection in palettes.
"""
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from typing import Tuple, Callable


class ColorButton(QPushButton):
    """
    A small circular button displaying a color.
    
    Used in color palettes to allow quick color selection.
    
    Args:
        color_hex: The color in hex format (e.g., "#FF0000").
        bgr_tuple: The color as a BGR tuple for OpenCV compatibility.
        callback: Function to call when the button is clicked, receives bgr_tuple.
    """
    
    def __init__(self, color_hex: str, bgr_tuple: Tuple[int, int, int], callback: Callable):
        super().__init__()
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color_hex)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                border: 1px solid #505050;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border: 2px solid #FFFFFF;
            }}
        """)
        self.clicked.connect(lambda: callback(bgr_tuple))
