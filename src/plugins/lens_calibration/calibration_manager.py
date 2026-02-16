import cv2
import numpy as np
import json
import os
from core.logger import get_logger
from utils import get_app_data_path

_logger = get_logger('calibration_mgr')

class CalibrationManager:
    """
    Manages lens calibration data and operations.
    Handles chessboard detection, camera calibration, and image undistortion.
    """
    def __init__(self, plugin):
        self.plugin = plugin
        self.camera_matrix = None
        self.dist_coeffs = None
        self.roi = None
        
        # Load Active State
        self.active = self.plugin.get_setting("active", False)
        
        # Calibration Parameters
        self.pattern_size = (9, 6) # Inner corners
        self.square_size_mm = 25.0
        
        self.load_calibration()

    def find_corners(self, frame):
        """
        Attempt to find chessboard corners in the frame.
        Returns (found, corners)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Flags: Adaptive thresh + Fast check + Normalize image
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE
        found, corners = cv2.findChessboardCorners(gray, self.pattern_size, flags)
        
        if found:
            # Refine corners
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
        return found, corners

    def calibrate(self, images_points, image_size):
        """
        Run calibration on collected points.
        images_points: List of arrays of corners found in images.
        image_size: (width, height)
        """
        # Prepare object points (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
        objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
        objp = objp * self.square_size_mm
        
        obj_points = [objp] * len(images_points) # Same for all images
        
        try:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                obj_points, images_points, image_size, None, None
            )
            
            if ret:
                self.camera_matrix = mtx
                self.dist_coeffs = dist
                
                # Compute optimal new camera matrix (alpha=0 ensures full FOV)
                h, w = image_size
                newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 0, (w,h), centerPrincipalPoint=True)
                # self.new_camera_matrix = newcameramtx # We calculate this dynamic now
                self.roi = roi
                
                _logger.info(f"Calibration successful. RMS Error: {ret:.4f}")
                self.save_calibration()
                return True, ret
            
            return False, 0.0
            
        except Exception as e:
            _logger.error(f"Calibration failed: {e}")
            return False, 0.0

    def get_undistorted_frame(self, frame):
        """Apply distortion correction to frame."""
        if self.camera_matrix is None or self.dist_coeffs is None:
            return frame
            
        h, w = frame.shape[:2]
        
        # Determine if we need to re-compute optimal matrix (e.g. if loaded one is alpha=1 or resolution changed)
        # We enforce alpha=0 (Keep All Pixels) logic here to solve "Cut Off" issue.
        if not hasattr(self, '_cache_res') or self._cache_res != (w, h):
            newcameramtx, roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.dist_coeffs, (w,h), 0, (w,h), centerPrincipalPoint=True)
            self._cached_new_matrix = newcameramtx
            self._cached_roi = roi
            self._cache_res = (w, h)
            
        # Rectify
        dst = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs, None, self._cached_new_matrix)
        
        return dst

    def save_calibration(self):
        """Save current calibration to Managed Settings."""
        if self.camera_matrix is None: return
        
        # Save active state
        self.plugin.save_setting("active", self.active)
        
        self.plugin.save_setting("camera_matrix", self.camera_matrix.tolist())
        self.plugin.save_setting("dist_coeffs", self.dist_coeffs.tolist())
        self.plugin.save_setting("roi", self.roi)
        
        _logger.info("Saved calibration to Managed Settings")

    def load_calibration(self):
        """Load calibration from Managed Settings."""
        mtx_list = self.plugin.get_setting("camera_matrix")
        dist_list = self.plugin.get_setting("dist_coeffs")
        roi_data = self.plugin.get_setting("roi")
        
        if mtx_list and dist_list:
            try:
                self.camera_matrix = np.array(mtx_list)
                self.dist_coeffs = np.array(dist_list)
                self.roi = tuple(roi_data) if roi_data else None
                _logger.info("Loaded lens calibration data")
            except Exception as e:
                _logger.error(f"Failed to load calibration: {e}")
        else:
             _logger.info("No calibration data found in settings")

    def generate_pattern_image(self, width=800, height=600):
        """
        Generate a synthetic image of the chessboard pattern for printing/display.
        Returns numpy image (BGR).
        """
        # Create white image
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img.fill(255)
        
        # Margins
        margin = 40
        
        # Calculate square size to fit content
        rows, cols = self.pattern_size[1] + 1, self.pattern_size[0] + 1 # Pattern size is inner corners
        
        avail_w = width - 2 * margin
        avail_h = height - 2 * margin
        
        sq_w = avail_w // cols
        sq_h = avail_h // rows
        sq = min(sq_w, sq_h)
        
        # Start pos
        start_x = (width - (cols * sq)) // 2
        start_y = (height - (rows * sq)) // 2
        
        # Draw squares
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 1:
                    pt1 = (start_x + c*sq, start_y + r*sq)
                    pt2 = (start_x + (c+1)*sq, start_y + (r+1)*sq)
                    cv2.rectangle(img, pt1, pt2, (0,0,0), -1)
                    
        return img
