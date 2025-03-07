#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Dashboard Module

This module implements the performance dashboard for visualizing
shooting performance trends and generating reports.

Author: Claude
Date: March 6, 2025
"""

import os
import logging
import time
import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt backend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QScrollArea, QSplitter, QFrame, QTabWidget,
    QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon

from core.report_generator import ReportGenerator
from utils.constants import (
    REPORTS_DIR,
    COLORS, SCORE_EXCELLENT, SCORE_GOOD, SCORE_FAIR
)
from utils.helpers import (
    show_error_message, show_info_message, format_timestamp,
    get_score_color
)

# Initialize logger
logger = logging.getLogger(__name__)

class MatplotlibCanvas(FigureCanvas):
    """Matplotlib canvas for embedding plots in PyQt."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        Initialize the canvas.
        
        Args:
            parent: Parent widget
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set up figure appearance
        self.fig.tight_layout()
        self.fig.patch.set_facecolor('none')  # Transparent background

class PerformanceWidget(QWidget):
    """
    Widget for performance dashboard screen.
    Visualizes performance trends and generates reports.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the performance widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Create report generator
        self.report_generator = ReportGenerator(data_manager)
        
        # Current user ID
        self.current_user_id = None
        
        # Current data
        self.performance_history = []
        self.trend_data = []
        self.joint_improvement = {}
        
        # Initialize UI
        self._init_ui()
        
        logger.info("PerformanceWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("Performance Dashboard")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Add user selection/info
        user_layout = QHBoxLayout()
        
        self.user_label = QLabel("Current Shooter: None Selected")
        self.user_label.setFont(QFont("Arial", 12))
        user_layout.addWidget(self.user_label)
        
        user_layout.addStretch()
        
        # Report controls
        self.report_btn = QPushButton("Generate Report")
        self.report_btn.setEnabled(False)
        self.report_btn.clicked.connect(self.generate_report)
        user_layout.addWidget(self.report_btn)
        
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._load_data)
        user_layout.addWidget(self.refresh_btn)
        
        self.main_layout.addLayout(user_layout)
        
        # Create tabbed interface for different visualizations
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Overview tab
        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Sessions tab
        self.sessions_tab = QWidget()
        self._setup_sessions_tab()
        self.tab_widget.addTab(self.sessions_tab, "Sessions")
        
        # Trends tab
        self.trends_tab = QWidget()
        self._setup_trends_tab()
        self.tab_widget.addTab(self.trends_tab, "Trends")
        
        # Joint Analysis tab
        self.joints_tab = QWidget()
        self._setup_joints_tab()
        self.tab_widget.addTab(self.joints_tab, "Joint Analysis")
    
    def _setup_overview_tab(self):
        """Set up the overview tab with enhanced performance metrics."""
        layout = QVBoxLayout(self.overview_tab)

        # Create top metrics row with progress indicators
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QHBoxLayout(metrics_group)

        # Performance summary with 4 metrics in a row
        self.avg_score_frame = self._create_metric_frame("Average Score", "0")
        metrics_layout.addWidget(self.avg_score_frame)

        self.best_score_frame = self._create_metric_frame("Best Score", "0")
        metrics_layout.addWidget(self.best_score_frame)

        self.session_count_frame = self._create_metric_frame("Total Sessions", "0")
        metrics_layout.addWidget(self.session_count_frame)

        self.trend_frame = self._create_metric_frame("Overall Trend", "N/A")
        metrics_layout.addWidget(self.trend_frame)

        layout.addWidget(metrics_group)

        # Add new progress tracker
        progress_group = QGroupBox("Progress Tracker")
        progress_layout = QVBoxLayout(progress_group)

        # Create progress bars for key performance indicators
        self.progress_bars = {}

        # Overall progress
        overall_layout = QHBoxLayout()
        overall_label = QLabel("Overall:")
        overall_layout.addWidget(overall_label, 1)

        self.progress_bars['overall'] = QProgressBar()
        self.progress_bars['overall'].setRange(0, 100)
        self.progress_bars['overall'].setValue(0)
        self.progress_bars['overall'].setTextVisible(True)
        self.progress_bars['overall'].setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        overall_layout.addWidget(self.progress_bars['overall'], 5)

        goal_label = QLabel("Goal: 90+")
        goal_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        overall_layout.addWidget(goal_label, 1)

        progress_layout.addLayout(overall_layout)

        # Stability progress
        stability_layout = QHBoxLayout()
        stability_label = QLabel("Stability:")
        stability_layout.addWidget(stability_label, 1)

        self.progress_bars['stability'] = QProgressBar()
        self.progress_bars['stability'].setRange(0, 100)
        self.progress_bars['stability'].setValue(0)
        self.progress_bars['stability'].setTextVisible(True)
        self.progress_bars['stability'].setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
        """)
        stability_layout.addWidget(self.progress_bars['stability'], 5)

        stability_goal = QLabel("Goal: Very Stable")
        stability_goal.setAlignment(Qt.AlignmentFlag.AlignRight)
        stability_layout.addWidget(stability_goal, 1)

        progress_layout.addLayout(stability_layout)

        # Joint alignment progress
        joints_layout = QHBoxLayout()
        joints_label = QLabel("Joint Alignment:")
        joints_layout.addWidget(joints_label, 1)

        self.progress_bars['joints'] = QProgressBar()
        self.progress_bars['joints'].setRange(0, 100)
        self.progress_bars['joints'].setValue(0)
        self.progress_bars['joints'].setTextVisible(True)
        self.progress_bars['joints'].setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #9b59b6;
                border-radius: 3px;
            }
        """)
        joints_layout.addWidget(self.progress_bars['joints'], 5)

        joints_goal = QLabel("Goal: Optimal Alignment")
        joints_goal.setAlignment(Qt.AlignmentFlag.AlignRight)
        joints_layout.addWidget(joints_goal, 1)

        progress_layout.addLayout(joints_layout)

        layout.addWidget(progress_group)

        # Recent performance plot (enhanced)
        recent_group = QGroupBox("Recent Performance")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_canvas = MatplotlibCanvas(width=8, height=4)
        recent_layout.addWidget(self.recent_canvas)

        layout.addWidget(recent_group)

        # Strengths and weaknesses in a horizontal layout
        strengths_weakness_layout = QHBoxLayout()

        # Strengths
        strengths_group = QGroupBox("Strengths")
        strengths_layout = QVBoxLayout(strengths_group)
        self.strengths_label = QLabel("No data available")
        self.strengths_label.setWordWrap(True)
        strengths_layout.addWidget(self.strengths_label)
        strengths_weakness_layout.addWidget(strengths_group)

        # Weaknesses
        weaknesses_group = QGroupBox("Areas to Improve")
        weaknesses_layout = QVBoxLayout(weaknesses_group)
        self.weaknesses_label = QLabel("No data available")
        self.weaknesses_label.setWordWrap(True)
        weaknesses_layout.addWidget(self.weaknesses_label)
        strengths_weakness_layout.addWidget(weaknesses_group)

        layout.addLayout(strengths_weakness_layout)
    
    def _setup_sessions_tab(self):
        """Set up the sessions tab with detailed session history."""
        layout = QVBoxLayout(self.sessions_tab)
        
        # Session table
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(7)
        self.session_table.setHorizontalHeaderLabels([
            "ID", "Name", "Date", "Duration", "Score", "Posture", "Stability"
        ])
        
        # Set column properties
        self.session_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.session_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect selection signal
        self.session_table.itemSelectionChanged.connect(self._session_selection_changed)
        
        layout.addWidget(self.session_table)
        
        # Session details
        details_group = QGroupBox("Session Details")
        details_layout = QVBoxLayout(details_group)
        
        self.session_details = QLabel("Select a session to view details")
        self.session_details.setWordWrap(True)
        details_layout.addWidget(self.session_details)
        
        # Session actions
        actions_layout = QHBoxLayout()
        
        self.view_session_btn = QPushButton("View Session")
        self.view_session_btn.setEnabled(False)
        self.view_session_btn.clicked.connect(self._view_session)
        actions_layout.addWidget(self.view_session_btn)
        
        self.report_session_btn = QPushButton("Generate Session Report")
        self.report_session_btn.setEnabled(False)
        self.report_session_btn.clicked.connect(self._generate_session_report)
        actions_layout.addWidget(self.report_session_btn)
        
        self.delete_session_btn = QPushButton("Delete Session")
        self.delete_session_btn.setEnabled(False)
        self.delete_session_btn.clicked.connect(self._delete_session)
        actions_layout.addWidget(self.delete_session_btn)
        
        details_layout.addLayout(actions_layout)
        
        layout.addWidget(details_group)
    
    def _setup_trends_tab(self):
        """Set up the trends tab with trend visualizations."""
        layout = QVBoxLayout(self.trends_tab)
        
        # Time period selector
        period_layout = QHBoxLayout()
        
        period_label = QLabel("Time Period:")
        period_layout.addWidget(period_label)
        
        self.period_combo = QComboBox()
        self.period_combo.addItem("Last 30 Days", 30)
        self.period_combo.addItem("Last 90 Days", 90)
        self.period_combo.addItem("Last 180 Days", 180)
        self.period_combo.addItem("All Time", 365*10)  # 10 years as "all time"
        self.period_combo.currentIndexChanged.connect(self._period_changed)
        period_layout.addWidget(self.period_combo)
        
        period_layout.addStretch()
        
        layout.addLayout(period_layout)
        
        # Score trend plot
        trend_group = QGroupBox("Score Trend")
        trend_layout = QVBoxLayout(trend_group)
        
        self.trend_canvas = MatplotlibCanvas(width=8, height=4)
        trend_layout.addWidget(self.trend_canvas)
        
        layout.addWidget(trend_group)
        
        # Analysis plots
        analysis_layout = QHBoxLayout()
        
        # Posture quality distribution
        posture_group = QGroupBox("Posture Quality Distribution")
        posture_layout = QVBoxLayout(posture_group)
        
        self.posture_canvas = MatplotlibCanvas(width=4, height=4)
        posture_layout.addWidget(self.posture_canvas)
        
        analysis_layout.addWidget(posture_group)
        
        # Stability distribution
        stability_group = QGroupBox("Stability Distribution")
        stability_layout = QVBoxLayout(stability_group)
        
        self.stability_canvas = MatplotlibCanvas(width=4, height=4)
        stability_layout.addWidget(self.stability_canvas)
        
        analysis_layout.addWidget(stability_group)
        
        layout.addLayout(analysis_layout)
    
    def _setup_joints_tab(self):
        """Set up the joints tab with joint-specific analysis."""
        layout = QVBoxLayout(self.joints_tab)
        
        # Joint improvement plot
        improvement_group = QGroupBox("Joint Improvement")
        improvement_layout = QVBoxLayout(improvement_group)
        
        self.joint_canvas = MatplotlibCanvas(width=8, height=4)
        improvement_layout.addWidget(self.joint_canvas)
        
        layout.addWidget(improvement_group)
        
        # Joint details
        details_group = QGroupBox("Joint Details")
        details_layout = QHBoxLayout(details_group)
        
        # Create frames for each joint group
        joints_layout = QHBoxLayout()
        
        # Upper body joints
        upper_group = QGroupBox("Upper Body")
        upper_layout = QVBoxLayout(upper_group)
        
        self.shoulder_label = QLabel("Shoulders: No data")
        upper_layout.addWidget(self.shoulder_label)
        
        self.elbow_label = QLabel("Elbows: No data")
        upper_layout.addWidget(self.elbow_label)
        
        self.wrist_label = QLabel("Wrists: No data")
        upper_layout.addWidget(self.wrist_label)
        
        self.neck_label = QLabel("Neck: No data")
        upper_layout.addWidget(self.neck_label)
        
        joints_layout.addWidget(upper_group)
        
        # Lower body joints
        lower_group = QGroupBox("Lower Body")
        lower_layout = QVBoxLayout(lower_group)
        
        self.hip_label = QLabel("Hips: No data")
        lower_layout.addWidget(self.hip_label)
        
        self.knee_label = QLabel("Knees: No data")
        lower_layout.addWidget(self.knee_label)
        
        joints_layout.addWidget(lower_group)
        
        details_layout.addLayout(joints_layout)
        
        layout.addWidget(details_group)
        
        # Recommendations based on joint analysis
        recommendations_group = QGroupBox("Joint-Specific Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.joint_recommendations = QLabel("No recommendations available")
        self.joint_recommendations.setWordWrap(True)
        recommendations_layout.addWidget(self.joint_recommendations)
        
        layout.addWidget(recommendations_group)
    
    def _create_metric_frame(self, title, value):
        """
        Create a frame for displaying a metric.
        
        Args:
            title: Metric title
            value: Initial value
            
        Returns:
            QFrame containing the metric display
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame.setLineWidth(1)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 10))
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # Store value label for later updates
        frame.value_label = value_label
        
        return frame
    
    def set_user(self, user_id):
        """
        Set the current user and load their data.
        
        Args:
            user_id: User ID
        """
        self.current_user_id = user_id
        
        if user_id:
            # Get user data
            user = self.data_manager.get_user(user_id)
            if user:
                self.user_label.setText(f"Current Shooter: {user['name']}")
                self.report_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                
                # Load data
                self._load_data()
            else:
                self.user_label.setText("Current Shooter: Unknown")
                self.report_btn.setEnabled(False)
                self.refresh_btn.setEnabled(False)
        else:
            self.user_label.setText("Current Shooter: None Selected")
            self.report_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)

    def _load_data(self):
        """Load performance data for the current user."""
        if not self.current_user_id:
            return

        try:
            # Show busy cursor
            self.setCursor(Qt.CursorShape.WaitCursor)

            # Try loading performance history
            self.performance_history = self.data_manager.get_user_performance_history(
                self.current_user_id, limit=20
            )

            # If no data, use direct session data approach
            if not self.performance_history:
                logger.info("No performance history found, generating from session data directly")
                self.performance_history = self.data_manager.get_performance_data_from_session_data(
                    self.current_user_id, limit=20
                )

            # Log what we got
            logger.info(f"Performance history items: {len(self.performance_history)}")

            # If we still have no performance history, the user truly has no sessions
            if not self.performance_history:
                logger.info("No sessions found for this user")

                # Display a message to the user
                self.score_value.setText("0")
                self.score_value.setStyleSheet("")

                self.session_info.setText("No sessions found")
                self.feedback_text.setText("Complete a shooting session to view performance data")

                # Update empty UI
                self._update_overview_tab()
                self._update_progress_tracker()
                self._update_sessions_tab()
                self._update_trends_tab()
                self._update_joints_tab()

                self.setCursor(Qt.CursorShape.ArrowCursor)
                return

            # Load trend data (from actual performance or generate if needed)
            days = self.period_combo.currentData()
            self.trend_data = self.data_manager.get_performance_trend(
                self.current_user_id, days=days
            )

            # If no trend data but we have performance history, create trend data
            if not self.trend_data and self.performance_history:
                logger.info("Generating trend data from performance history")
                self._generate_trend_data_from_history()

            # Load joint improvement data
            self.joint_improvement = self.data_manager.get_joint_improvement(
                self.current_user_id, sessions=10
            )

            # If no joint improvement data but we have session_data, generate it
            if (not self.joint_improvement or all(not data.get('trend') for data in self.joint_improvement.values())) and self.performance_history:
                logger.info("Generating joint improvement data")
                self._generate_joint_improvement_data()

            # Update UI
            self._update_overview_tab()
            self._update_progress_tracker()
            self._update_sessions_tab()
            self._update_trends_tab()
            self._update_joints_tab()

            logger.info(f"Loaded performance data for user {self.current_user_id}")

        except Exception as e:
            logger.error(f"Error loading performance data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            show_error_message(self, "Data Error", 
                             f"Failed to load performance data: {str(e)}")
        finally:
            # Restore cursor
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # Enhance the _generate_trend_data_from_history method in performance.py

    def _generate_trend_data_from_history(self):
        """Generate trend data from performance history."""
        try:
            if not self.performance_history:
                logger.info("No performance history to generate trend data from")
                return

            logger.info(f"Generating trend data from {len(self.performance_history)} history items")

            # Group by date
            date_groups = {}
            for session in self.performance_history:
                # Skip sessions with no score
                if session.get('overall_score') is None:
                    continue

                # Extract date part from timestamp
                if 'timestamp' in session and session['timestamp']:
                    try:
                        # Try to handle different timestamp formats
                        if ' ' in session['timestamp']:
                            date_str = session['timestamp'].split()[0]  # Format: YYYY-MM-DD HH:MM:SS
                        else:
                            date_str = session['timestamp']  # Already just the date

                        # Ensure it's a valid date format
                        import datetime
                        datetime.datetime.strptime(date_str, '%Y-%m-%d')

                        # Store by date
                        if date_str not in date_groups:
                            date_groups[date_str] = []

                        date_groups[date_str].append(session['overall_score'])
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse timestamp {session['timestamp']}: {e}")
                        continue
                else:
                    logger.warning(f"Session missing timestamp: {session}")

            # Debug
            logger.info(f"Grouped into {len(date_groups)} dates")

            # Calculate average score for each date
            trend_data = []
            for date_str, scores in date_groups.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    trend_data.append({
                        'date': date_str,
                        'avg_score': avg_score
                    })

            # If we only have one data point, create a second artificial one
            # This helps the graph render properly
            if len(trend_data) == 1:
                import datetime
                from datetime import timedelta

                # Get yesterday's date
                today_date = datetime.datetime.strptime(trend_data[0]['date'], '%Y-%m-%d')
                yesterday = today_date - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')

                # Add a duplicate point with yesterday's date
                # Using same score to show a flat trend
                trend_data.append({
                    'date': yesterday_str,
                    'avg_score': trend_data[0]['avg_score']
                })

            # Sort by date
            trend_data.sort(key=lambda x: x['date'])

            logger.info(f"Generated {len(trend_data)} trend data points")
            for point in trend_data:
                logger.info(f"  {point['date']}: {point['avg_score']}")

            self.trend_data = trend_data

        except Exception as e:
            logger.error(f"Error generating trend data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.trend_data = []

    def _generate_joint_improvement_data(self):
        """Generate joint improvement data from session data."""
        try:
            # Get all session IDs from performance history
            session_ids = [s['session_id'] for s in self.performance_history]

            if not session_ids:
                return

            # Initialize joint data
            joint_data = {}
            for joint in ['knees', 'hips', 'left_shoulder', 'right_shoulder', 
                         'left_elbow', 'right_elbow', 'wrists', 'neck']:
                joint_data[joint] = {'sessions': [], 'trend': None}

            # Process each session
            for session_id in session_ids:
                # Get session data
                session_data = self.data_manager.get_session_data(session_id)
                if not session_data:
                    continue

                # Get session info
                session_info = next((s for s in self.performance_history if s['session_id'] == session_id), None)
                if not session_info:
                    continue
                
                # Calculate average angles and deviations for each joint
                for joint in joint_data.keys():
                    angles = []
                    deviations = []

                    for frame in session_data:
                        if 'joint_angles' not in frame or not frame['joint_angles']:
                            continue

                        joint_angles = frame['joint_angles']
                        if joint in joint_angles:
                            angle = joint_angles[joint]
                            angles.append(angle)

                            # Calculate deviation from ideal (if available)
                            ideal_angles = {
                                'knees': 172.5,
                                'hips': 180.0,
                                'left_shoulder': 45.0,
                                'right_shoulder': 15.0,
                                'left_elbow': 75.0,
                                'right_elbow': 90.0,
                                'wrists': 180.0,
                                'neck': 12.5,
                            }

                            if joint in ideal_angles:
                                deviation = abs(angle - ideal_angles[joint])
                                deviations.append(deviation)

                    if angles:
                        avg_angle = sum(angles) / len(angles)
                        avg_deviation = sum(deviations) / len(deviations) if deviations else None

                        # Add to joint data
                        joint_data[joint]['sessions'].append({
                            'session_id': session_id,
                            'timestamp': session_info['timestamp'],
                            'avg_angle': avg_angle,
                            'avg_deviation': avg_deviation
                        })

            # Calculate improvement trends
            for joint, data in joint_data.items():
                if len(data['sessions']) >= 2:
                    # Sort by timestamp
                    sessions_sorted = sorted(data['sessions'], key=lambda x: x['timestamp'])

                    if sessions_sorted[0]['avg_deviation'] is not None and sessions_sorted[-1]['avg_deviation'] is not None:
                        # Calculate trend (positive = improvement = less deviation)
                        first_deviation = sessions_sorted[0]['avg_deviation']
                        last_deviation = sessions_sorted[-1]['avg_deviation']

                        # A negative trend means deviation decreased (improvement)
                        # We flip the sign to make positive values = improvement
                        trend = first_deviation - last_deviation
                        data['trend'] = trend

                        # Generate improvement values between -10 and +10
                        norm_trend = max(-10, min(10, trend))
                        data['trend'] = norm_trend

                        logger.info(f"Joint {joint} trend: {norm_trend}")

            self.joint_improvement = joint_data

        except Exception as e:
            logger.error(f"Error generating joint improvement data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_overview_tab(self):
        """Update overview tab with current data."""
        if not self.performance_history:
            # Clear metrics
            self.avg_score_frame.value_label.setText("0")
            self.best_score_frame.value_label.setText("0")
            self.session_count_frame.value_label.setText("0")
            self.trend_frame.value_label.setText("N/A")

            # Update strengths and weaknesses with more informative messages
            self.strengths_label.setText("No performance data available. Complete a shooting session to view your strengths.")
            self.weaknesses_label.setText("No performance data available. Complete a shooting session to identify areas for improvement.")

            # Clear plot but add informative text
            self.recent_canvas.axes.clear()
            self.recent_canvas.axes.text(0.5, 0.5, "No session data available\nComplete a shooting session to see performance metrics", 
                                       horizontalalignment='center', verticalalignment='center',
                                       transform=self.recent_canvas.axes.transAxes)
            self.recent_canvas.draw()

            return

        try:
            # Calculate metrics
            scores = [s['overall_score'] for s in self.performance_history if s.get('overall_score') is not None]

            if scores:
                avg_score = sum(scores) / len(scores)
                best_score = max(scores)

                # Update metric frames
                self.avg_score_frame.value_label.setText(f"{avg_score:.1f}")
                self.best_score_frame.value_label.setText(f"{best_score:.1f}")

                # Set colors based on score
                self.avg_score_frame.value_label.setStyleSheet(f"color: {get_score_color(avg_score)};")
                self.best_score_frame.value_label.setStyleSheet(f"color: {get_score_color(best_score)};")

            # Update session count
            self.session_count_frame.value_label.setText(str(len(self.performance_history)))

            # Calculate trend
            if self.trend_data and len(self.trend_data) >= 2:
                first_score = self.trend_data[0]['avg_score']
                last_score = self.trend_data[-1]['avg_score']

                trend = last_score - first_score

                if abs(trend) < 1:
                    trend_text = "Stable"
                    trend_color = COLORS['primary']
                elif trend > 0:
                    trend_text = f"↑ {trend:.1f}"
                    trend_color = COLORS['secondary']
                else:
                    trend_text = f"↓ {abs(trend):.1f}"
                    trend_color = COLORS['danger']

                self.trend_frame.value_label.setText(trend_text)
                self.trend_frame.value_label.setStyleSheet(f"color: {trend_color};")
            else:
                self.trend_frame.value_label.setText("N/A")
                self.trend_frame.value_label.setStyleSheet("")

            # Plot recent performance
            ax = self.recent_canvas.axes
            ax.clear()

            if scores:
                # Reverse data to show most recent on the right
                session_indices = list(range(1, len(scores) + 1))
                scores_to_plot = scores.copy()  # Create a copy to avoid modifying the original
                scores_to_plot.reverse()
                session_indices.reverse()

                # Create the bar chart
                bars = ax.bar(session_indices, scores_to_plot, color=COLORS['primary'])

                # Color bars based on score
                for i, bar in enumerate(bars):
                    bar.set_color(get_score_color(scores_to_plot[i]))

                # Add threshold lines
                ax.axhline(y=SCORE_EXCELLENT, color=COLORS['secondary'], linestyle='--', alpha=0.7, 
                          label=f'Excellent ({SCORE_EXCELLENT})')
                ax.axhline(y=SCORE_GOOD, color=COLORS['primary'], linestyle='--', alpha=0.7,
                          label=f'Good ({SCORE_GOOD})')
                ax.axhline(y=SCORE_FAIR, color=COLORS['warning'], linestyle='--', alpha=0.7,
                          label=f'Fair ({SCORE_FAIR})')

                # Add legend
                ax.legend(loc='upper right', fontsize='small')

                # Add labels
                ax.set_xlabel('Session (Most Recent → Oldest)')
                ax.set_ylabel('Score')
                ax.set_title('Recent Session Scores')

                # Set y limits
                ax.set_ylim(0, 100)

                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7, axis='y')

                # Adjust layout for better fit
                self.recent_canvas.fig.tight_layout()

            self.recent_canvas.draw()

            # Update strengths and weaknesses
            strengths = []
            weaknesses = []

            # Analyze posture qualities
            quality_counts = {}
            for session in self.performance_history:
                quality = session.get('posture_quality')
                if quality:
                    if quality not in quality_counts:
                        quality_counts[quality] = 0
                    quality_counts[quality] += 1

            # Identify most common quality
            if quality_counts:
                most_common = max(quality_counts.items(), key=lambda x: x[1])

                if most_common[0] in ('Excellent', 'Good'):
                    strengths.append(f"Consistent {most_common[0]} posture quality")
                elif most_common[0] in ('Fair', 'Needs Improvement'):
                    weaknesses.append(f"Posture quality often rated as '{most_common[0]}'")

            # Analyze joint improvement
            for joint, data in self.joint_improvement.items():
                if data.get('trend') is not None:
                    if data['trend'] > 5:
                        strengths.append(f"Strong improvement in {joint.replace('_', ' ')} positioning")
                    elif data['trend'] < -5:
                        weaknesses.append(f"Declining performance in {joint.replace('_', ' ')} positioning")

            # Update labels
            if strengths:
                self.strengths_label.setText("\n".join(f"• {s}" for s in strengths))
            else:
                self.strengths_label.setText("No specific strengths identified yet")

            if weaknesses:
                self.weaknesses_label.setText("\n".join(f"• {w}" for w in weaknesses))
            else:
                self.weaknesses_label.setText("No specific weaknesses identified yet")

        except Exception as e:
            logger.error(f"Error updating overview tab: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_sessions_tab(self):
        """Update sessions tab with current data."""
        # Clear current data
        self.session_table.setRowCount(0)
        self.session_details.setText("Select a session to view details")
        self.view_session_btn.setEnabled(False)
        self.report_session_btn.setEnabled(False)
        self.delete_session_btn.setEnabled(False)
        
        if not self.performance_history:
            return
        
        try:
            # Populate session table
            for session in self.performance_history:
                row = self.session_table.rowCount()
                self.session_table.insertRow(row)
                
                # Create items
                id_item = QTableWidgetItem(str(session['session_id']))
                name_item = QTableWidgetItem(session['name'])
                date_item = QTableWidgetItem(format_timestamp(session['timestamp']))
                
                duration_text = "N/A"
                if session.get('duration'):
                    minutes, seconds = divmod(session['duration'], 60)
                    duration_text = f"{minutes}:{seconds:02d}"
                
                duration_item = QTableWidgetItem(duration_text)
                
                score_text = "N/A"
                if session.get('overall_score'):
                    score_text = f"{session['overall_score']:.1f}"
                
                score_item = QTableWidgetItem(score_text)
                
                posture_item = QTableWidgetItem(session.get('posture_quality', "N/A"))
                stability_item = QTableWidgetItem(session.get('stability', "N/A"))
                
                # Set items as non-editable
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                score_item.setFlags(score_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                posture_item.setFlags(posture_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                stability_item.setFlags(stability_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Add items to table
                self.session_table.setItem(row, 0, id_item)
                self.session_table.setItem(row, 1, name_item)
                self.session_table.setItem(row, 2, date_item)
                self.session_table.setItem(row, 3, duration_item)
                self.session_table.setItem(row, 4, score_item)
                self.session_table.setItem(row, 5, posture_item)
                self.session_table.setItem(row, 6, stability_item)
            
        except Exception as e:
            logger.error(f"Error updating sessions tab: {str(e)}")

        # Enhance the _update_trends_tab method in performance.py
    def _update_trends_tab(self):
        """Update trends tab with current data."""
        try:
            # Update score trend plot
            ax = self.trend_canvas.axes
            ax.clear()

            # Check if we have trend data
            if self.trend_data and len(self.trend_data) >= 1:
                logger.info(f"Plotting trend data with {len(self.trend_data)} points")

                # Extract data
                dates = [item['date'] for item in self.trend_data]
                scores = [item['avg_score'] for item in self.trend_data]

                # Print data for debugging
                for i, (date, score) in enumerate(zip(dates, scores)):
                    logger.info(f"Data point {i}: {date} = {score}")

                # Format dates for display
                import matplotlib.dates as mdates
                import datetime

                # Convert string dates to datetime objects
                date_objects = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in dates]

                # Plot trend with markers for each data point
                ax.plot(date_objects, scores, marker='o', linestyle='-', color=COLORS['primary'], 
                       linewidth=2, markersize=8, label='Daily Score')

                # Add threshold lines
                ax.axhline(y=SCORE_EXCELLENT, color=COLORS['secondary'], linestyle='--', alpha=0.5, 
                          label=f'Excellent ({SCORE_EXCELLENT})')
                ax.axhline(y=SCORE_GOOD, color=COLORS['primary'], linestyle='--', alpha=0.5, 
                          label=f'Good ({SCORE_GOOD})')
                ax.axhline(y=SCORE_FAIR, color=COLORS['warning'], linestyle='--', alpha=0.5, 
                          label=f'Fair ({SCORE_FAIR})')

                # Add labels
                ax.set_xlabel('Date')
                ax.set_ylabel('Average Score')
                ax.set_title('Score Trend Over Time')

                # Format x-axis dates
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(date_objects)//5)))
                ax.tick_params(axis='x', rotation=45)

                # Set y limits
                ax.set_ylim(0, 100)

                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7)

                # Add legend
                ax.legend(loc='best', fontsize='small')

                # Tight layout
                self.trend_canvas.fig.tight_layout()
            else:
                # No trend data - show message
                ax.text(0.5, 0.5, "No trend data available\nComplete more sessions to see trends", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)

                # Set empty axes limits
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_xlabel('Time')
                ax.set_ylabel('Score')

            self.trend_canvas.draw()

            # Update posture quality distribution plot
            ax = self.posture_canvas.axes
            ax.clear()

            if self.performance_history:
                # Count posture qualities
                quality_counts = {}
                for session in self.performance_history:
                    quality = session.get('posture_quality')
                    if quality:
                        if quality not in quality_counts:
                            quality_counts[quality] = 0
                        quality_counts[quality] += 1

                if quality_counts:
                    # Create pie chart
                    labels = list(quality_counts.keys())
                    sizes = list(quality_counts.values())

                    # Define colors for each quality
                    colors = []
                    for label in labels:
                        if label == 'Excellent':
                            colors.append(COLORS['secondary'])
                        elif label == 'Good':
                            colors.append(COLORS['primary'])
                        elif label == 'Fair':
                            colors.append(COLORS['warning'])
                        else:
                            colors.append(COLORS['danger'])

                    # Add percentage to labels
                    total = sum(sizes)
                    labels = [f'{label} ({sizes[i]/total*100:.1f}%)' for i, label in enumerate(labels)]

                    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='',
                                                      startangle=90, wedgeprops={'edgecolor': 'w', 'linewidth': 1})

                    # Customize text
                    for text in texts:
                        text.set_fontsize(9)

                    ax.axis('equal')
                    
                else:
                    ax.text(0.5, 0.5, "No quality data available", 
                           horizontalalignment='center', verticalalignment='center',
                           transform=ax.transAxes)
                    ax.axis('equal')
            else:
                ax.text(0.5, 0.5, "No quality data available", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
                ax.axis('equal')

            self.posture_canvas.draw()

            # Update stability distribution plot
            ax = self.stability_canvas.axes
            ax.clear()

            if self.performance_history:
                # Count stability categories
                stability_counts = {}
                for session in self.performance_history:
                    stability = session.get('stability')
                    if stability:
                        if stability not in stability_counts:
                            stability_counts[stability] = 0
                        stability_counts[stability] += 1

                if stability_counts:
                    # Create pie chart
                    labels = list(stability_counts.keys())
                    sizes = list(stability_counts.values())

                    # Define colors for each stability
                    colors = []
                    for label in labels:
                        if label == 'Very Stable':
                            colors.append(COLORS['secondary'])
                        elif label == 'Stable':
                            colors.append(COLORS['primary'])
                        elif label == 'Moderately Stable':
                            colors.append(COLORS['warning'])
                        else:
                            colors.append(COLORS['danger'])

                    # Add percentage to labels
                    total = sum(sizes)
                    labels = [f'{label} ({sizes[i]/total*100:.1f}%)' for i, label in enumerate(labels)]

                    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='',
                                                      startangle=90, wedgeprops={'edgecolor': 'w', 'linewidth': 1})

                    # Customize text
                    for text in texts:
                        text.set_fontsize(9)

                    ax.axis('equal')
                    
                else:
                    ax.text(0.5, 0.5, "No stability data available", 
                           horizontalalignment='center', verticalalignment='center',
                           transform=ax.transAxes)
                    ax.axis('equal')
            else:
                ax.text(0.5, 0.5, "No stability data available", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
                ax.axis('equal')

            self.stability_canvas.draw()

        except Exception as e:
            logger.error(f"Error updating trends tab: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_joints_tab(self):
        """Update joints tab with current data."""
        try:
            # Update joint improvement plot
            ax = self.joint_canvas.axes
            ax.clear()

            if self.joint_improvement:
                # Extract joint trends
                trends = {}
                for joint, data in self.joint_improvement.items():
                    if data.get('trend') is not None:
                        trends[joint] = data['trend']

                if trends:
                    # Sort joints by name
                    sorted_joints = sorted(trends.keys())

                    # Prepare data for plotting
                    x = np.arange(len(sorted_joints))
                    trend_values = [trends[j] for j in sorted_joints]

                    # Determine colors based on trend (positive = green, negative = red)
                    colors = [COLORS['secondary'] if v > 0 else COLORS['danger'] for v in trend_values]

                    # Create the bar chart
                    bars = ax.bar(x, trend_values, color=colors)

                    # Add data labels on top of each bar
                    for i, v in enumerate(trend_values):
                        if v > 0:
                            label_y = v + 0.5
                            va = 'bottom'
                        else:
                            label_y = v - 0.5
                            va = 'top'
                        ax.text(i, label_y, f"{v:.1f}", ha='center', va=va, fontweight='bold')

                    # Add joint names to x-axis with better formatting
                    ax.set_xticks(x)
                    ax.set_xticklabels([j.replace('_', ' ').title() for j in sorted_joints])
                    ax.tick_params(axis='x', rotation=45)

                    # Add labels
                    ax.set_ylabel('Improvement Score')
                    ax.set_title('Joint Improvement Across Sessions')

                    # Add horizontal line at y=0
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)

                    # Add grid
                    ax.grid(True, linestyle='--', alpha=0.7, axis='y')

                    # Add text annotations explaining the chart
                    ax.text(0.02, 0.98, "Green bars: Improving\nRed bars: Needs work", 
                           transform=ax.transAxes, fontsize=9,
                           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

                    # Set y limits with some padding
                    max_val = max(max(trend_values) + 2, 5)
                    min_val = min(min(trend_values) - 2, -5)
                    ax.set_ylim(min_val, max_val)

                    # Tight layout
                    self.joint_canvas.fig.tight_layout()

            self.joint_canvas.draw()

            # Create and add a body map visualization
            self._create_body_map()

            # Update joint details
            self._update_joint_details()

        except Exception as e:
            logger.error(f"Error updating joints tab: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def _update_progress_tracker(self):
        """Update the progress tracker with latest performance data."""
        if not self.performance_history:
            # Reset progress bars
            for key, bar in self.progress_bars.items():
                bar.setValue(0)
            return

        try:
            # Calculate overall progress
            scores = [s.get('overall_score', 0) for s in self.performance_history if s.get('overall_score') is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                best_score = max(scores)

                # Update overall progress (as percentage of 90+ goal)
                overall_progress = min(100, int((avg_score / 90) * 100))
                self.progress_bars['overall'].setValue(overall_progress)
                self.progress_bars['overall'].setFormat(f"{avg_score:.1f}/90 ({overall_progress}%)")

                # Set color based on progress
                if avg_score >= 85:
                    color = COLORS['secondary']  # Green for excellent
                elif avg_score >= 70:
                    color = COLORS['primary']    # Blue for good
                elif avg_score >= 50:
                    color = COLORS['warning']    # Orange for fair
                else:
                    color = COLORS['danger']     # Red for poor

                self.progress_bars['overall'].setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #bbb;
                        border-radius: 4px;
                        text-align: center;
                        height: 20px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        border-radius: 3px;
                    }}
                """)

            # Calculate stability progress
            stability_mapping = {
                'Very Stable': 100,
                'Stable': 75,
                'Moderately Stable': 50,
                'Unstable': 25,
                None: 0
            }

            stability_values = [stability_mapping.get(s.get('stability'), 0) for s in self.performance_history]
            if stability_values:
                avg_stability = sum(stability_values) / len(stability_values)
                stability_progress = int(avg_stability)
                self.progress_bars['stability'].setValue(stability_progress)

                # Map value back to label
                if stability_progress >= 90:
                    stability_label = "Very Stable"
                elif stability_progress >= 70:
                    stability_label = "Stable"
                elif stability_progress >= 40:
                    stability_label = "Moderately Stable"
                else:
                    stability_label = "Unstable"

                self.progress_bars['stability'].setFormat(f"{stability_label} ({stability_progress}%)")

            # Calculate joint alignment progress
            joint_progress = 0
            if self.joint_improvement:
                joint_scores = []
                for joint, data in self.joint_improvement.items():
                    if data.get('trend') is not None:
                        # Normalize trend to 0-100 scale (trend can be negative)
                        score = 50 + data['trend'] * 5  # Center at 50, adjust by trend
                        score = max(0, min(100, score))  # Clamp to 0-100
                        joint_scores.append(score)

                if joint_scores:
                    joint_progress = int(sum(joint_scores) / len(joint_scores))
                    self.progress_bars['joints'].setValue(joint_progress)

                    # Create a descriptive label
                    if joint_progress >= 80:
                        joint_label = "Excellent"
                    elif joint_progress >= 60:
                        joint_label = "Good"
                    elif joint_progress >= 40:
                        joint_label = "Fair"
                    else:
                        joint_label = "Needs Work"

                    self.progress_bars['joints'].setFormat(f"{joint_label} ({joint_progress}%)")

        except Exception as e:
            logger.error(f"Error updating progress tracker: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _create_body_map(self):
        """Create a body map visualization showing problem areas."""
        # Create a new figure if it doesn't exist
        if not hasattr(self, 'body_map_canvas'):
            # Create a group box for the body map
            if not hasattr(self, 'body_map_group'):
                self.body_map_group = QGroupBox("Body Map Analysis")
                body_map_layout = QVBoxLayout(self.body_map_group)

                # Create canvas
                self.body_map_canvas = MatplotlibCanvas(width=4, height=6)
                body_map_layout.addWidget(self.body_map_canvas)

                # Add description
                description = QLabel("This body map shows problem areas. Red indicates joints that need improvement.")
                description.setWordWrap(True)
                body_map_layout.addWidget(description)

                # Add to joints tab layout
                # Find the joints_tab layout
                for i in range(self.joints_tab.layout().count()):
                    item = self.joints_tab.layout().itemAt(i)
                    if isinstance(item, QHBoxLayout):
                        # Add the body map group to this layout
                        item.addWidget(self.body_map_group)
                        break
                    
        # Update the body map
        ax = self.body_map_canvas.axes
        ax.clear()

        # Draw a simple stick figure
        # Head
        head = plt.Circle((0.5, 0.9), 0.1, fill=False)
        ax.add_patch(head)

        # Torso
        ax.plot([0.5, 0.5], [0.8, 0.5], 'k-', linewidth=2)

        # Arms
        ax.plot([0.5, 0.3], [0.7, 0.6], 'k-', linewidth=2)  # Left arm upper
        ax.plot([0.5, 0.7], [0.7, 0.6], 'k-', linewidth=2)  # Right arm upper
        ax.plot([0.3, 0.2], [0.6, 0.5], 'k-', linewidth=2)  # Left forearm
        ax.plot([0.7, 0.8], [0.6, 0.5], 'k-', linewidth=2)  # Right forearm

        # Legs
        ax.plot([0.5, 0.4], [0.5, 0.3], 'k-', linewidth=2)  # Left upper leg
        ax.plot([0.5, 0.6], [0.5, 0.3], 'k-', linewidth=2)  # Right upper leg
        ax.plot([0.4, 0.35], [0.3, 0.1], 'k-', linewidth=2)  # Left lower leg
        ax.plot([0.6, 0.65], [0.3, 0.1], 'k-', linewidth=2)  # Right lower leg

        # Joint positions
        joint_positions = {
            'neck': (0.5, 0.8),
            'left_shoulder': (0.5, 0.7),
            'right_shoulder': (0.5, 0.7),
            'left_elbow': (0.3, 0.6),
            'right_elbow': (0.7, 0.6),
            'left_wrist': (0.2, 0.5),
            'right_wrist': (0.8, 0.5),
            'hips': (0.5, 0.5),
            'knees': (0.5, 0.3),
            'left_knee': (0.4, 0.3),
            'right_knee': (0.6, 0.3),
            'wrists': (0.5, 0.5)  # Placeholder, will be split
        }

        # Draw problem areas if data is available
        if self.joint_improvement:
            for joint, data in self.joint_improvement.items():
                if data.get('trend') is not None:
                    trend = data['trend']

                    # Get position (handle special cases)
                    if joint in joint_positions:
                        pos = joint_positions[joint]
                    elif joint == 'wrists':
                        # Split to both wrists
                        left_pos = joint_positions['left_wrist']
                        right_pos = joint_positions['right_wrist']

                        # Draw circles at both wrists with color based on trend
                        size = max(300, min(800, 500 - trend * 50))  # Larger circle for worse trend
                        if trend < 0:
                            color = 'red'
                            alpha = min(0.8, 0.3 + abs(trend) * 0.05)
                        else:
                            color = 'green'
                            alpha = min(0.8, 0.3 + trend * 0.05)

                        ax.scatter(left_pos[0], left_pos[1], s=size, color=color, alpha=alpha)
                        ax.scatter(right_pos[0], right_pos[1], s=size, color=color, alpha=alpha)
                        continue
                    else:
                        # Skip unknown joints
                        continue
                    
                    # Draw circle at joint with color based on trend
                    size = max(300, min(800, 500 - trend * 50))  # Larger circle for worse trend
                    if trend < 0:
                        color = 'red'
                        alpha = min(0.8, 0.3 + abs(trend) * 0.05)
                    else:
                        color = 'green'
                        alpha = min(0.8, 0.3 + trend * 0.05)

                    ax.scatter(pos[0], pos[1], s=size, color=color, alpha=alpha)

                    # Add label for significantly problematic joints
                    if trend < -5:
                        ax.text(pos[0], pos[1], joint.replace('_', ' ').title(), 
                               ha='center', va='center', fontsize=8, fontweight='bold')

        # Set axis properties
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Body Map: Problem Areas')

        # Update canvas
        self.body_map_canvas.draw()
    
    def _update_joint_details(self):
        """Update the joint detail labels with enhanced information."""
        if not self.joint_improvement:
            # Clear all joint labels
            self.shoulder_label.setText("Shoulders: No data")
            self.elbow_label.setText("Elbows: No data")
            self.wrist_label.setText("Wrists: No data")
            self.neck_label.setText("Neck: No data")
            self.hip_label.setText("Hips: No data")
            self.knee_label.setText("Knees: No data")

            # Clear recommendations
            self.joint_recommendations.setText("No recommendations available")

            return

        try:
            # Update each joint group with more detailed information

            # Shoulders
            left_shoulder_data = self.joint_improvement.get('left_shoulder', {})
            right_shoulder_data = self.joint_improvement.get('right_shoulder', {})

            left_trend = left_shoulder_data.get('trend')
            right_trend = right_shoulder_data.get('trend')

            if left_trend is not None or right_trend is not None:
                shoulder_text = "<b>Shoulders:</b> "

                if left_trend is not None:
                    trend_sign = "+" if left_trend > 0 else ""
                    shoulder_text += f"Left <span style='color:{get_score_color(left_trend+50)};'>{trend_sign}{left_trend:.1f}</span> "

                if right_trend is not None:
                    trend_sign = "+" if right_trend > 0 else ""
                    shoulder_text += f"Right <span style='color:{get_score_color(right_trend+50)};'>{trend_sign}{right_trend:.1f}</span>"

                self.shoulder_label.setText(shoulder_text)
            else:
                self.shoulder_label.setText("<b>Shoulders:</b> No data")

            # Elbows
            left_elbow_data = self.joint_improvement.get('left_elbow', {})
            right_elbow_data = self.joint_improvement.get('right_elbow', {})

            left_trend = left_elbow_data.get('trend')
            right_trend = right_elbow_data.get('trend')

            if left_trend is not None or right_trend is not None:
                elbow_text = "<b>Elbows:</b> "

                if left_trend is not None:
                    trend_sign = "+" if left_trend > 0 else ""
                    elbow_text += f"Left <span style='color:{get_score_color(left_trend+50)};'>{trend_sign}{left_trend:.1f}</span> "

                if right_trend is not None:
                    trend_sign = "+" if right_trend > 0 else ""
                    elbow_text += f"Right <span style='color:{get_score_color(right_trend+50)};'>{trend_sign}{right_trend:.1f}</span>"

                self.elbow_label.setText(elbow_text)
            else:
                self.elbow_label.setText("<b>Elbows:</b> No data")

            # Wrists
            wrists_data = self.joint_improvement.get('wrists', {})
            wrists_trend = wrists_data.get('trend')

            if wrists_trend is not None:
                trend_sign = "+" if wrists_trend > 0 else ""
                self.wrist_label.setText(f"<b>Wrists:</b> <span style='color:{get_score_color(wrists_trend+50)};'>{trend_sign}{wrists_trend:.1f}</span>")
            else:
                self.wrist_label.setText("<b>Wrists:</b> No data")

            # Neck
            neck_data = self.joint_improvement.get('neck', {})
            neck_trend = neck_data.get('trend')

            if neck_trend is not None:
                trend_sign = "+" if neck_trend > 0 else ""
                self.neck_label.setText(f"<b>Neck:</b> <span style='color:{get_score_color(neck_trend+50)};'>{trend_sign}{neck_trend:.1f}</span>")
            else:
                self.neck_label.setText("<b>Neck:</b> No data")

            # Hips
            hips_data = self.joint_improvement.get('hips', {})
            hips_trend = hips_data.get('trend')

            if hips_trend is not None:
                trend_sign = "+" if hips_trend > 0 else ""
                self.hip_label.setText(f"<b>Hips:</b> <span style='color:{get_score_color(hips_trend+50)};'>{trend_sign}{hips_trend:.1f}</span>")
            else:
                self.hip_label.setText("<b>Hips:</b> No data")

            # Knees
            knees_data = self.joint_improvement.get('knees', {})
            knees_trend = knees_data.get('trend')

            if knees_trend is not None:
                trend_sign = "+" if knees_trend > 0 else ""
                self.knee_label.setText(f"<b>Knees:</b> <span style='color:{get_score_color(knees_trend+50)};'>{trend_sign}{knees_trend:.1f}</span>")
            else:
                self.knee_label.setText("<b>Knees:</b> No data")

            # Generate enhanced recommendations
            recommendations = []

            # Find joints that need improvement
            needs_improvement = []
            for joint, data in self.joint_improvement.items():
                trend = data.get('trend')
                if trend is not None and trend < -2:
                    needs_improvement.append((joint, trend))

            if needs_improvement:
                # Sort by most negative trend
                needs_improvement.sort(key=lambda x: x[1])

                # Add specific, actionable recommendations for top 3 issues
                for joint, trend in needs_improvement[:3]:
                    if 'shoulder' in joint:
                        if 'left' in joint:
                            recommendations.append(
                                f"<b>Left Shoulder Issue:</b> Your left shoulder position shows a decline of {abs(trend):.1f} points. "
                                f"Focus on maintaining proper shoulder alignment. Try these exercises:<br>"
                                f"• Shoulder raises with light weights<br>"
                                f"• Wall presses to strengthen stabilizing muscles<br>"
                                f"• Practice maintaining rifle support with your left arm"
                            )
                        else:
                            recommendations.append(
                                f"<b>Right Shoulder Issue:</b> Your right shoulder position shows a decline of {abs(trend):.1f} points. "
                                f"Ensure your right shoulder remains relaxed while shooting. Try:<br>"
                                f"• Shoulder rotation exercises<br>"
                                f"• Conscious relaxation of your trigger arm"
                            )
                    elif 'elbow' in joint:
                        if 'left' in joint:
                            recommendations.append(
                                f"<b>Left Elbow Issue:</b> Your supporting arm elbow position needs work ({abs(trend):.1f} points decline). "
                                f"Focus on creating a stable platform. Try:<br>"
                                f"• Practice left elbow positioning against a bench or table<br>"
                                f"• Use a sling to help support the rifle weight<br>"
                                f"• Strengthen triceps for better support"
                            )
                        else:
                            recommendations.append(
                                f"<b>Right Elbow Issue:</b> Your trigger arm elbow position shows a {abs(trend):.1f} point decline. "
                                f"Work on consistent positioning. Try:<br>"
                                f"• Practice maintaining a consistent trigger pull angle<br>"
                                f"• Ensure your grip is not causing your elbow to rise"
                            )
                    elif joint == 'neck':
                        recommendations.append(
                            f"<b>Neck Position Issue:</b> Your neck angle has declined by {abs(trend):.1f} points. "
                            f"This affects your sight alignment. Try:<br>"
                            f"• Practice proper cheek weld on the stock<br>"
                            f"• Check if your stock height is appropriate<br>"
                            f"• Strengthen neck muscles with isometric exercises"
                        )
                    elif joint == 'hips':
                        recommendations.append(
                            f"<b>Hip Alignment Issue:</b> Your hip alignment shows a {abs(trend):.1f} point decline. "
                            f"This affects your overall stability. Try:<br>"
                            f"• Practice your stance without the rifle<br>"
                            f"• Core strengthening exercises<br>"
                            f"• Balance exercises on one foot"
                        )
                    elif joint == 'knees':
                        recommendations.append(
                            f"<b>Knee Position Issue:</b> Your knee bend shows a {abs(trend):.1f} point decline. "
                            f"This affects your stability. Try:<br>"
                            f"• Practice maintaining slight knee bend in your stance<br>"
                            f"• Leg strengthening exercises like squats<br>"
                            f"• Balance practice in shooting position"
                        )
                    elif joint == 'wrists':
                        recommendations.append(
                            f"<b>Wrist Position Issue:</b> Your wrist position has declined by {abs(trend):.1f} points. "
                            f"This can affect trigger control. Try:<br>"
                            f"• Wrist strengthening exercises<br>"
                            f"• Practice maintaining a straight line from elbow through wrist"
                        )

            # If no specific issues, add general recommendation
            if not recommendations:
                recommendations.append(
                    "<b>Good progress!</b> Your joint positions show good improvement or stability. "
                    "Continue practicing your current form. Consider these maintenance exercises:<br>"
                    "• Regular shoulder and arm strengthening<br>"
                    "• Core stability work<br>"
                    "• Balance practice in shooting stance"
                )

            # Update recommendations label
            self.joint_recommendations.setText("<br><br>".join(recommendations))

        except Exception as e:
            logger.error(f"Error updating joint details: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _session_selection_changed(self):
        """Handle selection change in the session table."""
        selected_items = self.session_table.selectedItems()

        if not selected_items:
            self.session_details.setText("Select a session to view details")
            self.view_session_btn.setEnabled(False)
            self.report_session_btn.setEnabled(False)
            self.delete_session_btn.setEnabled(False)
            return

        # Get the first selected row
        row = selected_items[0].row()

        # Get session ID from the first column
        session_id_item = self.session_table.item(row, 0)
        if not session_id_item:
            return

        session_id = int(session_id_item.text())

        # Load session details
        try:
            session = self.data_manager.get_session(session_id)

            if not session:
                self.session_details.setText("Session details not available")
                return

            # Enable buttons
            self.view_session_btn.setEnabled(True)
            self.report_session_btn.setEnabled(True)
            self.delete_session_btn.setEnabled(True)

            # Get detailed session data for analysis
            session_data = self.data_manager.get_session_data(session_id)

            # Format details text with enhanced analysis
            details = f"<h3>Session: {session['name']}</h3>"
            details += f"<p><b>Date:</b> {format_timestamp(session['timestamp'])}</p>"

            if session.get('duration'):
                minutes, seconds = divmod(session['duration'], 60)
                details += f"<p><b>Duration:</b> {minutes}:{seconds:02d}</p>"

            if session.get('overall_score'):
                score = session['overall_score']
                score_color = get_score_color(score)
                details += f"<p><b>Overall Score:</b> <span style='color:{score_color};font-weight:bold;'>{score:.1f}</span></p>"

            if session.get('posture_quality'):
                quality = session['posture_quality']
                quality_color = COLORS['secondary'] if quality in ('Excellent', 'Good') else COLORS['warning'] if quality == 'Fair' else COLORS['danger']
                details += f"<p><b>Posture Quality:</b> <span style='color:{quality_color};font-weight:bold;'>{quality}</span></p>"

            if session.get('stability'):
                stability = session['stability']
                stability_color = COLORS['secondary'] if stability in ('Very Stable', 'Stable') else COLORS['warning'] if stability == 'Moderately Stable' else COLORS['danger']
                details += f"<p><b>Stability:</b> <span style='color:{stability_color};font-weight:bold;'>{stability}</span></p>"

            # Add frame count if available
            if session_data:
                details += f"<p><b>Frames Analyzed:</b> {len(session_data)}</p>"

            # Add performance breakdown if data available
            if session_data and len(session_data) > 0:
                details += "<h4>Performance Breakdown:</h4>"

                # Calculate joint angle consistency
                joint_stats = {}
                for frame in session_data:
                    for joint, angle in frame.get('joint_angles', {}).items():
                        if joint not in joint_stats:
                            joint_stats[joint] = []
                        joint_stats[joint].append(angle)

                # Identify most and least consistent joints
                joint_consistency = {}
                for joint, angles in joint_stats.items():
                    if len(angles) >= 2:
                        mean = sum(angles) / len(angles)
                        variance = sum((x - mean) ** 2 for x in angles) / len(angles)
                        std_dev = variance ** 0.5
                        coefficient_of_variation = (std_dev / mean) * 100 if mean != 0 else float('inf')
                        joint_consistency[joint] = coefficient_of_variation

                if joint_consistency:
                    # Sort by consistency (lower is better)
                    sorted_joints = sorted(joint_consistency.items(), key=lambda x: x[1])

                    most_consistent = sorted_joints[0]
                    least_consistent = sorted_joints[-1]

                    details += f"<p><b>Most Consistent Joint:</b> {most_consistent[0].replace('_', ' ').title()} (±{most_consistent[1]:.1f}%)</p>"
                    details += f"<p><b>Least Consistent Joint:</b> {least_consistent[0].replace('_', ' ').title()} (±{least_consistent[1]:.1f}%)</p>"

                # Calculate score progression
                scores = [frame.get('posture_score', 0) for frame in session_data]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    min_score = min(scores)
                    max_score = max(scores)

                    # Calculate trend within session
                    if len(scores) >= 2:
                        start_score = scores[0]
                        end_score = scores[-1]
                        session_trend = end_score - start_score

                        trend_text = "improved" if session_trend > 0 else "declined" if session_trend < 0 else "remained stable"
                        trend_color = COLORS['secondary'] if session_trend > 0 else COLORS['danger'] if session_trend < 0 else COLORS['primary']

                        details += f"<p><b>Score Progression:</b> Performance <span style='color:{trend_color};'>{trend_text}</span> during session ({abs(session_trend):.1f} points)</p>"

                    details += f"<p><b>Score Range:</b> {min_score:.1f} to {max_score:.1f} (Average: {avg_score:.1f})</p>"

            # Add summary if available
            if session.get('summary'):
                summary = session['summary']

                details += "<h4>Session Summary:</h4>"

                if summary.get('key_strengths'):
                    details += "<p><b>Key Strengths:</b></p><ul>"
                    for strength in summary['key_strengths']:
                        details += f"<li>{strength}</li>"
                    details += "</ul>"

                if summary.get('areas_to_improve'):
                    details += "<p><b>Areas to Improve:</b></p><ul>"
                    for area in summary['areas_to_improve']:
                        details += f"<li>{area}</li>"
                    details += "</ul>"

                if summary.get('recommendations'):
                    details += "<p><b>Recommendations:</b></p><ul>"
                    for rec in summary['recommendations']:
                        details += f"<li>{rec}</li>"
                    details += "</ul>"

            # Create comparison with previous sessions
            if self.performance_history and len(self.performance_history) > 1:
                # Find this session's index in history
                session_index = -1
                for i, s in enumerate(self.performance_history):
                    if s['session_id'] == session_id:
                        session_index = i
                        break
                    
                if session_index >= 0 and session_index < len(self.performance_history) - 1:
                    # Get previous session for comparison
                    prev_session = self.performance_history[session_index + 1]  # +1 because history is in reverse order

                    if prev_session.get('overall_score') and session.get('overall_score'):
                        score_diff = session['overall_score'] - prev_session['overall_score']

                        # Add comparison section
                        details += "<h4>Comparison to Previous Session:</h4>"

                        comparison_color = COLORS['secondary'] if score_diff > 0 else COLORS['danger'] if score_diff < 0 else COLORS['primary']
                        comparison_text = "improvement" if score_diff > 0 else "decline" if score_diff < 0 else "no change"

                        details += f"<p><b>Score Change:</b> <span style='color:{comparison_color};'>{abs(score_diff):.1f} point {comparison_text}</span></p>"

                        # Compare stability if available
                        if prev_session.get('stability') and session.get('stability'):
                            stability_mapping = {
                                'Very Stable': 4,
                                'Stable': 3,
                                'Moderately Stable': 2,
                                'Unstable': 1
                            }

                            current_stability = stability_mapping.get(session['stability'], 0)
                            prev_stability = stability_mapping.get(prev_session['stability'], 0)

                            if current_stability != prev_stability:
                                stability_text = "improved" if current_stability > prev_stability else "declined"
                                stability_color = COLORS['secondary'] if current_stability > prev_stability else COLORS['danger']

                                details += f"<p><b>Stability:</b> <span style='color:{stability_color};'>Stability {stability_text}</span> from previous session</p>"

            self.session_details.setText(details)

        except Exception as e:
            logger.error(f"Error loading session details: {str(e)}")
            self.session_details.setText(f"Error loading session details: {str(e)}")
    
    def _view_session(self):
        """View the selected session in the replay screen."""
        selected_items = self.session_table.selectedItems()
        
        if not selected_items:
            return
        
        # Get the first selected row
        row = selected_items[0].row()
        
        # Get session ID from the first column
        session_id_item = self.session_table.item(row, 0)
        if not session_id_item:
            return
        
        session_id = int(session_id_item.text())
        
        # Notify parent to navigate to replay screen and load session
        # This is a simplified approach - in a real app, you'd use signals or other mechanisms
        parent = self.parent()
        while parent and not hasattr(parent, '_navigate'):
            parent = parent.parent()
        
        if parent and hasattr(parent, '_navigate'):
            parent._navigate('replay')
            if hasattr(parent.widgets['replay'], 'load_session'):
                parent.widgets['replay'].load_session(session_id)
    
    def _generate_session_report(self):
        """Generate a report for the selected session."""
        selected_items = self.session_table.selectedItems()
        
        if not selected_items:
            return
        
        # Get the first selected row
        row = selected_items[0].row()
        
        # Get session ID from the first column
        session_id_item = self.session_table.item(row, 0)
        if not session_id_item:
            return
        
        session_id = int(session_id_item.text())
        
        try:
            # Show "Generating report" message
            QMessageBox.information(
                self, 
                "Generating Report", 
                "Generating session report...\n\nThis may take a moment."
            )
            
            # Generate report
            report_path = self.report_generator.create_session_report(
                session_id, REPORTS_DIR
            )
            
            if report_path and os.path.exists(report_path):
                # Show success message with file location
                QMessageBox.information(
                    self, 
                    "Report Generated", 
                    f"Session report generated successfully!\n\n"
                    f"The report has been saved to:\n{report_path}"
                )
                
                # Open the report file or containing folder
                # This uses platform-specific commands, simplified here
                try:
                    import subprocess
                    import platform
                    
                    if platform.system() == 'Windows':
                        os.startfile(report_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', report_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', report_path])
                except Exception as e:
                    logger.error(f"Error opening report: {str(e)}")
            else:
                show_error_message(self, "Report Error", 
                                  "Failed to generate the report.")
            
        except Exception as e:
            logger.error(f"Error generating session report: {str(e)}")
            show_error_message(self, "Report Error", 
                              f"Failed to generate report: {str(e)}")
    
    def _delete_session(self):
        """Delete the selected session."""
        selected_items = self.session_table.selectedItems()
        
        if not selected_items:
            return
        
        # Get the first selected row
        row = selected_items[0].row()
        
        # Get session ID and name
        session_id_item = self.session_table.item(row, 0)
        session_name_item = self.session_table.item(row, 1)
        
        if not session_id_item or not session_name_item:
            return
        
        session_id = int(session_id_item.text())
        session_name = session_name_item.text()
        
        # Confirm deletion
        confirmed = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete the session '{session_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Delete the session
            success = self.data_manager.delete_session(session_id)
            
            if success:
                # Refresh data
                self._load_data()
                
                # Show success message
                QMessageBox.information(
                    self, 
                    "Session Deleted", 
                    f"Session '{session_name}' has been deleted successfully."
                )
            else:
                show_error_message(self, "Delete Error", 
                                  "Failed to delete the session. Session not found.")
            
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            show_error_message(self, "Delete Error", 
                              f"Failed to delete session: {str(e)}")
    
    def _period_changed(self, index):
        """
        Handle change in time period selection.
        
        Args:
            index: New index in the combo box
        """
        # Reload trend data
        if self.current_user_id:
            days = self.period_combo.currentData()
            self.trend_data = self.data_manager.get_performance_trend(
                self.current_user_id, days=days
            )
            
            # Update trend plot
            self._update_trends_tab()
    
    def generate_report(self):
        """Generate a comprehensive performance report."""
        if not self.current_user_id:
            show_error_message(self, "No User Selected", 
                              "Please select a shooter profile before generating a report.")
            return
        
        try:
            # Show "Generating report" message
            QMessageBox.information(
                self, 
                "Generating Report", 
                "Generating performance report...\n\nThis may take a moment."
            )
            
            # Generate report
            report_path = self.report_generator.create_progress_report(
                self.current_user_id, REPORTS_DIR
            )
            
            if report_path and os.path.exists(report_path):
                # Show success message with file location
                QMessageBox.information(
                    self, 
                    "Report Generated", 
                    f"Performance report generated successfully!\n\n"
                    f"The report has been saved to:\n{report_path}"
                )
                
                # Open the report file or containing folder
                try:
                    import subprocess
                    import platform
                    
                    if platform.system() == 'Windows':
                        os.startfile(report_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', report_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', report_path])
                except Exception as e:
                    logger.error(f"Error opening report: {str(e)}")
            else:
                show_error_message(self, "Report Error", 
                                  "Failed to generate the report.")
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            show_error_message(self, "Report Error", 
                              f"Failed to generate report: {str(e)}")