"""
HTTP server for serving WebRTC client interface
"""

import asyncio
import json
import logging
import threading
from typing import Optional
from aiohttp import web
import aiohttp_cors

logger = logging.getLogger(__name__)

class HTTPServer:
    """Simple HTTP server for serving WebRTC client interface"""
    
    def __init__(self, port: int = 8080) -> None:
        self.port = port
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        
    def start_server(self) -> bool:
        """Start the HTTP server in a separate thread"""
        try:
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            # Give the server a moment to start
            import time
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False
    
    def _run_server(self) -> None:
        """Run the server in the thread"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._setup_server())
        except Exception as e:
            logger.error(f"Error running HTTP server: {e}")
    
    async def _setup_server(self) -> None:
        """Set up the web server"""
        try:
            self.app = web.Application()
            
            # CORS setup for browser compatibility
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Routes
            self.app.router.add_get('/', self._serve_client)
            
            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
            
            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, 'localhost', self.port)
            await self.site.start()
            
            self.is_running = True
            logger.info(f"HTTP server started on http://localhost:{self.port}")
            
            # Keep the server running
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error setting up HTTP server: {e}")
    
    async def _serve_client(self, request: web.Request) -> web.Response:
        """Serve the WebRTC client HTML page"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>WayMirror WebRTC Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        #video {
            max-width: 90vw;
            max-height: 70vh;
            background-color: #000;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        #status {
            margin-top: 20px;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
        }
        .connecting { background-color: #fff3cd; color: #856404; }
        .connected { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        #info {
            margin-top: 10px;
            color: #666;
            text-align: center;
        }
        #controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        #connectBtn {
            background-color: #007bff;
            color: white;
        }
        #connectBtn:hover {
            background-color: #0056b3;
        }
        #connectBtn:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <h1>WayMirror WebRTC Stream</h1>
    <video id="video" autoplay muted playsinline></video>
    <div id="status" class="connecting">Ready to connect</div>
    <div id="controls">
        <button id="connectBtn">Connect to Stream</button>
    </div>
    <div id="info">Low-latency screen mirroring via WebRTC<br>
    Make sure WebRTC streaming is enabled in the WayMirror application</div>

    <script>
        const video = document.getElementById('video');
        const status = document.getElementById('status');
        const connectBtn = document.getElementById('connectBtn');
        
        let client = null;
        
        function updateStatus(message, className) {
            status.textContent = message;
            status.className = className;
        }
        
        connectBtn.addEventListener('click', () => {
            if (client) {
                client.disconnect();
                client = null;
                connectBtn.textContent = 'Connect to Stream';
                updateStatus('Disconnected', 'error');
            } else {
                client = new WebRTCClient();
                connectBtn.textContent = 'Disconnect';
                connectBtn.disabled = true;
            }
        });
        
        class WebRTCClient {
            constructor() {
                this.ws = null;
                this.pc = null;
                this.init();
            }
            
            async init() {
                try {
                    updateStatus('Initializing...', 'connecting');
                    
                    // Create WebRTC peer connection
                    this.pc = new RTCPeerConnection({
                        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
                    });
                    
                    this.pc.ontrack = (event) => {
                        console.log('Received track:', event.track.kind);
                        if (event.track.kind === 'video') {
                            video.srcObject = event.streams[0];
                            updateStatus('Connected - Streaming', 'connected');
                            connectBtn.disabled = false;
                        }
                    };
                    
                    this.pc.onicecandidate = (event) => {
                        if (event.candidate) {
                            this.sendMessage({
                                type: 'ice-candidate',
                                candidate: event.candidate.candidate,
                                sdpMLineIndex: event.candidate.sdpMLineIndex
                            });
                        }
                    };
                    
                    this.pc.onconnectionstatechange = () => {
                        console.log('Connection state:', this.pc.connectionState);
                        if (this.pc.connectionState === 'failed') {
                            updateStatus('Connection failed', 'error');
                            connectBtn.disabled = false;
                        } else if (this.pc.connectionState === 'disconnected') {
                            updateStatus('Disconnected', 'error');
                            connectBtn.disabled = false;
                        }
                    };
                    
                    // Connect WebSocket
                    this.connectWebSocket();
                    
                } catch (error) {
                    console.error('Error initializing WebRTC:', error);
                    updateStatus('Initialization failed', 'error');
                    connectBtn.disabled = false;
                }
            }
            
            connectWebSocket() {
                const wsUrl = `ws://localhost:8000/ws`;
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    updateStatus('WebSocket connected', 'connecting');
                };
                
                this.ws.onmessage = async (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        await this.handleMessage(message);
                    } catch (error) {
                        console.error('Error handling message:', error);
                    }
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    updateStatus('WebSocket disconnected', 'error');
                    connectBtn.disabled = false;
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    updateStatus('Connection error - Make sure WebRTC streaming is enabled', 'error');
                    connectBtn.disabled = false;
                };
            }
            
            async handleMessage(message) {
                switch (message.type) {
                    case 'offer':
                        await this.pc.setRemoteDescription(new RTCSessionDescription({
                            type: 'offer',
                            sdp: message.sdp
                        }));
                        
                        const answer = await this.pc.createAnswer();
                        await this.pc.setLocalDescription(answer);
                        
                        this.sendMessage({
                            type: 'answer',
                            sdp: answer.sdp
                        });
                        break;
                        
                    case 'ice-candidate':
                        await this.pc.addIceCandidate(new RTCIceCandidate({
                            candidate: message.candidate,
                            sdpMLineIndex: message.sdpMLineIndex
                        }));
                        break;
                }
            }
            
            sendMessage(message) {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify(message));
                }
            }
            
            disconnect() {
                if (this.ws) {
                    this.ws.close();
                }
                if (this.pc) {
                    this.pc.close();
                }
                video.srcObject = null;
            }
        }
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    def stop_server(self) -> None:
        """Stop the HTTP server"""
        try:
            self.is_running = False
            
            # Stop web server
            if self.loop:
                async def cleanup():
                    if self.site:
                        await self.site.stop()
                    if self.runner:
                        await self.runner.cleanup()
                
                asyncio.run_coroutine_threadsafe(cleanup(), self.loop)
            
            # Stop the event loop
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
            
            # Wait for thread to finish
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2)
            
            logger.info("HTTP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")
    
    def is_server_running(self) -> bool:
        """Check if the server is running"""
        return self.is_running and self.thread and self.thread.is_alive()
