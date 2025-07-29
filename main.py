#!/usr/bin/env python3
"""
WayMirror - Screen capture application for Wayland using FreeDesktop Portal API
"""

import sys
import signal
import logging
from typing import Any, NoReturn
from PyQt6.QtWidgets import QApplication
from waymirror.main_window import MainWindow

def signal_handler(sig: int, frame: Any) -> None:
    """Handle Ctrl+C gracefully"""
    QApplication.quit()

def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def main() -> NoReturn:
    setup_logging()
    
    app = QApplication(sys.argv)
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
