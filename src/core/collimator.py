import cv2
import numpy as np
import time
from .logger import get_logger

_logger = get_logger('calibration')

class Collimator:
    def __init__(self):
        # Global Offset for ALL overlays (relative to image center)
        self.global_offset_x = 0.0
        self.global_offset_y = 0.0
        
        # Overlay State
        self.overlays = [] # List of dicts: {'type': 'circle', 'radius': r, 'color': (r,g,b)}
        self.active_circle_index = -1
        
        # Algorithmic State
        self.algorithm_mode = 'dark_spot'
        self.threshold = 100
        self.invert = False
        self.blur = False
        self.debug_contours = [] # For visualization
        
        # Predefined colors (16 colors matching UI, BGR format)
        self.preset_colors = [
            (255, 255, 0),    # Cyan
            (0, 255, 255),    # Yellow
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (0, 0, 255),      # Red
            (255, 0, 0),      # Blue
            (255, 255, 255),  # White
            (0, 165, 255),    # Orange
            (128, 0, 128),    # Purple
            (0, 255, 191),    # Lime
            (203, 192, 255),  # Pink
            (128, 128, 0),    # Teal
            (0, 215, 255),    # Gold
            (128, 0, 0),      # Navy
            (0, 0, 128),      # Maroon
            (0, 128, 128),    # Olive
        ]
        

    # find_centroid and calculate_center moved to plugins/offset_measurement

    # capture_p1, capture_p2, reset removed

        # Predefined colors (16 colors matching UI, BGR format)
        self.preset_colors = [
            (255, 255, 0),    # Cyan
            (0, 255, 255),    # Yellow
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (0, 0, 255),      # Red
            (255, 0, 0),      # Blue
            (255, 255, 255),  # White
            (0, 165, 255),    # Orange
            (128, 0, 128),    # Purple
            (0, 255, 191),    # Lime
            (203, 192, 255),  # Pink
            (128, 128, 0),    # Teal
            (0, 215, 255),    # Gold
            (128, 0, 0),      # Navy
            (0, 0, 128),      # Maroon
            (0, 128, 128),    # Olive
        ]

    def add_overlay_circle(self, radius=200, color=None):
        # Determine color: passed arg > next in sequence > default
        if color is None:
            # Pick next color in cycle
            idx = len(self.overlays) % len(self.preset_colors)
            color = self.preset_colors[idx]
            
        # Note: x, y arguments removed as we use global offset now
        self.overlays.append({
            'type': 'circle',
            'radius': radius,
            'color': color,
            'thickness': 2
        })
        self.active_circle_index = len(self.overlays) - 1
        return self.active_circle_index

    def update_active_circle_radius(self, radius):
        if 0 <= self.active_circle_index < len(self.overlays):
            # No int() cast here, keep float
            self.overlays[self.active_circle_index]['radius'] = radius

    def update_active_circle_thickness(self, thickness):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['thickness'] = thickness

    def update_active_circle_offset_x(self, x):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['offset_x'] = x

    def update_active_circle_offset_y(self, y):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['offset_y'] = y

    def update_active_overlay_name(self, name):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['name'] = name

    def update_active_circle_color(self, color):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['color'] = color
            
    def set_active_index(self, index):
        if 0 <= index < len(self.overlays):
            self.active_circle_index = index
        else:
            self.active_circle_index = -1
            
    def remove_active_overlay(self):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays.pop(self.active_circle_index)
            # Adjust active index
            if self.active_circle_index >= len(self.overlays):
                self.active_circle_index = len(self.overlays) - 1
            return True
        return False

    def remove_last_overlay(self):
        # Legacy support, can remove later if unused
        if self.overlays:
            self.overlays.pop()
            self.active_circle_index = len(self.overlays) - 1

    def add_overlay_shape(self, shape_type, radius=200.0, color=None, arms=4):
        # determine color
        if color is None:
            idx = len(self.overlays) % len(self.preset_colors)
            color = self.preset_colors[idx]
            
        self.overlays.append({
            'type': shape_type, # 'circle' or 'crosshair'
            'radius': float(radius),
            'color': color,
            'thickness': 2,
            'angle': 0.0,
            'arms': arms,
            'offset_x': 0.0,
            'offset_y': 0.0,
            'name': '' # Initialize empty name
        })
        self.active_circle_index = len(self.overlays) - 1
        return self.active_circle_index

    # Compatibility wrapper for existing code
    def add_overlay_circle(self, radius=200.0, color=None):
        return self.add_overlay_shape('circle', radius, color)

    def update_active_angle(self, angle):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['angle'] = float(angle)

    def update_active_arms(self, arms):
        if 0 <= self.active_circle_index < len(self.overlays):
            self.overlays[self.active_circle_index]['arms'] = int(arms)

    def _draw_radial_overlay(self, frame, center_fixed, radius_fixed, arms, angle_deg, color, thickness, shift=4):
        """
        Draws radial overlay using subpixel fixed-point coordinates.
        center_fixed: (cx * 2^shift, cy * 2^shift)
        radius_fixed: radius * 2^shift
        """
        angle_rad = np.radians(angle_deg)
        step = 2 * np.pi / arms
        
        # Start at -90 deg (top) by default if angle is 0
        start_angle = -np.pi / 2 + angle_rad
        
        cx, cy = center_fixed
        
        for i in range(arms):
            theta = start_angle + i * step
            # Calculate end point in FIXED POINT space directly
            # r * cos(theta) is still in normal scale, so we multiply radius_fixed directly
            # x = center + radius * cos(theta)
            # x_fixed = center_fixed + radius_fixed * cos(theta)
            
            x = int(cx + radius_fixed * np.cos(theta))
            y = int(cy + radius_fixed * np.sin(theta))
            
            # Draw line using shift
            cv2.line(frame, (cx, cy), (x, y), color, thickness, lineType=cv2.LINE_AA, shift=shift)

    def draw_overlays(self, frame, zoom_params=None):
        """
        Draws active overlays. TRANSFORMING coordinates if zoom is active.
        
        Args:
            frame: The image to draw on (could be zoomed/cropped)
            zoom_params: Dict {'zoom': float, 'left': int, 'top': int} defining the crop in original image space.
                         If None, assumes full frame (zoom=1.0, left=0, top=0).
        """
        h, w = frame.shape[:2]
        
        # Default params (Zoom 1.0, Full Frame)
        zoom = 1.0
        crop_left = 0
        crop_top = 0
        
        if zoom_params:
            zoom = zoom_params.get('zoom', 1.0)
            crop_left = zoom_params.get('left', 0)
            crop_top = zoom_params.get('top', 0)
            
        # Helper to transform World Coord (Original Image) -> Screen Coord (Zoomed Frame)
        def to_screen(wx, wy):
            sx = (wx - crop_left) * zoom
            sy = (wy - crop_top) * zoom
            return sx, sy
            
        # --- 0. Calculate Global Center (World Coordinates) ---
        # Note: We need the ORIGINAL image size to know true center
        # We can infer it if zoom=1 from frame size, but better if CameraThread logic handles this.
        # But wait: 'global_offset' is relative to image center.
        # So World Center = (Orig_W/2 + Global_Off_X, Orig_H/2 + Global_Off_Y)
        
        # Since we don't pass Orig_W/H here easily, let's assume CameraThread 
        # calculates the "Global Center" (World Coords) and passes it?
        # OR: We keep assuming global_offset is relative to center.
        # Let's derive Orig dimensions from current frame and zoom.
        
        orig_w = int(w / zoom) # Approximate if cropped? No, w is screen width. 
        # Screen width = Crop width * Zoom. Crop width = Orig w / Zoom. 
        # So Screen W = (Orig W / Zoom) * Zoom = Orig W (roughly, minus rounding)
        # Actually: If we crop to aspect ratio, W might change.
        
        # Better: CameraThread knows everything. Let's just rely on global_offset logic relative to "Virtual Center".
        # Let's Calculate the "World Center" position relative to the Crop Top-Left.
        
        # We need the Original Image Center coordinates to apply Global Offset correctly.
        # Let's assume we pass `orig_dim` in `zoom_params` too for safety?
        # Or just calculate:
        
        orig_w = zoom_params.get('orig_w', w) if zoom_params else w
        orig_h = zoom_params.get('orig_h', h) if zoom_params else h
        
        world_center_x = orig_w / 2 + self.global_offset_x
        world_center_y = orig_h / 2 + self.global_offset_y
        
        # --- 1. Draw Global Crosshair ---
        # Transform World Center -> Screen
        screen_cx, screen_cy = to_screen(world_center_x, world_center_y)
        
        # Draw Crosshair
        # Note: Check bounds to avoid integer overflow in cv2.line with large coordinates
        # Use int for drawing
        dcx, dcy = int(screen_cx), int(screen_cy)
        
        color_cross = (0, 0, 255) # BGR
        
        # Draw Vertical Line using clipLine for robustness against overflow
        safe_dcx = max(-20000, min(20000, dcx))
        # Define a long vertical segment, clipped to image rect
        # The rect is defined by (x, y, w, h)
        rect = (0, 0, w, h)
        
        # Calculate thickness scale based on resolution to avoid display aliasing
        # At 4K, 1px lines disappear when downscaled to 1080p display
        # Base resolution: ~1500px (HD-ish) -> Scale 1.0
        # 4K (3840px) -> Scale ~2.5
        thickness_scale = max(1.0, max(w, h) / 1500.0)
        cross_thickness = int(1 * thickness_scale) # Base thickness 1 for crosshair
        
        # Vertical Line: (safe_dcx, -10000) to (safe_dcx, h+10000)
        # We clamp Y coordinates to avoid overflow too, even though clipLine handles them
        pt1 = (safe_dcx, -20000)
        pt2 = (safe_dcx, h + 20000)
        
        ret, p1_out, p2_out = cv2.clipLine(rect, pt1, pt2)
        if ret:
            cv2.line(frame, p1_out, p2_out, color_cross, cross_thickness)

        # Draw Horizontal Line
        safe_dcy = max(-20000, min(20000, dcy))
        pt1 = (-20000, safe_dcy)
        pt2 = (w + 20000, safe_dcy)
        
        ret, p1_out, p2_out = cv2.clipLine(rect, pt1, pt2)
        if ret:
            cv2.line(frame, p1_out, p2_out, color_cross, cross_thickness)
        
        # 1.5 Debug Contours (Cyan)
        if self.debug_contours:
            cv2.drawContours(frame, self.debug_contours, -1, (255, 255, 0), int(1 * thickness_scale))
        
        # 2. User Overlays
        # Determine safe shift value based on image dimensions to prevent overflow
        # OpenCV internal fixed-point coordinates often use 16-bit signed integers (max 32767)
        # So dimension * (1 << shift) must be < 32768
        max_dim = max(w, h)
        shift = 4
        while shift > 0 and (max_dim * (1 << shift)) > 30000:
            shift -= 1
            
        mult = 1 << shift
        
        for i, ov in enumerate(self.overlays):
            # Calculate actual center for this specific overlay
            # Global Basis + Local Offset
            local_x = ov.get('offset_x', 0)
            local_y = ov.get('offset_y', 0)
            
            # World Coord of this overlay
            ov_world_x = world_center_x + local_x
            ov_world_y = world_center_y + local_y
            
            # Screen Coord (Float)
            scx, scy = to_screen(ov_world_x, ov_world_y)
            
            # Create FIXED POINT coordinates (shifted)
            center_fixed = (int(scx * mult), int(scy * mult))
            
            # Radius scales with zoom! (Vector behavior)
            r_screen_float = ov['radius'] * zoom
            r_fixed = int(r_screen_float * mult)
            
            stype = ov.get('type', 'circle')
            color = ov['color']
            
            # Thickness does NOT scale with zoom (keep crisp lines), BUT scales with Resolution
            base_thickness = int(ov.get('thickness', 2))
            thickness = max(1, int(base_thickness * thickness_scale))
            
            angle = float(ov.get('angle', 0))
            arms = int(ov.get('arms', 4))
            
            if stype == 'circle':
                 # Use SHIFT for subpixel rendering
                 cv2.circle(frame, center_fixed, r_fixed, color, thickness, lineType=cv2.LINE_AA, shift=shift)
            elif stype == 'crosshair':
                 self._draw_radial_overlay(frame, center_fixed, r_fixed, arms, angle, color, thickness, shift=shift)
            elif stype == 'radial':
                 self._draw_radial_overlay(frame, center_fixed, r_fixed, arms, angle, color, thickness, shift=shift)
            # Legacy/Fallback support
            elif stype == 'triangle':
                 self._draw_radial_overlay(frame, center_fixed, r_fixed, 3, angle, color, thickness, shift=shift)
            elif stype == 'cross':
                 self._draw_radial_overlay(frame, center_fixed, r_fixed, 4, angle, color, thickness, shift=shift)
                 self._draw_radial_overlay(frame, center_fixed, r_fixed, 6, angle, color, thickness, shift=shift)

        return frame

    # _draw_mark removed

    # Calibration Logic moved to plugins/offset_measurement

    def clear_overlays(self):
        """Removes all user defined overlays."""
        self.overlays.clear()
        self.active_circle_index = -1

