"""
Portal API handler for screen capture using FreeDesktop Portal
"""

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from typing import Dict, Any, Optional, Callable, Union
import logging

logger = logging.getLogger(__name__)

class PortalHandler:
    """Handles communication with the FreeDesktop Portal API for screen capture"""
    
    def __init__(self) -> None:
        # Initialize D-Bus main loop
        DBusGMainLoop(set_as_default=True)
        
        try:
            self.bus = dbus.SessionBus()
            self.portal = self.bus.get_object(
                'org.freedesktop.portal.Desktop',
                '/org/freedesktop/portal/desktop'
            )
            self.screencast_iface = dbus.Interface(
                self.portal,
                'org.freedesktop.portal.ScreenCast'
            )
            logger.info("Portal initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing portal: {e}")
            raise
        
        self.session_handle: Optional[str] = None
        self.stream_node_id: Optional[int] = None
        self._signal_matches: list = []  # Track signal handlers for cleanup
        self._start_called: bool = False  # Track if Start has been called to prevent duplicates
        
        # Callbacks
        self.on_stream_ready: Optional[Callable[[int], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    def start_capture(self, output_type: str = "monitor") -> bool:
        """
        Start screen capture session
        
        Args:
            output_type: "monitor" or "window"
        
        Returns:
            True if session started successfully
        """
        try:
            # Get a unique token for the request
            import time
            token = f"waymirror{int(time.time() * 1000)}"
            
            # Create session options
            options = {
                'handle_token': dbus.String(token),
                'session_handle_token': dbus.String(f"session{token}")
            }
            
            logger.info("Creating Portal session...")
            create_response: Any = self.screencast_iface.CreateSession(options)
            
            # Connect to response using the actual path returned by Portal
            if isinstance(create_response, str):
                match = self.bus.add_signal_receiver(
                    self._on_create_session_response,
                    signal_name='Response',
                    dbus_interface='org.freedesktop.portal.Request',
                    path=create_response
                )
                self._signal_matches.append(match)
            else:
                logger.error(f"Unexpected response type: {type(create_response)}")
                if self.on_error:
                    self.on_error("Unexpected response from CreateSession")
                return False
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error starting capture: {str(e)}")
            logger.error(f"Error starting capture: {str(e)}")
            return False
    
    def _on_create_session_response(self, response: int, results: Dict[str, Any]) -> None:
        """Handle CreateSession response"""
        logger.info(f"CreateSession response received: response={response}, results={results}")
        
        if response != 0:
            logger.error(f"CreateSession failed with response code: {response}")
            if self.on_error:
                self.on_error("Failed to create session")
            return
        
        try:
            self.session_handle = results.get('session_handle')
            logger.info(f"Session handle: {self.session_handle}")
            
            if not self.session_handle:
                logger.error("No session handle received in response")
                if self.on_error:
                    self.on_error("No session handle received")
                return
            
            # Now select sources
            logger.info("Proceeding to select sources...")
            self._select_sources()
            
        except Exception as e:
            logger.error(f"Error in create session response: {str(e)}")
            if self.on_error:
                self.on_error(f"Error in create session response: {str(e)}")
    
    def _select_sources(self) -> None:
        """Select capture sources"""
        try:
            # Get a unique token for the request
            import time
            token = f"waymirror{int(time.time() * 1000)}"
            
            # Select sources options - try with different settings
            select_options = {
                'handle_token': dbus.String(token),
                'types': dbus.UInt32(1),  # Monitor = 1
                'multiple': dbus.Boolean(False),  # Single selection might work better
                'cursor_mode': dbus.UInt32(2),  # Embedded cursor = 2
            }
            
            logger.info("Selecting capture sources...")
            logger.info(f"SelectSources options: {select_options}")
            select_response: Any = self.screencast_iface.SelectSources(
                self.session_handle,
                select_options
            )
            
            # Connect to response signal using the actual path returned
            if isinstance(select_response, str):
                logger.info(f"SelectSources request path: {select_response}")
                match = self.bus.add_signal_receiver(
                    self._on_select_sources_response,
                    signal_name='Response',
                    dbus_interface='org.freedesktop.portal.Request',
                    path=select_response
                )
                self._signal_matches.append(match)
            else:
                logger.error(f"SelectSources unexpected response type: {type(select_response)}")
                if self.on_error:
                    self.on_error("Unexpected response from SelectSources")
            
        except Exception as e:
            logger.error(f"Error selecting sources: {str(e)}")
            if self.on_error:
                self.on_error(f"Error selecting sources: {str(e)}")
    
    def _on_select_sources_response(self, response: int, results: Dict[str, Any]) -> None:
        """Handle SelectSources response"""
        logger.info(f"SelectSources response received: response={response}, results={results}")
        
        if response != 0:
            logger.error(f"SelectSources failed with response code: {response}")
            if self.on_error:
                self.on_error("User cancelled source selection or error occurred")
            return
        
        # Check if we have streams in the results - only proceed if we do
        streams = results.get('streams', [])
        if not streams:
            logger.info("No streams in SelectSources response - trying to call Start anyway...")
            # Sometimes the streams are provided in the Start response instead
            # Let's try calling Start even without streams in SelectSources
        else:
            logger.info(f"User selected {len(streams)} stream(s), proceeding to start...")
        
        # Prevent duplicate Start calls
        if self._start_called:
            logger.info("Start already called, ignoring duplicate SelectSources response")
            return
        
        try:
            # Mark that we're calling Start to prevent duplicates
            self._start_called = True
            
            # Get a unique token for the request
            import time
            token = f"waymirror{int(time.time() * 1000)}"
            
            # Start options
            start_options = {
                'handle_token': dbus.String(token)
            }
            
            logger.info("Calling Start...")
            start_response: Any = self.screencast_iface.Start(
                self.session_handle,
                "",  # parent_window - empty string
                start_options
            )
            
            # Connect to response signal using the actual path returned
            if isinstance(start_response, str):
                logger.info(f"Start request path: {start_response}")
                match = self.bus.add_signal_receiver(
                    self._on_start_response,
                    signal_name='Response',
                    dbus_interface='org.freedesktop.portal.Request',
                    path=start_response
                )
                self._signal_matches.append(match)
            else:
                logger.error(f"Start unexpected response type: {type(start_response)}")
                if self.on_error:
                    self.on_error("Unexpected response from Start")
            
        except Exception as e:
            logger.error(f"Error in select sources response: {str(e)}")
            self._start_called = False  # Reset flag on error
            if self.on_error:
                self.on_error(f"Error in select sources response: {str(e)}")
    
    def _on_start_response(self, response: int, results: Dict[str, Any]) -> None:
        """Handle Start response"""
        logger.info(f"Start response received: response={response}, results={results}")
        
        if response != 0:
            logger.error(f"Start failed with response code: {response}")
            if self.on_error:
                self.on_error("Failed to start screen cast")
            return
        
        try:
            # Extract stream information
            streams = results.get('streams', [])
            if not streams:
                logger.error("No streams available in Start response")
                if self.on_error:
                    self.on_error("No streams available")
                return
            
            # Get the first stream
            stream = streams[0]
            self.stream_node_id = stream[0]  # PipeWire node ID
            
            logger.info(f"Stream ready! PipeWire node ID: {self.stream_node_id}")
            
            # Notify that stream is ready
            if self.on_stream_ready and self.stream_node_id is not None:
                self.on_stream_ready(self.stream_node_id)
                
        except Exception as e:
            logger.error(f"Error in start response: {str(e)}")
            if self.on_error:
                self.on_error(f"Error in start response: {str(e)}")
    
    def stop_capture(self) -> None:
        """Stop the current capture session"""
        try:
            # Clean up signal handlers
            for match in self._signal_matches:
                match.remove()
            self._signal_matches.clear()
            
            # Reset state
            self.session_handle = None
            self.stream_node_id = None
            self._start_called = False
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error stopping capture: {str(e)}")
    
    def get_stream_node_id(self) -> Optional[int]:
        """Get the PipeWire stream node ID"""
        return self.stream_node_id
