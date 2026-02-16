import cv2
import numpy as np
from core.logger import get_logger

_logger = get_logger('auto_detect')

class AutoDetectionManager:
    """
    Manages automatic feature detection (Mirrors, Center).
    """
    def __init__(self, plugin):
        self.plugin = plugin
        
        # State
        self.active = False
        self.detected_circles = [] # List of (x, y, r)
        self.detected_center = None # (x, y)
        
        # Parameters (Hough) - Loaded from Settings
        self.dp = self.plugin.get_setting("hough_dp", 1.2)
        self.minDist = self.plugin.get_setting("hough_minDist", 100)
        self.param1 = self.plugin.get_setting("hough_param1", 50) # Canny High Threshold
        self.param2 = self.plugin.get_setting("hough_param2", 30) # Accumulator Threshold
        self.minRadius = self.plugin.get_setting("hough_minRadius", 50)
        self.maxRadius = self.plugin.get_setting("hough_maxRadius", 400)
        
        # Blur Parameter
        self.blur_size = self.plugin.get_setting("blur_size", 9)
        
        # Smoothing Parameters
        self.smoothing = self.plugin.get_setting("smoothing", 5) # 1 = No smoothing
        self.history = [] # List of list of circles: [ [c1, c2], [c1, c2] ... ]
        
    def process_frame(self, frame):
        if not self.active:
            self.history.clear()
            return frame
            
        # Detect
        self.find_circles(frame)
        
        # Smooth
        self.smooth_detections()
        
        # Draw Results
        self.draw_debug(frame)
        
        return frame

    def find_circles(self, frame):
        """Run Hough Circle Transform."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Optimization: Downscaling was causing detection failures.
        # Validated that scale=1.0 works reliably. 
        # Future optimization: Tuning param1 for lower resolutions may allow enabling this again.
        scale = 1.0 
        
        if scale != 1.0:
            small_gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            small_gray = gray
        
        # Blur
        scaled_blur = max(1, int(self.blur_size * scale))
        k = scaled_blur | 1 
        small_gray = cv2.medianBlur(small_gray, k)
        
        # Scale parameters
        s_minDist = self.minDist * scale
        s_minRadius = self.minRadius * scale
        s_maxRadius = self.maxRadius * scale
        s_param2 = max(10, self.param2 * scale) 
        
        circles = cv2.HoughCircles(
            small_gray, 
            cv2.HOUGH_GRADIENT, 
            dp=self.dp, 
            minDist=s_minDist,
            param1=self.param1,
            param2=s_param2,
            minRadius=int(s_minRadius), 
            maxRadius=int(s_maxRadius) 
        )
        
        current_frame_circles = []
        if circles is not None:
             candidates = np.around(circles)[0, :]
             
             for c in candidates:
                 # upscale
                 orig_x = c[0] / scale
                 orig_y = c[1] / scale
                 orig_r = c[2] / scale
                 
                 full_c = np.array([orig_x, orig_y, orig_r])
                 
                 if self.validate_circle(frame, full_c):
                     current_frame_circles.append(full_c.tolist())
        
        # Update History
        self.history.append(current_frame_circles)
        while len(self.history) > self.smoothing:
            self.history.pop(0)

    def validate_circle(self, frame, circle):
        """
        Check if circle is valid using intensity/edge analysis.
        Reject ghost circles in black areas.
        """
        x, y, r = int(circle[0]), int(circle[1]), int(circle[2])
        h, w = frame.shape[:2]
        
        # 1. Bounds Check (Relaxed slightly to allow partial objects)
        margin = 10
        if x+r < margin or x-r > w-margin or y+r < margin or y-r > h-margin:
            return False 
            
        # 2. Brightness Check (ROI)
        # Bounding box
        y1, y2 = max(0, y-r), min(h, y+r)
        x1, x2 = max(0, x-r), min(w, x+r)
        
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0: return False
        
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_val = cv2.mean(gray_roi)[0]
        
        # If area is pitch black (< 5), it's noise
        if mean_val < 5:
            return False
            
        # 3. Edge Contrast Check
        # We check Canny edge count in the ROI
        edges = cv2.Canny(gray_roi, self.param1 / 2, self.param1)
        edge_pixels = np.count_nonzero(edges)
        
        # Normalize by PERIMETER (2*pi*r), not Area!
        # Large circles have huge area but linear perimeter.
        perimeter = 2 * np.pi * r
        
        # We expect at least X% of the perimeter to have edges.
        # 10% seems safe for partial occlusion.
        if edge_pixels < (perimeter * 0.1): 
            return False
            
        return True
            
    def smooth_detections(self):
        """
        Average circles across history.
        Simple approach: Flatten history and cluster.
        """
        if not self.history:
            self.detected_circles = []
            return

        # Flatten all candidates
        all_circles = []
        for frame_circles in self.history:
            all_circles.extend(frame_circles)
            
        if not all_circles:
            self.detected_circles = []
            return
            
        # Simple Clustering (by proximity)
        # We greedily merge circles close to each other
        clusters = [] # list of [x, y, r]
        
        threshold_dist = 20 # Distance pixels to consider same circle
        
        for c in all_circles:
            matched = False
            for cluster in clusters:
                # Distance to cluster mean?
                # For simplicity, cluster is just a list of raw circles now, we check average
                
                # Check distance to FIRST element of cluster (approx) for speed
                cx, cy, cr = cluster[0]
                dist = np.sqrt((c[0]-cx)**2 + (c[1]-cy)**2)
                
                if dist < threshold_dist:
                    cluster.append(c)
                    matched = True
                    break
            
            if not matched:
                clusters.append([c])
                
        # Compute averages for valid clusters
        final_circles = []
        min_support = max(1, len(self.history) // 2) # Appear in at least 50% of history frames
        
        for cluster in clusters:
            if len(cluster) >= min_support:
                # Average
                avg = np.mean(cluster, axis=0)
                final_circles.append(avg) # (x, y, r) float
                
        self.detected_circles = final_circles
            
    def draw_debug(self, frame):
        """Draw detected circles on frame."""
        for x, y, r in self.detected_circles:
            # Draw outer circle (Green)
            cv2.circle(frame, (int(x), int(y)), int(r), (0, 255, 0), 2)
            # Draw center (Red)
            cv2.circle(frame, (int(x), int(y)), 2, (0, 0, 255), 3)

    def apply_detection_to_overlays(self):
        """Convert detected circles to persistent user overlays."""
        thread = self.plugin.context.get('camera_thread')
        if not thread: return
        
        count = 0
        for x, y, r in self.detected_circles:
            # Add to Core
            # Note: Hough returns pixel coords (0..W, 0..H).
            # Core Overlays work with Global Offset + Local Offset.
            # But the user interacts with "Screen Space" usually?
            # Actually, `collimator` overlays are drawn relative to World Center + Offsets.
            
            # We need to calculate the "Local Offset" relative to the "World Center".
            # World Center = (W/2, H/2) + Global Offset
            
            w = thread.cap.get(cv2.CAP_PROP_FRAME_WIDTH) if thread.cap else 1920
            h = thread.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) if thread.cap else 1080
            
            world_cx = w / 2 + thread.collimator.global_offset_x
            world_cy = h / 2 + thread.collimator.global_offset_y
            
            # Local Offset = Detected Pos - World Center
            off_x = x - world_cx
            off_y = y - world_cy
            
            idx = thread.add_overlay_shape('circle', radius=r)
            thread.collimator.update_active_circle_offset_x(off_x)
            thread.collimator.update_active_circle_offset_y(off_y)
            thread.collimator.update_active_overlay_name(f"Detected {count+1}")
            count += 1
            
        return count
