import os
import cv2
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QIcon
from PyQt6.QtWidgets import QMessageBox

from utils.constants import (
    APP_DIR, DATA_DIR, TEMP_DIR, REPORTS_DIR, LOG_DIR, 
    COLORS
)

# Initialize logger
logger = logging.getLogger(__name__)

def ensure_app_directories():
    """Create application directories if they don't exist."""
    dirs_to_create = [APP_DIR, DATA_DIR, TEMP_DIR, REPORTS_DIR, LOG_DIR]
    
    for directory in dirs_to_create:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def cv_to_qt_image(cv_img):
    """
    Convert OpenCV image to QImage.
    
    Args:
        cv_img: OpenCV image (numpy array)
        
    Returns:
        QImage object
    """
    # Convert to RGB if needed
    if len(cv_img.shape) == 3:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    
    height, width = cv_img.shape[:2]
    
    # Get correct format based on image channels
    if len(cv_img.shape) == 3:
        bytes_per_line = width * 3
        q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    else:
        bytes_per_line = width
        q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
    
    return q_img

def cv_to_qt_pixmap(cv_img):
    """
    Convert OpenCV image to QPixmap.
    
    Args:
        cv_img: OpenCV image (numpy array)
        
    Returns:
        QPixmap object
    """
    q_img = cv_to_qt_image(cv_img)
    return QPixmap.fromImage(q_img)

def get_icon(name, color=None):
    """
    Load an icon from the assets directory.
    
    Args:
        name: Icon name
        color: Optional color name from COLORS dict
        
    Returns:
        QIcon object
    """
    # This is a placeholder. In a real application, 
    # you would load icons from files or use a library like qta (QtAwesome)
    # For simplicity, we're using a placeholder method
    
    return QIcon()

def show_error_message(parent, title, message):
    """
    Show an error message dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Error message
    """
    QMessageBox.critical(parent, title, message)

def show_info_message(parent, title, message):
    """
    Show an information message dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Information message
    """
    QMessageBox.information(parent, title, message)

def show_question_message(parent, title, message):
    """
    Show a question message dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Question message
        
    Returns:
        True if user clicked Yes, False otherwise
    """
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    
    return reply == QMessageBox.StandardButton.Yes

def format_timestamp(timestamp):
    """
    Format a timestamp for display.
    
    Args:
        timestamp: Timestamp string
        
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%B %d, %Y %I:%M %p")
    except (ValueError, TypeError):
        return timestamp

def format_duration(seconds):
    """
    Format duration in seconds to a readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds is None:
        return "N/A"
    
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}:{int(secs):02d}"
    else:
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}:{int(minutes):02d}:{int(secs):02d}"

def get_score_color(score):
    """
    Get color for a score value.
    
    Args:
        score: Score value (0-100)
        
    Returns:
        Color as string (hex code)
    """
    if score >= 85:
        return COLORS['secondary']  # Green for excellent
    elif score >= 70:
        return COLORS['primary']  # Blue for good
    elif score >= 50:
        return COLORS['warning']  # Orange for fair
    else:
        return COLORS['danger']  # Red for poor

def get_file_extension(filepath):
    """
    Get file extension from a path.
    
    Args:
        filepath: File path
        
    Returns:
        Extension without dot
    """
    return os.path.splitext(filepath)[1][1:].lower()

def is_valid_image_file(filepath):
    """
    Check if a file is a valid image file.
    
    Args:
        filepath: File path
        
    Returns:
        True if valid image file, False otherwise
    """
    valid_extensions = ['jpg', 'jpeg', 'png', 'bmp', 'gif']
    return get_file_extension(filepath) in valid_extensions

def is_valid_video_file(filepath):
    """
    Check if a file is a valid video file.
    
    Args:
        filepath: File path
        
    Returns:
        True if valid video file, False otherwise
    """
    valid_extensions = ['mp4', 'avi', 'mov', 'wmv', 'mkv']
    return get_file_extension(filepath) in valid_extensions

def normalize_angle(angle):
    """
    Normalize an angle to 0-360 degrees.
    
    Args:
        angle: Angle in degrees
        
    Returns:
        Normalized angle
    """
    return angle % 360

def angle_diff(a, b):
    """
    Calculate the smallest difference between two angles (0-360 degrees).
    
    Args:
        a: First angle in degrees
        b: Second angle in degrees
        
    Returns:
        Smallest angular difference
    """
    a = normalize_angle(a)
    b = normalize_angle(b)
    
    diff = abs(a - b)
    if diff > 180:
        diff = 360 - diff
    
    return diff

def get_system_info():
    """
    Get system information.
    
    Returns:
        Dictionary with system information
    """
    import platform
    import sys
    
    system_info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': sys.version,
        'platform': platform.platform(),
        'processor': platform.processor()
    }
    
    # Add OpenCV version
    system_info['opencv_version'] = cv2.__version__
    
    # Try to get GPU info if available
    try:
        gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
        system_info['cuda_available'] = gpu_count > 0
        system_info['cuda_devices'] = gpu_count
    except Exception:
        system_info['cuda_available'] = False
    
    return system_info