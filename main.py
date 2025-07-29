#!/usr/bin/env python3
"""
WayMirror - Screen capture application for Wayland using FreeDesktop Portal API
"""

import sys
import signal
import logging
from PyQt6.QtWidgets import QApplication
from waymirror.main_window import MainWindow

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("Received Ctrl+C, shutting down...")
    QApplication.quit()

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    print("Starting WayMirror...")
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing Qt application...")
    app = QApplication(sys.argv)
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Creating main window...")
    try:
        window = MainWindow()
        logger.info("Showing main window...")
        window.show()
        
        logger.info("Starting Qt event loop...")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
