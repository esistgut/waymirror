"""
Main application window
"""

import logging
from typing import Optional, Any
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QStatusBar, QMessageBox, QComboBox, QCheckBox, QSizePolicy)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

from .portal import PortalHandler
from .gstreamer_pipeline import GStreamerPipeline
from .video_widget import VideoWidget

# Try to import WebRTC server, handle gracefully if dependencies are missing
try:
    from .webrtc_server import WebRTCServer
    WEBRTC_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"WebRTC functionality not available: {e}")
    WebRTCServer = None
    WEBRTC_AVAILABLE = False

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
        self.webrtc_server: Optional[Any] = None
        self.capture_thread: Optional[CaptureThread] = None
        self.is_capturing: bool = False
        self.is_webrtc_streaming: bool = False
        
        # UI Components (will be initialized in setup_ui)
        self.start_button: QPushButton
        self.preview_checkbox: QCheckBox
        self.webrtc_checkbox: QCheckBox
        self.aspect_ratio_combo: QComboBox
        self.video_widget: VideoWidget
        self.status_bar: QStatusBar
        self.info_label: QLabel
        self.main_layout: QVBoxLayout  # Keep reference to main layout
        
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
        self.main_layout = layout  # Keep reference for later use
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Buttons
        self.start_button = QPushButton("Start Capture")
        self.start_button.clicked.connect(self.toggle_capture)
        
        control_layout.addWidget(self.start_button)
        
        # Preview checkbox
        self.preview_checkbox = QCheckBox("Preview")
        self.preview_checkbox.setChecked(True)  # Default to showing preview
        self.preview_checkbox.toggled.connect(self.on_preview_toggled)
        control_layout.addWidget(self.preview_checkbox)
        
        # WebRTC streaming checkbox
        self.webrtc_checkbox = QCheckBox("WebRTC Streaming")
        self.webrtc_checkbox.setChecked(False)
        if WEBRTC_AVAILABLE:
            self.webrtc_checkbox.toggled.connect(self.on_webrtc_toggled)
        else:
            self.webrtc_checkbox.setEnabled(False)
            self.webrtc_checkbox.setToolTip("WebRTC streaming requires aiohttp and aiohttp-cors packages")
        control_layout.addWidget(self.webrtc_checkbox)
        
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
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.video_widget)
        
        # Info label
        self.info_label = QLabel("Click 'Start Capture' to begin screen capture")
        layout.addWidget(self.info_label)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Initially show/hide video widget based on preview checkbox state
        if not self.preview_checkbox.isChecked():
            layout.removeWidget(self.video_widget)
            self.video_widget.hide()
            self.aspect_ratio_combo.setEnabled(False)
    
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
    
    def on_preview_toggled(self, checked: bool) -> None:
        """Handle preview checkbox toggle"""
        if self.video_widget:
            if checked:
                # Add video widget back to layout at position 1 (after control layout, before info label)
                self.main_layout.insertWidget(1, self.video_widget)
                self.video_widget.show()
                self.aspect_ratio_combo.setEnabled(True)
                # Restore window to reasonable size for video display
                self.resize(1024, 768)
                if self.is_capturing:
                    self.info_label.setText(f"Capturing with preview enabled")
                else:
                    self.info_label.setText("Click 'Start Capture' to begin screen capture")
                logger.info("Preview enabled")
            else:
                # Remove video widget from layout
                self.main_layout.removeWidget(self.video_widget)
                self.video_widget.hide()
                self.aspect_ratio_combo.setEnabled(False)
                # Resize window to compact size when no preview
                self.resize(400, 120)
                if self.is_capturing:
                    self.info_label.setText(f"Capturing (preview disabled)")
                else:
                    self.info_label.setText("Preview disabled - Click 'Start Capture' to begin screen capture")
                logger.info("Preview disabled")
        
        # Update the frame callback to respect preview state
        if self.gstreamer_pipeline:
            if checked:
                self.gstreamer_pipeline.on_frame_ready = self.video_widget.update_frame
            else:
                self.gstreamer_pipeline.on_frame_ready = None
    
    def on_webrtc_toggled(self, checked: bool) -> None:
        """Handle WebRTC streaming checkbox toggle"""
        logger.info(f"WebRTC checkbox toggled: {checked}")
        
        if not WEBRTC_AVAILABLE:
            self.webrtc_checkbox.setChecked(False)
            self.show_error("WebRTC streaming requires aiohttp and aiohttp-cors packages.\nPlease install them with: pip install aiohttp aiohttp-cors")
            return
            
        if checked and not self.is_capturing:
            # WebRTC requires capture to be active
            self.webrtc_checkbox.setChecked(False)
            self.show_error("Please start capture first before enabling WebRTC streaming")
            return
        
        if checked:
            # Start WebRTC streaming
            logger.info("Starting WebRTC streaming...")
            if self.portal_handler and hasattr(self.portal_handler, 'node_id') and self.portal_handler.node_id:
                if self.start_webrtc_streaming(self.portal_handler.node_id):
                    self.is_webrtc_streaming = True
                    self.info_label.setText(self.info_label.text() + " | WebRTC: http://localhost:8000")
                    logger.info("WebRTC streaming started")
                else:
                    self.webrtc_checkbox.setChecked(False)
                    self.show_error("Failed to start WebRTC streaming")
            else:
                self.webrtc_checkbox.setChecked(False)
                self.show_error("No active capture stream for WebRTC")
        else:
            # Stop WebRTC streaming
            logger.info("Stopping WebRTC streaming...")
            self.stop_webrtc_streaming()
            self.is_webrtc_streaming = False
            # Remove WebRTC info from label
            current_text = self.info_label.text()
            if " | WebRTC: http://localhost:8000" in current_text:
                self.info_label.setText(current_text.replace(" | WebRTC: http://localhost:8000", ""))
            logger.info("WebRTC streaming stopped")
    
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
            
            # Stop WebRTC streaming first
            if self.is_webrtc_streaming:
                self.stop_webrtc_streaming()
                self.webrtc_checkbox.setChecked(False)
                self.is_webrtc_streaming = False
            
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
            
            # Show the video widget and add it back to layout if preview is enabled
            if self.preview_checkbox.isChecked():
                if self.video_widget.parent() is None:
                    self.main_layout.insertWidget(1, self.video_widget)
                self.video_widget.show()
                self.video_widget.setText("No video feed")
                self.video_widget.clear()  # Clear the pixmap properly
                self.info_label.setText("Capture stopped")
            else:
                # Keep it hidden and removed from layout
                if self.video_widget.parent() is not None:
                    self.main_layout.removeWidget(self.video_widget)
                self.video_widget.hide()
                self.info_label.setText("Capture stopped (preview disabled)")
            
            self.status_bar.showMessage("Ready")
            
        except Exception as e:
            self.show_error(f"Error stopping capture: {str(e)}")
    
    def on_stream_ready(self, node_id: int) -> None:
        """Handle when stream is ready from portal"""
        try:
            self.status_bar.showMessage("Stream ready, setting up pipeline...")
            
            # Create GStreamer pipeline
            self.gstreamer_pipeline = GStreamerPipeline()
            
            # Set frame callback based on preview checkbox state
            if self.preview_checkbox.isChecked():
                self.gstreamer_pipeline.on_frame_ready = self.video_widget.update_frame
                # Ensure video widget is in layout and visible
                if self.video_widget.parent() is None:
                    self.main_layout.insertWidget(1, self.video_widget)
                self.video_widget.show()
            else:
                self.gstreamer_pipeline.on_frame_ready = None
                # Ensure video widget is removed from layout
                if self.video_widget.parent() is not None:
                    self.main_layout.removeWidget(self.video_widget)
                self.video_widget.hide()
                
            self.gstreamer_pipeline.on_error = self.on_gstreamer_error
            
            if self.gstreamer_pipeline.create_pipeline(node_id):
                if self.gstreamer_pipeline.start():
                    self.is_capturing = True
                    self.start_button.setText("Stop Capture")
                    self.start_button.setEnabled(True)
                    
                    # Update info based on preview state
                    if self.preview_checkbox.isChecked():
                        self.info_label.setText(f"Capturing from PipeWire node: {node_id}")
                    else:
                        self.info_label.setText(f"Capturing from PipeWire node: {node_id} (preview disabled)")
                        
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
    
    def start_webrtc_streaming(self, node_id: int) -> bool:
        """Start WebRTC streaming server"""
        if not WEBRTC_AVAILABLE or not WebRTCServer:
            logger.error("WebRTC server not available")
            return False
            
        try:
            if self.webrtc_server:
                self.stop_webrtc_streaming()
            
            self.webrtc_server = WebRTCServer(port=8000)
            
            # Connect the WebRTC server to the existing GStreamer pipeline
            if self.gstreamer_pipeline:
                self.webrtc_server.set_gstreamer_pipeline(self.gstreamer_pipeline)
            
            success = self.webrtc_server.start_server()
            if success:
                logger.info("WebRTC server started successfully")
                return True
            else:
                logger.error("Failed to start WebRTC server")
                return False
                
        except Exception as e:
            logger.error(f"Error starting WebRTC streaming: {e}")
            return False
    
    def stop_webrtc_streaming(self) -> None:
        """Stop WebRTC streaming server"""
        try:
            logger.info(f"stop_webrtc_streaming called, webrtc_server: {self.webrtc_server}")
            if self.webrtc_server:
                logger.info("Calling webrtc_server.stop_server()")
                self.webrtc_server.stop_server()
                self.webrtc_server = None
                logger.info("WebRTC server stopped and set to None")
            else:
                logger.info("No WebRTC server to stop")
        except Exception as e:
            logger.error(f"Error stopping WebRTC streaming: {e}")
            import traceback
            traceback.print_exc()
    
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
        
        if self.is_webrtc_streaming:
            self.stop_webrtc_streaming()
        
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.wait(1000)  # Wait up to 1 second
        
        if event:
            event.accept()
