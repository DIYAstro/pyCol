import cv2
import numpy as np
import time
from core.logger import get_logger

_logger = get_logger('offset_mgr')

class OffsetManager:
    """
    Manages centroid detection and offset calibration.
    Migrated from Collimator logic.
    """
    def __init__(self, plugin):
        self.plugin = plugin
        self.thread = plugin._context.get('camera_thread')
        
        # Detection Settings (Loaded from Managed Settings)
        self.threshold = self.plugin.get_setting("threshold", 100)
        self.invert = self.plugin.get_setting("invert", False)
        self.blur = False
        
        # Calibration State
        self.is_calibrating = False
        self.calibration_points = []
        self.center = None
        self.measurement_complete_time = None
        
        # Detection State
        self.detection_active = False
        self.last_centroid = None
        self.debug_contours = []
        
        # P1/P2 Measurement (Manual)
        self.p1 = None
        self.p2 = None

    def process_frame(self, frame):
        """
        Called by plugin hook. 
        Detects centroid if active and draws debug info.
        """
        if not self.detection_active:
            return frame
            
        # Detect
        centroid = self.find_centroid(frame)
        self.last_centroid = centroid
        
        # Draw Debug Contours first (underneath everything)
        if self.debug_contours:
            cv2.drawContours(frame, self.debug_contours, -1, (255, 255, 0), 1)
            
        if centroid:
            # Draw detected center (Cyan dot)
            cx, cy = int(centroid[0]), int(centroid[1])
            cv2.circle(frame, (cx, cy), 3, (255, 255, 0), -1)
            
            # If calibrating, collect points
            if self.is_calibrating:
                self.calibration_points.append(centroid)
                
        # Draw Calibration Trail
        if self.is_calibrating:
            for pt in self.calibration_points:
                cv2.circle(frame, (int(pt[0]), int(pt[1])), 1, (0, 255, 255), -1)
                
        # Draw P1/P2 manual tools
        if self.p1: self._draw_mark(frame, self.p1, (0, 255, 255), "P1")
        if self.p2: self._draw_mark(frame, self.p2, (0, 255, 255), "P2")
        
        # Draw Result Center
        if self.center:
            # Auto-hide after 5s
            if self.measurement_complete_time and (time.time() - self.measurement_complete_time) < 5.0:
                 cx, cy = int(self.center[0]), int(self.center[1])
                 cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 2)
                 cv2.putText(frame, "CENTER", (cx+10, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame

    def find_centroid(self, frame):
        """Finds the centroid of a spot."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.blur:
            gray = cv2.blur(gray, (5, 5))
            
        type_ = cv2.THRESH_BINARY_INV if self.invert else cv2.THRESH_BINARY
        _, thresh = cv2.threshold(gray, self.threshold, 255, type_) 
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.debug_contours = contours
        
        if not contours:
            return None
            
        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < 10: continue
            
            perimeter = cv2.arcLength(c, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [c], -1, 255, -1)
            mean_val = cv2.mean(gray, mask=mask)[0]
            
            candidates.append({
                'contour': c,
                'area': area,
                'circularity': circularity,
                'brightness': mean_val
            })
            
        if not candidates: return None
            
        # Selection Logic: Roundest
        best_candidate = min(candidates, key=lambda x: x['brightness'] - (x['circularity'] * 100))
        c = best_candidate['contour']
        self.debug_contours = [c]

        M = cv2.moments(c)
        if M["m00"] != 0:
            return (M["m10"] / M["m00"], M["m01"] / M["m00"])
        return None

    def start_calibration(self):
        self.calibration_points = []
        self.is_calibrating = True
        self.center = None
        _logger.info("Starting visual calibration")

    def stop_calibration(self, frame_w, frame_h):
        self.is_calibrating = False
        _logger.info(f"Stopping calibration. Points: {len(self.calibration_points)}")
        
        if len(self.calibration_points) < 10:
            return None
            
        center = self.fit_circle(self.calibration_points)
        if center:
            self.center = center
            cx, cy = center
            
            # Apply to Core
            # Global Offset = Center - (W/2, H/2)
            off_x = cx - (frame_w / 2)
            off_y = cy - (frame_h / 2)
            
            if self.thread:
                self.thread.set_global_offset_x(off_x)
                self.thread.set_global_offset_y(off_y)
                _logger.info(f"Applied Global Offset: x={off_x:.2f}, y={off_y:.2f}")
                
            self.measurement_complete_time = time.time()
            return center
        return None

    def fit_circle(self, points):
        """Algebraic circle fit."""
        if not points: return None
        pts = np.array(points)
        x = pts[:, 0]
        y = pts[:, 1]
        
        A = np.column_stack((x, y, np.ones_like(x)))
        b = -(x**2 + y**2)
        
        try:
            res, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
            D, E, F = res
            return (-D / 2, -E / 2)
        except:
            return None

    def _draw_mark(self, frame, pos, color, label):
        x, y = int(pos[0]), int(pos[1])
        cv2.line(frame, (x-10, y-10), (x+10, y+10), color, 2)
        cv2.line(frame, (x+10, y-10), (x-10, y+10), color, 2)
