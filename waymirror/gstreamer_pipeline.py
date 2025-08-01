"""
GStreamer pipeline for handling PipeWire video streams with multiple outputs
"""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import Gst, GstVideo, GstWebRTC, GstSdp, GObject
from typing import Optional, Callable, Tuple, Dict, Any
import logging
import uuid

# Initialize GStreamer
Gst.init(None)

logger = logging.getLogger(__name__)

class GStreamerPipeline:
    """Manages GStreamer pipeline for PipeWire video streams with multiple outputs"""
    
    def __init__(self) -> None:
        self.pipeline: Optional[Gst.Pipeline] = None
        self.bus: Optional[Gst.Bus] = None
        self.preview_sink: Optional[Gst.Element] = None
        self.tee: Optional[Gst.Element] = None
        self.webrtc_peers: Dict[str, Gst.Element] = {}
        
        # Callbacks
        self.on_frame_ready: Optional[Callable[[Gst.Sample], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_webrtc_offer: Optional[Callable[[str, str], None]] = None
        self.on_webrtc_ice: Optional[Callable[[str, int, str], None]] = None
        
    def create_pipeline(self, node_id: int) -> bool:
        """
        Create GStreamer pipeline for PipeWire source with tee for multiple outputs
        
        Args:
            node_id: PipeWire node ID from portal
            
        Returns:
            True if pipeline created successfully
        """
        try:
            # Create pipeline with tee for multiple outputs
            pipeline_desc = (
                f"pipewiresrc path={node_id} ! "
                "video/x-raw ! "
                "videoconvert ! "
                "tee name=t ! "
                "queue ! videoconvert ! video/x-raw,format=RGB ! "
                "appsink name=preview_sink emit-signals=true sync=false max-buffers=1 drop=true"
            )
            
            self.pipeline = Gst.parse_launch(pipeline_desc)
            
            if not self.pipeline:
                if self.on_error:
                    self.on_error("Failed to create GStreamer pipeline")
                return False
            
            # Get the tee element for adding WebRTC branches
            self.tee = self.pipeline.get_by_name("t")
            if not self.tee:
                if self.on_error:
                    self.on_error("Failed to get tee element")
                return False
            
            # Get the preview appsink element
            self.preview_sink = self.pipeline.get_by_name("preview_sink")
            if not self.preview_sink:
                if self.on_error:
                    self.on_error("Failed to get preview appsink element")
                return False
            
            # Connect to new-sample signal for preview
            self.preview_sink.connect("new-sample", self._on_new_sample)
            
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
    
    def stop(self) -> None:
        """Stop the pipeline"""
        if self.pipeline:
            try:
                self.pipeline.set_state(Gst.State.NULL)
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Error stopping pipeline: {str(e)}")
    
    def _on_new_sample(self, sink: Gst.Element) -> Gst.FlowReturn:
        """Handle new video frame for preview"""
        try:
            sample = sink.emit("pull-sample")
            if sample and self.on_frame_ready:
                self.on_frame_ready(sample)
            return Gst.FlowReturn.OK
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error processing frame: {str(e)}")
            return Gst.FlowReturn.ERROR
    
    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> None:
        """Handle bus messages"""
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            if self.on_error:
                self.on_error(f"GStreamer error: {err.message}")
        elif message.type == Gst.MessageType.EOS:
            if self.on_error:
                self.on_error("End of stream")
    
    def get_frame_dimensions(self) -> Tuple[int, int]:
        """Get current frame dimensions"""
        if not self.preview_sink:
            return (0, 0)
        
        try:
            pad = self.preview_sink.get_static_pad("sink")
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
    
    def add_webrtc_peer(self, peer_id: str) -> bool:
        """Add a WebRTC peer to the pipeline"""
        try:
            if peer_id in self.webrtc_peers:
                logger.warning(f"WebRTC peer {peer_id} already exists")
                return False
            
            # Create webrtcbin element
            webrtc = Gst.ElementFactory.make("webrtcbin", f"webrtc_{peer_id}")
            if not webrtc:
                logger.error("Failed to create webrtcbin element")
                return False
            
            # Configure for low latency
            webrtc.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)
            webrtc.set_property("ice-transport-policy", GstWebRTC.WebRTCICETransportPolicy.ALL)
            
            # Create encoder branch
            encoder_desc = (
                "queue max-size-buffers=1 leaky=downstream ! "
                "videoconvert ! "
                "video/x-raw,format=I420 ! "
                "vp8enc target-bitrate=2000000 deadline=1 cpu-used=4 keyframe-max-dist=30 ! "
                "rtpvp8pay ! "
                "queue max-size-buffers=1 leaky=downstream"
            )
            
            encoder_bin = Gst.parse_bin_from_description(encoder_desc, True)
            if not encoder_bin:
                logger.error("Failed to create encoder bin")
                return False
            
            # Add elements to pipeline
            self.pipeline.add(encoder_bin)
            self.pipeline.add(webrtc)
            
            # Connect tee to encoder
            tee_pad = self.tee.get_request_pad("src_%u")
            encoder_sink_pad = encoder_bin.get_static_pad("sink")
            if tee_pad and encoder_sink_pad:
                if tee_pad.link(encoder_sink_pad) != Gst.PadLinkReturn.OK:
                    logger.error("Failed to link tee to encoder")
                    return False
            else:
                logger.error("Failed to get pads for tee-encoder link")
                return False
            
            # Connect encoder to webrtc
            encoder_src_pad = encoder_bin.get_static_pad("src")
            webrtc_sink_pad = webrtc.get_request_pad("sink_0")
            if encoder_src_pad and webrtc_sink_pad:
                if encoder_src_pad.link(webrtc_sink_pad) != Gst.PadLinkReturn.OK:
                    logger.error("Failed to link encoder to webrtc")
                    return False
            else:
                logger.error("Failed to get pads for encoder-webrtc link")
                return False
            
            # Connect WebRTC signals
            webrtc.connect("on-negotiation-needed", self._on_negotiation_needed, peer_id)
            webrtc.connect("on-ice-candidate", self._on_ice_candidate, peer_id)
            
            # Sync state with parent
            encoder_bin.sync_state_with_parent()
            webrtc.sync_state_with_parent()
            
            # Store the peer
            self.webrtc_peers[peer_id] = {
                'webrtc': webrtc,
                'encoder': encoder_bin,
                'tee_pad': tee_pad
            }
            
            logger.info(f"WebRTC peer {peer_id} added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding WebRTC peer {peer_id}: {e}")
            return False
    
    def remove_webrtc_peer(self, peer_id: str) -> bool:
        """Remove a WebRTC peer from the pipeline"""
        try:
            if peer_id not in self.webrtc_peers:
                logger.warning(f"WebRTC peer {peer_id} not found")
                return False
            
            peer_data = self.webrtc_peers[peer_id]
            webrtc = peer_data['webrtc']
            encoder = peer_data['encoder']
            tee_pad = peer_data['tee_pad']
            
            # Stop elements
            webrtc.set_state(Gst.State.NULL)
            encoder.set_state(Gst.State.NULL)
            
            # Remove from pipeline
            self.pipeline.remove(webrtc)
            self.pipeline.remove(encoder)
            
            # Release tee pad
            if tee_pad:
                self.tee.release_request_pad(tee_pad)
            
            # Remove from tracking
            del self.webrtc_peers[peer_id]
            
            logger.info(f"WebRTC peer {peer_id} removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error removing WebRTC peer {peer_id}: {e}")
            return False
    
    def set_webrtc_remote_description(self, peer_id: str, sdp: str, sdp_type: str) -> bool:
        """Set remote description for WebRTC peer"""
        try:
            if peer_id not in self.webrtc_peers:
                logger.error(f"WebRTC peer {peer_id} not found")
                return False
            
            webrtc = self.webrtc_peers[peer_id]['webrtc']
            
            # Parse SDP type
            if sdp_type == "answer":
                gst_sdp_type = GstWebRTC.WebRTCSDPType.ANSWER
            elif sdp_type == "offer":
                gst_sdp_type = GstWebRTC.WebRTCSDPType.OFFER
            else:
                logger.error(f"Unknown SDP type: {sdp_type}")
                return False
            
            # Create SDP message
            ret, sdp_msg = GstSdp.SDPMessage.new_from_text(sdp)
            if ret != GstSdp.SDPResult.OK:
                logger.error("Failed to parse SDP")
                return False
            
            # Create session description
            session_desc = GstWebRTC.WebRTCSessionDescription.new(gst_sdp_type, sdp_msg)
            
            # Set remote description
            promise = Gst.Promise.new()
            webrtc.emit("set-remote-description", session_desc, promise)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting remote description for peer {peer_id}: {e}")
            return False
    
    def add_webrtc_ice_candidate(self, peer_id: str, mline_index: int, candidate: str) -> bool:
        """Add ICE candidate for WebRTC peer"""
        try:
            if peer_id not in self.webrtc_peers:
                logger.error(f"WebRTC peer {peer_id} not found")
                return False
            
            webrtc = self.webrtc_peers[peer_id]['webrtc']
            webrtc.emit("add-ice-candidate", mline_index, candidate)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding ICE candidate for peer {peer_id}: {e}")
            return False
    
    def _on_negotiation_needed(self, webrtc: Gst.Element, peer_id: str) -> None:
        """Handle WebRTC negotiation needed"""
        try:
            logger.info(f"Negotiation needed for peer {peer_id}")
            promise = Gst.Promise.new()
            webrtc.emit("create-offer", None, promise)
            
            # Use GLib.idle_add to handle the promise result
            from gi.repository import GLib
            GLib.idle_add(self._check_offer_promise, promise, peer_id)
            
        except Exception as e:
            logger.error(f"Error in negotiation for peer {peer_id}: {e}")
    
    def _check_offer_promise(self, promise: Gst.Promise, peer_id: str) -> bool:
        """Check the offer creation promise"""
        try:
            # Wait for promise to complete
            result = promise.wait()
            if result == Gst.PromiseResult.REPLIED:
                self._on_offer_created(promise, peer_id)
            else:
                logger.error(f"Offer creation failed for peer {peer_id}: {result}")
            return False  # Don't repeat this idle callback
        except Exception as e:
            logger.error(f"Error checking offer promise for peer {peer_id}: {e}")
            return False
    
    def _on_offer_created(self, promise: Gst.Promise, peer_id: str) -> None:
        """Handle created offer"""
        try:
            reply = promise.get_reply()
            if not reply:
                logger.error(f"No reply in offer creation for peer {peer_id}")
                return
                
            offer = reply.get_value("offer")
            if not offer:
                logger.error(f"No offer in reply for peer {peer_id}")
                return
            
            webrtc = self.webrtc_peers.get(peer_id, {}).get('webrtc')
            if not webrtc:
                logger.error(f"WebRTC element not found for peer {peer_id}")
                return
            
            # Set local description
            promise = Gst.Promise.new()
            webrtc.emit("set-local-description", offer, promise)
            
            # Send offer to client via callback
            if self.on_webrtc_offer:
                sdp = offer.sdp.as_text()
                self.on_webrtc_offer(peer_id, sdp)
                
        except Exception as e:
            logger.error(f"Error creating offer for peer {peer_id}: {e}")
    
    def _on_ice_candidate(self, webrtc: Gst.Element, mline_index: int, candidate: str, peer_id: str) -> None:
        """Handle ICE candidate"""
        try:
            if self.on_webrtc_ice:
                self.on_webrtc_ice(peer_id, mline_index, candidate)
        except Exception as e:
            logger.error(f"Error handling ICE candidate for peer {peer_id}: {e}")
