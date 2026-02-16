from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QSpinBox, QDoubleSpinBox
from PySide6.QtCore import Qt, Signal, QLocale
from PySide6.QtGui import QDoubleValidator, QKeyEvent


class CommaDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox that accepts both comma and period as decimal separator."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Use C locale which uses period as decimal separator
        locale = QLocale(QLocale.C)
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        self.setLocale(locale)
        
        # Acceleration tracking
        self._last_step_time = 0
        self._step_count = 0
    
    def stepBy(self, steps):
        """Override stepBy to add acceleration based on repeat speed."""
        import time
        
        current_time = time.time()
        time_delta = current_time - self._last_step_time
        
        # Reset counter if too much time passed (user paused)
        if time_delta > 0.5:
            self._step_count = 0
        else:
            self._step_count += 1
        
        self._last_step_time = current_time
        
        # Calculate multiplier based on repeat count
        # More repeats = faster acceleration
        if self._step_count < 3:
            multiplier = 1
        elif self._step_count < 8:
            multiplier = 2
        elif self._step_count < 15:
            multiplier = 5
        else:
            multiplier = 10
        
        # Apply accelerated step
        super().stepBy(steps * multiplier)
    
    def keyPressEvent(self, event: QKeyEvent):
        # Convert comma to period
        if event.text() == ",":
            # Create a new event with period instead of comma
            from PySide6.QtCore import QEvent
            new_event = QKeyEvent(
                QEvent.KeyPress,
                Qt.Key_Period,
                event.modifiers(),
                "."
            )
            super().keyPressEvent(new_event)
        else:
            super().keyPressEvent(event)
    
    def textFromValue(self, value: float) -> str:
        return f"{value:.{self.decimals()}f}"
    
    def valueFromText(self, text: str) -> float:
        # Replace comma with period for parsing
        return float(text.replace(",", "."))


class AcceleratedSpinBox(QSpinBox):
    """Integer SpinBox with stepBy acceleration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Acceleration tracking
        self._last_step_time = 0
        self._step_count = 0
    
    def stepBy(self, steps):
        """Override stepBy to add acceleration based on repeat speed."""
        import time
        
        current_time = time.time()
        time_delta = current_time - self._last_step_time
        
        # Reset counter if too much time passed (user paused)
        if time_delta > 0.5:
            self._step_count = 0
        else:
            self._step_count += 1
        
        self._last_step_time = current_time
        
        # Calculate multiplier based on repeat count
        if self._step_count < 3:
            multiplier = 1
        elif self._step_count < 8:
            multiplier = 2
        elif self._step_count < 15:
            multiplier = 5
        else:
            multiplier = 10
        
        # Apply accelerated step
        super().stepBy(steps * multiplier)



class SliderSpinbox(QWidget):
    """
    Combined slider and spinbox widget with bidirectional sync.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        default_val: Default/initial value
        decimals: Number of decimal places (0 for integer)
        step: Step size for spinbox (default 1 for int, 0.1 for decimal)
        parent: Parent widget
    """
    
    valueChanged = Signal(float)  # Emits the actual value (not scaled)
    
    def __init__(self, min_val: float, max_val: float, default_val: float = 0,
                 decimals: int = 0, step: float = None, parent=None):
        super().__init__(parent)
        
        self.decimals = decimals
        self.min_val = min_val
        self.max_val = max_val
        
        # For decimal values, we scale internally
        if decimals > 0:
            self.scale = 10 ** decimals
            step = step or 0.1
        else:
            self.scale = 1
            step = step or 1
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(min_val * self.scale), int(max_val * self.scale))
        self.slider.setValue(int(default_val * self.scale))
        self.slider.valueChanged.connect(self._on_slider_changed)
        
        # Spinbox
        if decimals > 0:
            self.spinbox = CommaDoubleSpinBox()
            self.spinbox.setDecimals(decimals)
            self.spinbox.setSingleStep(step)
        else:
            self.spinbox = AcceleratedSpinBox()
            self.spinbox.setSingleStep(int(step))
        
        self.spinbox.setRange(int(min_val) if decimals == 0 else min_val,
                              int(max_val) if decimals == 0 else max_val)
        self.spinbox.setValue(int(default_val) if decimals == 0 else default_val)
        self.spinbox.setFixedWidth(60)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spinbox)
        
        self._syncing = False
    
    def _on_slider_changed(self, val: int):
        if self._syncing:
            return
        self._syncing = True
        
        actual_val = val / self.scale
        if self.decimals > 0:
            self.spinbox.setValue(actual_val)
        else:
            self.spinbox.setValue(int(actual_val))
        
        self.valueChanged.emit(actual_val)
        self._syncing = False
    
    def _on_spinbox_changed(self, val):
        if self._syncing:
            return
        self._syncing = True
        
        if self.decimals > 0:
            self.slider.setValue(int(val * self.scale))
        else:
            self.slider.setValue(int(val))
        
        self.valueChanged.emit(float(val))
        self._syncing = False
    
    def value(self) -> float:
        """Get current value."""
        return self.spinbox.value()
    
    def setValue(self, val: float):
        """Set value (updates both slider and spinbox)."""
        self._syncing = True
        if self.decimals > 0:
            self.spinbox.setValue(val)
            self.slider.setValue(int(val * self.scale))
        else:
            self.spinbox.setValue(int(val))
            self.slider.setValue(int(val))
        self._syncing = False
        # Emit signal for external setValue calls (e.g., mouse wheel zoom)
        self.valueChanged.emit(float(val))
    
    def setEnabled(self, enabled: bool):
        """Enable/disable both controls."""
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.spinbox.setEnabled(enabled)
        
        # Force visual update via GraphicsOpacityEffect
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        op = QGraphicsOpacityEffect(self)
        op.setOpacity(1.0 if enabled else 0.5)
        self.setGraphicsEffect(op)
        self.setAutoFillBackground(True) # Improve rendering with effect
    
    def blockSignals(self, block: bool):
        """Block signals on both controls."""
        super().blockSignals(block)
        self.slider.blockSignals(block)
        self.spinbox.blockSignals(block)
