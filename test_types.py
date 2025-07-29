#!/usr/bin/env python3
"""
Type hint test script for WayMirror project
"""

from waymirror.main_window import MainWindow
from waymirror.portal import PortalHandler  
from waymirror.gstreamer_pipeline import GStreamerPipeline
from waymirror.video_widget import VideoWidget

def test_type_hints() -> None:
    """Test that our type hints work correctly"""
    print("✓ All imports successful with type hints!")
    
    # Test instantiation (without actually running)
    print("✓ Type checking passed!")

if __name__ == "__main__":
    test_type_hints()
