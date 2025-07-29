"""
Video display widget using Qt
"""

from typing import Optional, Tuple
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QImage
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import numpy as np

class VideoWidget(QLabel):
    """Widget for displaying video frames from GStreamer"""
    
    frameReceived = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Widget setup
        self.setScaledContents(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black; border: 1px solid gray;")
        self.setText("No video feed")
        
        # Video properties
        self.frame_width: int = 0
        self.frame_height: int = 0
        
        # Aspect ratio mode: "source" or "window"
        self.aspect_ratio_mode: str = "source"
        
        # Apply initial scaling behavior
        self._update_scaling_behavior()
        
    def update_frame(self, sample: Gst.Sample) -> None:
        """Update the widget with a new video frame"""
        try:
            # Get buffer from sample
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            
            # Get video info from caps
            structure = caps.get_structure(0)
            width = structure.get_int("width")[1]
            height = structure.get_int("height")[1]
            
            self.frame_width = width
            self.frame_height = height
            
            # Map buffer to access data
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return
            
            try:
                # Convert buffer data to numpy array
                # Assuming RGB format from our pipeline
                data = np.frombuffer(map_info.data, dtype=np.uint8)
                
                # Reshape to image dimensions (height, width, 3 for RGB)
                if len(data) >= width * height * 3:
                    image_array = data[:width * height * 3].reshape((height, width, 3))
                    
                    # Create QImage from numpy array
                    qimage = QImage(
                        image_array.data,
                        width,
                        height,
                        width * 3,  # bytes per line
                        QImage.Format.Format_RGB888
                    )
                    
                    # Convert to QPixmap and display
                    pixmap = QPixmap.fromImage(qimage)
                    
                    # Apply aspect ratio scaling
                    self._apply_aspect_ratio_to_pixmap(pixmap)
                    
                    # Emit signal
                    self.frameReceived.emit()
                    
            finally:
                buffer.unmap(map_info)
                
        except Exception as e:
            print(f"Error updating frame: {e}")
    
    def get_frame_size(self) -> Tuple[int, int]:
        """Get the current frame dimensions"""
        return (self.frame_width, self.frame_height)
    
    def set_aspect_ratio_mode(self, mode: str) -> None:
        """Set aspect ratio mode: 'source' or 'window'"""
        if mode in ["source", "window"]:
            self.aspect_ratio_mode = mode
            self._update_scaling_behavior()
            # If we have a current pixmap, reapply the scaling
            if hasattr(self, 'pixmap') and self.pixmap() and not self.pixmap().isNull():
                current_pixmap = self.pixmap()
                self._apply_aspect_ratio_to_pixmap(current_pixmap)
    
    def _apply_aspect_ratio_to_pixmap(self, pixmap: QPixmap) -> None:
        """Apply the current aspect ratio mode to a pixmap"""
        if self.aspect_ratio_mode == "source":
            # Scale pixmap to maintain aspect ratio within widget bounds
            widget_size = self.size()
            scaled_pixmap = pixmap.scaled(
                widget_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
        else:
            # Use original pixmap - setScaledContents will handle stretching
            self.setPixmap(pixmap)
    
    def _update_scaling_behavior(self) -> None:
        """Update the scaling behavior based on aspect ratio mode"""
        if self.aspect_ratio_mode == "source":
            # Respect source aspect ratio - don't scale to fill completely
            self.setScaledContents(False)
            # Use alignment to center the content
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:  # window mode
            # Adapt to window - scale to fill the widget
            self.setScaledContents(True)
