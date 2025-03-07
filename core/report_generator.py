#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Report Generator Module

This module generates concise one-page PDF reports for shooting sessions
with focus on the 3 key metrics for improvement.

Author: Claude
Date: March 7, 2025
"""

import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
import logging
import datetime
import tempfile
import time  # For timestamp generation
from typing import Dict, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.units import inch

# Initialize logger
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates concise one-page PDF reports for shooting sessions.
    Focuses on key metrics for improvement.
    """
    
    def __init__(self, data_manager):
        """Initialize the report generator with data manager."""
        self.data_manager = data_manager
        self.styles = getSampleStyleSheet()
        
        # Modify existing styles
        self.styles['Heading1'].fontSize = 16
        self.styles['Heading1'].spaceAfter = 8
        
        self.styles['Heading2'].fontSize = 14
        self.styles['Heading2'].spaceAfter = 6
        
        self.styles['Normal'].fontSize = 10
        self.styles['Normal'].spaceAfter = 4
        
        # Add custom style for joint angles table
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,  # Center alignment
        ))
        
        logger.info("Simplified ReportGenerator initialized")
    
    def create_session_report(self, session_id: int, output_path: str) -> str:
        """
        Create a concise one-page PDF report for a shooting session.
        
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
                                   rightMargin=36, leftMargin=36,
                                   topMargin=36, bottomMargin=36)
            
            # Build content
            elements = []
            
            # Add title
            elements.append(Paragraph(
                f"Shooting Posture Analysis: Key Improvement Areas", 
                self.styles['Title']
            ))
            elements.append(Spacer(1, 0.15*inch))
            
            # Add session info
            elements.append(Paragraph(
                f"Session: {session['name']}", 
                self.styles['Heading1']
            ))
            elements.append(Paragraph(
                f"Shooter: {user['name']} | Date: {timestamp.strftime('%B %d, %Y at %I:%M %p')}",
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 1: Overall Performance Score
            elements.append(Paragraph(
                "1. Overall Performance", 
                self.styles['Heading2']
            ))
            
            # Create performance summary table
            overall_score = session.get('overall_score', 0)
            posture_quality = session.get('posture_quality', 'N/A')
            stability = session.get('stability', 'N/A')
            
            # Get color for score
            score_color = self._get_score_color(overall_score)
            
            data = [
                ["Overall Score", f"{overall_score:.1f}/100"],
                ["Posture Quality", posture_quality],
                ["Stability", stability]
            ]
            
            table = Table(data, colWidths=[2*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BACKGROUND', (1, 0), (1, 0), score_color),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (1, 1), (1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 2: Joint Angles Analysis
            elements.append(Paragraph(
                "2. Joint Angles Analysis", 
                self.styles['Heading2']
            ))
            
            # Create joint angles table
            joint_data = self._extract_joint_angles(session_data)
            if joint_data:
                joint_table = self._create_joint_angles_table(joint_data)
                elements.append(joint_table)
                elements.append(Spacer(1, 0.1*inch))
            else:
                elements.append(Paragraph(
                    "No joint angle data available for this session.",
                    self.styles['Normal']
                ))
                elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 3: Specific Recommendations
            elements.append(Paragraph(
                "3. Key Recommendations", 
                self.styles['Heading2']
            ))
            
            # Get recommendations from session summary or generate them based on joint data
            recommendations = self._get_recommendations(session, joint_data)
            
            recommendation_items = [
                ListItem(Paragraph(rec, self.styles['Normal']))
                for rec in recommendations
            ]
            
            elements.append(ListFlowable(
                recommendation_items,
                bulletType='bullet',
                leftIndent=20
            ))
            
            # Add joint angles graph if space allows
            if joint_data:
                elements.append(Spacer(1, 0.1*inch))
                joint_graph_path = self._create_joint_angles_graph(joint_data)
                
                if joint_graph_path:
                    img = Image(joint_graph_path, width=6*inch, height=2*inch)
                    elements.append(img)
                    
            # Add footer
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                "Focus on these 3 key areas to significantly improve your shooting posture.", 
                self.styles['Italic']
            ))
            
            # Build PDF
            doc.build(elements)
            
            # We're no longer cleaning up temporary files here as they're stored in the reports directory
            
            logger.info(f"Created concise session report at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating session report: {str(e)}")
            raise
    
    def _extract_joint_angles(self, session_data: List[Dict]) -> Dict:
        """
        Extract joint angles from session data.
        
        Args:
            session_data: List of session data frames
            
        Returns:
            Dictionary with joint angle statistics
        """
        if not session_data:
            return {}
        
        # Get ideal angles
        ideal_angles = {
            'knees': 172.5,  # Slightly bent (170°-175°)
            'hips': 180.0,   # Straight (175°-185°)
            'left_shoulder': 45.0,  # Raised to support rifle (30°-60°)
            'right_shoulder': 15.0,  # Closer to body (0°-30°)
            'left_elbow': 75.0,  # Bent to support rifle (60°-90°)
            'right_elbow': 90.0,  # Bent for grip (80°-100°)
            'wrists': 180.0,  # Straight (170°-190°)
            'neck': 12.5,    # Tilted forward (10°-15°)
        }
        
        # Extract joint angles from all frames
        joint_data = {}
        for frame in session_data:
            angles = frame.get('joint_angles', {})
            for joint, angle in angles.items():
                if joint not in joint_data:
                    joint_data[joint] = []
                joint_data[joint].append(angle)
        
        # Calculate statistics for each joint
        result = {}
        for joint, angles in joint_data.items():
            if angles:
                avg_angle = sum(angles) / len(angles)
                ideal = ideal_angles.get(joint, 0)
                diff = abs(avg_angle - ideal)
                
                result[joint] = {
                    'average': avg_angle,
                    'ideal': ideal,
                    'difference': diff,
                    'count': len(angles)
                }
        
        return result
    
    def _create_joint_angles_table(self, joint_data: Dict) -> Table:
        """
        Create a table showing joint angles comparison.
        
        Args:
            joint_data: Dictionary with joint angle statistics
            
        Returns:
            Table object for PDF
        """
        # Define table headers
        headers = ["Joint", "Your Avg. Angle", "Ideal Angle", "Difference", "Assessment"]
        
        # Sort joints by difference (largest first) to highlight areas for improvement
        sorted_joints = sorted(joint_data.items(), key=lambda x: x[1]['difference'], reverse=True)
        
        # Prepare table data
        data = [headers]
        
        for joint, stats in sorted_joints:
            # Get assessment based on difference
            if stats['difference'] <= 5:
                assessment = "Excellent"
                color = colors.green
            elif stats['difference'] <= 15:
                assessment = "Good"
                color = colors.blue
            elif stats['difference'] <= 25:
                assessment = "Fair"
                color = colors.orange
            else:
                assessment = "Needs Work"
                color = colors.red
            
            # Format joint name
            joint_name = joint.replace('_', ' ').title()
            
            # Add row
            data.append([
                joint_name,
                f"{stats['average']:.1f}°",
                f"{stats['ideal']:.1f}°",
                f"{stats['difference']:.1f}°",
                assessment
            ])
        
        # Create table
        table = Table(data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1*inch, 1.2*inch])
        
        # Define style
        style = TableStyle([
            # Headers
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # General cells
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ])
        
        # Add colors to assessment column based on values
        for i, (joint, stats) in enumerate(sorted_joints, 1):
            if stats['difference'] <= 5:
                style.add('TEXTCOLOR', (4, i), (4, i), colors.green)
            elif stats['difference'] <= 15:
                style.add('TEXTCOLOR', (4, i), (4, i), colors.blue)
            elif stats['difference'] <= 25:
                style.add('TEXTCOLOR', (4, i), (4, i), colors.orange)
            else:
                style.add('TEXTCOLOR', (4, i), (4, i), colors.red)
            
            # Highlight the difference column
            style.add('FONTNAME', (3, i), (3, i), 'Helvetica-Bold')
        
        table.setStyle(style)
        
        return table
    
    def _get_recommendations(self, session: Dict, joint_data: Dict) -> List[str]:
        """
        Get key recommendations for improvement.
        
        Args:
            session: Session data dictionary
            joint_data: Joint angle statistics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # If session has summary with recommendations, use those
        if session.get('summary') and session['summary'].get('recommendations'):
            # Take up to 3 recommendations from the summary
            return session['summary']['recommendations'][:3]
        
        # Otherwise, generate recommendations based on joint data
        if joint_data:
            # Sort joints by difference (largest first)
            problem_joints = sorted(joint_data.items(), key=lambda x: x[1]['difference'], reverse=True)
            
            # Generate specific recommendations for the top 3 problem areas
            for joint, stats in problem_joints[:3]:
                if stats['difference'] > 10:  # Only suggest improvements for significant deviations
                    if joint == 'left_shoulder':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Raise your left shoulder more to better support the rifle. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Lower your left shoulder slightly for better control. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'right_shoulder':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Raise your right shoulder slightly. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Lower your right shoulder to be closer to your body. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'left_elbow':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Bend your left elbow more to provide stable support for the rifle. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Extend your left elbow slightly for better rifle support. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'right_elbow':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Bend your right elbow more for proper grip. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Straighten your right elbow slightly for better control. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'knees':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Straighten your knees slightly. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Bend your knees slightly for better stability. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'hips':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Stand more upright to improve your hip alignment. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Lower your hips slightly for better alignment. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'neck':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Tilt your head forward slightly to better align with sights. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Raise your head slightly to improve sight alignment. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                    
                    elif joint == 'wrists':
                        if stats['average'] < stats['ideal']:
                            recommendations.append(f"Straighten your wrists more for consistent support. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
                        else:
                            recommendations.append(f"Relax your wrists slightly for better control. Current angle is {stats['average']:.1f}° but should be closer to {stats['ideal']:.1f}°.")
        
        # If no specific recommendations could be generated, provide general ones
        if not recommendations:
            recommendations = [
                "Focus on maintaining proper shoulder alignment to support the rifle efficiently.",
                "Practice proper elbow positioning to create a stable shooting platform.",
                "Work on achieving a consistent stance with proper knee bend for stability."
            ]
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _create_joint_angles_graph(self, joint_data: Dict) -> str:
        """
        Create a graph showing joint angles comparison to ideal angles.
        
        Args:
            joint_data: Dictionary with joint angle statistics
            
        Returns:
            Path to the generated graph image
        """
        try:
            # Sort joints by difference (largest first)
            sorted_joints = sorted(joint_data.items(), key=lambda x: x[1]['difference'], reverse=True)
            
            # Take top 6 joints for clarity
            top_joints = sorted_joints[:6]
            
            # Create figure
            plt.figure(figsize=(8, 4))
            
            # Extract data for plotting
            joint_names = [j[0].replace('_', ' ').title() for j in top_joints]
            your_angles = [j[1]['average'] for j in top_joints]
            ideal_angles = [j[1]['ideal'] for j in top_joints]
            
            # Set positions on x-axis
            x = np.arange(len(joint_names))
            width = 0.35
            
            # Plot bars
            plt.bar(x - width/2, your_angles, width, label='Your Average', color='#3498db')
            plt.bar(x + width/2, ideal_angles, width, label='Ideal', color='#2ecc71')
            
            # Add labels and title
            plt.xlabel('Joint')
            plt.ylabel('Angle (degrees)')
            plt.title('Joint Angles Comparison: Your Average vs. Ideal')
            plt.xticks(x, joint_names, rotation=45, ha='right')
            plt.legend()
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7, axis='y')
            
            # Tight layout for better fit
            plt.tight_layout()
            
            # Create a path for the graph in a fixed location
            reports_dir = os.path.join(os.path.expanduser("~"), ".shooting_analyzer", "reports")
            os.makedirs(reports_dir, exist_ok=True)
            graph_path = os.path.join(reports_dir, f"joint_angles_graph_{int(datetime.datetime.now().timestamp())}.png")
            
            # Save the graph
            plt.savefig(graph_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            # Verify file exists
            if os.path.exists(graph_path):
                logger.info(f"Created joint angles graph at {graph_path}")
                return graph_path
            else:
                logger.error(f"Failed to create joint angles graph at {graph_path}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating joint angles graph: {str(e)}")
            return None
    
    def _get_score_color(self, score: float):
        """Get color for score display based on value."""
        if score >= 85:
            return colors.green
        elif score >= 70:
            return colors.blue
        elif score >= 50:
            return colors.orange
        else:
            return colors.red
            
    def create_progress_report(self, user_id: int, output_path: str) -> str:
        """
        Create a concise one-page PDF progress report showing improvement over time.
        
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
            
            # Get performance history
            performance_history = self.data_manager.get_user_performance_history(user_id, limit=10)
            
            # Get trend data
            trend_data = self.data_manager.get_performance_trend(user_id, days=30)
            
            # Get joint improvement data
            joint_improvement = self.data_manager.get_joint_improvement(user_id)
            
            # Generate report filename
            timestamp = datetime.datetime.now()
            filename = f"progress_report_{user['name'].replace(' ', '_')}_{timestamp.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(output_path, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                   rightMargin=36, leftMargin=36,
                                   topMargin=36, bottomMargin=36)
            
            # Build content
            elements = []
            
            # Add title
            elements.append(Paragraph(
                f"Shooting Progress Report: Key Improvement Areas", 
                self.styles['Title']
            ))
            elements.append(Spacer(1, 0.15*inch))
            
            # Add user info
            elements.append(Paragraph(
                f"Shooter: {user['name']}", 
                self.styles['Heading1']
            ))
            elements.append(Paragraph(
                f"Report generated on: {timestamp.strftime('%B %d, %Y')}",
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 1: Performance Trend
            elements.append(Paragraph(
                "1. Performance Trend", 
                self.styles['Heading2']
            ))
            
            if trend_data and len(trend_data) >= 2:
                # Create performance trend graph
                trend_graph_path = self._create_trend_graph(trend_data)
                if trend_graph_path:
                    img = Image(trend_graph_path, width=6*inch, height=2*inch)
                    elements.append(img)
                    
                    # Calculate trend analysis
                    first_score = trend_data[0]['avg_score']
                    last_score = trend_data[-1]['avg_score']
                    trend = last_score - first_score
                    
                    if trend > 0:
                        trend_text = f"Your performance has improved by {trend:.1f} points over this period."
                    elif trend < 0:
                        trend_text = f"Your performance has decreased by {abs(trend):.1f} points over this period."
                    else:
                        trend_text = "Your performance has remained stable over this period."
                    
                    elements.append(Paragraph(trend_text, self.styles['Normal']))
                    # We'll keep the trend graph file for now
            else:
                elements.append(Paragraph(
                    "Insufficient data to show performance trend. Complete more sessions to track progress.",
                    self.styles['Normal']
                ))
            
            elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 2: Joint Improvement
            elements.append(Paragraph(
                "2. Joint Improvement Analysis", 
                self.styles['Heading2']
            ))
            
            if joint_improvement:
                # Find most improved and declining joints
                improved_joints = []
                needs_work_joints = []
                
                for joint, data in joint_improvement.items():
                    if data.get('trend') is not None:
                        if data['trend'] > 0:
                            improved_joints.append((joint, data['trend']))
                        elif data['trend'] < 0:
                            needs_work_joints.append((joint, data['trend']))
                
                # Create joint improvement table
                if improved_joints or needs_work_joints:
                    # Table headers
                    data = [["Joint", "Change", "Status"]]
                    
                    # Add improved joints
                    if improved_joints:
                        improved_joints.sort(key=lambda x: x[1], reverse=True)
                        for joint, trend in improved_joints[:3]:  # Top 3 most improved
                            joint_name = joint.replace('_', ' ').title()
                            data.append([
                                joint_name, 
                                f"+{trend:.1f}", 
                                "Improving"
                            ])
                    
                    # Add joints needing work
                    if needs_work_joints:
                        needs_work_joints.sort(key=lambda x: x[1])
                        for joint, trend in needs_work_joints[:3]:  # Top 3 needs work
                            joint_name = joint.replace('_', ' ').title()
                            data.append([
                                joint_name, 
                                f"{trend:.1f}", 
                                "Needs Work"
                            ])
                    
                    # Create table
                    joint_table = Table(data, colWidths=[2*inch, 1.5*inch, 2*inch])
                    
                    # Add style
                    style = TableStyle([
                        # Headers
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        
                        # General cells
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                    ])
                    
                    # Color the status column
                    row = 1
                    for joint, trend in (improved_joints[:3] if improved_joints else []):
                        style.add('TEXTCOLOR', (1, row), (1, row), colors.green)
                        style.add('TEXTCOLOR', (2, row), (2, row), colors.green)
                        row += 1
                    
                    for joint, trend in (needs_work_joints[:3] if needs_work_joints else []):
                        style.add('TEXTCOLOR', (1, row), (1, row), colors.red)
                        style.add('TEXTCOLOR', (2, row), (2, row), colors.red)
                        row += 1
                    
                    joint_table.setStyle(style)
                    elements.append(joint_table)
                else:
                    elements.append(Paragraph(
                        "No significant joint improvement data available yet. Complete more sessions to track progress.",
                        self.styles['Normal']
                    ))
            else:
                elements.append(Paragraph(
                    "No joint improvement data available. Complete more sessions to track progress.",
                    self.styles['Normal']
                ))
            
            elements.append(Spacer(1, 0.1*inch))
            
            # KEY METRIC 3: Targeted Recommendations
            elements.append(Paragraph(
                "3. Targeted Recommendations", 
                self.styles['Heading2']
            ))
            
            # Generate recommendations based on performance and joint data
            recommendations = self._get_progress_recommendations(performance_history, joint_improvement)
            
            recommendation_items = [
                ListItem(Paragraph(rec, self.styles['Normal']))
                for rec in recommendations
            ]
            
            elements.append(ListFlowable(
                recommendation_items,
                bulletType='bullet',
                leftIndent=20
            ))
            
            # Add recent sessions table if space allows
            if performance_history:
                elements.append(Spacer(1, 0.1*inch))
                elements.append(Paragraph(
                    "Recent Sessions", 
                    self.styles['Heading2']
                ))
                
                # Create sessions table
                data = [
                    ["Date", "Score", "Quality"]
                ]
                
                for i, session in enumerate(performance_history[:5]):  # Limit to 5 most recent
                    timestamp = datetime.datetime.fromisoformat(session['timestamp'])
                    data.append([
                        timestamp.strftime('%m/%d/%Y'),
                        f"{session['overall_score']:.1f}" if session.get('overall_score') else "N/A",
                        session.get('posture_quality', 'N/A')
                    ])
                
                table = Table(data, colWidths=[1.5*inch, 1*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (1, -1), 'CENTER')
                ]))
                
                elements.append(table)
            
            # Add footer
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                "Focus on these 3 key areas to significantly improve your shooting posture over time.", 
                self.styles['Italic']
            ))
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"Created concise progress report at {filepath}")
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
            # Extract dates and scores
            dates = [item['date'] for item in trend_data]
            scores = [item['avg_score'] for item in trend_data]
            
            # Convert string dates to datetime objects
            date_objects = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
            
            # Create figure
            plt.figure(figsize=(8, 4))
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
            
            # Create a path for the graph in a fixed location
            reports_dir = os.path.join(os.path.expanduser("~"), ".shooting_analyzer", "reports")
            os.makedirs(reports_dir, exist_ok=True)
            graph_path = os.path.join(reports_dir, f"trend_graph_{int(datetime.datetime.now().timestamp())}.png")
            
            # Save the graph
            plt.savefig(graph_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            # Make sure the file exists before returning
            if os.path.exists(graph_path):
                logger.info(f"Created trend graph at {graph_path}")
                return graph_path
            else:
                logger.error(f"Failed to create trend graph at {graph_path}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating trend graph: {str(e)}")
            return None
    
    def _get_progress_recommendations(self, performance_history: List[Dict], joint_improvement: Dict) -> List[str]:
        """
        Generate targeted recommendations based on progress data.
        
        Args:
            performance_history: List of session performance data
            joint_improvement: Dictionary with joint improvement data
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Analyze overall trend if we have performance history
        if performance_history and len(performance_history) >= 2:
            first_session = performance_history[-1]  # Oldest session (reversed order)
            last_session = performance_history[0]    # Most recent session
            
            if first_session.get('overall_score') and last_session.get('overall_score'):
                first_score = first_session['overall_score']
                last_score = last_session['overall_score']
                trend = last_score - first_score
                
                if trend > 10:
                    recommendations.append("Continue your current training approach - you're making excellent progress. Focus on maintaining consistency in your form.")
                elif trend > 0:
                    recommendations.append("You're making steady progress. Consider increasing your practice frequency to accelerate improvement.")
                else:
                    recommendations.append("Your scores indicate a plateau or slight decline. Consider working with a coach to identify and address specific challenges.")
        
        # Add joint-specific recommendations based on improvement data
        if joint_improvement:
            # Find joints that need work
            needs_work_joints = []
            for joint, data in joint_improvement.items():
                if data.get('trend') is not None and data['trend'] < -3:  # Significant negative trend
                    needs_work_joints.append((joint, data['trend']))
            
            if needs_work_joints:
                # Sort by most problematic
                needs_work_joints.sort(key=lambda x: x[1])
                
                # Add specific recommendations for top problem areas
                for joint, trend in needs_work_joints[:2]:  # Limit to top 2
                    if 'shoulder' in joint:
                        recommendations.append(f"Focus on {joint.replace('_', ' ')} position exercises to improve stability and strength. Your trend of {trend:.1f} indicates this needs attention.")
                    elif 'elbow' in joint:
                        recommendations.append(f"Practice proper {joint.replace('_', ' ')} positioning using a mirror or training partner. Your trend of {trend:.1f} shows consistent challenges here.")
                    elif joint == 'knees' or joint == 'hips':
                        recommendations.append(f"Work on lower body stability with balance exercises and stance practice. Your {joint} position shows a trend of {trend:.1f}.")
                    elif joint == 'neck':
                        recommendations.append(f"Practice proper head position and cheek weld for consistent sight alignment. Your neck positioning trend of {trend:.1f} needs improvement.")
                    elif joint == 'wrists':
                        recommendations.append(f"Strengthen your wrists and practice maintaining a consistent position. Your wrist positioning trend of {trend:.1f} indicates room for improvement.")
            else:
                # If no specific problem joints, check for improvements
                improved_joints = []
                for joint, data in joint_improvement.items():
                    if data.get('trend') is not None and data['trend'] > 3:  # Significant positive trend
                        improved_joints.append((joint, data['trend']))
                
                if improved_joints:
                    recommendations.append("Continue the exercises that have helped improve your joint positioning. Your consistent practice is showing positive results.")
        
        # Add general recommendation if we don't have enough specific ones
        if len(recommendations) < 3:
            general_recommendations = [
                "Maintain a consistent practice schedule, focusing on quality rather than quantity of shots.",
                "Record your sessions regularly to track subtle changes in your posture over time.",
                "Incorporate strength and stability exercises specific to shooting posture into your regular fitness routine.",
                "Practice dry firing with focus on maintaining perfect form to build muscle memory."
            ]
            
            # Add general recommendations until we have 3 total
            for rec in general_recommendations:
                if rec not in recommendations:
                    recommendations.append(rec)
                    if len(recommendations) >= 3:
                        break
        
        return recommendations[:3]  # Limit to top 3 recommendations