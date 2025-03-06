#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generator Module

This module generates PDF reports for shooting sessions.
It creates visualizations and performance summaries.

Author: Claude
Date: March 6, 2025
"""

import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
import logging
import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
from matplotlib.figure import Figure
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import PageBreak, ListFlowable, ListItem
from reportlab.lib.units import inch
import io
import base64
import tempfile

# Initialize logger
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates PDF reports for shooting sessions.
    Creates visualizations and performance summaries.
    """
    
    def __init__(self, data_manager):

        self.data_manager = data_manager
        self.styles = getSampleStyleSheet()
    
    # Modify existing styles instead of adding new ones
    # Heading1 modification
        self.styles['Heading1'].fontSize = 16
        self.styles['Heading1'].spaceAfter = 12
    
    # Heading2 modification
        self.styles['Heading2'].fontSize = 14
        self.styles['Heading2'].spaceAfter = 10
    
    # Normal modification
        self.styles['Normal'].fontSize = 12
        self.styles['Normal'].spaceAfter = 6
    
        logger.info("ReportGenerator initialized")
    
    def create_session_report(self, session_id: int, output_path: str) -> str:
        """
        Create a PDF report for a shooting session.
        
        Args:
            session_id: Session ID
            output_path: Directory to save the report
            
        Returns:
            Path to the generated PDF file
        """
        try:
            # Get session data
            session = self.data_manager.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return None
            
            # Get user data
            user = self.data_manager.get_user(session['user_id'])
            if not user:
                logger.error(f"User {session['user_id']} not found")
                return None
            
            # Get detailed session data
            session_data = self.data_manager.get_session_data(session_id)
            
            # Generate report filename
            timestamp = datetime.datetime.fromisoformat(session['timestamp'])
            filename = f"shooting_report_{user['name'].replace(' ', '_')}_{timestamp.strftime('%Y%m%d_%H%M')}.pdf"
            filepath = os.path.join(output_path, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=72)
            
            # Build content
            elements = []
            
            # Add title
            elements.append(Paragraph(
                f"Shooting Posture Analysis Report", 
                self.styles['Title']
            ))
            elements.append(Spacer(1, 0.25*inch))
            
            # Add session info
            elements.append(Paragraph(
                f"Session: {session['name']}", 
                self.styles['Heading1']
            ))
            elements.append(Paragraph(
                f"Shooter: {user['name']}", 
                self.styles['Normal']
            ))
            elements.append(Paragraph(
                f"Date: {timestamp.strftime('%B %d, %Y at %I:%M %p')}", 
                self.styles['Normal']
            ))
            elements.append(Paragraph(
                f"Duration: {self._format_duration(session['duration'])}", 
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.25*inch))
            
            # Add performance summary
            elements.append(Paragraph(
                "Performance Summary", 
                self.styles['Heading1']
            ))
            
            # Create performance summary table
            data = [
                ["Overall Score", f"{session['overall_score']:.1f}/100"],
                ["Posture Quality", session['posture_quality']],
                ["Stability", session['stability']]
            ]
            
            table = Table(data, colWidths=[2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.25*inch))
            
            # Add performance graph
            if session_data:
                graph_path = self._create_performance_graph(session_data)
                
                if graph_path:
                    elements.append(Paragraph(
                        "Performance Graph", 
                        self.styles['Heading2']
                    ))
                    
                    img = Image(graph_path, width=6*inch, height=3*inch)
                    elements.append(img)
                    elements.append(Spacer(1, 0.25*inch))
            
            # Add joint analysis if we have session summary
            if session.get('summary'):
                elements.append(Paragraph(
                    "Posture Analysis", 
                    self.styles['Heading1']
                ))
                
                summary = session['summary']
                
                # Add key strengths
                if summary.get('key_strengths'):
                    elements.append(Paragraph(
                        "Key Strengths", 
                        self.styles['Heading2']
                    ))
                    
                    strength_items = [
                        ListItem(Paragraph(strength, self.styles['Normal']))
                        for strength in summary['key_strengths']
                    ]
                    
                    elements.append(ListFlowable(
                        strength_items,
                        bulletType='bullet',
                        leftIndent=20
                    ))
                    elements.append(Spacer(1, 0.15*inch))
                
                # Add areas to improve
                if summary.get('areas_to_improve'):
                    elements.append(Paragraph(
                        "Areas to Improve", 
                        self.styles['Heading2']
                    ))
                    
                    improvement_items = [
                        ListItem(Paragraph(area, self.styles['Normal']))
                        for area in summary['areas_to_improve']
                    ]
                    
                    elements.append(ListFlowable(
                        improvement_items,
                        bulletType='bullet',
                        leftIndent=20
                    ))
                    elements.append(Spacer(1, 0.15*inch))
                
                # Add recommendations
                if summary.get('recommendations'):
                    elements.append(Paragraph(
                        "Recommendations", 
                        self.styles['Heading2']
                    ))
                    
                    recommendation_items = [
                        ListItem(Paragraph(rec, self.styles['Normal']))
                        for rec in summary['recommendations']
                    ]
                    
                    elements.append(ListFlowable(
                        recommendation_items,
                        bulletType='bullet',
                        leftIndent=20
                    ))
                    elements.append(Spacer(1, 0.25*inch))
            
            # Add joint angles analysis
            if session_data:
                elements.append(PageBreak())
                elements.append(Paragraph(
                    "Joint Angles Analysis", 
                    self.styles['Heading1']
                ))
                
                joint_graph_path = self._create_joint_angles_graph(session_data)
                
                if joint_graph_path:
                    img = Image(joint_graph_path, width=6*inch, height=4*inch)
                    elements.append(img)
                    elements.append(Spacer(1, 0.25*inch))
                
                elements.append(Paragraph(
                    "The graph above shows the average joint angles throughout your session compared to ideal angles. "
                    "Angles within the green zone are considered optimal for shooting posture.",
                    self.styles['Normal']
                ))
                elements.append(Spacer(1, 0.25*inch))
            
            # Add footer
            elements.append(Paragraph(
                "This report was generated by Shooting Posture Analyzer.", 
                self.styles['Italic']
            ))
            
            # Build PDF
            doc.build(elements)
            
            # Clean up temporary files
            if 'graph_path' in locals() and graph_path:
                os.remove(graph_path)
            
            if 'joint_graph_path' in locals() and joint_graph_path:
                os.remove(joint_graph_path)
            
            logger.info(f"Created session report at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating session report: {str(e)}")
            raise
    
    def _format_duration(self, duration: int) -> str:
        """
        Format duration in seconds to a readable string.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if duration is None:
            return "N/A"
        
        minutes, seconds = divmod(duration, 60)
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}, {seconds} second{'s' if seconds != 1 else ''}"
        else:
            hours, minutes = divmod(minutes, 60)
            return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
    
    def _create_performance_graph(self, session_data: List[Dict]) -> str:
        """
        Create a performance graph for the session.
        
        Args:
            session_data: List of session data frames
            
        Returns:
            Path to the generated graph image
        """
        try:
            # Extract frame numbers and scores
            frame_numbers = [frame['frame_number'] for frame in session_data]
            scores = [frame['posture_score'] for frame in session_data]
            
            # Create figure
            plt.figure(figsize=(10, 5))
            plt.plot(frame_numbers, scores, '-', color='#3498db', linewidth=2)
            
            # Add horizontal lines for score categories
            plt.axhspan(0, 50, alpha=0.2, color='red')
            plt.axhspan(50, 70, alpha=0.2, color='orange')
            plt.axhspan(70, 85, alpha=0.2, color='yellow')
            plt.axhspan(85, 100, alpha=0.2, color='green')
            
            # Add labels
            plt.xlabel('Frame Number')
            plt.ylabel('Posture Score')
            plt.title('Posture Score Throughout Session')
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Set y-axis limits
            plt.ylim(0, 100)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
            plt.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error creating performance graph: {str(e)}")
            return None
    
    def _create_joint_angles_graph(self, session_data: List[Dict]) -> str:
        """
        Create a graph showing joint angles comparison to ideal angles.
        
        Args:
            session_data: List of session data frames
            
        Returns:
            Path to the generated graph image
        """
        try:
            # Extract joint angles from all frames
            joint_data = {}
            for frame in session_data:
                angles = frame['joint_angles']
                for joint, angle in angles.items():
                    if joint not in joint_data:
                        joint_data[joint] = []
                    joint_data[joint].append(angle)
            
            # Calculate average angles
            avg_angles = {joint: np.mean(angles) for joint, angles in joint_data.items() if angles}
            
            if not avg_angles:
                return None
            
            # Define ideal angles
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
            
            # Define angle ranges (min, max) for each joint
            angle_ranges = {
                'knees': (170.0, 175.0),
                'hips': (175.0, 185.0),
                'left_shoulder': (30.0, 60.0),
                'right_shoulder': (0.0, 30.0),
                'left_elbow': (60.0, 90.0),
                'right_elbow': (80.0, 100.0),
                'wrists': (170.0, 190.0),
                'neck': (10.0, 15.0),
            }
            
            # Filter to only include joints with data and ideal angles
            joints = [j for j in avg_angles.keys() if j in ideal_angles]
            
            if not joints:
                return None
            
            # Prepare data for plotting
            x = np.arange(len(joints))
            measured = [avg_angles[j] for j in joints]
            ideal = [ideal_angles[j] for j in joints]
            
            # Create figure
            plt.figure(figsize=(10, 6))
            
            width = 0.35
            plt.bar(x - width/2, measured, width, label='Your Average', color='#3498db')
            plt.bar(x + width/2, ideal, width, label='Ideal', color='#2ecc71')
            
            # Add joint names to x-axis
            plt.xticks(x, [j.replace('_', ' ').title() for j in joints])
            plt.ylabel('Angle (degrees)')
            plt.title('Joint Angles Comparison')
            plt.legend()
            
            # Add optimal ranges as green bands
            for i, joint in enumerate(joints):
                if joint in angle_ranges:
                    min_val, max_val = angle_ranges[joint]
                    plt.axhspan(min_val, max_val, xmin=(i/len(joints)), xmax=((i+1)/len(joints)), 
                               alpha=0.2, color='green')
            
            # Add grid
            plt.grid(True, axis='y', linestyle='--', alpha=0.7)
            
            # Rotate x labels for better readability
            plt.xticks(rotation=45, ha='right')
            
            # Tight layout
            plt.tight_layout()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
            plt.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error creating joint angles graph: {str(e)}")
            return None
    
    def create_progress_report(self, user_id: int, output_path: str) -> str:
        """
        Create a progress report for a user across multiple sessions.
        
        Args:
            user_id: User ID
            output_path: Directory to save the report
            
        Returns:
            Path to the generated PDF file
        """
        try:
            # Get user data
            user = self.data_manager.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # Get sessions for this user (limit to 10 most recent)
            sessions = self.data_manager.get_user_performance_history(user_id, 10)
            
            if not sessions:
                logger.error(f"No sessions found for user {user_id}")
                return None
            
            # Get performance trend
            trend_data = self.data_manager.get_performance_trend(user_id)
            
            # Generate report filename
            timestamp = datetime.datetime.now()
            filename = f"progress_report_{user['name'].replace(' ', '_')}_{timestamp.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(output_path, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=72)
            
            # Build content
            elements = []
            
            # Add title
            elements.append(Paragraph(
                f"Shooting Progress Report", 
                self.styles['Title']
            ))
            elements.append(Spacer(1, 0.25*inch))
            
            # Add user info
            elements.append(Paragraph(
                f"Shooter: {user['name']}", 
                self.styles['Heading1']
            ))
            elements.append(Paragraph(
                f"Report generated on: {timestamp.strftime('%B %d, %Y')}", 
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.25*inch))
            
            # Add performance trend graph
            trend_graph_path = self._create_trend_graph(trend_data)
            
            if trend_graph_path:
                elements.append(Paragraph(
                    "Performance Trend", 
                    self.styles['Heading1']
                ))
                
                img = Image(trend_graph_path, width=6*inch, height=3*inch)
                elements.append(img)
                elements.append(Spacer(1, 0.25*inch))
                
                # Add trend analysis
                if len(trend_data) >= 2:
                    start_score = trend_data[0]['avg_score']
                    end_score = trend_data[-1]['avg_score']
                    
                    if end_score > start_score:
                        elements.append(Paragraph(
                            f"Your performance has improved by {(end_score - start_score):.1f} points over this period.",
                            self.styles['Normal']
                        ))
                    elif end_score < start_score:
                        elements.append(Paragraph(
                            f"Your performance has decreased by {(start_score - end_score):.1f} points over this period.",
                            self.styles['Normal']
                        ))
                    else:
                        elements.append(Paragraph(
                            "Your performance has remained stable over this period.",
                            self.styles['Normal']
                        ))
                    
                elements.append(Spacer(1, 0.25*inch))
            
            # Add recent sessions summary
            elements.append(Paragraph(
                "Recent Sessions", 
                self.styles['Heading1']
            ))
            
            # Create sessions table
            data = [
                ["Date", "Session", "Score", "Quality"]
            ]
            
            for session in sessions:
                timestamp = datetime.datetime.fromisoformat(session['timestamp'])
                data.append([
                    timestamp.strftime('%m/%d/%Y'),
                    session['name'],
                    f"{session['overall_score']:.1f}",
                    session['posture_quality']
                ])
            
            table = Table(data, colWidths=[1*inch, 2.5*inch, 1*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (2, 1), (2, -1), 'CENTER')
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.25*inch))
            
            # Get joint improvement data
            joint_improvement = self.data_manager.get_joint_improvement(user_id)
            
            if joint_improvement:
                # Create joint improvement graph
                joint_improvement_graph = self._create_joint_improvement_graph(joint_improvement)
                
                if joint_improvement_graph:
                    elements.append(PageBreak())
                    elements.append(Paragraph(
                        "Joint Posture Improvement", 
                        self.styles['Heading1']
                    ))
                    
                    img = Image(joint_improvement_graph, width=6*inch, height=4*inch)
                    elements.append(img)
                    elements.append(Spacer(1, 0.25*inch))
                    
                    # Add analysis of most improved and needs work joints
                    improved_joints = []
                    needs_work_joints = []
                    
                    for joint, data in joint_improvement.items():
                        if data.get('trend') is not None:
                            if data['trend'] > 0:
                                improved_joints.append((joint, data['trend']))
                            elif data['trend'] < 0:
                                needs_work_joints.append((joint, data['trend']))
                    
                    if improved_joints:
                        improved_joints.sort(key=lambda x: x[1], reverse=True)
                        elements.append(Paragraph(
                            "Most Improved Joints", 
                            self.styles['Heading2']
                        ))
                        
                        for joint, trend in improved_joints[:3]:  # Top 3 most improved
                            elements.append(Paragraph(
                                f"• {joint.replace('_', ' ').title()}: +{trend:.1f} points improvement",
                                self.styles['Normal']
                            ))
                        
                        elements.append(Spacer(1, 0.15*inch))
                    
                    if needs_work_joints:
                        needs_work_joints.sort(key=lambda x: x[1])
                        elements.append(Paragraph(
                            "Joints that Need Work", 
                            self.styles['Heading2']
                        ))
                        
                        for joint, trend in needs_work_joints[:3]:  # Top 3 needs work
                            elements.append(Paragraph(
                                f"• {joint.replace('_', ' ').title()}: {trend:.1f} points decline",
                                self.styles['Normal']
                            ))
                        
                        elements.append(Spacer(1, 0.15*inch))
            
            # Add recommendations
            elements.append(Paragraph(
                "Recommendations", 
                self.styles['Heading1']
            ))
            
            # Generate recommendations based on data
            recommendations = []
            
            # Look at overall trend
            if trend_data and len(trend_data) >= 2:
                start_score = trend_data[0]['avg_score']
                end_score = trend_data[-1]['avg_score']
                
                if end_score > start_score:
                    if (end_score - start_score) > 10:
                        recommendations.append(
                            "Continue your current training approach - it's working well."
                        )
                    else:
                        recommendations.append(
                            "You're making progress, but consider intensifying your training frequency."
                        )
                else:
                    recommendations.append(
                        "Consider working with a coach to identify and address your specific challenges."
                    )
            
            # Look at joint-specific issues
            joints_to_work_on = []
            
            if joint_improvement:
                for joint, data in joint_improvement.items():
                    if data.get('trend') is not None and data['trend'] < 0:
                        joints_to_work_on.append(joint)
            
            if 'left_shoulder' in joints_to_work_on or 'right_shoulder' in joints_to_work_on:
                recommendations.append(
                    "Focus on shoulder position exercises to improve stability and strength."
                )
            
            if 'left_elbow' in joints_to_work_on or 'right_elbow' in joints_to_work_on:
                recommendations.append(
                    "Practice proper elbow positioning using a mirror or training partner."
                )
            
            if 'knees' in joints_to_work_on or 'hips' in joints_to_work_on:
                recommendations.append(
                    "Work on lower body stability with balance exercises and stance practice."
                )
            
            if 'neck' in joints_to_work_on:
                recommendations.append(
                    "Practice proper head position and cheek weld for consistent sight alignment."
                )
            
            # Add default recommendation if none generated
            if not recommendations:
                recommendations.append(
                    "Continue practicing regularly and focus on maintaining consistency in your form."
                )
            
            # Add recommendations to report
            recommendation_items = [
                ListItem(Paragraph(rec, self.styles['Normal']))
                for rec in recommendations
            ]
            
            elements.append(ListFlowable(
                recommendation_items,
                bulletType='bullet',
                leftIndent=20
            ))
            
            # Add footer
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph(
                "This report was generated by Shooting Posture Analyzer.", 
                self.styles['Italic']
            ))
            
            # Build PDF
            doc.build(elements)
            
            # Clean up temporary files
            if 'trend_graph_path' in locals() and trend_graph_path:
                os.remove(trend_graph_path)
            
            if 'joint_improvement_graph' in locals() and joint_improvement_graph:
                os.remove(joint_improvement_graph)
            
            logger.info(f"Created progress report at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating progress report: {str(e)}")
            raise
    
    def _create_trend_graph(self, trend_data: List[Dict]) -> str:
        """
        Create a performance trend graph.
        
        Args:
            trend_data: List of dictionaries with date and average score
            
        Returns:
            Path to the generated graph image
        """
        try:
            if not trend_data:
                return None
            
            # Extract dates and scores
            dates = [item['date'] for item in trend_data]
            scores = [item['avg_score'] for item in trend_data]
            
            # Convert dates to datetime objects for better plotting
            date_objects = [datetime.datetime.strptime(d, '%Y-%m-%d') for d in dates]
            
            # Create figure
            plt.figure(figsize=(10, 5))
            plt.plot(date_objects, scores, '-o', color='#3498db', linewidth=2, markersize=6)
            
            # Add labels
            plt.xlabel('Date')
            plt.ylabel('Average Score')
            plt.title('Performance Trend Over Time')
            
            # Format x-axis dates
            plt.gcf().autofmt_xdate()
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Set y-axis limits
            plt.ylim(0, 100)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
            plt.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error creating trend graph: {str(e)}")
            return None
    
    def _create_joint_improvement_graph(self, joint_improvement: Dict) -> str:
        """
        Create a graph showing improvement in joint postures.
        
        Args:
            joint_improvement: Dictionary with joint improvement data
            
        Returns:
            Path to the generated graph image
        """
        try:
            # Extract joint trends
            trends = {}
            for joint, data in joint_improvement.items():
                if data.get('trend') is not None:
                    trends[joint] = data['trend']
            
            if not trends:
                return None
            
            # Sort joints by name
            sorted_joints = sorted(trends.keys())
            
            # Prepare data for plotting
            x = np.arange(len(sorted_joints))
            trend_values = [trends[j] for j in sorted_joints]
            
            # Determine colors based on trend (positive = green, negative = red)
            colors = ['#2ecc71' if v > 0 else '#e74c3c' for v in trend_values]
            
            # Create figure
            plt.figure(figsize=(10, 6))
            
            plt.bar(x, trend_values, color=colors)
            
            # Add joint names to x-axis
            plt.xticks(x, [j.replace('_', ' ').title() for j in sorted_joints])
            plt.ylabel('Improvement (points)')
            plt.title('Joint Posture Improvement Across Sessions')
            
            # Add horizontal line at y=0
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            
            # Add grid
            plt.grid(True, axis='y', linestyle='--', alpha=0.7)
            
            # Rotate x labels for better readability
            plt.xticks(rotation=45, ha='right')
            
            # Tight layout
            plt.tight_layout()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=100, bbox_inches='tight')
            plt.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error creating joint improvement graph: {str(e)}")
            return None