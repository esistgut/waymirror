#!/usr/bin/env python3
"""
Dependency checker for WayMirror
"""

import sys
import subprocess

def check_python_modules():
    """Check if required Python modules are available"""
    modules = [
        ("PyQt6", "PyQt6.QtWidgets"),
        ("PyGObject", "gi"),
        ("D-Bus", "dbus"),
        ("NumPy", "numpy"),
    ]
    
    missing = []
    for name, module in modules:
        try:
            __import__(module)
            print(f"✓ {name} is available")
        except ImportError:
            print(f"✗ {name} is missing")
            missing.append(name)
    
    return missing

def check_gstreamer():
    """Check GStreamer and plugins"""
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)
        print("✓ GStreamer is available")
        
        # Check for PipeWire plugin
        registry = Gst.Registry.get()
        plugin = registry.find_plugin("pipewire")
        if plugin:
            print("✓ GStreamer PipeWire plugin is available")
        else:
            print("✗ GStreamer PipeWire plugin is missing")
            return False
        
        return True
    except Exception as e:
        print(f"✗ GStreamer error: {e}")
        return False

def check_dbus_portal():
    """Check if Portal is available via D-Bus"""
    try:
        import dbus
        bus = dbus.SessionBus()
        
        # Try to get the portal object
        portal = bus.get_object(
            'org.freedesktop.portal.Desktop',
            '/org/freedesktop/portal/desktop'
        )
        print("✓ FreeDesktop Portal is available")
        return True
    except Exception as e:
        print(f"✗ Portal not available: {e}")
        return False

def check_wayland():
    """Check if running on Wayland"""
    import os
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    if wayland_display:
        print(f"✓ Running on Wayland (WAYLAND_DISPLAY={wayland_display})")
        return True
    else:
        print("✗ Not running on Wayland (WAYLAND_DISPLAY not set)")
        return False

def main():
    """Main dependency check"""
    print("WayMirror Dependency Checker")
    print("=" * 30)
    
    all_good = True
    
    print("\nChecking Python modules:")
    missing_modules = check_python_modules()
    if missing_modules:
        all_good = False
        print(f"\nInstall missing modules with:")
        print("pip install " + " ".join(missing_modules))
    
    print("\nChecking GStreamer:")
    if not check_gstreamer():
        all_good = False
    
    print("\nChecking FreeDesktop Portal:")
    if not check_dbus_portal():
        all_good = False
    
    print("\nChecking Wayland:")
    if not check_wayland():
        all_good = False
    
    print("\n" + "=" * 30)
    if all_good:
        print("✓ All dependencies are satisfied!")
        print("You can run: python main.py")
    else:
        print("✗ Some dependencies are missing.")
        print("Please install the missing components.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
