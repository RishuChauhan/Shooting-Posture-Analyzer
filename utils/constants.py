import os
import pathlib

# Application information
APP_NAME = "Rifle Shooting Posture Analyzer"
APP_VERSION = "1.0.0"

# Logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Application directories
APP_DIR = os.path.join(os.path.expanduser("~"), ".shooting_analyzer")
DATA_DIR = os.path.join(APP_DIR, "data")
TEMP_DIR = os.path.join(APP_DIR, "temp")
REPORTS_DIR = os.path.join(APP_DIR, "reports")
LOG_DIR = os.path.join(APP_DIR, "logs")

# Database path
DATABASE_PATH = os.path.join(DATA_DIR, "shooting_analyzer.db")

# UI constants
UI_TITLE = "Rifle Shooting Posture Analyzer"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Video constants
DEFAULT_CAMERA_ID = 0
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
RECORDING_FPS = 15
MAX_RECORDING_SECONDS = 300  # 5 minutes

# Analysis constants
ANALYSIS_INTERVAL = 1.0  # seconds between analyses
POSTURE_SENSITIVITY = 0.5  # 0.0 to 1.0

# Posture score thresholds
SCORE_EXCELLENT = 85
SCORE_GOOD = 70
SCORE_FAIR = 50

# Color schemes
COLORS = {
    'primary': '#3498db',     # Blue
    'secondary': '#2ecc71',   # Green
    'warning': '#f39c12',     # Orange
    'danger': '#e74c3c',      # Red
    'info': '#9b59b6',        # Purple
    'light': '#ecf0f1',       # Light gray
    'dark': '#2c3e50',        # Dark blue/gray
    'white': '#ffffff',       # White
    'black': '#000000',       # Black
    'gray': '#95a5a6',        # Gray
}

# Stylesheet templates
STYLESHEET_LIGHT = """
    QMainWindow {
        background-color: #f5f5f5;
    }
    QWidget {
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #1c6ea4;
    }
    QPushButton:disabled {
        background-color: #95a5a6;
    }
    QLabel {
        color: #2c3e50;
    }
    QTabWidget::pane {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
    }
    QTabBar::tab {
        background-color: #ecf0f1;
        border: 1px solid #bdc3c7;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 6px 12px;
        color: #7f8c8d;
    }
    QTabBar::tab:selected {
        background-color: white;
        color: #2c3e50;
    }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 4px;
    }
    QGroupBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        margin-top: 1em;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
    }
"""

STYLESHEET_DARK = """
    QMainWindow {
        background-color: #2c3e50;
    }
    QWidget {
        font-family: 'Segoe UI', 'Arial', sans-serif;
        color: #ecf0f1;
    }
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #1c6ea4;
    }
    QPushButton:disabled {
        background-color: #7f8c8d;
    }
    QLabel {
        color: #ecf0f1;
    }
    QTabWidget::pane {
        border: 1px solid #7f8c8d;
        border-radius: 4px;
    }
    QTabBar::tab {
        background-color: #34495e;
        border: 1px solid #7f8c8d;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 6px 12px;
        color: #bdc3c7;
    }
    QTabBar::tab:selected {
        background-color: #2c3e50;
        color: #ecf0f1;
    }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        border: 1px solid #7f8c8d;
        border-radius: 4px;
        padding: 4px;
        background-color: #34495e;
    }
    QGroupBox {
        border: 1px solid #7f8c8d;
        border-radius: 4px;
        margin-top: 1em;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
    }
"""