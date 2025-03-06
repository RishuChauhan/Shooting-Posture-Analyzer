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
        """Set up the overview tab with summary information."""
        layout = QVBoxLayout(self.overview_tab)
        
        # Performance summary
        summary_group = QGroupBox("Performance Summary")
        summary_layout = QHBoxLayout(summary_group)
        
        # Create metric frames
        self.avg_score_frame = self._create_metric_frame("Average Score", "0")
        summary_layout.addWidget(self.avg_score_frame)
        
        self.best_score_frame = self._create_metric_frame("Best Score", "0")
        summary_layout.addWidget(self.best_score_frame)
        
        self.session_count_frame = self._create_metric_frame("Total Sessions", "0")
        summary_layout.addWidget(self.session_count_frame)
        
        self.trend_frame = self._create_metric_frame("Overall Trend", "N/A")
        summary_layout.addWidget(self.trend_frame)
        
        layout.addWidget(summary_group)
        
        # Recent performance plot
        recent_group = QGroupBox("Recent Performance")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_canvas = MatplotlibCanvas(width=8, height=4)
        recent_layout.addWidget(self.recent_canvas)
        
        layout.addWidget(recent_group)
        
        # Strengths and weaknesses
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
            
            # Load performance history
            self.performance_history = self.data_manager.get_user_performance_history(
                self.current_user_id, limit=20
            )
            
            # Load trend data
            days = self.period_combo.currentData()
            self.trend_data = self.data_manager.get_performance_trend(
                self.current_user_id, days=days
            )
            
            # Load joint improvement data
            self.joint_improvement = self.data_manager.get_joint_improvement(
                self.current_user_id, sessions=10
            )
            
            # Update UI
            self._update_overview_tab()
            self._update_sessions_tab()
            self._update_trends_tab()
            self._update_joints_tab()
            
            logger.info(f"Loaded performance data for user {self.current_user_id}")
            
        except Exception as e:
            logger.error(f"Error loading performance data: {str(e)}")
            show_error_message(self, "Data Error", 
                              f"Failed to load performance data: {str(e)}")
        finally:
            # Restore cursor
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _update_overview_tab(self):
        """Update overview tab with current data."""
        if not self.performance_history:
            # Clear metrics
            self.avg_score_frame.value_label.setText("0")
            self.best_score_frame.value_label.setText("0")
            self.session_count_frame.value_label.setText("0")
            self.trend_frame.value_label.setText("N/A")
            
            # Clear strengths and weaknesses
            self.strengths_label.setText("No data available")
            self.weaknesses_label.setText("No data available")
            
            # Clear plot
            self.recent_canvas.axes.clear()
            self.recent_canvas.draw()
            
            return
        
        try:
            # Calculate metrics
            scores = [s['overall_score'] for s in self.performance_history if s['overall_score']]
            
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
                scores.reverse()
                session_indices.reverse()
                
                # Create the bar chart
                bars = ax.bar(session_indices, scores, color=COLORS['primary'])
                
                # Color bars based on score
                for i, bar in enumerate(bars):
                    bar.set_color(get_score_color(scores[i]))
                
                # Add threshold lines
                ax.axhline(y=SCORE_EXCELLENT, color=COLORS['secondary'], linestyle='--', alpha=0.7)
                ax.axhline(y=SCORE_GOOD, color=COLORS['primary'], linestyle='--', alpha=0.7)
                ax.axhline(y=SCORE_FAIR, color=COLORS['warning'], linestyle='--', alpha=0.7)
                
                # Add labels
                ax.set_xlabel('Session')
                ax.set_ylabel('Score')
                ax.set_title('Recent Session Scores')
                
                # Set y limits
                ax.set_ylim(0, 100)
                
                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7, axis='y')
            
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
    
    def _update_trends_tab(self):
        """Update trends tab with current data."""
        try:
            # Update score trend plot
            ax = self.trend_canvas.axes
            ax.clear()
            
            if self.trend_data:
                dates = [item['date'] for item in self.trend_data]
                scores = [item['avg_score'] for item in self.trend_data]
                
                # Plot trend
                ax.plot(dates, scores, marker='o', linestyle='-', color=COLORS['primary'], 
                       linewidth=2, markersize=6)
                
                # Add threshold lines
                ax.axhline(y=SCORE_EXCELLENT, color=COLORS['secondary'], linestyle='--', alpha=0.7)
                ax.axhline(y=SCORE_GOOD, color=COLORS['primary'], linestyle='--', alpha=0.7)
                ax.axhline(y=SCORE_FAIR, color=COLORS['warning'], linestyle='--', alpha=0.7)
                
                # Add labels
                ax.set_xlabel('Date')
                ax.set_ylabel('Average Score')
                ax.set_title('Score Trend Over Time')
                
                # Format x-axis dates
                ax.tick_params(axis='x', rotation=45)
                
                # Set y limits
                ax.set_ylim(0, 100)
                
                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # Tight layout
                self.trend_canvas.fig.tight_layout()
            
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
                    
                    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                          startangle=90, wedgeprops={'edgecolor': 'w'})
                    ax.axis('equal')
                    ax.set_title('Posture Quality Distribution')
            
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
                    
                    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                          startangle=90, wedgeprops={'edgecolor': 'w'})
                    ax.axis('equal')
                    ax.set_title('Stability Distribution')
            
            self.stability_canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating trends tab: {str(e)}")
    
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
                    ax.bar(x, trend_values, color=colors)
                    
                    # Add joint names to x-axis
                    ax.set_xticks(x)
                    ax.set_xticklabels([j.replace('_', ' ').title() for j in sorted_joints])
                    ax.tick_params(axis='x', rotation=45)
                    
                    # Add labels
                    ax.set_ylabel('Improvement')
                    ax.set_title('Joint Improvement Across Sessions')
                    
                    # Add horizontal line at y=0
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
                    
                    # Add grid
                    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
                    
                    # Adjust layout
                    self.joint_canvas.fig.tight_layout()
            
            self.joint_canvas.draw()
            
            # Update joint details
            self._update_joint_details()
            
        except Exception as e:
            logger.error(f"Error updating joints tab: {str(e)}")
    
    def _update_joint_details(self):
        """Update the joint detail labels."""
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
            # Update each joint group
            
            # Shoulders
            left_shoulder_data = self.joint_improvement.get('left_shoulder', {})
            right_shoulder_data = self.joint_improvement.get('right_shoulder', {})
            
            left_trend = left_shoulder_data.get('trend')
            right_trend = right_shoulder_data.get('trend')
            
            if left_trend is not None or right_trend is not None:
                shoulder_text = "Shoulders: "
                
                if left_trend is not None:
                    trend_sign = "+" if left_trend > 0 else ""
                    shoulder_text += f"Left {trend_sign}{left_trend:.1f} "
                
                if right_trend is not None:
                    trend_sign = "+" if right_trend > 0 else ""
                    shoulder_text += f"Right {trend_sign}{right_trend:.1f}"
                
                self.shoulder_label.setText(shoulder_text)
            else:
                self.shoulder_label.setText("Shoulders: No data")
            
            # Elbows
            left_elbow_data = self.joint_improvement.get('left_elbow', {})
            right_elbow_data = self.joint_improvement.get('right_elbow', {})
            
            left_trend = left_elbow_data.get('trend')
            right_trend = right_elbow_data.get('trend')
            
            if left_trend is not None or right_trend is not None:
                elbow_text = "Elbows: "
                
                if left_trend is not None:
                    trend_sign = "+" if left_trend > 0 else ""
                    elbow_text += f"Left {trend_sign}{left_trend:.1f} "
                
                if right_trend is not None:
                    trend_sign = "+" if right_trend > 0 else ""
                    elbow_text += f"Right {trend_sign}{right_trend:.1f}"
                
                self.elbow_label.setText(elbow_text)
            else:
                self.elbow_label.setText("Elbows: No data")
            
            # Wrists
            wrists_data = self.joint_improvement.get('wrists', {})
            wrists_trend = wrists_data.get('trend')
            
            if wrists_trend is not None:
                trend_sign = "+" if wrists_trend > 0 else ""
                self.wrist_label.setText(f"Wrists: {trend_sign}{wrists_trend:.1f}")
            else:
                self.wrist_label.setText("Wrists: No data")
            
            # Neck
            neck_data = self.joint_improvement.get('neck', {})
            neck_trend = neck_data.get('trend')
            
            if neck_trend is not None:
                trend_sign = "+" if neck_trend > 0 else ""
                self.neck_label.setText(f"Neck: {trend_sign}{neck_trend:.1f}")
            else:
                self.neck_label.setText("Neck: No data")
            
            # Hips
            hips_data = self.joint_improvement.get('hips', {})
            hips_trend = hips_data.get('trend')
            
            if hips_trend is not None:
                trend_sign = "+" if hips_trend > 0 else ""
                self.hip_label.setText(f"Hips: {trend_sign}{hips_trend:.1f}")
            else:
                self.hip_label.setText("Hips: No data")
            
            # Knees
            knees_data = self.joint_improvement.get('knees', {})
            knees_trend = knees_data.get('trend')
            
            if knees_trend is not None:
                trend_sign = "+" if knees_trend > 0 else ""
                self.knee_label.setText(f"Knees: {trend_sign}{knees_trend:.1f}")
            else:
                self.knee_label.setText("Knees: No data")
            
            # Generate recommendations
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
                
                # Add recommendations for top 3 issues
                for joint, trend in needs_improvement[:3]:
                    if 'shoulder' in joint:
                        recommendations.append(
                            f"Focus on {joint.replace('_', ' ')} positioning. Try shoulder strengthening exercises."
                        )
                    elif 'elbow' in joint:
                        recommendations.append(
                            f"Work on {joint.replace('_', ' ')} position. Practice holding the rifle with proper form."
                        )
                    elif joint == 'neck':
                        recommendations.append(
                            "Improve neck position by practicing proper cheek weld against the stock."
                        )
                    elif joint == 'hips':
                        recommendations.append(
                            "Work on hip alignment in your stance. Try balance exercises."
                        )
                    elif joint == 'knees':
                        recommendations.append(
                            "Adjust knee bend for better stability. Practice your stance without the rifle."
                        )
                    elif joint == 'wrists':
                        recommendations.append(
                            "Focus on wrist position for consistent rifle support."
                        )
            
            # If no specific issues, add general recommendation
            if not recommendations:
                recommendations.append(
                    "Your joint positions show good improvement or stability. "
                    "Continue practicing your current form."
                )
            
            # Update recommendations label
            self.joint_recommendations.setText("\n".join(f"• {r}" for r in recommendations))
            
        except Exception as e:
            logger.error(f"Error updating joint details: {str(e)}")
    
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
            
            # Format details text
            details = f"<b>Session:</b> {session['name']}<br>"
            details += f"<b>Date:</b> {format_timestamp(session['timestamp'])}<br>"
            
            if session.get('duration'):
                minutes, seconds = divmod(session['duration'], 60)
                details += f"<b>Duration:</b> {minutes}:{seconds:02d}<br>"
            
            if session.get('overall_score'):
                details += f"<b>Overall Score:</b> {session['overall_score']:.1f}<br>"
            
            if session.get('posture_quality'):
                details += f"<b>Posture Quality:</b> {session['posture_quality']}<br>"
            
            if session.get('stability'):
                details += f"<b>Stability:</b> {session['stability']}<br>"
            
            # Add summary if available
            if session.get('summary'):
                summary = session['summary']
                
                details += "<br><b>Summary:</b><br>"
                
                if summary.get('key_strengths'):
                    details += "<u>Key Strengths:</u><br>"
                    for strength in summary['key_strengths'][:3]:
                        details += f"• {strength}<br>"
                
                if summary.get('areas_to_improve'):
                    details += "<u>Areas to Improve:</u><br>"
                    for area in summary['areas_to_improve'][:3]:
                        details += f"• {area}<br>"
            
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