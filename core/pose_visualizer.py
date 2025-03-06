#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pose Visualizer Module

This module provides 3D visualization of pose data.

Author: Claude
Date: March 6, 2025
"""

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging

logger = logging.getLogger(__name__)

class PoseVisualizer:
    """
    Provides 3D visualization of shooting pose data.
    """
    
    def __init__(self):
        """Initialize the pose visualizer."""
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Configure plot
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Z')
        self.ax.set_zlabel('Y')
        self.ax.set_title('3D Pose Visualization')
        
        # Initial view angle
        self.ax.view_init(elev=10, azim=45)
        
        # Default line settings
        self.line_settings = {
            'body': {'color': 'blue', 'linewidth': 2},
            'arms': {'color': 'green', 'linewidth': 2},
            'legs': {'color': 'red', 'linewidth': 2}
        }
        
        # Lines for body parts
        self.lines = {}
        
        logger.info("PoseVisualizer initialized")
    
    def clear(self):
        """Clear the visualization."""
        self.ax.clear()
        
        # Reset axis labels and title
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Z')
        self.ax.set_zlabel('Y')
        self.ax.set_title('3D Pose Visualization')
        
        self.lines = {}
        self.canvas.draw()
    
    def visualize_pose(self, landmarks):
   
    # Clear previous visualization
        self.ax.clear()
    
    # Reset axis labels and title
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Z')
        self.ax.set_zlabel('Y')
        self.ax.set_title('3D Pose Visualization')
    
    # Check if we have landmarks
        if not landmarks:
            self.canvas.draw()
            return
    
        # Extract 3D coordinates from landmarks
        x = []
        y = []
        z = []
    
        for landmark in landmarks:
            if hasattr(landmark, 'x') and hasattr(landmark, 'y') and hasattr(landmark, 'z'):
                x.append(landmark.x)
            # Flip y and z for better visualization (MediaPipe uses y-down)
                y.append(-landmark.z)  # Use negative z as y
                z.append(-landmark.y)  # Use negative y as z
    
    # Plot landmarks as points
        if x and y and z:  # Make sure we have valid data
            self.ax.scatter(x, y, z, c='b', marker='o')
        
        # Connect landmarks with lines to form the pose skeleton
            self._draw_skeleton(landmarks)
        
        # Set axis limits with some padding
            self.ax.set_xlim(min(x)-0.1, max(x)+0.1)
            self.ax.set_ylim(min(y)-0.1, max(y)+0.1)
            self.ax.set_zlim(min(z)-0.1, max(z)+0.1)
    
    # Update canvas
        self.canvas.draw()
    
    def _draw_skeleton(self, landmarks):
        """
        Draw a skeleton by connecting landmarks with lines.
        
        Args:
            landmarks: List of pose landmarks
        """
        # Define connections for different body parts
        connections = {
            'body': [
                # Torso
                (11, 12),  # Left shoulder to right shoulder
                (11, 23),  # Left shoulder to left hip
                (12, 24),  # Right shoulder to right hip
                (23, 24),  # Left hip to right hip
            ],
            'arms': [
                # Left arm
                (11, 13),  # Left shoulder to left elbow
                (13, 15),  # Left elbow to left wrist
                # Right arm
                (12, 14),  # Right shoulder to right elbow
                (14, 16),  # Right elbow to right wrist
            ],
            'legs': [
                # Left leg
                (23, 25),  # Left hip to left knee
                (25, 27),  # Left knee to left ankle
                # Right leg
                (24, 26),  # Right hip to right knee
                (26, 28),  # Right knee to right ankle
            ]
        }
        
        # Draw connections for each body part
        for part, part_connections in connections.items():
            for start_idx, end_idx in part_connections:
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    start = landmarks[start_idx]
                    end = landmarks[end_idx]
                    
                    self.ax.plot([start.x, end.x], 
                                [start.z, end.z], 
                                [start.y, end.y], 
                                **self.line_settings[part])
    
    def set_camera_angle(self, elev, azim):
        """
        Set the camera view angle.
        
        Args:
            elev: Elevation angle in degrees
            azim: Azimuth angle in degrees
        """
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw()