#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay & Analysis Module

This module implements the session replay screen for reviewing
recorded shooting sessions with detailed analysis.

Author: Claude
Date: March 6, 2025
"""

import os
import logging
import time
import cv2
import numpy as np
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QComboBox, QGroupBox, QCheckBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

from core.video_processor import VideoPlayer
from core.posture_analyzer import PostureAnalyzer
from utils.constants import COLORS, VIDEO_WIDTH, VIDEO_HEIGHT
from utils.helpers import (
    cv_to_qt_pixmap, show_error_message, show_info_message,
    get_score_color, format_timestamp
)

# Initialize logger
logger = logging.getLogger(__name__)

class ReplayWidget(QWidget):
    """
    Widget for session replay screen.
    Allows reviewing recorded sessions with detailed analysis.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the replay widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Initialize video player
        self.video_player = VideoPlayer()
        
        # Initialize posture analyzer for reference angles
        self.posture_analyzer = PostureAnalyzer()
        
        # Current user ID
        self.current_user_id = None
        
        # Current session ID and data
        self.current_session_id = None
        self.current_session = None
        self.session_data = None
        
        # Playback state
        self.is_playing = False
        self.current_frame_index = 0
        self.last_frame_time = 0
        
        # Display options
        self.show_keypoints = True
        self.show_angles = True
        self.show_ideal_overlay = False
        
        # Initialize UI
        self._init_ui()
        
        # Initialize playback timer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._play_next_frame)
        self.playback_timer.setInterval(100)  # 10 fps playback

        self.video_cap = None
        self.video_thread = None
        self.stop_video_thread = False
        self.current_video_path = None
        self.frame_rate = 15
        
        logger.info("ReplayWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("Replay & Analysis")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Add session selector
        selector_layout = QHBoxLayout()
        
        session_label = QLabel("Select Session:")
        selector_layout.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(300)
        self.session_combo.currentIndexChanged.connect(self._session_selected)
        selector_layout.addWidget(self.session_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_sessions)
        selector_layout.addWidget(self.refresh_btn)
        
        selector_layout.addStretch()
        
        self.main_layout.addLayout(selector_layout)
        
        # Create splitter for video and analysis panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Create left panel (video display)
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 10, 10, 0)
        
        # Video display
        self.video_frame = QLabel()
        self.video_frame.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame.setStyleSheet("background-color: black;")
        left_layout.addWidget(self.video_frame)
        
        # Playback controls
        controls_layout = QHBoxLayout()
        
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setEnabled(False)
        self.play_pause_btn.setMinimumHeight(30)
        self.play_pause_btn.clicked.connect(self._toggle_playback)
        controls_layout.addWidget(self.play_pause_btn)
        
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setEnabled(False)
        self.restart_btn.setMinimumHeight(30)
        self.restart_btn.clicked.connect(self._restart_playback)
        controls_layout.addWidget(self.restart_btn)
        
        left_layout.addLayout(controls_layout)
        
        # Playback slider
        slider_layout = QHBoxLayout()
        
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(100)
        self.frame_slider.setValue(0)
        self.frame_slider.valueChanged.connect(self._slider_moved)
        slider_layout.addWidget(self.frame_slider)
        
        self.frame_counter = QLabel("0/0")
        slider_layout.addWidget(self.frame_counter)
        
        left_layout.addLayout(slider_layout)
        
        # Display options
        options_group = QGroupBox("Display Options")
        options_layout = QHBoxLayout(options_group)
        
        self.keypoints_check = QCheckBox("Show Keypoints")
        self.keypoints_check.setChecked(self.show_keypoints)
        self.keypoints_check.toggled.connect(self._toggle_keypoints)
        options_layout.addWidget(self.keypoints_check)
        
        self.angles_check = QCheckBox("Show Angles")
        self.angles_check.setChecked(self.show_angles)
        self.angles_check.toggled.connect(self._toggle_angles)
        options_layout.addWidget(self.angles_check)
        
        self.ideal_check = QCheckBox("Show Ideal Overlay")
        self.ideal_check.setChecked(self.show_ideal_overlay)
        self.ideal_check.toggled.connect(self._toggle_ideal_overlay)
        options_layout.addWidget(self.ideal_check)
        
        left_layout.addWidget(options_group)
        
        # Add left panel to splitter
        self.splitter.addWidget(self.left_panel)
        
        # Create right panel (analysis)
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 10, 0, 0)
        
        # Session info
        info_group = QGroupBox("Session Information")
        info_layout = QVBoxLayout(info_group)
        
        self.session_info = QLabel("No session loaded")
        self.session_info.setWordWrap(True)
        info_layout.addWidget(self.session_info)
        
        right_layout.addWidget(info_group)
        
        # Current frame analysis
        analysis_group = QGroupBox("Current Frame Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        # Create score display
        score_layout = QHBoxLayout()
        
        score_label = QLabel("Posture Score:")
        score_layout.addWidget(score_label)
        
        self.score_value = QLabel("0")
        self.score_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        score_layout.addWidget(self.score_value)
        
        score_layout.addStretch()
        
        analysis_layout.addLayout(score_layout)
        
        # Feedback text
        self.feedback_text = QLabel("No feedback available")
        self.feedback_text.setWordWrap(True)
        analysis_layout.addWidget(self.feedback_text)
        
        right_layout.addWidget(analysis_group)
        
        # Joint angles display
        angles_group = QGroupBox("Joint Angles")
        angles_scroll = QScrollArea()
        angles_scroll.setWidgetResizable(True)
        angles_content = QWidget()
        angles_layout = QVBoxLayout(angles_content)
        
        # Create frames for each joint
        self.angle_frames = {}
        joint_names = [
            'knees', 'hips', 'left_shoulder', 'right_shoulder', 
            'left_elbow', 'right_elbow', 'wrists', 'neck'
        ]
        
        for joint in joint_names:
            frame = self._create_joint_angle_frame(joint)
            self.angle_frames[joint] = frame
            angles_layout.addWidget(frame)
        
        angles_scroll.setWidget(angles_content)
        angles_layout.addStretch()
        
        right_layout.addWidget(angles_scroll)
        
        # Add right panel to splitter
        self.splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
    
    def _create_joint_angle_frame(self, joint_name):
        """
        Create a frame for displaying joint angle information.
        
        Args:
            joint_name: Name of the joint
            
        Returns:
            QFrame containing the joint angle display
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame.setLineWidth(1)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Joint name label
        name_label = QLabel(joint_name.replace('_', ' ').title())
        name_label.setMinimumWidth(100)
        layout.addWidget(name_label)
        
        # Current angle
        current_label = QLabel("Current:")
        layout.addWidget(current_label)
        
        current_value = QLabel("N/A")
        current_value.setMinimumWidth(50)
        layout.addWidget(current_value)
        
        # Ideal angle
        ideal_label = QLabel("Ideal:")
        layout.addWidget(ideal_label)
        
        ideal_value = QLabel("N/A")
        ideal_value.setMinimumWidth(50)
        layout.addWidget(ideal_value)
        
        # Difference
        diff_label = QLabel("Diff:")
        layout.addWidget(diff_label)
        
        diff_value = QLabel("N/A")
        diff_value.setMinimumWidth(50)
        layout.addWidget(diff_value)
        
        # Store value labels for updates
        frame.current_value = current_value
        frame.ideal_value = ideal_value
        frame.diff_value = diff_value
        
        return frame
    
    def set_user(self, user_id):
        """
        Set the current user and load their sessions.
        
        Args:
            user_id: User ID
        """
        self.current_user_id = user_id
        
        if user_id:
            self._refresh_sessions()
        else:
            self.session_combo.clear()
            self._clear_session()
    
    def _refresh_sessions(self):
        """Refresh the list of available sessions."""
        if not self.current_user_id:
            return
        
        try:
            # Get user sessions
            sessions = self.data_manager.get_user_performance_history(
                self.current_user_id, limit=20
            )
            
            # Update combo box
            self.session_combo.blockSignals(True)
            self.session_combo.clear()
            
            self.session_combo.addItem("Select a session...", None)
            
            for session in sessions:
                # Format label as "Name - Date (Score)"
                label = f"{session['name']} - {session['timestamp'].split()[0]}"
                
                if session.get('overall_score'):
                    label += f" ({session['overall_score']:.1f})"
                
                self.session_combo.addItem(label, session['session_id'])
            
            self.session_combo.blockSignals(False)
            
            # Clear current session
            self._clear_session()
            
            logger.info(f"Loaded {len(sessions)} sessions for user {self.current_user_id}")
            
        except Exception as e:
            logger.error(f"Error refreshing sessions: {str(e)}")
            show_error_message(self, "Data Error", 
                              f"Failed to load sessions: {str(e)}")
    
    def _session_selected(self, index):
        """
        Handle selection of a session from the combo box.
        
        Args:
            index: Index of the selected item
        """
        if index <= 0:
            self._clear_session()
            return
        
        # Get session ID
        session_id = self.session_combo.currentData()
        
        if session_id is None:
            self._clear_session()
            return
        
        # Load the session
        self.load_session(session_id)
    
    def load_session(self, session_id):
        """
        Load a session for replay.

        Args:
            session_id: Session ID to load
        """
        try:
            # Clear current session
            self._clear_session()

            # Store session ID
            self.current_session_id = session_id

            # Get session data
            self.current_session = self.data_manager.get_session(session_id)

            if not self.current_session:
                show_error_message(self, "Session Error", 
                                  "Failed to load session. Session not found.")
                return

            # Check if there's a video path
            if 'video_path' in self.current_session and self.current_session['video_path']:
                # Store the video path
                data_dir = os.path.dirname(self.data_manager.db_path)
                self.current_video_path = os.path.join(data_dir, self.current_session['video_path'])

                # Validate the video file
                if not os.path.exists(self.current_video_path):
                    logger.warning(f"Video file not found: {self.current_video_path}")
                    self.current_video_path = None

                    # Show warning to user
                    show_error_message(self, "Video Not Found", 
                                     f"The video file for this session could not be found. "
                                     f"Will attempt to load individual frames instead.")
            else:
                self.current_video_path = None

            # Get detailed session data
            self.session_data = self.data_manager.get_session_data(session_id)

            if not self.session_data:
                show_error_message(self, "Session Error", 
                                  "This session has no recorded data.")
                return

            # Update UI with session info
            self._update_session_info()

            # Prepare video player
            self._prepare_playback()

            logger.info(f"Loaded session ID: {session_id} with {len(self.session_data)} frames")

        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            show_error_message(self, "Session Error", 
                              f"Failed to load session: {str(e)}")
            self._clear_session()
    
    def _clear_session(self):
        """Clear the current session and reset UI."""
        # Reset session data
        self.current_session_id = None
        self.current_session = None
        self.session_data = None
        self.current_frame_index = 0
        
        # Stop playback
        self._stop_playback()
        
        # Reset video display
        self.video_frame.clear()
        self.video_frame.setText("No session loaded")
        
        # Reset controls
        self.play_pause_btn.setText("Play")
        self.play_pause_btn.setEnabled(False)
        self.restart_btn.setEnabled(False)
        self.frame_slider.setValue(0)
        self.frame_slider.setEnabled(False)
        self.frame_counter.setText("0/0")
        
        # Reset session info
        self.session_info.setText("No session loaded")
        
        # Reset analysis display
        self.score_value.setText("0")
        self.score_value.setStyleSheet("")
        self.feedback_text.setText("No feedback available")
        
        # Reset joint angles
        for joint, frame in self.angle_frames.items():
            frame.current_value.setText("N/A")
            frame.ideal_value.setText("N/A")
            frame.diff_value.setText("N/A")
            frame.current_value.setStyleSheet("")
            frame.diff_value.setStyleSheet("")
    
    def _update_session_info(self):
        """Update the session information display."""
        if not self.current_session:
            self.session_info.setText("No session loaded")
            return
        
        # Format session info text
        info_text = f"<b>Session:</b> {self.current_session['name']}<br>"
        info_text += f"<b>Date:</b> {format_timestamp(self.current_session['timestamp'])}<br>"
        
        if self.current_session.get('duration'):
            minutes, seconds = divmod(self.current_session['duration'], 60)
            info_text += f"<b>Duration:</b> {minutes}:{seconds:02d}<br>"
        
        if self.current_session.get('overall_score'):
            info_text += f"<b>Overall Score:</b> {self.current_session['overall_score']:.1f}<br>"
        
        if self.current_session.get('posture_quality'):
            info_text += f"<b>Posture Quality:</b> {self.current_session['posture_quality']}<br>"
        
        if self.current_session.get('stability'):
            info_text += f"<b>Stability:</b> {self.current_session['stability']}<br>"
        
        if self.session_data:
            info_text += f"<b>Frames:</b> {len(self.session_data)}<br>"
        
        self.session_info.setText(info_text)
    
    def _prepare_playback(self):
        """Prepare the video player for playback."""
        if not self.session_data:
            return

        # Set up slider
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(len(self.session_data) - 1)
        self.frame_slider.setValue(0)
        self.frame_slider.setEnabled(True)

        # Update frame counter
        self.frame_counter.setText(f"0/{len(self.session_data) - 1}")

        # Enable controls
        self.play_pause_btn.setEnabled(True)
        self.restart_btn.setEnabled(True)

        # Close existing video capture if any
        if self.video_cap is not None:
            self.video_cap.release()
            self.video_cap = None

        # Initialize video capture if video path exists
        if self.current_video_path and os.path.exists(self.current_video_path):
            try:
                self.video_cap = cv2.VideoCapture(self.current_video_path)

                if self.video_cap.isOpened():
                    # Get video properties
                    fps = self.video_cap.get(cv2.CAP_PROP_FPS)
                    if fps > 0:
                        self.frame_rate = fps

                    frame_count = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    logger.info(f"Opened video with {frame_count} frames at {self.frame_rate} FPS")

                    # Reset to first frame
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                else:
                    logger.warning(f"Failed to open video file: {self.current_video_path}")
                    self.video_cap = None
            except Exception as e:
                logger.error(f"Error initializing video capture: {str(e)}")
                self.video_cap = None

        # Display first frame
        self._show_frame(0)

    

    def _show_frame(self, frame_index):
        """
        Display a specific frame from the session.

        Args:
            frame_index: Index of the frame to display
        """
        if not self.session_data or frame_index < 0 or frame_index >= len(self.session_data):
            return

        try:
            # Get frame data
            frame_data = self.session_data[frame_index]

            # Extract data
            joint_angles = frame_data['joint_angles']
            posture_score = frame_data['posture_score']
            feedback = frame_data['feedback']

            # Update UI
            self._update_analysis_display(posture_score, feedback, joint_angles)

            # Update frame counter
            self.frame_counter.setText(f"{frame_index}/{len(self.session_data) - 1}")

            # Update slider (without triggering valueChanged)
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(frame_index)
            self.frame_slider.blockSignals(False)

            # Store current index
            self.current_frame_index = frame_index

            # Get the frame image - try multiple sources in order of preference:
            # 1. Video file if available
            # 2. Preloaded frame_image if available
            # 3. Load from frame_path if available
            # 4. Generate a placeholder

            display_frame = None

            # 1. Try to get frame from video file
            if self.video_cap is not None and self.video_cap.isOpened():
                # Seek to the correct frame
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ret, frame = self.video_cap.read()

                if ret:
                    display_frame = frame

            # 2. Try to use preloaded frame_image
            if display_frame is None and 'frame_image' in frame_data and frame_data['frame_image'] is not None:
                display_frame = frame_data['frame_image']

            # 3. Try to load from frame_path
            if display_frame is None and 'frame_path' in frame_data and frame_data['frame_path']:
                try:
                    # Construct absolute path
                    data_dir = os.path.dirname(self.data_manager.db_path)
                    abs_path = os.path.join(data_dir, frame_data['frame_path'])

                    if os.path.exists(abs_path):
                        display_frame = cv2.imread(abs_path)

                        if display_frame is None:
                            logger.warning(f"Failed to load image at {abs_path}")
                    else:
                        logger.warning(f"Image file not found at {abs_path}")
                except Exception as e:
                    logger.error(f"Error loading frame from path: {str(e)}")

            # 4. If all else fails, generate a placeholder
            if display_frame is None:
                placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder_frame, "Frame data unavailable", (50, 240), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(placeholder_frame, f"Score: {posture_score:.1f}", 
                          (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                display_frame = placeholder_frame

            # Update display
            pixmap = cv_to_qt_pixmap(display_frame)
            scaled_pixmap = pixmap.scaled(
                self.video_frame.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_frame.setPixmap(scaled_pixmap)

        except Exception as e:
            logger.error(f"Error displaying frame {frame_index}: {str(e)}")
    
    def _update_analysis_display(self, score, feedback, joint_angles):
        """
        Update the analysis display with the current frame data.
        
        Args:
            score: Posture score
            feedback: Feedback messages
            joint_angles: Joint angle measurements
        """
        # Update score
        self.score_value.setText(f"{score:.1f}")
        self.score_value.setStyleSheet(f"color: {get_score_color(score)};")
        
        # Update feedback
        if isinstance(feedback, list) and feedback:
            self.feedback_text.setText("<br>".join(f"• {msg}" for msg in feedback))
        else:
            self.feedback_text.setText("No feedback available")
        
        # Update joint angles
        self._update_joint_angles(joint_angles)
    
    def _update_joint_angles(self, joint_angles):
        """
        Update the joint angle display.
        
        Args:
            joint_angles: Dictionary of joint angle measurements
        """
        # Get ideal angles
        ideal_angles = self.posture_analyzer.ideal_angles
        
        # Update each joint frame
        for joint, frame in self.angle_frames.items():
            if joint in joint_angles:
                current_angle = joint_angles[joint]
                ideal_angle = ideal_angles.get(joint, 0)
                diff = abs(current_angle - ideal_angle)
                
                # Update values
                frame.current_value.setText(f"{current_angle:.1f}°")
                frame.ideal_value.setText(f"{ideal_angle:.1f}°")
                frame.diff_value.setText(f"{diff:.1f}°")
                
                # Set colors based on difference
                if diff <= 5:
                    color = COLORS['secondary']  # Green for good
                elif diff <= 15:
                    color = COLORS['warning']  # Orange for fair
                else:
                    color = COLORS['danger']  # Red for poor
                
                frame.current_value.setStyleSheet(f"color: {color};")
                frame.diff_value.setStyleSheet(f"color: {color};")
            else:
                # Clear values
                frame.current_value.setText("N/A")
                frame.ideal_value.setText("N/A")
                frame.diff_value.setText("N/A")
                frame.current_value.setStyleSheet("")
                frame.diff_value.setStyleSheet("")
    
    def _toggle_playback(self):
        """Toggle playback state."""
        if not self.session_data:
            return
        
        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()
    
    def _start_playback(self):
        """Start playback."""
        if not self.session_data:
            return

        self.is_playing = True
        self.play_pause_btn.setText("Pause")

        # If we have a video file, use video playback thread
        if self.video_cap is not None and self.video_cap.isOpened():
            # Stop existing thread if running
            self._stop_video_thread()

            # Start new thread
            self.stop_video_thread = False
            self.video_thread = threading.Thread(target=self._video_playback_loop)
            self.video_thread.daemon = True
            self.video_thread.start()
        else:
            # Use timer for frame-by-frame playback from images
            self.last_frame_time = time.time()
            self.playback_timer.start()
    
    def _stop_playback(self):
        """Stop playback."""
        self.is_playing = False
        self.play_pause_btn.setText("Play")

        # Stop playback timer
        self.playback_timer.stop()

        # Stop video thread if running
        self._stop_video_thread()
    
    def _restart_playback(self):
        """Restart playback from the beginning."""
        if not self.session_data:
            return
        
        # Stop playback
        self._stop_playback()
        
        # Reset to first frame
        self._show_frame(0)
        
        # Start playback again if desired
        if QMessageBox.question(
            self, 
            "Restart Playback", 
            "Would you like to start playback from the beginning?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        ) == QMessageBox.StandardButton.Yes:
            self._start_playback()
    
    def _play_next_frame(self):
        """Play the next frame during playback."""
        if not self.session_data or not self.is_playing:
            return
        
        # Calculate next frame
        next_frame = self.current_frame_index + 1
        
        # Check if we've reached the end
        if next_frame >= len(self.session_data):
            self._stop_playback()
            return
        
        # Show the next frame
        self._show_frame(next_frame)
    
    def _slider_moved(self, value):
        """
        Handle slider movement to seek to a specific frame.
        
        Args:
            value: New slider value (frame index)
        """
        if not self.session_data:
            return
        
        # Stop playback
        if self.is_playing:
            self._stop_playback()
        
        # Show the specified frame
        self._show_frame(value)
    
    def _toggle_keypoints(self, checked):
        """
        Toggle display of keypoints.
        
        Args:
            checked: New checkbox state
        """
        self.show_keypoints = checked
        self._show_frame(self.current_frame_index)
    
    def _toggle_angles(self, checked):
        """
        Toggle display of angle annotations.
        
        Args:
            checked: New checkbox state
        """
        self.show_angles = checked
        self._show_frame(self.current_frame_index)
    
    def _toggle_ideal_overlay(self, checked):
        """
        Toggle display of ideal pose overlay.
        
        Args:
            checked: New checkbox state
        """
        self.show_ideal_overlay = checked
        self._show_frame(self.current_frame_index)
    
    
    def _stop_video_thread(self):
        """Stop the video playback thread if running."""
        if self.video_thread and self.video_thread.is_alive():
            self.stop_video_thread = True
            self.video_thread.join(timeout=1.0)
            self.video_thread = None
    
    def _video_playback_loop(self):
        """Video playback loop running in a separate thread."""
        try:
            # Ensure video is at the current frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index)

            # Calculate frame interval
            frame_interval = 1.0 / self.frame_rate

            while not self.stop_video_thread and self.is_playing:
                # Get the next frame
                ret, frame = self.video_cap.read()

                if not ret:
                    # End of video, stop playback
                    break
                
                # Get current frame index
                current_pos = int(self.video_cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

                if current_pos >= len(self.session_data):
                    # We've reached the end of our data
                    break
                
                # Update the UI with the new frame
                # We need to use signals/slots to update UI from a background thread
                # For simplicity, we'll use the setValue signal from the slider
                # This will trigger _slider_moved which updates the display
                self.frame_slider.blockSignals(False)
                self.frame_slider.setValue(current_pos)
                self.frame_slider.blockSignals(True)

                # Sleep to maintain frame rate
                time.sleep(frame_interval)

            # Stop playback when the thread exits
            if self.is_playing:
                self.is_playing = False
                # Update UI in main thread
                QTimer.singleShot(0, lambda: self.play_pause_btn.setText("Play"))

        except Exception as e:
            logger.error(f"Error in video playback thread: {str(e)}")
            self.is_playing = False

    def cleanup(self):
        """Clean up resources before widget is destroyed."""
        # Stop playback timer
        if hasattr(self, 'playback_timer'):
            self.playback_timer.stop()

        # Stop video thread
        self._stop_video_thread()

        # Release video capture
        if hasattr(self, 'video_cap') and self.video_cap is not None:
            self.video_cap.release()
            self.video_cap = None