"""
Zoom Image Label Widget.

A label that displays images and forwards scroll events for zoom control.
Supports panning with Space + mouse drag.
"""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter


class ZoomImageLabel(QLabel):
    """
    A QLabel that displays the camera feed and supports zoom via scroll.
    
    Features:
    - Mouse wheel zoom with cursor-centered focus
    - Space key toggles pan mode (Hand tool)
    - Centered image drawing and self-managed scaling
    
    Args:
        main_window: The main window that handles zoom scroll events.
    """
    
    pan_mode_changed = Signal(bool)
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Internal image storage
        self._image = None
        
        # Pan state
        self._panning = False
        self._pan_start = None
        self._space_held = False # Re-introduced for 'hold' behavior
        self._pan_mode_enabled = False
        self._pan_behavior = 'toggle' # 'toggle' or 'hold'
        
    def set_pan_behavior(self, behavior: str):
        """Set space key behavior: 'toggle' or 'hold'."""
        self._pan_behavior = behavior
        
    def set_pan_mode(self, enabled: bool):
        """Enable or disable persistent pan mode."""
        if self._pan_mode_enabled != enabled:
            self._pan_mode_enabled = enabled
            self.pan_mode_changed.emit(enabled)
            
            if enabled:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
                self._panning = False
            
    def set_image(self, image):
        """Set the current image to display."""
        self._image = image
        self.update() # Trigger repaint
        
    def _get_scaled_rect(self):
        """Calculate the rect of the scaled image within the widget."""
        if self._image is None or self._image.isNull():
            return None
            
        # Widget dimensions
        w = self.width()
        h = self.height()
        
        # Calculate scaled size ensuring aspect ratio
        img_size = self._image.size()
        scaled_size = img_size.scaled(w, h, Qt.KeepAspectRatio)
        
        # Calculate centered offsets
        x = (w - scaled_size.width()) // 2
        y = (h - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())

    def paintEvent(self, event):
        """Custom paint event to ensure image is always centered."""
        # Fill background ensures no artifacts
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        
        if self._image and not self._image.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            rect = self._get_scaled_rect()
            if rect:
                painter.drawImage(rect, self._image)
        
    def enterEvent(self, event):
        self.setFocus()
        super().enterEvent(event)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            if self._pan_behavior == 'toggle':
                self.set_pan_mode(not self._pan_mode_enabled)
            else: # hold
                self._space_held = True
                if not self._panning and not self._pan_mode_enabled:
                    self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)
        
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            if self._pan_behavior == 'hold':
                self._space_held = False
                # If persistent mode is NOT on, stop panning
                if not self._pan_mode_enabled:
                    self._panning = False
                    self.setCursor(Qt.ArrowCursor)
                # If persistent mode IS on, we stay in pan mode (cursor remains Hand)
        super().keyReleaseEvent(event)
    
    def mousePressEvent(self, event):
        # Allow pan if persistent mode enabled OR space is held
        if (self._pan_mode_enabled or self._space_held) and event.button() == Qt.LeftButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._panning:
            self._panning = False
            # Cursor revert logic
            if self._pan_mode_enabled or self._space_held:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start:
            current_pos = event.position()
            delta_x = current_pos.x() - self._pan_start.x()
            delta_y = current_pos.y() - self._pan_start.y()
            
            rect = self._get_scaled_rect()
            if rect and rect.width() > 0 and rect.height() > 0:
                zoom = self.main_window.thread.zoom_val
                # Normalize delta against displayed size
                rel_delta_x = -delta_x / rect.width() / zoom
                rel_delta_y = -delta_y / rect.height() / zoom
                
                self.main_window.handle_pan(rel_delta_x, rel_delta_y)
            
            self._pan_start = current_pos
        super().mouseMoveEvent(event)
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        cursor_pos = event.position()
        
        rect = self._get_scaled_rect()
        
        if rect:
            # Calculate cursor position relative to image rect (0-1)
            # Subtract offset (rect.x)
            rel_x = cursor_pos.x() - rect.x()
            rel_y = cursor_pos.y() - rect.y()
            
            img_x = rel_x / rect.width()
            img_y = rel_y / rect.height()
            
            # Clamp
            img_x = max(0, min(1, img_x))
            img_y = max(0, min(1, img_y))
        else:
            img_x = 0.5
            img_y = 0.5
        
        self.main_window.handle_zoom_scroll(delta, img_x, img_y)
