#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rifle Shooting Posture Analysis System - Main Entry Point

This is the entry point for the application. It initializes the database,
sets up logging, and launches the main application window.

Author: Claude
Date: March 6, 2025
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# Import application modules
from core.data_manager import DataManager
from ui.main_window import MainWindow
from utils.constants import APP_NAME, APP_VERSION, LOG_FORMAT, DATABASE_PATH
from utils.helpers import ensure_app_directories

def setup_logging():
    """Configure application logging."""
    log_dir = os.path.join(os.path.expanduser("~"), ".shooting_analyzer", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """Main application entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Ensure application directories exist
    ensure_app_directories()
    
    # Initialize database
    db_manager = DataManager(DATABASE_PATH)
    db_manager.initialize_database()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    main_window = MainWindow(db_manager)
    main_window.show()
    
    # Start application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
