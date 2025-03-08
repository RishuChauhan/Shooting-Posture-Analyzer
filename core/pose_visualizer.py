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
    Provides enhanced 3D visualization of shooting pose data.
    """
    
    def __init__(self):
        """Initialize the pose visualizer with improved appearance."""
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Configure plot with better styling
        self.ax.set_xlabel('X - Left/Right', fontsize=9)
        self.ax.set_ylabel('Z - Front/Back', fontsize=9)
        self.ax.set_zlabel('Y - Up/Down', fontsize=9)
        self.ax.set_title('3D Pose Visualization', fontsize=12, fontweight='bold')
        
        # Set a better default view angle for shooting pose
        self.ax.view_init(elev=15, azim=70)
        
        # Add a grid for better spatial awareness
        self.ax.grid(True, alpha=0.3)
        
        # Improved color scheme for different body parts
        self.line_settings = {
            'head': {'color': '#E74C3C', 'linewidth': 3},     # Red
            'torso': {'color': '#3498DB', 'linewidth': 3},    # Blue
            'left_arm': {'color': '#2ECC71', 'linewidth': 3}, # Green
            'right_arm': {'color': '#F39C12', 'linewidth': 3}, # Orange
            'left_leg': {'color': '#9B59B6', 'linewidth': 3}, # Purple
            'right_leg': {'color': '#1ABC9C', 'linewidth': 3}  # Teal
        }
        
        # Lines for body parts
        self.lines = {}
        
        # Set equal aspect ratio for more realistic body proportions
        self.ax.set_box_aspect([1, 1, 1])
        
        logger.info("Enhanced PoseVisualizer initialized")
    
    def clear(self):
        """Clear the visualization."""
        self.ax.clear()
        
        # Reset axis labels and title with improved styling
        self.ax.set_xlabel('X - Left/Right', fontsize=9)
        self.ax.set_ylabel('Z - Front/Back', fontsize=9)
        self.ax.set_zlabel('Y - Up/Down', fontsize=9)
        self.ax.set_title('3D Pose Visualization', fontsize=12, fontweight='bold')
        
        # Reset grid
        self.ax.grid(True, alpha=0.3)
        
        self.lines = {}
        self.canvas.draw()
    
    def visualize_pose(self, landmarks):
        """
        Visualize the shooting pose in 3D with improved appearance.
        
        Args:
            landmarks: List of pose landmarks
        """
        # Clear previous visualization
        self.ax.clear()
        
        # Reset axis labels and title with improved styling
        self.ax.set_xlabel('X - Left/Right', fontsize=9)
        self.ax.set_ylabel('Z - Front/Back', fontsize=9)
        self.ax.set_zlabel('Y - Up/Down', fontsize=9)
        self.ax.set_title('3D Pose Visualization', fontsize=12, fontweight='bold')
        
        # Add grid back
        self.ax.grid(True, alpha=0.3)
        
        # Check if we have landmarks
        if not landmarks:
            self.canvas.draw()
            return
        
        try:
            # Extract 3D coordinates from landmarks
            x = []
            y = []
            z = []
            
            for landmark in landmarks:
                if hasattr(landmark, 'x') and hasattr(landmark, 'y') and hasattr(landmark, 'z'):
                    # Use coordinates directly - fixed coordinate system
                    x.append(landmark.x)
                    y.append(landmark.y)
                    z.append(landmark.z)
            
            # Plot landmarks as points with better styling
            if x and y and z:
                # Use smaller markers and better colors for joints
                self.ax.scatter(x, z, y, c='#34495E', marker='o', s=30, alpha=0.8)
                
                # Connect landmarks with colored lines to form the pose skeleton
                self._draw_skeleton(landmarks)
                
                # Set equal aspect ratio for more realistic body proportions
                self.ax.set_box_aspect([1, 1, 1])
                
                # Set axis limits with appropriate padding
                x_range = max(x) - min(x)
                y_range = max(y) - min(y)
                z_range = max(z) - min(z)
                
                # Calculate padding based on the largest range
                max_range = max(x_range, y_range, z_range)
                padding = max_range * 0.2
                
                # Ensure the view is centered properly
                x_mid = (max(x) + min(x)) / 2
                y_mid = (max(y) + min(y)) / 2
                z_mid = (max(z) + min(z)) / 2
                
                # Set limits with padding
                self.ax.set_xlim(x_mid - max_range/2 - padding, x_mid + max_range/2 + padding)
                self.ax.set_ylim(z_mid - max_range/2 - padding, z_mid + max_range/2 + padding)
                self.ax.set_zlim(y_mid - max_range/2 - padding, y_mid + max_range/2 + padding)
                
                # Add labels to key joints
                # Define key joints to label with their indices in the landmark list
                key_joints = {
                    # Head and neck
                    0: "Nose",
                    10: "Neck",
                    
                    # Shoulders
                    11: "L Shoulder",
                    12: "R Shoulder",
                    
                    # Elbows
                    13: "L Elbow",
                    14: "R Elbow",
                    
                    # Wrists
                    15: "L Wrist",
                    16: "R Wrist",
                    
                    # Hips
                    23: "L Hip",
                    24: "R Hip",
                    
                    # Knees
                    25: "L Knee",
                    26: "R Knee",
                    
                    # Ankles
                    27: "L Ankle",
                    28: "R Ankle"
                }
                
                # Add text labels with small offset for better visibility
                text_offset = max_range * 0.05
                for idx, label in key_joints.items():
                    if idx < len(landmarks):
                        lm = landmarks[idx]
                        # Use small offset in y (up) direction for better visibility
                        self.ax.text(lm.x, lm.z, lm.y + text_offset, 
                                    label, color='black', fontsize=8, 
                                    horizontalalignment='center',
                                    verticalalignment='bottom')
                
                # Reset the view angle to default
                self.ax.view_init(elev=15, azim=70)
            
            # Update canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error visualizing pose: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _draw_skeleton(self, landmarks):
        """
        Draw a skeleton by connecting landmarks with colored lines.

        Args:
            landmarks: List of pose landmarks
        """
        if not landmarks or len(landmarks) < 29:
            logger.warning(f"Not enough landmarks to draw skeleton: {len(landmarks) if landmarks else 0}")
            return

        # Define connections for different body parts with better organization
        connections = {
            'head': [
                (0, 1),   # Nose to between eyes
                (1, 2),   # Between eyes to left eye
                (1, 3),   # Between eyes to right eye
                (2, 4),   # Left eye to left ear
                (3, 5),   # Right eye to right ear
                (1, 8),   # Between eyes to center mouth
                (8, 9),   # Center mouth to chin
                (9, 10),  # Chin to neck
            ],
            'torso': [
                (10, 11), # Neck to left shoulder
                (10, 12), # Neck to right shoulder
                (11, 12), # Left shoulder to right shoulder
                (11, 23), # Left shoulder to left hip
                (12, 24), # Right shoulder to right hip
                (23, 24), # Left hip to right hip
            ],
            'left_arm': [
                (11, 13), # Left shoulder to left elbow
                (13, 15), # Left elbow to left wrist
                # FIX: Changed hand connections - left hand
                (15, 17), # Left wrist to left thumb
                (15, 18), # Left wrist to left index
                (15, 19), # Left wrist to left pinky
                # Remove connection between left thumb and left pinky
            ],
            'right_arm': [
                (12, 14), # Right shoulder to right elbow
                (14, 16), # Right elbow to right wrist
                # FIX: Changed hand connections - right hand
                (16, 20), # Right wrist to right thumb
                (16, 21), # Right wrist to right index
                (16, 22), # Right wrist to right pinky
                # Remove connection between right thumb and right pinky
            ],
            'left_leg': [
                (23, 25), # Left hip to left knee
                (25, 27), # Left knee to left ankle
                (27, 29), # Left ankle to left foot tip
                (27, 31), # Left ankle to left heel
            ],
            'right_leg': [
                (24, 26), # Right hip to right knee
                (26, 28), # Right knee to right ankle
                (28, 30), # Right ankle to right foot tip
                (28, 32), # Right ankle to right heel
            ]
        }

        try:
            # Draw connections for each body part with distinct colors
            for part, part_connections in connections.items():
                for start_idx, end_idx in part_connections:
                    if start_idx < len(landmarks) and end_idx < len(landmarks):
                        start = landmarks[start_idx]
                        end = landmarks[end_idx]

                        # Plot connection with the part's color settings
                        self.ax.plot([start.x, end.x], 
                                    [start.z, end.z], 
                                    [start.y, end.y], 
                                    **self.line_settings[part])
        except Exception as e:
            logger.error(f"Error drawing skeleton: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def set_camera_angle(self, elev, azim):
        """
        Set the camera view angle.
        
        Args:
            elev: Elevation angle in degrees
            azim: Azimuth angle in degrees
        """
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw()