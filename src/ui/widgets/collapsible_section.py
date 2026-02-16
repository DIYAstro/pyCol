"""
Collapsible Section Widget.

A collapsible panel with a header button that can show/hide content.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Qt


class CollapsibleSection(QWidget):
    """
    A widget that provides a collapsible section with a styled header.
    
    The header acts as a toggle button - clicking it shows/hides the content area.
    Content can be added using addWidget(), addLayout(), or addSpacing() methods.
    
    Args:
        title: The text to display in the header button.
        parent: Optional parent widget.
    """
    
    def __init__(self, title: str, parent=None, accent_color: str = "#2a82da"):
        super().__init__(parent)
        self.title = title
        self.accent_color = accent_color
        
        # Prevent the section from expanding beyond its content
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setStyleSheet(f"""
            QPushButton {{
                text-align: left; 
                font-weight: bold; 
                font-size: 9pt;
                text-transform: uppercase;
                padding: 8px; 
                background-color: #383838; 
                border: 1px solid #454545;
                color: #FFFFFF;
                border-radius: 4px;
                border-left: 4px solid {self.accent_color};
            }}
            QPushButton:checked {{
                background-color: #404040;
                font-weight: bold;
                border-bottom: none;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QPushButton:hover {{
                background-color: #505050;
            }}
        """)
        self.toggle_button.toggled.connect(self._on_toggle)
        self.layout.addWidget(self.toggle_button)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Adjust margins for Linux scrollbars (often overlay or consume space on right)
        import sys
        right_margin = 20 if sys.platform == 'linux' else 5
        
        self.content_layout.setContentsMargins(5, 5, right_margin, 5)
        self.content_layout.setSpacing(5)
        self.layout.addWidget(self.content_area)
        
    def _on_toggle(self, checked: bool):
        """Handle toggle button state changes."""
        self.content_area.setVisible(checked)
        
    def addWidget(self, widget: QWidget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
        
    def addLayout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)
        
    def addSpacing(self, size: int):
        """Add spacing to the content area."""
        self.content_layout.addSpacing(size)

    def addStretch(self, stretch=0):
        """Add a stretchable space to the content area."""
        self.content_layout.addStretch(stretch)

    def is_expanded(self) -> bool:
        """Return True if the section is currently expanded."""
        return self.toggle_button.isChecked()

    def set_expanded(self, expanded: bool):
        """Set the expanded state of the section."""
        self.toggle_button.setChecked(expanded)
        
    def set_accent_color(self, color: str):
        """Update the accent color of the header border."""
        self.accent_color = color
        self.toggle_button.setStyleSheet(f"""
            QPushButton {{
                text-align: left; 
                font-weight: bold; 
                font-size: 9pt;
                text-transform: uppercase;
                padding: 8px; 
                background-color: #383838; 
                border: 1px solid #454545;
                color: #FFFFFF;
                border-radius: 4px;
                border-left: 4px solid {self.accent_color};
            }}
            QPushButton:checked {{
                background-color: #404040;
                font-weight: bold;
                border-bottom: none;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QPushButton:hover {{
                background-color: #505050;
            }}
        """)
