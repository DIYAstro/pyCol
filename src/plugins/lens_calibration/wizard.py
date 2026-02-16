import cv2
import numpy as np
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QStackedWidget, QProgressBar, 
                               QFileDialog, QMessageBox, QWidget)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor

class CalibrationWizard(QDialog):
    """
    Wizard to guide user through lens calibration.
    Steps:
    1. Intro & Pattern Generation
    2. Image Capture (requires ~10-15 images)
    3. Processing
    4. Result & Save
    """
    
    def __init__(self, camera_thread, calibration_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lens Calibration Wizard")
        self.resize(800, 600)
        
        self.thread = camera_thread
        self.manager = calibration_manager
        
        # State
        self.captured_images = [] # Lists of (found, corners, gray_frame)
        self.min_images = 10
        self.pattern_size = self.manager.pattern_size
        
        # UI
        self.layout = QVBoxLayout(self)
        
        # Stack
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # Pages
        self.page_intro = self.create_intro_page()
        self.page_capture = self.create_capture_page()
        self.page_processing = self.create_processing_page()
        self.page_result = self.create_result_page()
        
        self.stack.addWidget(self.page_intro)
        self.stack.addWidget(self.page_capture)
        self.stack.addWidget(self.page_processing)
        self.stack.addWidget(self.page_result)
        
        # Buttons
        self.layout_buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.go_next)
        
        self.layout_buttons.addWidget(self.btn_cancel)
        self.layout_buttons.addStretch()
        self.layout_buttons.addWidget(self.btn_next)
        self.layout.addLayout(self.layout_buttons)
        
        # Connect Camera Signal for Live View
        self.thread.change_pixmap_signal.connect(self.update_live_view)
        
        # Internal processing loop trigger
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_frame)
        
        # Current frame buffer
        self.current_frame = None
        self.corners_found = False
        self.current_corners = None
        
    def create_intro_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        
        # Left Side: Instructions
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        lbl_title = QLabel("<h2>Step 1: Preparation</h2>")
        lbl_text = QLabel(
            "<p style='font-size: 14px;'>Lens calibration corrects optical distortion ('fisheye' effect) "
            "to ensure precise measurements.</p>"
            "<h3>Instructions:</h3>"
            "<ol style='font-size: 13px; line-height: 1.4;'>"
            "<li><b>Print the Pattern:</b> Use the buttons below to save or print the chessboard. <br><i>(Tip: Print in Landscape/Querformat for best fit)</i></li>"
            "<li><b>Mount Flat:</b> Tape the paper onto a rigid, flat surface (clipboard, wall, or board). "
            "Do not let it bend!</li>"
            "<li><b>Capture:</b> In the next step, you will take about 15 photos from different angles.</li>"
            "</ol>"
        )
        lbl_text.setWordWrap(True)
        lbl_text.setTextFormat(Qt.RichText)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 Save Image...")
        btn_save.setToolTip("Save as PNG file")
        btn_save.clicked.connect(self.save_pattern)
        
        btn_print = QPushButton("🖨️ Print Direct...")
        btn_print.setToolTip("Send directly to printer")
        btn_print.clicked.connect(self.print_pattern)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_print)
        btn_layout.addStretch()
        
        left_layout.addWidget(lbl_title)
        left_layout.addWidget(lbl_text)
        left_layout.addSpacing(20)
        left_layout.addLayout(btn_layout)
        left_layout.addStretch()
        
        # Right Side: Preview Image
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        lbl_preview_title = QLabel("<b>Pattern Preview (9x6)</b>")
        lbl_preview_title.setAlignment(Qt.AlignCenter)
        
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(300, 220)
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("border: 1px solid #555; background-color: white;")
        
        # Generate Preview
        preview_img = self.manager.generate_pattern_image(300, 220)
        # Convert BGR to RGB for Qt
        preview_rgb = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
        h, w, ch = preview_rgb.shape
        qimg = QImage(preview_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.lbl_preview.setPixmap(QPixmap.fromImage(qimg))
        
        right_layout.addWidget(lbl_preview_title)
        right_layout.addWidget(self.lbl_preview)
        right_layout.addStretch()
        
        layout.addWidget(left_widget, 1) # 66% width
        layout.addWidget(right_widget, 0) # Auto width
        
        return page

    def create_capture_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl_title = QLabel("<h2>Step 2: Image Capture</h2>")
        self.lbl_capture_status = QLabel(f"Captured: 0 / {self.min_images}")
        self.lbl_capture_status.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Live View Label
        self.lbl_feed = QLabel()
        self.lbl_feed.setAlignment(Qt.AlignCenter)
        self.lbl_feed.setStyleSheet("background-color: #000; border: 1px solid #444;")
        self.lbl_feed.setMinimumSize(640, 480)
        
        self.btn_capture = QPushButton("📸 Capture Frame")
        self.btn_capture.clicked.connect(self.capture_frame)
        self.btn_capture.setEnabled(False)
        self.btn_capture.setStyleSheet("font-size: 14px; padding: 10px;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_capture_status)
        layout.addWidget(self.lbl_feed, 1)
        layout.addWidget(self.btn_capture)
        return page

    def create_processing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl_title = QLabel("<h2>Step 3: Processing</h2>")
        self.lbl_proc_status = QLabel("Calibrating...")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        
        layout.addWidget(lbl_title)
        layout.addStretch()
        layout.addWidget(self.lbl_proc_status)
        layout.addWidget(self.progress)
        layout.addStretch()
        return page
        
    def create_result_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl_title = QLabel("<h2>Step 4: Calibration Result</h2>")
        self.lbl_result = QLabel("Result Placeholder")
        self.lbl_result.setWordWrap(True)
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_result)
        layout.addStretch()
        return page

    def go_next(self):
        idx = self.stack.currentIndex()
        
        if idx == 0: # Intro -> Capture
            self.stack.setCurrentIndex(1)
            self.btn_next.setEnabled(False) # Wait for captures
            self.timer.start(100) # Check for corners periodically (10fps is enough for detection UI)
            
        elif idx == 1: # Capture -> Processing
            self.timer.stop()
            self.stack.setCurrentIndex(2)
            self.btn_next.setEnabled(False)
            self.btn_next.setVisible(False)
            self.btn_cancel.setVisible(False)
            # Run Calibration
            self.run_calibration()
            
        elif idx == 2: # Processing -> Result (Auto transition usually)
            pass
            
        elif idx == 3: # Result -> Finish
            self.accept()

    def update_live_view(self, qt_img):
        # We need the raw CV image for detection
        
        # Let's convert QImage to numpy for detection (It's fast enough for 640x480 or even HD)
        if self.stack.currentIndex() != 1:
            return
            
        self.display_image = qt_img.copy()
        
        # Convert for OpenCV processing
        # QImage -> ptr -> numpy
        ptr = qt_img.constBits()
        w, h = qt_img.width(), qt_img.height()
        arr = np.array(ptr).reshape(h, w, 4) if qt_img.format() == QImage.Format_RGB32 else np.array(ptr).reshape(h, w, 3)
        
        # Only process every Nth frame or use timer buffer
        self.current_frame = arr.copy() # Store for capture
        
        # Update UI Feed
        # We will draw valid corners if found (done in timer loop for performance or here?)
        # Let's draw here if we have cached corners from timer
        
        pix = QPixmap.fromImage(qt_img)
        
        if self.corners_found and self.current_corners is not None:
             # Draw corners on pixmap using QPainter
             painter = QPainter(pix)
             painter.setPen(QPen(QColor(0, 255, 0), 3))
             for c in self.current_corners:
                 x, y = c[0]
                 painter.drawPoint(int(x), int(y))
             painter.end()
             self.btn_capture.setEnabled(True)
             self.btn_capture.setText(f"📸 Capture Frame ({len(self.captured_images)}/{self.min_images})")
        else:
             self.btn_capture.setEnabled(False)
             self.btn_capture.setText("No Pattern Detected")
             
        self.lbl_feed.setPixmap(pix.scaled(self.lbl_feed.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def process_frame(self):
        """Called by timer to search for corners."""
        if self.current_frame is None: return
        
        frame_rgb = self.current_frame
        
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        
        found, corners = cv2.findChessboardCorners(gray, self.pattern_size, 
                                                 cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE)
        
        self.corners_found = found
        self.current_corners = corners
        
        if found:
            # Refine
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            self.current_corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), term)

    def capture_frame(self):
        if self.corners_found and self.current_frame is not None:
            # Store point data
            self.captured_images.append(self.current_corners)
            count = len(self.captured_images)
            self.lbl_capture_status.setText(f"Captured: {count} / {self.min_images}")
            
            # Flash Effect?
            
            if count >= self.min_images:
                self.btn_next.setEnabled(True)
                self.lbl_capture_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")

    def run_calibration(self):
        """Run calibration in background."""
        import threading
        t = threading.Thread(target=self._worker_calibrate)
        t.start()
        
    def _worker_calibrate(self):
        # Prepare data
        img_points = self.captured_images
        
        # Get frame size from last captured
        h, w = self.current_frame.shape[:2]
        
        success, rms = self.manager.calibrate(img_points, (w, h))
        
        # Update UI in main thread
        from PySide6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(self, "on_calibration_finished", 
                               Qt.QueuedConnection,
                               Q_ARG(bool, success),
                               Q_ARG(float, rms))

    @Slot(bool, float)
    def on_calibration_finished(self, success, rms):
        self.btn_next.setVisible(True)
        self.btn_next.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.stack.setCurrentIndex(3)
        
        if success:
            self.lbl_result.setText(
                f"<h2>Calibration Successful! ✅</h2>"
                f"<p>RMS Error: <b>{rms:.4f} pixels</b></p>"
                f"<p>A lower error means better precision. values < 1.0 are good.</p>"
            )
            self.btn_next.setText("Finish")
            # Save is automatic in manager, but kept here for logical flow
        else:
            self.lbl_result.setText("<h2>Calibration Failed ❌</h2><p>Could not converge. Please try again with more diverse angles.</p>")
            self.btn_next.setText("Close")

    def save_pattern(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Pattern", "chessboard_pattern.png", "Images (*.png)")
        if path:
            img = self.manager.generate_pattern_image(1024, 768) # A4ish ratio
            cv2.imwrite(path, img)
            QMessageBox.information(self, "Saved", f"Pattern saved to {path}")

    def print_pattern(self):
        """Send pattern to printer."""
        try:
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        except ImportError:
            QMessageBox.warning(self, "Printing Not Supported", 
                              "The printing module is not available.\nPlease save the image and print it manually.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.Accepted:
            img_cv = self.manager.generate_pattern_image(2400, 1600)
            
            # Convert to QImage
            # CV2 is BGR, QImage needs RGB
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            qt_img = QImage(img_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            
            painter = QPainter(printer)
            
            # Scale to fit printer page
            rect = printer.pageRect(QPrinter.DevicePixel).toRect()
            scaled_img = qt_img.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Center it
            x = (rect.width() - scaled_img.width()) // 2
            y = (rect.height() - scaled_img.height()) // 2
            
            painter.drawImage(x, y, scaled_img)
            painter.end()
