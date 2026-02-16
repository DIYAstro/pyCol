"""
Two-Stage Slider Widget with Range Indicator.

Provides coarse and fine adjustment controls with visual feedback.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QFrame, QMenu
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont


class RangeIndicator(QWidget):
    """
    Visual range indicator showing the full range with current zoom window highlighted.
    
    Clicking on the indicator jumps to that position.
    """
    
    clicked = Signal(int)  # Emits the clicked value
    favorite_clicked = Signal(int)  # Emits favorite value when star is clicked
    
    def __init__(self, min_val: int, max_val: int, coarse_step: int, fine_range: int, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.coarse_step = coarse_step
        self.fine_range = fine_range
        self.current_coarse = 0
        self.current_value = 0
        self.favorites = []  # List of favorite positions (max 4)
        
        # Drag tracking for interactive slider behavior
        self._dragging = False
        self._last_emitted_value = None
        
        # Track star positions for click detection (x, y, value, is_above)
        self._star_positions = []
        
        # Track hovered star for visual feedback
        self._hovered_star_value = None
        
        self.setMinimumHeight(65)  # Increased to accommodate stars above AND below bar
        self.setMaximumHeight(65)
        self.setMouseTracking(True)  # Enable mouse tracking for hover effects
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
    def set_values(self, coarse: int, value: int):
        """Update the displayed coarse position and exact value."""
        self.current_coarse = coarse
        self.current_value = value
        self.update()
        
    def paintEvent(self, event):
        """Draw the range indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background bar (full range)
        bar_height = 12
        bar_y = (height - bar_height) // 2
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(80, 80, 80))
        painter.drawRoundedRect(0, bar_y, width, bar_height, 4, 4)
        
        # Calculate zoom window position
        range_size = self.max_val - self.min_val
        window_min = max(self.min_val, self.current_coarse - self.fine_range)
        window_max = min(self.max_val, self.current_coarse + self.fine_range)
        
        # Draw zoom window highlight
        window_x = int((window_min - self.min_val) / range_size * width)
        window_w = int((window_max - window_min) / range_size * width)
        
        painter.setBrush(QColor(100, 150, 200, 180))
        painter.drawRoundedRect(window_x, bar_y, window_w, bar_height, 4, 4)
        
        # Draw current value marker
        value_x = int((self.current_value - self.min_val) / range_size * width)
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        painter.setBrush(QColor(255, 255, 0))
        painter.drawEllipse(value_x - 4, bar_y + bar_height // 2 - 4, 8, 8)
        
        # Draw tick marks for coarse steps
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for tick_val in range(self.min_val, self.max_val + 1, self.coarse_step):
            tick_x = int((tick_val - self.min_val) / range_size * width)
            painter.drawLine(tick_x, bar_y - 3, tick_x, bar_y + bar_height + 3)
        
        # Draw favorite stars with intelligent staggered placement
        # Clear previous positions
        self._star_positions = []
        
        # Determine staggered positions (auto-alternate when stars are too close)
        OVERLAP_THRESHOLD = 20  # pixels - if stars closer than this, stagger them
        draw_above = True  # Start with first star above
        
        for i, fav_value in enumerate(self.favorites):
            fav_x = int((fav_value - self.min_val) / range_size * width)
            
            # Check if this star would overlap with previous star
            if i > 0 and self._star_positions:
                prev_x, prev_y, prev_val, prev_above = self._star_positions[-1]
                distance = abs(fav_x - prev_x)
                
                if distance < OVERLAP_THRESHOLD:
                    # Too close! Alternate position (above/below)
                    draw_above = not prev_above
                else:
                    # Far enough - reset to default (above)
                    draw_above = True
            
            # Calculate Y position
            if draw_above:
                star_y = bar_y - 15  # Above bar
            else:
                star_y = bar_y + bar_height + 15  # Below bar
            
            # Check if this star is hovered
            is_hovered = (fav_value == self._hovered_star_value)
            
            # Draw glow effect if hovered (outer white/bright star)
            if is_hovered:
                self._draw_star(painter, fav_x, star_y, 11, glow=True)
            
            # Draw star (normal)
            self._draw_star(painter, fav_x, star_y, 8, glow=False)
            
            # Track position for click detection
            self._star_positions.append((fav_x, star_y, fav_value, draw_above))
        
    def _draw_star(self, painter: QPainter, x: int, y: int, size: int, glow: bool = False):
        """Draw a star at the given position.
        
        Args:
            x, y: Center position
            size: Radius of star
            glow: If True, draw as glow effect (white/bright, semi-transparent)
        """
        if glow:
            # Glow effect: bright white/yellow, semi-transparent
            painter.setPen(QPen(QColor(255, 255, 200, 180), 2))  # Bright, semi-transparent
            painter.setBrush(QColor(255, 255, 150, 100))  # Light glow
        else:
            # Normal star: gold
            painter.setPen(QPen(QColor(255, 215, 0), 1))  # Gold outline
            painter.setBrush(QColor(255, 215, 0))  # Gold fill
        
        # Simple 5-point star using polygon
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        import math
        
        points = []
        for i in range(10):
            angle = math.pi * 2 * i / 10 - math.pi / 2
            radius = size if i % 2 == 0 else size / 2.5
            px = x + radius * math.cos(angle)
            py = y + radius * math.sin(angle)
            points.append(QPointF(px, py))
        
        painter.drawPolygon(QPolygonF(points))
        
    def _get_favorite_at_position(self, x: int, y: int) -> int:
        """Get favorite value at click position (2D distance), or -1 if none."""
        import math
        
        # Use tracked star positions (includes Y coordinate)
        CLICK_RADIUS = 12  # pixels
        
        closest_fav = -1
        closest_dist = float('inf')
        
        for star_x, star_y, fav_value, is_above in self._star_positions:
            # Calculate 2D distance
            distance = math.sqrt((x - star_x)**2 + (y - star_y)**2)
            
            if distance <= CLICK_RADIUS and distance < closest_dist:
                closest_dist = distance
                closest_fav = fav_value
        
        return closest_fav
    
    def _show_context_menu(self, pos: QPoint):
        """Show context menu for adding/removing favorites."""
        menu = QMenu(self)
        
        # Check if clicked on a favorite
        fav_at_pos = self._get_favorite_at_position(pos.x(), pos.y())
        
        if fav_at_pos != -1:
            # Clicked on a favorite - offer to remove it
            action = menu.addAction(f"Remove Favorite ({fav_at_pos})")
            action.triggered.connect(lambda: self.remove_favorite(fav_at_pos))
        else:
            # Not on a favorite - offer to add current position
            if len(self.favorites) < 4:
                action = menu.addAction(f"⭐ Add Current Position ({self.current_value}) as Favorite")
                action.triggered.connect(lambda: self.add_favorite(self.current_value))
            else:
                action = menu.addAction("Maximum 4 favorites reached")
                action.setEnabled(False)
        
        menu.exec(self.mapToGlobal(pos))
    
    def add_favorite(self, value: int):
        """Add a favorite position."""
        if len(self.favorites) < 4 and value not in self.favorites:
            self.favorites.append(value)
            self.favorites.sort()
            self.update()
            
    def remove_favorite(self, value: int):
        """Remove a favorite position."""
        if value in self.favorites:
            self.favorites.remove(value)
            self.update()
            
    def set_favorites(self, favorites: list):
        """Set the list of favorites."""
        self.favorites = sorted(favorites[:4])  # Max 4
        self.update()
        
    def get_favorites(self) -> list:
        """Get the list of favorites."""
        return self.favorites.copy()
        
    def _value_from_position(self, x: int) -> int:
        """Calculate value from X position (continuous, not snapped)."""
        width = self.width()
        range_size = self.max_val - self.min_val
        click_ratio = max(0.0, min(1.0, x / width))  # Clamp to 0-1
        value = int(self.min_val + click_ratio * range_size)
        return max(self.min_val, min(self.max_val, value))
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle clicks on the indicator to jump to a position or start drag."""
        if not self.isEnabled():
            return
            
        if event.button() == Qt.LeftButton:
            x_pos = int(event.position().x())
            y_pos = int(event.position().y())
            
            # Check if clicked on a favorite star
            fav_at_pos = self._get_favorite_at_position(x_pos, y_pos)
            
            if fav_at_pos != -1:
                # Clicked on favorite - jump to it
                self.favorite_clicked.emit(fav_at_pos)
                self._last_emitted_value = fav_at_pos
                # Enable dragging so user can immediately drag after clicking favorite
                self._dragging = True
            else:
                # Normal click - calculate continuous value
                value = self._value_from_position(x_pos)
                
                # Emit signal and start drag
                self.clicked.emit(value)
                self._last_emitted_value = value
                self._dragging = True
                
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle drag to continuously update value and track hover state."""
        if not self.isEnabled():
            return
        
        x_pos = int(event.position().x())
        y_pos = int(event.position().y())
        
        # Check if hovering over a star (for glow effect)
        hovered_fav = self._get_favorite_at_position(x_pos, y_pos)
        if hovered_fav != self._hovered_star_value:
            self._hovered_star_value = hovered_fav
            self.update()  # Trigger repaint for glow effect
            
        if self._dragging:
            value = self._value_from_position(x_pos)
            
            # Only emit if value changed (avoid spamming)
            if value != self._last_emitted_value:
                self.clicked.emit(value)
                self._last_emitted_value = value
                
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end drag."""
        if event.button() == Qt.LeftButton:
            self._dragging = False
            
    def leaveEvent(self, event):
        """Handle mouse leaving widget - clear hover state."""
        if self._hovered_star_value is not None:
            self._hovered_star_value = None
            self.update()


class TwoStageSlider(QFrame):
    """
    Interactive slider with range indicator and fine adjustment.
    
    Features:
    - Interactive range indicator: Click/drag for coarse positioning with visual feedback
    - Fine slider: Small adjustments around current value
    - Favorites: Mark and quickly jump to favorite positions (max 4)
    - Visual range indicator showing current zoom window and value
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        default_val: Initial value
        coarse_step: Step size for visual tick marks (cosmetic only)
        fine_range: Range for fine slider (±fine_range around current value)
        parent: Parent widget
    """
    
    valueChanged = Signal(float)  # Emits the final combined value
    
    def __init__(self, min_val: int = 0, max_val: int = 1000, default_val: int = 0,
                 coarse_step: int = 100, fine_range: int = 50, parent=None):
        super().__init__(parent)
        
        self.min_val = min_val
        self.max_val = max_val
        self.coarse_step = coarse_step
        self.fine_range = fine_range
        
        self._syncing = False
        
        # Add visual frame for separation
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        # Style with subtle background
        self.setStyleSheet("""
            TwoStageSlider {
                background-color: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        # Value display
        value_layout = QHBoxLayout()
        self.lbl_value = QLabel(f"Value: {default_val}")
        value_layout.addWidget(self.lbl_value)
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # Range indicator
        self.indicator = RangeIndicator(min_val, max_val, coarse_step, fine_range)
        self.indicator.clicked.connect(self._on_indicator_clicked)
        self.indicator.favorite_clicked.connect(self._on_favorite_clicked)
        layout.addWidget(self.indicator)
        
        
        # Fine slider
        fine_layout = QHBoxLayout()
        fine_layout.addWidget(QLabel("Fine:"))
        self.slider_fine = QSlider(Qt.Horizontal)
        self.slider_fine.setRange(-fine_range, fine_range)
        self.slider_fine.setValue(0)
        self.slider_fine.valueChanged.connect(self._on_fine_changed)
        fine_layout.addWidget(self.slider_fine, 1)
        self.lbl_fine = QLabel(f"{0:+d}")
        self.lbl_fine.setFixedWidth(40)
        fine_layout.addWidget(self.lbl_fine)
        layout.addLayout(fine_layout)
        
        # Initialize
        self._current_coarse = default_val // coarse_step * coarse_step
        self._current_fine = default_val - self._current_coarse
        self._update_display()
        
    def _on_coarse_changed(self, coarse_value: int):
        """Handle coarse value change from range indicator."""
        if self._syncing:
            return
            
        self._current_coarse = coarse_value
        self._update_display()
        
    def _on_fine_changed(self, offset: int):
        """Handle fine slider change."""
        if self._syncing:
            return
            
        self._current_fine = offset
        self.lbl_fine.setText(f"{offset:+d}")
        self._update_display()
        
    def _on_indicator_clicked(self, coarse_value: int):
        """Handle click/drag on range indicator - set coarse value directly."""
        # Directly update coarse value (no slider to sync)
        self._on_coarse_changed(coarse_value)
        
    def _on_favorite_clicked(self, favorite_value: int):
        """Handle click on favorite star - jump to that value."""
        self.setValue(favorite_value)
        
    def _update_display(self):
        """Update value display and emit signal."""
        final_value = self._current_coarse + self._current_fine
        
        # Clamp to valid range
        final_value = max(self.min_val, min(self.max_val, final_value))
        
        self.lbl_value.setText(f"Value: {final_value}")
        self.indicator.set_values(self._current_coarse, final_value)
        
        self.valueChanged.emit(float(final_value))
        
    def value(self) -> float:
        """Get current combined value."""
        return float(self._current_coarse + self._current_fine)
        
    def setValue(self, val: float):
        """Set value (updates both coarse and fine components)."""
        self._syncing = True
        
        val = max(self.min_val, min(self.max_val, int(val)))
        
        # Calculate coarse and fine components
        # Note: We don't snap to coarse_step anymore since range indicator is continuous
        # But we still want to keep fine adjustment within range
        self._current_coarse = val
        self._current_fine = 0
        
        # If value is too far from a reasonable coarse position, adjust
        # This ensures fine slider stays centered
        if abs(self._current_fine) > self.fine_range:
            adjustment = (self._current_fine // self.fine_range) * self.fine_range
            self._current_coarse += adjustment
            self._current_fine -= adjustment
        
        # Update fine slider only (coarse is controlled by range indicator)
        self.slider_fine.setValue(self._current_fine)
        self.lbl_fine.setText(f"{self._current_fine:+d}")
        
        self._syncing = False
        
        self._update_display()
        
    def setEnabled(self, enabled: bool):
        """Enable/disable all controls."""
        from core import get_logger
        _logger = get_logger('camera')
        _logger.debug(f"TwoStageSlider.setEnabled called with enabled={enabled}")
        
        super().setEnabled(enabled)
        self.slider_fine.setEnabled(enabled)
        self.indicator.setEnabled(enabled)
        self.lbl_value.setEnabled(enabled)
        self.lbl_fine.setEnabled(enabled)
        
        # Apply visual greyed-out effect using opacity
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        opacity_effect = QGraphicsOpacityEffect(self)
        if enabled:
            opacity_effect.setOpacity(1.0)
        else:
            opacity_effect.setOpacity(0.4)
        self.setGraphicsEffect(opacity_effect)
    
    def set_favorites(self, favorites: list):
        """Set the list of favorites."""
        self.indicator.set_favorites(favorites)
        
    def get_favorites(self) -> list:
        """Get the list of favorites."""
        return self.indicator.get_favorites()
