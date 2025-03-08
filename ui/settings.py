import os
import logging
import cv2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QSlider, QTabWidget, QFileDialog,
    QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QFont, QIcon

from utils.constants import (
    APP_NAME, APP_VERSION, DATA_DIR, REPORTS_DIR, TEMP_DIR,
    DEFAULT_CAMERA_ID, STYLESHEET_LIGHT, STYLESHEET_DARK,
    POSTURE_SENSITIVITY
)
from utils.helpers import (
    show_error_message, show_info_message, get_system_info
)

# Initialize logger
logger = logging.getLogger(__name__)

class SettingsWidget(QWidget):
    """
    Widget for application settings screen.
    Allows configuring application behavior and appearance.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the settings widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Current settings
        self.current_settings = {}
        
        # Initialize UI
        self._init_ui()
        
        # Load current settings
        self._load_settings()
        
        logger.info("SettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("Application Settings")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Create tabs for different settings categories
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # General settings tab
        self.general_tab = QWidget()
        self._setup_general_tab()
        self.tab_widget.addTab(self.general_tab, "General")
        
        # Camera settings tab
        self.camera_tab = QWidget()
        self._setup_camera_tab()
        self.tab_widget.addTab(self.camera_tab, "Camera")
        
        # Analysis settings tab
        self.analysis_tab = QWidget()
        self._setup_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "Analysis")
        
        # Recording settings tab
        self.recording_tab = QWidget()
        self._setup_recording_tab()
        self.tab_widget.addTab(self.recording_tab, "Recording")
        
        # Display settings tab
        self.display_tab = QWidget()
        self._setup_display_tab()
        self.tab_widget.addTab(self.display_tab, "Display")
        
        # System info tab
        self.system_tab = QWidget()
        self._setup_system_tab()
        self.tab_widget.addTab(self.system_tab, "System Info")
        
        # Add save and reset buttons
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setMinimumHeight(40)
        self.reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_btn)
        
        self.main_layout.addLayout(buttons_layout)
    
    def _setup_general_tab(self):
        """Set up the general settings tab."""
        layout = QVBoxLayout(self.general_tab)
        
        # Create form layout for settings
        form = QFormLayout()
        
        # Theme setting
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light Theme", "light")
        self.theme_combo.addItem("Dark Theme", "dark")
        form.addRow("Application Theme:", self.theme_combo)
        
        # Data directory setting
        data_dir_layout = QHBoxLayout()
        
        self.data_dir_edit = QLineEdit()
        self.data_dir_edit.setReadOnly(True)
        data_dir_layout.addWidget(self.data_dir_edit)
        
        self.data_dir_btn = QPushButton("Browse...")
        self.data_dir_btn.clicked.connect(self._browse_data_dir)
        data_dir_layout.addWidget(self.data_dir_btn)
        
        form.addRow("Data Directory:", data_dir_layout)
        
        # Reports directory setting
        reports_dir_layout = QHBoxLayout()
        
        self.reports_dir_edit = QLineEdit()
        self.reports_dir_edit.setReadOnly(True)
        reports_dir_layout.addWidget(self.reports_dir_edit)
        
        self.reports_dir_btn = QPushButton("Browse...")
        self.reports_dir_btn.clicked.connect(self._browse_reports_dir)
        reports_dir_layout.addWidget(self.reports_dir_btn)
        
        form.addRow("Reports Directory:", reports_dir_layout)
        
        # Add form to layout
        layout.addLayout(form)
        
        # Add management options
        management_group = QGroupBox("Data Management")
        management_layout = QVBoxLayout(management_group)
        
        self.clear_temp_btn = QPushButton("Clear Temporary Files")
        self.clear_temp_btn.clicked.connect(self._clear_temp_files)
        management_layout.addWidget(self.clear_temp_btn)
        
        self.backup_db_btn = QPushButton("Backup Database")
        self.backup_db_btn.clicked.connect(self._backup_database)
        management_layout.addWidget(self.backup_db_btn)
        
        layout.addWidget(management_group)
        
        # Add spacer
        layout.addStretch()
    
    def _setup_camera_tab(self):
        """Set up the camera settings tab."""
        layout = QVBoxLayout(self.camera_tab)
        
        # Create form layout for settings
        form = QFormLayout()
        
        # Camera device setting
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Default Camera", DEFAULT_CAMERA_ID)
        
        # Scan for available cameras (up to 5)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                if i != DEFAULT_CAMERA_ID:
                    self.camera_combo.addItem(f"Camera {i}", i)
        
        form.addRow("Camera Device:", self.camera_combo)
        
        # Resolution setting
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("640x480", "640x480")
        self.resolution_combo.addItem("800x600", "800x600")
        self.resolution_combo.addItem("1280x720", "1280x720")
        self.resolution_combo.addItem("1920x1080", "1920x1080")
        form.addRow("Video Resolution:", self.resolution_combo)
        
        # Frame rate setting
        self.fps_spin = QSpinBox()
        self.fps_spin.setMinimum(15)
        self.fps_spin.setMaximum(60)
        self.fps_spin.setSingleStep(5)
        self.fps_spin.setValue(30)
        form.addRow("Frame Rate (FPS):", self.fps_spin)
        
        # Add form to layout
        layout.addLayout(form)
        
        # Add camera test
        test_group = QGroupBox("Camera Test")
        test_layout = QVBoxLayout(test_group)
        
        self.test_camera_btn = QPushButton("Test Camera")
        self.test_camera_btn.clicked.connect(self._test_camera)
        test_layout.addWidget(self.test_camera_btn)
        
        self.camera_status = QLabel("Camera status: Not tested")
        test_layout.addWidget(self.camera_status)
        
        layout.addWidget(test_group)
        
        # Add spacer
        layout.addStretch()
    
    def _setup_analysis_tab(self):
        """Set up the analysis settings tab."""
        layout = QVBoxLayout(self.analysis_tab)
        
        # Create form layout for settings
        form = QFormLayout()
        
        # Pose detection confidence setting
        self.detection_slider = QSlider(Qt.Orientation.Horizontal)
        self.detection_slider.setMinimum(1)
        self.detection_slider.setMaximum(10)
        self.detection_slider.setValue(5)  # Default: 0.5
        self.detection_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.detection_slider.setTickInterval(1)
        
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Low"))
        slider_layout.addWidget(self.detection_slider)
        slider_layout.addWidget(QLabel("High"))
        
        form.addRow("Pose Detection Confidence:", slider_layout)
        
        # Analysis interval setting
        self.analysis_interval = QDoubleSpinBox()
        self.analysis_interval.setMinimum(0.1)
        self.analysis_interval.setMaximum(5.0)
        self.analysis_interval.setSingleStep(0.1)
        self.analysis_interval.setValue(1.0)
        self.analysis_interval.setSuffix(" seconds")
        form.addRow("Analysis Interval:", self.analysis_interval)
        
        # Posture sensitivity setting
        self.posture_sensitivity = QDoubleSpinBox()
        self.posture_sensitivity.setMinimum(0.1)
        self.posture_sensitivity.setMaximum(1.0)
        self.posture_sensitivity.setSingleStep(0.1)
        self.posture_sensitivity.setValue(POSTURE_SENSITIVITY)
        form.addRow("Posture Sensitivity:", self.posture_sensitivity)
        
        # Add form to layout
        layout.addLayout(form)
        
        # Add visual feedback options
        feedback_group = QGroupBox("Visual Feedback")
        feedback_layout = QVBoxLayout(feedback_group)
        
        self.show_angles_check = QCheckBox("Show Angle Measurements")
        self.show_angles_check.setChecked(True)
        feedback_layout.addWidget(self.show_angles_check)
        
        self.show_feedback_check = QCheckBox("Show Real-time Feedback")
        self.show_feedback_check.setChecked(True)
        feedback_layout.addWidget(self.show_feedback_check)
        
        layout.addWidget(feedback_group)
        
        # Add spacer
        layout.addStretch()
    
    def _setup_recording_tab(self):
        """Set up the recording settings tab."""
        layout = QVBoxLayout(self.recording_tab)
        
        # Create form layout for settings
        form = QFormLayout()
        
        # Recording frame rate setting
        self.recording_fps = QSpinBox()
        self.recording_fps.setMinimum(5)
        self.recording_fps.setMaximum(30)
        self.recording_fps.setSingleStep(5)
        self.recording_fps.setValue(15)
        self.recording_fps.setSuffix(" FPS")
        form.addRow("Recording Frame Rate:", self.recording_fps)
        
        # Max recording duration
        self.recording_duration = QSpinBox()
        self.recording_duration.setMinimum(60)
        self.recording_duration.setMaximum(3600)
        self.recording_duration.setSingleStep(60)
        self.recording_duration.setValue(300)  # 5 minutes
        self.recording_duration.setSuffix(" seconds")
        form.addRow("Maximum Recording Duration:", self.recording_duration)
        
        # Add form to layout
        layout.addLayout(form)
        
        # Add recording options
        options_group = QGroupBox("Recording Options")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_save_check = QCheckBox("Auto-save Recordings")
        options_layout.addWidget(self.auto_save_check)
        
        self.auto_analyze_check = QCheckBox("Auto-analyze After Recording")
        self.auto_analyze_check.setChecked(True)
        options_layout.addWidget(self.auto_analyze_check)
        
        layout.addWidget(options_group)
        
        # Add spacer
        layout.addStretch()
    
    def _setup_display_tab(self):
        """Set up the display settings tab."""
        layout = QVBoxLayout(self.display_tab)
        
        # Create keypoint display options
        keypoint_group = QGroupBox("Keypoint Display")
        keypoint_layout = QFormLayout(keypoint_group)
        
        self.keypoint_size = QSpinBox()
        self.keypoint_size.setMinimum(1)
        self.keypoint_size.setMaximum(10)
        self.keypoint_size.setValue(3)
        keypoint_layout.addRow("Keypoint Size:", self.keypoint_size)
        
        self.connection_width = QSpinBox()
        self.connection_width.setMinimum(1)
        self.connection_width.setMaximum(5)
        self.connection_width.setValue(2)
        keypoint_layout.addRow("Connection Width:", self.connection_width)
        
        layout.addWidget(keypoint_group)
        
        # Create UI scaling options
        ui_group = QGroupBox("UI Scaling")
        ui_layout = QVBoxLayout(ui_group)
        
        scale_layout = QHBoxLayout()
        
        self.scale_75 = QRadioButton("75%")
        self.scale_100 = QRadioButton("100%")
        self.scale_125 = QRadioButton("125%")
        self.scale_150 = QRadioButton("150%")
        
        self.scale_group = QButtonGroup()
        self.scale_group.addButton(self.scale_75, 75)
        self.scale_group.addButton(self.scale_100, 100)
        self.scale_group.addButton(self.scale_125, 125)
        self.scale_group.addButton(self.scale_150, 150)
        
        self.scale_100.setChecked(True)
        
        scale_layout.addWidget(self.scale_75)
        scale_layout.addWidget(self.scale_100)
        scale_layout.addWidget(self.scale_125)
        scale_layout.addWidget(self.scale_150)
        
        ui_layout.addLayout(scale_layout)
        
        layout.addWidget(ui_group)
        
        # Create text display options
        text_group = QGroupBox("Text Display")
        text_layout = QFormLayout(text_group)
        
        self.font_size = QSpinBox()
        self.font_size.setMinimum(8)
        self.font_size.setMaximum(16)
        self.font_size.setValue(10)
        text_layout.addRow("Font Size:", self.font_size)
        
        layout.addWidget(text_group)
        
        # Add spacer
        layout.addStretch()
    
    def _setup_system_tab(self):
        """Set up the system information tab."""
        layout = QVBoxLayout(self.system_tab)
        
        # Add application info
        app_group = QGroupBox("Application Information")
        app_layout = QFormLayout(app_group)
        
        app_layout.addRow("Application Name:", QLabel(APP_NAME))
        app_layout.addRow("Version:", QLabel(APP_VERSION))
        
        layout.addWidget(app_group)
        
        # Add system info
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout(system_group)
        
        # Get system info
        system_info = get_system_info()
        
        system_layout.addRow("Operating System:", QLabel(f"{system_info['os']} {system_info['os_version']}"))
        system_layout.addRow("Python Version:", QLabel(system_info['python_version'].split()[0]))
        system_layout.addRow("OpenCV Version:", QLabel(system_info['opencv_version']))
        
        # CUDA availability
        cuda_status = "Available" if system_info.get('cuda_available', False) else "Not Available"
        system_layout.addRow("CUDA Support:", QLabel(cuda_status))
        
        if system_info.get('cuda_available', False):
            system_layout.addRow("CUDA Devices:", QLabel(str(system_info.get('cuda_devices', 0))))
        
        layout.addWidget(system_group)
        
        # Add directory info
        dir_group = QGroupBox("Directory Information")
        dir_layout = QFormLayout(dir_group)
        
        dir_layout.addRow("Data Directory:", QLabel(DATA_DIR))
        dir_layout.addRow("Reports Directory:", QLabel(REPORTS_DIR))
        dir_layout.addRow("Temp Directory:", QLabel(TEMP_DIR))
        
        layout.addWidget(dir_group)
        
        # Add actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        self.refresh_info_btn = QPushButton("Refresh System Information")
        self.refresh_info_btn.clicked.connect(self._refresh_system_info)
        actions_layout.addWidget(self.refresh_info_btn)
        
        layout.addWidget(actions_group)
        
        # Add spacer
        layout.addStretch()
    
    def _load_settings(self):
        """Load current settings from database."""
        try:
            # Get all app settings
            self.current_settings = self.data_manager.get_app_settings()
            
            # Update UI with loaded settings
            self._update_ui_from_settings()
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            show_error_message(self, "Settings Error", 
                              f"Failed to load settings: {str(e)}")
    
    def _update_ui_from_settings(self):
        """Update UI components with loaded settings."""
        # General tab
        theme = self.current_settings.get('theme', 'light')
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        data_dir = self.current_settings.get('data_dir', DATA_DIR)
        self.data_dir_edit.setText(data_dir)
        
        reports_dir = self.current_settings.get('reports_dir', REPORTS_DIR)
        self.reports_dir_edit.setText(reports_dir)
        
        # Camera tab
        camera_id = int(self.current_settings.get('camera_id', DEFAULT_CAMERA_ID))
        index = self.camera_combo.findData(camera_id)
        if index >= 0:
            self.camera_combo.setCurrentIndex(index)
        
        resolution = self.current_settings.get('resolution', '640x480')
        index = self.resolution_combo.findData(resolution)
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)
        
        fps = int(self.current_settings.get('fps', '30'))
        self.fps_spin.setValue(fps)
        
        # Analysis tab
        detection_confidence = float(self.current_settings.get('detection_confidence', '0.5'))
        slider_value = int(detection_confidence * 10)
        self.detection_slider.setValue(slider_value)
        
        analysis_interval = float(self.current_settings.get('analysis_delay', '1.0'))
        self.analysis_interval.setValue(analysis_interval)
        
        posture_sensitivity = float(self.current_settings.get('posture_sensitivity', str(POSTURE_SENSITIVITY)))
        self.posture_sensitivity.setValue(posture_sensitivity)
        
        show_angles = self.current_settings.get('show_angles', 'true').lower() == 'true'
        self.show_angles_check.setChecked(show_angles)
        
        show_feedback = self.current_settings.get('show_feedback', 'true').lower() == 'true'
        self.show_feedback_check.setChecked(show_feedback)
        
        # Recording tab
        recording_fps = int(self.current_settings.get('recording_fps', '15'))
        self.recording_fps.setValue(recording_fps)
        
        recording_duration = int(self.current_settings.get('recording_duration_limit', '300'))
        self.recording_duration.setValue(recording_duration)
        
        auto_save = self.current_settings.get('auto_save', 'false').lower() == 'true'
        self.auto_save_check.setChecked(auto_save)
        
        auto_analyze = self.current_settings.get('auto_analyze', 'true').lower() == 'true'
        self.auto_analyze_check.setChecked(auto_analyze)
        
        # Display tab
        keypoint_size = int(self.current_settings.get('keypoint_size', '3'))
        self.keypoint_size.setValue(keypoint_size)
        
        connection_width = int(self.current_settings.get('connection_width', '2'))
        self.connection_width.setValue(connection_width)
        
        ui_scale = int(self.current_settings.get('ui_scale', '100'))
        for button in self.scale_group.buttons():
            if self.scale_group.id(button) == ui_scale:
                button.setChecked(True)
                break
        
        font_size = int(self.current_settings.get('font_size', '10'))
        self.font_size.setValue(font_size)
    
    def _save_settings(self):
        """Save settings to database."""
        try:
            # General tab
            self.data_manager.set_app_setting('theme', self.theme_combo.currentData())
            self.data_manager.set_app_setting('data_dir', self.data_dir_edit.text())
            self.data_manager.set_app_setting('reports_dir', self.reports_dir_edit.text())
            
            # Camera tab
            self.data_manager.set_app_setting('camera_id', str(self.camera_combo.currentData()))
            self.data_manager.set_app_setting('resolution', self.resolution_combo.currentData())
            self.data_manager.set_app_setting('fps', str(self.fps_spin.value()))
            
            # Analysis tab
            detection_confidence = self.detection_slider.value() / 10.0
            self.data_manager.set_app_setting('detection_confidence', str(detection_confidence))
            
            self.data_manager.set_app_setting('analysis_delay', str(self.analysis_interval.value()))
            self.data_manager.set_app_setting('posture_sensitivity', str(self.posture_sensitivity.value()))
            self.data_manager.set_app_setting('show_angles', 'true' if self.show_angles_check.isChecked() else 'false')
            self.data_manager.set_app_setting('show_feedback', 'true' if self.show_feedback_check.isChecked() else 'false')
            
            # Recording tab
            self.data_manager.set_app_setting('recording_fps', str(self.recording_fps.value()))
            self.data_manager.set_app_setting('recording_duration_limit', str(self.recording_duration.value()))
            self.data_manager.set_app_setting('auto_save', 'true' if self.auto_save_check.isChecked() else 'false')
            self.data_manager.set_app_setting('auto_analyze', 'true' if self.auto_analyze_check.isChecked() else 'false')
            
            # Display tab
            self.data_manager.set_app_setting('keypoint_size', str(self.keypoint_size.value()))
            self.data_manager.set_app_setting('connection_width', str(self.connection_width.value()))
            
            ui_scale = self.scale_group.checkedId()
            self.data_manager.set_app_setting('ui_scale', str(ui_scale))
            
            self.data_manager.set_app_setting('font_size', str(self.font_size.value()))
            
            # Show success message
            show_info_message(self, "Settings Saved", 
                             "Settings have been saved successfully.\n\n"
                             "Some settings may require restarting the application to take effect.")
            
            logger.info("Settings saved successfully")
            
            # Apply theme immediately if possible
            parent = self.parent()
            while parent and not hasattr(parent, '_apply_theme'):
                parent = parent.parent()
            
            if parent and hasattr(parent, '_apply_theme'):
                parent._apply_theme()
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            show_error_message(self, "Settings Error", 
                              f"Failed to save settings: {str(e)}")
    
    def _reset_settings(self):
        """Reset settings to defaults."""
        # Confirm reset
        confirmed = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Reset to default values
            
            # General tab
            self.theme_combo.setCurrentIndex(0)  # Light theme
            self.data_dir_edit.setText(DATA_DIR)
            self.reports_dir_edit.setText(REPORTS_DIR)
            
            # Camera tab
            index = self.camera_combo.findData(DEFAULT_CAMERA_ID)
            if index >= 0:
                self.camera_combo.setCurrentIndex(index)
            
            self.resolution_combo.setCurrentIndex(0)  # 640x480
            self.fps_spin.setValue(30)
            
            # Analysis tab
            self.detection_slider.setValue(5)  # 0.5
            self.analysis_interval.setValue(1.0)
            self.posture_sensitivity.setValue(POSTURE_SENSITIVITY)
            self.show_angles_check.setChecked(True)
            self.show_feedback_check.setChecked(True)
            
            # Recording tab
            self.recording_fps.setValue(15)
            self.recording_duration.setValue(300)  # 5 minutes
            self.auto_save_check.setChecked(False)
            self.auto_analyze_check.setChecked(True)
            
            # Display tab
            self.keypoint_size.setValue(3)
            self.connection_width.setValue(2)
            self.scale_100.setChecked(True)
            self.font_size.setValue(10)
            
            # Save reset settings
            self._save_settings()
            
            show_info_message(self, "Settings Reset", 
                             "Settings have been reset to defaults.")
            
            logger.info("Settings reset to defaults")
            
        except Exception as e:
            logger.error(f"Error resetting settings: {str(e)}")
            show_error_message(self, "Settings Error", 
                              f"Failed to reset settings: {str(e)}")
    
    def _browse_data_dir(self):
        """Browse for data directory."""
        current_dir = self.data_dir_edit.text() or DATA_DIR
        
        directory = QFileDialog.getExistingDirectory(
            self, "Select Data Directory", current_dir
        )
        
        if directory:
            self.data_dir_edit.setText(directory)
    
    def _browse_reports_dir(self):
        """Browse for reports directory."""
        current_dir = self.reports_dir_edit.text() or REPORTS_DIR
        
        directory = QFileDialog.getExistingDirectory(
            self, "Select Reports Directory", current_dir
        )
        
        if directory:
            self.reports_dir_edit.setText(directory)
    
    def _clear_temp_files(self):
        """Clear temporary files."""
        try:
            # Confirm action
            confirmed = QMessageBox.question(
                self, 
                "Clear Temporary Files", 
                "Are you sure you want to clear all temporary files?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirmed != QMessageBox.StandardButton.Yes:
                return
            
            # Count files to delete
            file_count = 0
            
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        file_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
            
            # Show success message
            show_info_message(self, "Temp Files Cleared", 
                             f"Successfully cleared {file_count} temporary files.")
            
            logger.info(f"Cleared {file_count} temporary files")
            
        except Exception as e:
            logger.error(f"Error clearing temp files: {str(e)}")
            show_error_message(self, "Error", 
                              f"Failed to clear temporary files: {str(e)}")
    
    def _backup_database(self):
        """Create a backup of the database."""
        try:
            # Choose backup location
            backup_path, _ = QFileDialog.getSaveFileName(
                self, "Save Database Backup", 
                os.path.join(DATA_DIR, "shooting_analyzer_backup.db"),
                "SQLite Database (*.db)"
            )
            
            if not backup_path:
                return
            
            # Get database path
            db_path = self.data_manager.db_path
            
            # Copy database file
            import shutil
            shutil.copy2(db_path, backup_path)
            
            # Show success message
            show_info_message(self, "Backup Created", 
                             f"Database backup created successfully at:\n{backup_path}")
            
            logger.info(f"Database backed up to {backup_path}")
            
        except Exception as e:
            logger.error(f"Error backing up database: {str(e)}")
            show_error_message(self, "Backup Error", 
                              f"Failed to create database backup: {str(e)}")
    
    def _test_camera(self):
        """Test the selected camera."""
        try:
            # Get selected camera ID
            camera_id = self.camera_combo.currentData()
            
            # Open camera
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                self.camera_status.setText("Camera status: Failed to open camera")
                self.camera_status.setStyleSheet("color: red;")
                return
            
            # Try to read a frame
            ret, frame = cap.read()
            
            # Release camera
            cap.release()
            
            if ret:
                self.camera_status.setText("Camera status: Working properly")
                self.camera_status.setStyleSheet("color: green;")
            else:
                self.camera_status.setText("Camera status: Failed to capture frame")
                self.camera_status.setStyleSheet("color: red;")
            
        except Exception as e:
            logger.error(f"Error testing camera: {str(e)}")
            self.camera_status.setText(f"Camera status: Error - {str(e)}")
            self.camera_status.setStyleSheet("color: red;")
    
    def _refresh_system_info(self):
        """Refresh system information display."""
        try:
            # Re-create system tab
            old_tab = self.system_tab
            
            self.system_tab = QWidget()
            self._setup_system_tab()
            
            index = self.tab_widget.indexOf(old_tab)
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, self.system_tab, "System Info")
            self.tab_widget.setCurrentIndex(index)
            
            # Show success message
            show_info_message(self, "System Info Refreshed", 
                             "System information has been refreshed.")
            
        except Exception as e:
            logger.error(f"Error refreshing system info: {str(e)}")
            show_error_message(self, "Refresh Error", 
                              f"Failed to refresh system information: {str(e)}")