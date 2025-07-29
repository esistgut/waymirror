"""
Main application window
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QStatusBar, QMessageBox, QComboBox)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

from .portal import PortalHandler
from .gstreamer_pipeline import GStreamerPipeline
from .video_widget import VideoWidget

logger = logging.getLogger(__name__)

class CaptureThread(QThread):
    """Thread for handling the GLib main loop"""
    
    def __init__(self) -> None:
        super().__init__()
        self.main_loop: Optional[GLib.MainLoop] = None
        
    def run(self) -> None:
        """Run the GLib main loop"""
        self.main_loop = GLib.MainLoop()
        self.main_loop.run()
    
    def stop(self) -> None:
        """Stop the main loop"""
        if self.main_loop:
            self.main_loop.quit()

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self) -> None:
        super().__init__()
        
        self.setWindowTitle("WayMirror - Screen Capture")
        self.setGeometry(100, 100, 1024, 768)
        
        # Components
        self.portal_handler: Optional[PortalHandler] = None
        self.gstreamer_pipeline: Optional[GStreamerPipeline] = None
        self.capture_thread: Optional[CaptureThread] = None
        self.is_capturing: bool = False
        
        # UI Components (will be initialized in setup_ui)
        self.start_button: QPushButton
        self.aspect_ratio_combo: QComboBox
        self.video_widget: VideoWidget
        self.status_bar: QStatusBar
        self.info_label: QLabel
        
        self.setup_ui()
        self.setup_menu()
        
        # Start the capture thread for GLib main loop
        self.capture_thread = CaptureThread()
        self.capture_thread.start()
        
    def setup_ui(self) -> None:
        """Set up the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Buttons
        self.start_button = QPushButton("Start Capture")
        self.start_button.clicked.connect(self.toggle_capture)
        
        control_layout.addWidget(self.start_button)
        
        # Aspect ratio selector
        aspect_label = QLabel("Aspect Ratio:")
        control_layout.addWidget(aspect_label)
        
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItem("Respect Source", "source")
        self.aspect_ratio_combo.addItem("Adapt to Window", "window")
        self.aspect_ratio_combo.setCurrentIndex(0)  # Default to "Respect Source"
        self.aspect_ratio_combo.currentTextChanged.connect(self.on_aspect_ratio_changed)
        control_layout.addWidget(self.aspect_ratio_combo)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # Video display
        self.video_widget = VideoWidget()
        layout.addWidget(self.video_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Info label
        self.info_label = QLabel("Click 'Start Capture' to begin screen capture")
        layout.addWidget(self.info_label)
    
    def setup_menu(self) -> None:
        """Set up the menu bar"""
        menubar = self.menuBar()
        assert menubar is not None
        
        # File menu
        file_menu = menubar.addMenu("File")
        assert file_menu is not None
        
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        assert help_menu is not None
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def toggle_capture(self) -> None:
        """Toggle screen capture on/off"""
        if not self.is_capturing:
            self.start_capture()
        else:
            self.stop_capture()
    
    def on_aspect_ratio_changed(self, text: str) -> None:
        """Handle aspect ratio selection change"""
        if self.video_widget:
            aspect_mode = self.aspect_ratio_combo.currentData()
            if aspect_mode == "source":
                self.video_widget.set_aspect_ratio_mode("source")
                self.info_label.setText("Aspect ratio: Respecting source dimensions")
            elif aspect_mode == "window":
                self.video_widget.set_aspect_ratio_mode("window") 
                self.info_label.setText("Aspect ratio: Adapted to window")
            logger.info(f"Aspect ratio mode changed to: {aspect_mode}")
    
    def start_capture(self) -> None:
        """Start screen capture"""
        try:
            logger.info("Starting screen capture...")
            
            # Initialize portal handler
            logger.info("Initializing portal handler...")
            self.portal_handler = PortalHandler()
            self.portal_handler.on_stream_ready = self.on_stream_ready
            self.portal_handler.on_error = self.on_portal_error
            
            # Start capture
            self.status_bar.showMessage("Starting capture...")
            self.start_button.setEnabled(False)
            
            logger.info("Calling portal start_capture...")
            if self.portal_handler.start_capture():
                self.info_label.setText("Requesting screen capture permission...")
                logger.info("Portal start_capture returned True")
            else:
                logger.error("Portal start_capture returned False")
                self.on_portal_error("Failed to start capture")
                
        except Exception as e:
            logger.error(f"Exception in start_capture: {e}")
            import traceback
            traceback.print_exc()
            self.on_portal_error(f"Error starting capture: {str(e)}")
    
    def stop_capture(self) -> None:
        """Stop screen capture"""
        try:
            self.status_bar.showMessage("Stopping capture...")
            
            # Stop GStreamer pipeline
            if self.gstreamer_pipeline:
                self.gstreamer_pipeline.stop()
                self.gstreamer_pipeline = None
            
            # Stop portal
            if self.portal_handler:
                self.portal_handler.stop_capture()
                self.portal_handler = None
            
            self.is_capturing = False
            self.start_button.setText("Start Capture")
            self.start_button.setEnabled(True)
            self.video_widget.setText("No video feed")
            self.video_widget.clear()  # Clear the pixmap properly
            self.info_label.setText("Capture stopped")
            self.status_bar.showMessage("Ready")
            
        except Exception as e:
            self.show_error(f"Error stopping capture: {str(e)}")
    
    def on_stream_ready(self, node_id: int) -> None:
        """Handle when stream is ready from portal"""
        try:
            self.status_bar.showMessage("Stream ready, setting up pipeline...")
            
            # Create GStreamer pipeline
            self.gstreamer_pipeline = GStreamerPipeline()
            self.gstreamer_pipeline.on_frame_ready = self.video_widget.update_frame
            self.gstreamer_pipeline.on_error = self.on_gstreamer_error
            
            if self.gstreamer_pipeline.create_pipeline(node_id):
                if self.gstreamer_pipeline.start():
                    self.is_capturing = True
                    self.start_button.setText("Stop Capture")
                    self.start_button.setEnabled(True)
                    self.info_label.setText(f"Capturing from PipeWire node: {node_id}")
                    self.status_bar.showMessage("Capturing...")
                else:
                    self.on_gstreamer_error("Failed to start pipeline")
            else:
                self.on_gstreamer_error("Failed to create pipeline")
                
        except Exception as e:
            self.on_gstreamer_error(f"Error setting up stream: {str(e)}")
    
    def on_portal_error(self, error: str) -> None:
        """Handle portal errors"""
        self.show_error(f"Portal error: {error}")
        self.start_button.setEnabled(True)
        self.status_bar.showMessage("Error")
        self.info_label.setText(f"Error: {error}")
    
    def on_gstreamer_error(self, error: str) -> None:
        """Handle GStreamer errors"""
        self.show_error(f"GStreamer error: {error}")
        self.stop_capture()
    
    def show_error(self, message: str) -> None:
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
    
    def show_about(self) -> None:
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About WayMirror",
            "WayMirror - Screen Capture for Wayland\n\n"
            "Uses FreeDesktop Portal API and GStreamer\n"
            "for real-time screen capture on Wayland."
        )
    
    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        """Handle window close event"""
        if self.is_capturing:
            self.stop_capture()
        
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.wait(1000)  # Wait up to 1 second
        
        if event:
            event.accept()
