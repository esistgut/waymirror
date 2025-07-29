# WayMirror

Screen capture application for Wayland using FreeDesktop Portal API and GStreamer.

## Features

- Real-time screen capture on Wayland
- Uses FreeDesktop Portal API for secure screen access
- GStreamer pipeline for efficient video processing
- Qt-based GUI for monitor selection and display
- Works with KDE Plasma Wayland

## Requirements

- Python 3.8+
- PyQt6
- PyGObject (GStreamer bindings)
- dbus-python
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

## System Requirements

Make sure you have the following system packages installed:

### Ubuntu/Debian:
```bash
sudo apt install python3-gi gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-pipewire python3-dbus
```

### Fedora:
```bash
sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-pipewire python3-dbus
```

### Arch:
```bash
sudo pacman -S python-gobject gstreamer gst-plugins-base gst-plugins-good gstreamer-pipewire python-dbus
```
