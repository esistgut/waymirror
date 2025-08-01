#!/bin/bash
# Install and test script for WayMirror with WebRTC support

echo "WayMirror Installation and Test Script"
echo "======================================"

# Check if we're running on Wayland
if [ "$XDG_SESSION_TYPE" != "wayland" ]; then
    echo "Warning: This application is designed for Wayland. Current session: $XDG_SESSION_TYPE"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Python dependencies installed successfully"
else
    echo "✗ Failed to install Python dependencies"
    exit 1
fi

# Check for GStreamer WebRTC plugin
echo "Checking GStreamer WebRTC plugin..."
if gst-inspect-1.0 webrtcbin > /dev/null 2>&1; then
    echo "✓ GStreamer WebRTC plugin found"
else
    echo "✗ GStreamer WebRTC plugin not found"
    echo "Please install gst-plugins-bad:"
    echo "  Ubuntu/Debian: sudo apt install gstreamer1.0-plugins-bad"
    echo "  Fedora: sudo dnf install gstreamer1-plugins-bad-free"
    echo "  Arch: sudo pacman -S gst-plugins-bad"
    echo ""
    echo "You can still use WayMirror without WebRTC functionality."
fi

# Test the application
echo ""
echo "Testing WayMirror..."
python3 -c "
import sys
try:
    from waymirror.main_window import MainWindow, WEBRTC_AVAILABLE
    print('✓ WayMirror core functionality available')
    if WEBRTC_AVAILABLE:
        print('✓ WebRTC streaming functionality available')
    else:
        print('! WebRTC streaming functionality not available (missing aiohttp/aiohttp-cors)')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Installation completed successfully!"
    echo ""
    echo "Usage:"
    echo "  python main.py"
    echo ""
    echo "For WebRTC streaming:"
    echo "  1. Start capture in WayMirror"
    echo "  2. Check 'WebRTC Streaming'"
    echo "  3. Open http://localhost:8000 in your browser"
else
    echo "✗ Installation test failed"
    exit 1
fi
