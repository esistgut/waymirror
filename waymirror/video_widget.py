"""
Video display widget using Qt
"""

from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import numpy as np

class VideoWidget(QLabel):
    """Widget for displaying video frames from GStreamer"""
    
    frameReceived = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Widget setup
        self.setScaledContents(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black; border: 1px solid gray;")
        self.setText("No video feed")
        
        # Video properties
        self.frame_width = 0
        self.frame_height = 0
        
    def update_frame(self, sample: Gst.Sample):
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
                    self.setPixmap(pixmap)
                    
                    # Emit signal
                    self.frameReceived.emit()
                    
            finally:
                buffer.unmap(map_info)
                
        except Exception as e:
            print(f"Error updating frame: {e}")
    
    def get_frame_size(self) -> tuple[int, int]:
        """Get the current frame dimensions"""
        return (self.frame_width, self.frame_height)
