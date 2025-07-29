"""
GStreamer pipeline for handling PipeWire video streams
"""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GObject
from typing import Optional, Callable

# Initialize GStreamer
Gst.init(None)

class GStreamerPipeline:
    """Manages GStreamer pipeline for PipeWire video streams"""
    
    def __init__(self):
        self.pipeline: Optional[Gst.Pipeline] = None
        self.bus: Optional[Gst.Bus] = None
        self.sink: Optional[Gst.Element] = None
        
        # Callbacks
        self.on_frame_ready: Optional[Callable[[Gst.Sample], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
    def create_pipeline(self, node_id: int) -> bool:
        """
        Create GStreamer pipeline for PipeWire source
        
        Args:
            node_id: PipeWire node ID from portal
            
        Returns:
            True if pipeline created successfully
        """
        try:
            # Create pipeline
            pipeline_desc = (
                f"pipewiresrc path={node_id} ! "
                "video/x-raw,format=BGRx ! "
                "videoconvert ! "
                "video/x-raw,format=RGB ! "
                "appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
            )
            
            self.pipeline = Gst.parse_launch(pipeline_desc)
            
            if not self.pipeline:
                if self.on_error:
                    self.on_error("Failed to create GStreamer pipeline")
                return False
            
            # Get the appsink element
            self.sink = self.pipeline.get_by_name("sink")
            if not self.sink:
                if self.on_error:
                    self.on_error("Failed to get appsink element")
                return False
            
            # Connect to new-sample signal
            self.sink.connect("new-sample", self._on_new_sample)
            
            # Set up bus for error handling
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self._on_bus_message)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error creating pipeline: {str(e)}")
            return False
    
    def start(self) -> bool:
        """Start the pipeline"""
        if not self.pipeline:
            if self.on_error:
                self.on_error("No pipeline to start")
            return False
        
        try:
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                if self.on_error:
                    self.on_error("Failed to start pipeline")
                return False
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error starting pipeline: {str(e)}")
            return False
    
    def stop(self):
        """Stop the pipeline"""
        if self.pipeline:
            try:
                self.pipeline.set_state(Gst.State.NULL)
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Error stopping pipeline: {str(e)}")
    
    def _on_new_sample(self, sink: Gst.Element) -> Gst.FlowReturn:
        """Handle new video frame"""
        try:
            sample = sink.emit("pull-sample")
            if sample and self.on_frame_ready:
                self.on_frame_ready(sample)
            return Gst.FlowReturn.OK
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error processing frame: {str(e)}")
            return Gst.FlowReturn.ERROR
    
    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message):
        """Handle bus messages"""
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            if self.on_error:
                self.on_error(f"GStreamer error: {err.message}")
        elif message.type == Gst.MessageType.EOS:
            if self.on_error:
                self.on_error("End of stream")
    
    def get_frame_dimensions(self) -> tuple[int, int]:
        """Get current frame dimensions"""
        if not self.sink:
            return (0, 0)
        
        try:
            pad = self.sink.get_static_pad("sink")
            if pad:
                caps = pad.get_current_caps()
                if caps:
                    structure = caps.get_structure(0)
                    width = structure.get_int("width")[1]
                    height = structure.get_int("height")[1]
                    return (width, height)
        except:
            pass
        
        return (0, 0)
