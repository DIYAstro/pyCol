"""
Overlay Panel UI Component.

Provides overlay management, global offset, and per-overlay property controls.
"""
from PySide6.QtWidgets import (QLabel, QPushButton, QComboBox,
                               QListWidget, QListWidgetItem, QGroupBox, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QCheckBox, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from typing import Tuple
from ui.widgets import CollapsibleSection, ColorButton, SliderSpinbox
from core import get_logger

_logger = get_logger('overlay')


class OverlayPanel(CollapsibleSection):
    """
    Panel for managing visual overlays in the collimation view.
    
    Provides controls for:
    - Global center offset (X/Y position adjustment)
    - Overlay list management (add/remove circles, crosshairs)
    - Per-overlay properties (radius, angle, color, thickness)
    - Local offset for individual overlays
    
    Args:
        camera_thread: The CameraThread instance to control.
        parent: Optional parent widget.
    """
    
    def __init__(self, camera_thread, parent=None):
        super().__init__("Overlays", parent)
        self.thread = camera_thread
        
        # Global Center Offset
        self.chk_global_offset = QCheckBox("Enable Global Center Offset")
        self.chk_global_offset.setChecked(True)
        self.chk_global_offset.stateChanged.connect(self.toggle_global_offset)
        
        self.lbl_off_x = QLabel("Center X:")
        self.slider_off_x = SliderSpinbox(-2000, 2000, 0, decimals=2)
        self.slider_off_x.valueChanged.connect(self.update_offset_x)

        self.lbl_off_y = QLabel("Center Y:")
        self.slider_off_y = SliderSpinbox(-2000, 2000, 0, decimals=2)
        self.slider_off_y.valueChanged.connect(self.update_offset_y)
        
        # Store current offset values for restore
        self._stored_offset_x = 0
        self._stored_offset_y = 0
        
        # Connect signal from thread to update sliders when offsets change externally
        self.thread.global_offset_changed.connect(self._on_global_offset_changed)
        
        # List of Overlays
        self.lbl_list = QLabel("Active Overlays:")
        self.list_circles = QListWidget()
        self.list_circles.setFixedHeight(120)
        # Connect signals
        self.list_circles.currentRowChanged.connect(self.on_overlay_selected)
        self.list_circles.itemChanged.connect(self.on_item_changed)
        
        # Add New Shape UI
        self.layout_add = QHBoxLayout()
        self.combo_shape = QComboBox()
        self.combo_shape.addItems(["Circle", "Crosshair"])
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_overlay)
        # Consistent Blue Style (Add/Load)
        self.btn_add.setStyleSheet("background-color: #2a82da; color: white; font-weight: bold;")
        
        self.layout_add.addWidget(self.combo_shape)
        self.layout_add.addWidget(self.btn_add)
        

        # Add to layout
        self.addWidget(self.chk_global_offset)
        self.addWidget(self.lbl_off_x)
        self.addWidget(self.slider_off_x)
        self.addWidget(self.lbl_off_y)
        self.addWidget(self.slider_off_y)
        self.addSpacing(10)
        self.addWidget(self.lbl_list)
        self.addWidget(self.list_circles)
        self.addLayout(self.layout_add)

        self.btn_remove_circle = QPushButton("Delete Overlay")
        self.btn_remove_circle.setStyleSheet("background-color: #502020; color: #ffaaaa; margin-top: 5px;") 
        self.btn_remove_circle.clicked.connect(self.remove_circle)
        self.btn_remove_circle.setEnabled(False)
        self.addWidget(self.btn_remove_circle)
        
        self.btn_clear = QPushButton("Clear All Overlays")
        self.btn_clear.setStyleSheet("background-color: #502020; color: #ffaaaa; margin-top: 5px;")
        self.btn_clear.clicked.connect(self.clear_all_overlays)
        self.addWidget(self.btn_clear)
        
        self.addSpacing(10)

        # Properties for Selected Overlay
        self.grp_props = QGroupBox("Selected Properties")
        self.grp_props.setCheckable(False)
        self.layout_props = QVBoxLayout(self.grp_props)
        self.layout_props.setSpacing(5)
        self.layout_props.setContentsMargins(5, 10, 5, 5)
        
        self.lbl_radius = QLabel("Radius:")
        # Enable subpixel precision (decimals=1)
        self.slider_radius = SliderSpinbox(0.1, 2000.0, 200.0, decimals=1)
        self.slider_radius.valueChanged.connect(self.update_radius)
        
        self.lbl_arms = QLabel("Arms:")
        self.slider_arms = SliderSpinbox(1, 12, 4, decimals=0)
        self.slider_arms.valueChanged.connect(self.update_arms)
        self.lbl_arms.setVisible(False)
        self.slider_arms.setVisible(False)
        
        self.lbl_angle = QLabel("Rotation:")
        self.slider_angle = SliderSpinbox(0, 360, 0, decimals=1)
        self.slider_angle.valueChanged.connect(self.update_angle)
        
        self.lbl_thickness = QLabel("Thickness:")
        self.slider_thickness = SliderSpinbox(1, 10, 2, decimals=0)
        self.slider_thickness.valueChanged.connect(self.update_thickness)
        
        # Local Offset
        self.lbl_local_x = QLabel("Local X:")
        self.slider_local_x = SliderSpinbox(-2000, 2000, 0, decimals=2)
        self.slider_local_x.valueChanged.connect(self.update_local_x)
        
        self.lbl_local_y = QLabel("Local Y:")
        self.slider_local_y = SliderSpinbox(-2000, 2000, 0, decimals=2)
        self.slider_local_y.valueChanged.connect(self.update_local_y)
        
        # Color Grid
        self.lbl_color = QLabel("Color:")
        self.layout_color_grid = QGridLayout()
        
        colors = [
            ("Cyan", "#00FFFF", (255, 255, 0)),
            ("Yellow", "#FFFF00", (0, 255, 255)),
            ("Green", "#00FF00", (0, 255, 0)),
            ("Magenta", "#FF00FF", (255, 0, 255)),
            ("Red", "#FF0000", (0, 0, 255)),
            ("Blue", "#0000FF", (255, 0, 0)),
            ("White", "#FFFFFF", (255, 255, 255)),
            ("Orange", "#FFA500", (0, 165, 255)),
            ("Purple", "#800080", (128, 0, 128)),
            ("Lime", "#BFFF00", (0, 255, 191)),
            ("Pink", "#FFC0CB", (203, 192, 255)),
            ("Teal", "#008080", (128, 128, 0)),
            ("Gold", "#FFD700", (0, 215, 255)),
            ("Navy", "#000080", (128, 0, 0)),
            ("Maroon", "#800000", (0, 0, 128)),
            ("Olive", "#808000", (0, 128, 128)),
        ]
        
        row, col = 0, 0
        for name, hexa, bgr in colors:
            btn = ColorButton(hexa, bgr, self.set_color)
            self.layout_color_grid.addWidget(btn, row, col)
            col += 1
            if col > 7:
                col = 0
                row += 1
        
        # Build Properties Layout
        self.layout_props.addWidget(self.lbl_radius)
        self.layout_props.addWidget(self.slider_radius)
        self.layout_props.addWidget(self.lbl_arms)
        self.layout_props.addWidget(self.slider_arms)
        self.layout_props.addWidget(self.lbl_angle)
        self.layout_props.addWidget(self.slider_angle)
        self.layout_props.addWidget(self.lbl_local_x)
        self.layout_props.addWidget(self.slider_local_x)
        self.layout_props.addWidget(self.lbl_local_y)
        self.layout_props.addWidget(self.slider_local_y)
        self.layout_props.addWidget(self.lbl_thickness)
        self.layout_props.addWidget(self.slider_thickness)
        self.layout_props.addWidget(self.lbl_color)
        self.layout_props.addLayout(self.layout_color_grid)
        self.layout_props.addSpacing(5)

        self.addWidget(self.grp_props)
        self.grp_props.setEnabled(False)
        
        self.addStretch(1)
        
    # --- Handlers ---
    def toggle_global_offset(self, state):
        """Enable or disable global center offset."""
        enabled = bool(state)  # 0 = unchecked, 2 = checked
        self.slider_off_x.setEnabled(enabled)
        self.slider_off_y.setEnabled(enabled)
        self.lbl_off_x.setEnabled(enabled)
        self.lbl_off_y.setEnabled(enabled)
        
        if enabled:
            # Restore stored offsets
            self.thread.set_global_offset_x(self._stored_offset_x)
            self.thread.set_global_offset_y(self._stored_offset_y)
        else:
            # Store current offsets and set to 0
            self._stored_offset_x = int(self.slider_off_x.value())
            self._stored_offset_y = int(self.slider_off_y.value())
            self.thread.set_global_offset_x(0)
            self.thread.set_global_offset_y(0)
    
    def update_offset_x(self, val: float):
        self._stored_offset_x = val
        if self.chk_global_offset.isChecked():
            self.thread.set_global_offset_x(val)
        
    def update_offset_y(self, val: float):
        self._stored_offset_y = val
        if self.chk_global_offset.isChecked():
            self.thread.set_global_offset_y(val)
    
    def _on_global_offset_changed(self, offset_x: float, offset_y: float):
        """Slot called when thread emits global_offset_changed signal."""
        # Block signals to prevent circular updates (slider → thread → slider)
        self.slider_off_x.blockSignals(True)
        self.slider_off_y.blockSignals(True)
        
        # Update slider values
        self.slider_off_x.setValue(offset_x)
        self.slider_off_y.setValue(offset_y)
        
        # Update stored values
        self._stored_offset_x = offset_x
        self._stored_offset_y = offset_y
        
        # Unblock signals
        self.slider_off_x.blockSignals(False)
        self.slider_off_y.blockSignals(False)
        
        _logger.debug(f"Global offset updated from signal: X={offset_x:.2f}, Y={offset_y:.2f}")
        
    def update_radius(self, val: float):
        self.thread.set_active_radius(float(val))
        self.update_list_item()

    def update_angle(self, val: float):
        self.thread.set_active_angle(val)

    def update_arms(self, val: float):
        self.thread.set_active_arms(int(val))

    def update_thickness(self, val: float):
        self.thread.collimator.update_active_circle_thickness(int(val))
        
    def update_local_x(self, val: float):
        self.thread.set_active_offset_x(val)

    def update_local_y(self, val: float):
        self.thread.set_active_offset_y(val)

    def on_overlay_selected(self, row):
        if row >= 0:
            self.thread.collimator.set_active_index(row)
            self.grp_props.setEnabled(True)
            self.btn_remove_circle.setEnabled(True) # Enable delete button
            try:
                c = self.thread.collimator.overlays[row]
                self.slider_radius.blockSignals(True)
                self.slider_thickness.blockSignals(True)
                self.slider_angle.blockSignals(True)
                self.slider_arms.blockSignals(True)
                self.slider_local_x.blockSignals(True)
                self.slider_local_y.blockSignals(True)
                
                self.slider_local_x.blockSignals(True)
                self.slider_local_y.blockSignals(True)
                
                self.slider_radius.setValue(float(c.get('radius', 200)))
                self.slider_thickness.setValue(int(c.get('thickness', 2)))
                self.slider_angle.setValue(float(c.get('angle', 0)))
                self.slider_arms.setValue(int(c.get('arms', 4)))
                self.slider_local_x.setValue(float(c.get('offset_x', 0)))
                self.slider_local_y.setValue(float(c.get('offset_y', 0)))
                
                # Show/Hide Angle/Arms slider based on type
                stype = c.get('type', 'circle')
                if stype == 'circle':
                    self.slider_angle.setVisible(False)
                    self.lbl_angle.setVisible(False)
                    self.slider_arms.setVisible(False)
                    self.lbl_arms.setVisible(False)
                else:
                    self.slider_angle.setVisible(True)
                    self.lbl_angle.setVisible(True)
                    if stype == 'crosshair' or stype == 'radial':
                        self.slider_arms.setVisible(True)
                        self.lbl_arms.setVisible(True)
                    else:
                        self.slider_arms.setVisible(False)
                        self.lbl_arms.setVisible(False)

                self.slider_radius.blockSignals(False)
                self.slider_thickness.blockSignals(False)
                self.slider_angle.blockSignals(False)
                self.slider_arms.blockSignals(False)
                self.slider_local_x.blockSignals(False)
                self.slider_local_y.blockSignals(False)
            except:
                pass
        else:
            self.grp_props.setEnabled(False)
            self.btn_remove_circle.setEnabled(False) # Disable delete button

    def update_list_item(self):
        row = self.list_circles.currentRow()
        if row >= 0:
            val = self.slider_radius.value() # Float
            item = self.list_circles.item(row)
            
            # Avoid infinite loop if setText triggers itemChanged
            self.list_circles.blockSignals(True)
            
            # Preserve the name part (everything before the last parenthesis group)
            text = item.text()
            if " (r=" in text:
                 # "Name (r=200.0)" -> "Name"
                 base_name = text.rsplit(" (r=", 1)[0]
            else:
                 base_name = text
            
            item.setText(f"{base_name} (r={val:.1f})")
            self.list_circles.blockSignals(False)
            
    def on_item_changed(self, item):
        """Handle item renaming."""
        row = self.list_circles.row(item)
        if row >= 0:
            # Extract base name (remove radius info if user accidentally edited it or if we are syncing)
            text = item.text()
            if " (r=" in text:
                 name = text.rsplit(" (r=", 1)[0]
            else:
                 name = text
                 # If user removed the radius part, we might want to add it back?
                 # ideally update_list_item will handle it subsequent updates.
            
            # Update backend
            # Note: We can't easily set active index here without triggering selection logic
            # taking a shortcut: Assume row matches index
            if 0 <= row < len(self.thread.collimator.overlays):
                self.thread.collimator.overlays[row]['name'] = name
                _logger.debug(f"Renamed overlay {row} to '{name}'")

    def remove_circle(self):
        row = self.list_circles.currentRow()
        if row >= 0:
            _logger.debug(f"User removed overlay at index {row}")
            self.thread.collimator.remove_active_overlay()
            self.list_circles.takeItem(row)
            if self.list_circles.count() == 0:
               self.grp_props.setEnabled(False)
               self.btn_remove_circle.setEnabled(False) # Disable delete button

    def clear_all_overlays(self):
        """Remove all overlays after confirmation."""
        reply = QMessageBox.question(self, "Confirm Clear All", 
                                   "Are you sure you want to remove ALL overlays?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.thread.collimator.clear_overlays()
            self.list_circles.clear()
            self.grp_props.setEnabled(False)
            self.btn_remove_circle.setEnabled(False) # Disable delete button
               
    def add_overlay(self):
        shape = self.combo_shape.currentText().lower()
        idx = self.thread.add_overlay_shape(shape)
        _logger.debug(f"User added overlay: {shape} (index {idx})")
        
        # Get the color assigned by backend
        ov = self.thread.collimator.overlays[idx]
        bgr = ov['color']
        rgb = (bgr[2], bgr[1], bgr[0])
        
        count = self.list_circles.count() + 1
        name = f"{shape.capitalize()} {count}"
        
        item = QListWidgetItem(name)
        item.setForeground(QColor(*rgb))
        item.setFlags(item.flags() | Qt.ItemIsEditable) # Make editable
        
        self.list_circles.addItem(item)
        
        # Store initial name in backend
        self.thread.collimator.overlays[idx]['name'] = name
        
        self.list_circles.setCurrentRow(self.list_circles.count() - 1)
        self.grp_props.setEnabled(True)
        
    def set_color(self, color_bgr):
        self.thread.collimator.update_active_circle_color(color_bgr)
        row = self.list_circles.currentRow()
        if row >= 0:
            item = self.list_circles.item(row)
            rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
            item.setForeground(QColor(*rgb))
