"""
Reusable UI widgets for the application.

This package contains custom widgets used across the application:
- CollapsibleSection: A panel with a toggle header
- ColorButton: A small colored button for color palettes
- ZoomImageLabel: A label that supports scroll-to-zoom
"""
from .collapsible_section import CollapsibleSection
from .color_button import ColorButton
from .zoom_image_label import ZoomImageLabel
from .slider_spinbox import SliderSpinbox
from .two_stage_slider import TwoStageSlider

__all__ = ['CollapsibleSection', 'ColorButton', 'ZoomImageLabel', 'SliderSpinbox', 'TwoStageSlider']
