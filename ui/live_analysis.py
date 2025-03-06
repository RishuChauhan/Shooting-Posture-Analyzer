#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Analysis Module

This module implements the live video analysis screen for
real-time posture feedback and recording.

Author: Claude
Date: March 6, 2025
"""

import os
import logging
import time
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QFrame, QSplitter, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor

from core.video_processor import VideoThread
from core.posture_analyzer import PostureAnalyzer
from utils.constants import (
    VIDEO_WIDTH, VIDEO_HEIGHT, DEFAULT_CAMERA_ID,
    ANALYSIS_INTERVAL, SCORE_EXCELLENT, SCORE_GOOD, SCORE_FAIR,
    COLORS
)
from utils.helpers import (
    cv_to_qt_pixmap, show_error_message, show_info_message,
    get_score_color, format_duration
)

# Initialize logger
logger = logging.getLogger(__name__)

class LiveAnalysisWidget(QWidget):
    """
    Widget for live video analysis screen.
    Provides real-time posture feedback and session recording.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the live analysis widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Initialize video thread
        self.video_thread = None
        
        # Initialize posture analyzer
        self.posture_analyzer = PostureAnalyzer()
        
        # Current user ID
        self.current_user_id = None
        
        # Current session ID
        self.current_session_id = None
        
        # Recording state
        self.is_recording = False
        self.recording_start_time = None
        self.frame_count = 0
        
        # Analysis state
        self.last_analysis_time = 0
        self.current_score = 0
        self.pose_detected = False
        self.analysis_results = []
        
        # Initialize UI
        self._init_ui()
        
        # Initialize camera from settings
        self._init_camera()
        
        logger.info("LiveAnalysisWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("Live Posture Analysis")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Create left panel (video feed)
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 10, 10, 0)
        
        # Video display
        self.video_frame = QLabel()
        self.video_frame.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame.setStyleSheet("background-color: black;")
        left_layout.addWidget(self.video_frame)
        
        # Camera controls
        camera_controls = QWidget()
        camera_layout = QHBoxLayout(camera_controls)
        
        self.camera_label = QLabel("Camera:")
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Default Camera", DEFAULT_CAMERA_ID)
        
        # Scan for available cameras (up to 5)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                if i != DEFAULT_CAMERA_ID:
                    self.camera_combo.addItem(f"Camera {i}", i)
        
        self.refresh_camera_btn = QPushButton("Refresh")
        self.refresh_camera_btn.clicked.connect(self._refresh_cameras)
        
        camera_layout.addWidget(self.camera_label)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addWidget(self.refresh_camera_btn)
        camera_layout.addStretch()
        
        left_layout.addWidget(camera_controls)
        
        # Recording controls
        recording_controls = QWidget()
        recording_layout = QHBoxLayout(recording_controls)
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setMinimumHeight(40)
        self.record_btn.clicked.connect(self._toggle_recording)
        
        self.save_session_btn = QPushButton("Save Session")
        self.save_session_btn.setMinimumHeight(40)
        self.save_session_btn.setEnabled(False)
        self.save_session_btn.clicked.connect(self._save_session)
        
        recording_layout.addWidget(self.record_btn)
        recording_layout.addWidget(self.save_session_btn)
        
        left_layout.addWidget(recording_controls)
        
        # Add left panel to splitter
        self.splitter.addWidget(self.left_panel)
        
        # Create right panel (feedback and analysis)
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 10, 0, 0)
        
        # Current score display
        score_group = QGroupBox("Posture Score")
        score_layout = QVBoxLayout(score_group)
        
        self.score_label = QLabel("0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        
        self.score_bar = QProgressBar()
        self.score_bar.setMinimum(0)
        self.score_bar.setMaximum(100)
        self.score_bar.setValue(0)
        self.score_bar.setTextVisible(False)
        self.score_bar.setMinimumHeight(30)
        
        score_layout.addWidget(self.score_label)
        score_layout.addWidget(self.score_bar)
        
        right_layout.addWidget(score_group)
        
        # Real-time feedback
        feedback_group = QGroupBox("Posture Feedback")
        feedback_layout = QVBoxLayout(feedback_group)
        
        self.feedback_text = QTextEdit()
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setMinimumHeight(150)
        
        feedback_layout.addWidget(self.feedback_text)
        
        right_layout.addWidget(feedback_group)
        
        # Session info
        session_group = QGroupBox("Session Information")
        session_layout = QVBoxLayout(session_group)
        
        self.session_info = QLabel("No active session")
        self.session_info.setWordWrap(True)
        
        self.duration_label = QLabel("Duration: 00:00")
        self.frames_label = QLabel("Frames: 0")
        
        session_layout.addWidget(self.session_info)
        session_layout.addWidget(self.duration_label)
        session_layout.addWidget(self.frames_label)
        
        right_layout.addWidget(session_group)
        
        # Joint angles display
        angles_group = QGroupBox("Joint Angles")
        angles_layout = QVBoxLayout(angles_group)
        
        # Create scrollable area for joint angles
        angles_scroll = QScrollArea()
        angles_scroll.setWidgetResizable(True)
        angles_content = QWidget()
        self.angles_layout = QVBoxLayout(angles_content)
        
        # Create labels for each joint
        self.angle_labels = {}
        joint_names = [
            'knees', 'hips', 'left_shoulder', 'right_shoulder', 
            'left_elbow', 'right_elbow', 'wrists', 'neck'
        ]
        
        for joint in joint_names:
            label = QLabel(f"{joint.replace('_', ' ').title()}: N/A")
            self.angle_labels[joint] = label
            self.angles_layout.addWidget(label)
        
        angles_scroll.setWidget(angles_content)
        angles_layout.addWidget(angles_scroll)
        
        right_layout.addWidget(angles_group)
        
        # Add right panel to splitter
        self.splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        
        # Add timer for updating UI
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start(100)  # Update every 100ms
    
    def _init_camera(self):
        """Initialize the camera and video thread."""
        try:
            # Get camera ID from settings
            camera_id_str = self.data_manager.get_app_setting('camera_id')
            camera_id = int(camera_id_str) if camera_id_str else DEFAULT_CAMERA_ID
            
            # Update combo box
            index = self.camera_combo.findData(camera_id)
            if index >= 0:
                self.camera_combo.setCurrentIndex(index)
            
            # Connect camera change signal
            self.camera_combo.currentIndexChanged.connect(self._change_camera)
            
            # Initialize video thread
            self._start_video_thread(camera_id)
            
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            show_error_message(self, "Camera Error", 
                              f"Failed to initialize camera: {str(e)}")
    
    def _start_video_thread(self, camera_id):
        """
        Start the video capture thread.
        
        Args:
            camera_id: Camera device ID
        """
        # Clean up existing thread if any
        if self.video_thread is not None:
            self.video_thread.stop()
            self.video_thread = None
        
        # Create and start new thread
        self.video_thread = VideoThread(camera_id)
        self.video_thread.frame_ready.connect(self._update_frame)
        self.video_thread.pose_data_ready.connect(self._process_pose_data)
        self.video_thread.error_occurred.connect(self._handle_video_error)
        self.video_thread.start()
        
        logger.info(f"Started video thread with camera ID: {camera_id}")
    
    def _update_frame(self, frame):
        """
        Update the video frame display.
        
        Args:
            frame: OpenCV image frame
        """
        # Convert to QPixmap and display
        pixmap = cv_to_qt_pixmap(frame)
        
        # Scale pixmap to fit the label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.video_frame.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.video_frame.setPixmap(scaled_pixmap)
        
        # Update frame count if recording
        if self.is_recording:
            self.frame_count += 1
    
    def _process_pose_data(self, joint_angles, pose_detected):
        """
        Process pose data from video thread.
        
        Args:
            joint_angles: Dictionary of joint angles
            pose_detected: Boolean indicating if pose was detected
        """
        self.pose_detected = pose_detected
        
        # Skip if no pose detected
        if not pose_detected:
            self._update_feedback(["No pose detected. Please stand in front of the camera."])
            self._update_joint_angles({})
            self.current_score = 0
            return
        
        # Update joint angle display
        self._update_joint_angles(joint_angles)
        
        # Perform analysis at intervals
        current_time = time.time()
        if current_time - self.last_analysis_time >= ANALYSIS_INTERVAL:
            # Analyze posture
            analysis = self.posture_analyzer.analyze_posture(joint_angles)
            
            # Update UI with results
            self.current_score = analysis['score']
            self._update_feedback(analysis['feedback'])
            
            # Store analysis results if recording
            if self.is_recording:
                self.analysis_results.append(analysis)
            
            self.last_analysis_time = current_time
    
    def _update_feedback(self, feedback_messages):
        """
        Update the feedback text display.
        
        Args:
            feedback_messages: List of feedback messages
        """
        self.feedback_text.clear()
        
        if not feedback_messages:
            self.feedback_text.setPlainText("No feedback available.")
            return
        
        for msg in feedback_messages:
            self.feedback_text.append(f"• {msg}")
    
    def _update_joint_angles(self, joint_angles):
        """
        Update the joint angles display.
        
        Args:
            joint_angles: Dictionary of joint angles
        """
        if not joint_angles:
            # Clear all labels if no data
            for joint, label in self.angle_labels.items():
                label.setText(f"{joint.replace('_', ' ').title()}: N/A")
            return
        
        # Get ideal angles for comparison
        ideal_angles = self.posture_analyzer.ideal_angles
        
        # Update each joint label
        for joint, label in self.angle_labels.items():
            if joint in joint_angles:
                angle = joint_angles[joint]
                ideal = ideal_angles.get(joint, 0)
                diff = abs(angle - ideal)
                
                # Format with color based on difference
                if diff <= 5:
                    color = COLORS['secondary']  # Green for good
                elif diff <= 15:
                    color = COLORS['warning']  # Orange for fair
                else:
                    color = COLORS['danger']  # Red for poor
                
                label.setText(f"{joint.replace('_', ' ').title()}: {angle:.1f}° (Ideal: {ideal:.1f}°)")
                label.setStyleSheet(f"color: {color};")
            else:
                label.setText(f"{joint.replace('_', ' ').title()}: N/A")
                label.setStyleSheet("")
    
    def _update_ui(self):
        """Update UI elements periodically."""
        # Update score display
        self.score_label.setText(f"{int(self.current_score)}")
        self.score_bar.setValue(int(self.current_score))
        
        # Set color based on score
        score_color = get_score_color(self.current_score)
        self.score_label.setStyleSheet(f"color: {score_color};")
        self.score_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #f0f0f0;
                border: 1px solid #bdbdbd;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {score_color};
                border-radius: 5px;
            }}
        """)
        
        # Update session info if recording
        if self.is_recording and self.recording_start_time:
            elapsed = time.time() - self.recording_start_time
            self.duration_label.setText(f"Duration: {format_duration(int(elapsed))}")
            self.frames_label.setText(f"Frames: {self.frame_count}")
    
    def _toggle_recording(self):
        """Toggle recording state."""
        if not self.current_user_id:
            show_error_message(self, "No User Selected", 
                              "Please select a shooter profile before recording.")
            return
        
        if not self.video_thread:
            show_error_message(self, "No Camera", 
                              "Camera is not initialized. Cannot record.")
            return
        
        if self.is_recording:
            # Stop recording
            self._stop_recording()
        else:
            # Start recording
            self._start_recording()
    
    def _start_recording(self):
        """Start recording a new session."""
        self.is_recording = True
        self.recording_start_time = time.time()
        self.frame_count = 0
        self.analysis_results = []
        
        # Start video recording
        self.video_thread.start_recording()
        
        # Update UI
        self.record_btn.setText("Stop Recording")
        self.record_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        self.save_session_btn.setEnabled(False)
        
        # Create a new session in database
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        session_name = f"Session {timestamp}"
        self.current_session_id = self.data_manager.create_session(
            self.current_user_id, session_name
        )
        
        self.session_info.setText(f"Recording: {session_name}")
        
        logger.info(f"Started recording session ID: {self.current_session_id}")
    
    def _stop_recording(self):
        """Stop the current recording."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Calculate duration
        duration = int(time.time() - self.recording_start_time)
        
        # Stop video recording
        self.recorded_frames = self.video_thread.stop_recording()
        
        # Update UI
        self.record_btn.setText("Start Recording")
        self.record_btn.setStyleSheet("")
        self.save_session_btn.setEnabled(True)
        
        # Update session in database with duration
        if self.current_session_id:
            self.data_manager.update_session(
                self.current_session_id, duration=duration
            )
        
        self.session_info.setText(f"Session recorded: {duration} seconds, {len(self.recorded_frames)} frames")
        
        logger.info(f"Stopped recording session ID: {self.current_session_id}")
    
    def _save_session(self):
        """Save the recorded session with analysis."""
        if not self.current_session_id or not hasattr(self, 'recorded_frames'):
            show_error_message(self, "No Session", 
                              "No recorded session to save.")
            return
        
        try:
            # Process recorded frames for detailed analysis
            self._process_recorded_session()
            
            show_info_message(self, "Session Saved", 
                             "Session has been saved successfully!")
            
            # Reset state
            self.save_session_btn.setEnabled(False)
            self.session_info.setText("No active session")
            self.duration_label.setText("Duration: 00:00")
            self.frames_label.setText("Frames: 0")
            self.current_session_id = None
            
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            show_error_message(self, "Save Error", 
                              f"Failed to save session: {str(e)}")
    
    def _process_recorded_session(self):
        """Process and analyze the recorded session data."""
        if not self.recorded_frames:
            return
        
        # Extract joint angles from all frames
        joint_angles_sequence = []
        all_posture_analyses = []
        
        # Process each frame
        for i, frame_data in enumerate(self.recorded_frames):
            # Get joint angles
            joint_angles = frame_data['joint_angles']
            
            if joint_angles:
                joint_angles_sequence.append(joint_angles)
                
                # Get or create analysis for this frame
                if i < len(self.analysis_results):
                    analysis = self.analysis_results[i]
                else:
                    analysis = self.posture_analyzer.analyze_posture(joint_angles)
                
                all_posture_analyses.append(analysis)
                
                # Save frame data to database
                self.data_manager.add_session_data(
                    self.current_session_id,
                    i,
                    joint_angles,
                    analysis['score'],
                    analysis['feedback']
                )
        
        # Analyze stability
        stability_analysis = self.posture_analyzer.analyze_stability(joint_angles_sequence)
        
        # Generate session summary
        summary = self.posture_analyzer.generate_session_summary(
            all_posture_analyses, stability_analysis
        )
        
        # Update session in database
        self.data_manager.update_session(
            self.current_session_id,
            overall_score=summary['overall_score'],
            posture_quality=summary['posture_quality'],
            stability=summary['stability'],
            summary=summary
        )
        
        logger.info(f"Processed {len(self.recorded_frames)} frames for session ID: {self.current_session_id}")
    
    def _refresh_cameras(self):
        """Refresh the list of available cameras."""
        self.camera_combo.clear()
        self.camera_combo.addItem("Default Camera", DEFAULT_CAMERA_ID)
        
        # Scan for available cameras (up to 5)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                if i != DEFAULT_CAMERA_ID:
                    self.camera_combo.addItem(f"Camera {i}", i)
    
    def _change_camera(self, index):
        """
        Change the active camera.
        
        Args:
            index: Index of the selected camera in the combo box
        """
        if index < 0:
            return
        
        # Get camera ID from combo box
        camera_id = self.camera_combo.itemData(index)
        
        # Save to settings
        self.data_manager.set_app_setting('camera_id', str(camera_id))
        
        # Restart video thread with new camera
        self._start_video_thread(camera_id)
    
    def _handle_video_error(self, error_message):
        """
        Handle errors from the video thread.
        
        Args:
            error_message: Error message from the thread
        """
        logger.error(f"Video thread error: {error_message}")
        
        # Show error message to user
        if not hasattr(self, '_error_shown') or not self._error_shown:
            show_error_message(self, "Camera Error", 
                              f"Camera error: {error_message}")
            self._error_shown = True
    
    def set_user(self, user_id):
        """
        Set the current user.
        
        Args:
            user_id: User ID
        """
        self.current_user_id = user_id
    
    def start_new_session(self):
        """Start a new recording session."""
        if self.is_recording:
            # Stop current recording first
            self._stop_recording()
        
        # Start new recording
        self._start_recording()
    
    def cleanup(self):
        """Clean up resources before widget is destroyed."""
        # Stop video thread
        if self.video_thread is not None:
            self.video_thread.stop()
            self.video_thread = None
        
        # Stop timer
        if hasattr(self, 'ui_timer'):
            self.ui_timer.stop()