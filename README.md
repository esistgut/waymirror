# WayMirror

Screen capture application for Wayland using FreeDesktop Portal API and GStreamer.

## Features

- **Real-time screen capture** on Wayland
- **WebRTC streaming** for low-latency remote viewing
- Uses FreeDesktop Portal API for secure screen access
- GStreamer pipeline for efficient video processing
- Qt-based GUI for monitor selection and display
- Independent preview and streaming modes
- Works with KDE Plasma Wayland

## Requirements

- Python 3.8+
- PyQt6
- PyGObject (GStreamer bindings)
- dbus-python
- **Optional for WebRTC streaming:**
  - aiohttp
  - aiohttp-cors
- GStreamer with PipeWire support
- Running on Wayland with Portal support

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### WebRTC Streaming

1. Start screen capture in WayMirror
2. Check "WebRTC Streaming" to enable the streaming server
3. Open http://localhost:8000 in any modern web browser
4. Click "Connect to Stream" to view the live stream

The WebRTC streaming provides ultra-low latency screen mirroring, similar to services like Amazon Luna or Google Stadia. You can:
- Use preview and WebRTC streaming simultaneously
- Use only preview (local viewing)
- Use only WebRTC streaming (headless mode)
- Access the stream from any device on your network

## System Requirements

Make sure you have the following system packages installed:

### Ubuntu/Debian:
```bash
sudo apt install python3-gi gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-pipewire python3-dbus gstreamer1.0-plugins-bad
```

### Fedora:
```bash
sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-pipewire python3-dbus gstreamer1-plugins-bad-free
```

### Arch:
```bash
sudo pacman -S python-gobject gstreamer gst-plugins-base gst-plugins-good gstreamer-pipewire python-dbus gst-plugins-bad
```

**Note:** The `gst-plugins-bad` package is required for WebRTC functionality (webrtcbin element).
