import os
import logging
import numpy as np
import cv2
import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt backend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QGroupBox, QScrollArea, QFrame, QSplitter,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont

from core.pose_visualizer import PoseVisualizer
from utils.helpers import show_error_message, show_info_message
from utils.constants import COLORS

# Initialize logger
logger = logging.getLogger(__name__)

class Plot3DWidget(QWidget):
    """
    Widget for 3D plot analysis screen.
    Displays 3D visualizations of the shooter's body with joint angles.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the 3D plot widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Current user ID
        self.current_user_id = None
        
        # Shots history - store up to 30 shots
        self.shot_history = []
        self.current_shot_index = 0
        
        # Initialize pose visualizer
        self.pose_visualizer = PoseVisualizer()
        
        # Initialize UI
        self._init_ui()
        
        logger.info("Plot3DWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("3D Plot Analysis")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel(
            "View 3D visualizations of shooting posture with joint angles. "
            "Navigate through past shots to analyze technique."
        )
        desc_label.setWordWrap(True)
        self.main_layout.addWidget(desc_label)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Create left panel (3D plot)
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 10, 10, 0)
        
        # Add 3D plot canvas
        self.canvas_container = QGroupBox("3D Visualization")
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.addWidget(self.pose_visualizer.canvas)
        
        left_layout.addWidget(self.canvas_container)
        
        # Add controls for navigation through shots
        controls_group = QGroupBox("Shot Navigation")
        controls_layout = QHBoxLayout(controls_group)
        
        self.prev_btn = QPushButton("Previous Shot")
        self.prev_btn.clicked.connect(self._show_previous_shot)
        self.prev_btn.setEnabled(False)
        controls_layout.addWidget(self.prev_btn)
        
        self.shot_label = QLabel("No shots available")
        self.shot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.shot_label)
        
        self.next_btn = QPushButton("Next Shot")
        self.next_btn.clicked.connect(self._show_next_shot)
        self.next_btn.setEnabled(False)
        controls_layout.addWidget(self.next_btn)
        
        left_layout.addWidget(controls_group)
        
        # Camera control panel
        camera_group = QGroupBox("Camera Controls")
        camera_layout = QHBoxLayout(camera_group)
        
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self._reset_camera_view)
        camera_layout.addWidget(self.reset_view_btn)
        
        self.front_view_btn = QPushButton("Front View")
        self.front_view_btn.clicked.connect(lambda: self._set_camera_angle(0, 0))
        camera_layout.addWidget(self.front_view_btn)
        
        self.side_view_btn = QPushButton("Side View")
        self.side_view_btn.clicked.connect(lambda: self._set_camera_angle(0, 90))
        camera_layout.addWidget(self.side_view_btn)
        
        self.top_view_btn = QPushButton("Top View")
        self.top_view_btn.clicked.connect(lambda: self._set_camera_angle(90, 0))
        camera_layout.addWidget(self.top_view_btn)
        
        left_layout.addWidget(camera_group)
        
        # Add left panel to splitter
        self.splitter.addWidget(self.left_panel)
        
        # Create right panel (analysis and details)
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 10, 0, 0)
        
        # Shot information
        shot_info_group = QGroupBox("Shot Information")
        shot_info_layout = QVBoxLayout(shot_info_group)
        
        self.shot_info_label = QLabel("No shot selected")
        self.shot_info_label.setWordWrap(True)
        shot_info_layout.addWidget(self.shot_info_label)
        
        right_layout.addWidget(shot_info_group)
        
        # Joint angles display
        angles_group = QGroupBox("Joint Angles")
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
        angles_layout = QVBoxLayout(angles_group)
        angles_layout.addWidget(angles_scroll)
        
        right_layout.addWidget(angles_group)
        
        # Session selector
        session_group = QGroupBox("Select Session")
        session_layout = QHBoxLayout(session_group)
        
        session_label = QLabel("Session:")
        session_layout.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self._session_selected)
        session_layout.addWidget(self.session_combo)
        
        self.load_btn = QPushButton("Load Shots")
        self.load_btn.clicked.connect(self._load_shots)
        session_layout.addWidget(self.load_btn)
        
        right_layout.addWidget(session_group)
        
        # Add right panel to splitter
        self.splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes
        self.splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])
    
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
            self._clear_display()
    
    def _refresh_sessions(self):
        """Refresh the list of available sessions."""
        if not self.current_user_id:
            return

        try:
            # Get user sessions
            sessions = self.data_manager.get_user_sessions(self.current_user_id)

            # Update combo box
            self.session_combo.blockSignals(True)
            self.session_combo.clear()

            self.session_combo.addItem("Select a session...", None)

            for session in sessions:
                # Format label as "Name - Date (Frames)"
                frame_count = self._get_session_frame_count(session['session_id'])
                label = f"{session['name']} - {session['timestamp'].split()[0]}"

                if frame_count > 0:
                    label += f" ({frame_count} frames)"

                self.session_combo.addItem(label, session['session_id'])

            self.session_combo.blockSignals(False)

            # Clear display
            self._clear_display()

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
        # Clear current shot history
        self.shot_history = []
        self.current_shot_index = 0
        
        # Update UI
        self._update_navigation_controls()
        self._clear_display()
    
    def _load_shots(self):
        """Load shots from the selected session."""
        # Get session ID
        session_id = self.session_combo.currentData()

        if not session_id:
            show_error_message(self, "No Session", 
                              "Please select a session first.")
            return

        try:
            # Get session data
            session_data = self.data_manager.get_session_data(session_id)

            if not session_data:
                show_error_message(self, "No Data", 
                                  "This session has no recorded data.")
                return

            # Get session info
            session = self.data_manager.get_session(session_id)

            # Clear current shot history
            self.shot_history = []

            # Debug: Check for missing files
            files_checked = 0
            files_missing = 0

            # Process session data into shots
            for frame_data in session_data:
                files_checked += 1

                # Check for frame image (either in memory or on disk)
                frame_image = None
                has_image = False

                if 'frame_image' in frame_data and frame_data['frame_image'] is not None:
                    frame_image = frame_data['frame_image']
                    has_image = True
                    logger.info(f"Using preloaded frame image for frame {frame_data.get('frame_number', 'unknown')}")
                elif 'frame_path' in frame_data and frame_data['frame_path']:
                    # Construct absolute path and check if file exists
                    data_dir = os.path.dirname(self.data_manager.db_path)
                    abs_path = os.path.join(data_dir, frame_data['frame_path'])

                    if os.path.exists(abs_path):
                        try:
                            # Actually load the image here
                            frame_image = cv2.imread(abs_path)
                            if frame_image is not None:
                                has_image = True
                                logger.info(f"Successfully loaded image from {abs_path}")
                            else:
                                logger.warning(f"Failed to load image: {abs_path}")
                                files_missing += 1
                        except Exception as e:
                            logger.error(f"Error loading image {abs_path}: {str(e)}")
                            files_missing += 1
                    else:
                        logger.warning(f"Image file not found: {abs_path}")
                        files_missing += 1

                # Validate joint angles data
                if 'joint_angles' in frame_data:
                    # Log the joint angles for debugging
                    logger.debug(f"Joint angles for frame {frame_data.get('frame_number', 'unknown')}: {frame_data['joint_angles']}")

                    # Ensure joint_angles is not empty or null
                    if not frame_data['joint_angles']:
                        logger.warning(f"Empty joint_angles in frame {frame_data.get('frame_number', 'unknown')}")
                        frame_data['joint_angles'] = {}  # Set to empty dict to avoid errors

                # Add to shot history with image
                self.shot_history.append({
                    'frame_data': frame_data,
                    'session_info': session,
                    'timestamp': session['timestamp'],
                    'has_image': has_image,
                    'frame_image': frame_image  # Store the actual loaded image
                })

            # Set current index to first shot
            self.current_shot_index = 0

            # Update display
            if self.shot_history:
                self._display_current_shot()
            else:
                self._clear_display()

            # Update navigation controls
            self._update_navigation_controls()

            # Show loading summary
            logger.info(f"Loaded {len(self.shot_history)} shots from session {session_id}")

            if files_missing > 0:
                logger.warning(f"{files_missing} out of {files_checked} image files are missing")
                show_info_message(self, "Files Missing", 
                                 f"Loaded {len(self.shot_history)} shots, but {files_missing} "
                                 f"image files could not be found. The 3D visualization will "
                                 f"still work based on the saved joint angle data.")

        except Exception as e:
            logger.error(f"Error loading shots: {str(e)}")
            show_error_message(self, "Data Error", 
                              f"Failed to load shots: {str(e)}")
    
    def _display_current_shot(self):
        """Display the current shot from history."""
        if not self.shot_history or self.current_shot_index >= len(self.shot_history):
            self._clear_display()
            return

        try:
            # Get current shot data
            shot = self.shot_history[self.current_shot_index]
            frame_data = shot['frame_data']

            # Log for debugging
            logger.info(f"Displaying shot {self.current_shot_index + 1}/{len(self.shot_history)}, "
                      f"Frame: {frame_data.get('frame_number', 'unknown')}")

            # Get joint angles and pose data
            joint_angles = frame_data.get('joint_angles', {})
            if not joint_angles:
                logger.warning(f"No joint angles found for frame {frame_data.get('frame_number', 'unknown')}")
                # Even if no joint angles are found, continue to display what we can

            # Update shot label
            self.shot_label.setText(f"Shot {self.current_shot_index + 1} of {len(self.shot_history)}")

            # Update shot info
            session_info = shot['session_info']
            self.shot_info_label.setText(
                f"Session: {session_info['name']}\n"
                f"Date: {shot['timestamp']}\n"
                f"Frame: {frame_data.get('frame_number', 'unknown')}\n"
                f"Posture Score: {frame_data.get('posture_score', 0):.1f}"
            )

            # Update joint angle labels
            self._update_joint_angles(joint_angles)

            # Visualize 3D pose using joint angles
            if joint_angles:
                logger.info(f"Visualizing pose with joint angles: {joint_angles}")
                self._visualize_pose(joint_angles)
            else:
                logger.warning("No joint angles available for visualization")
                self.pose_visualizer.clear()

        except Exception as e:
            logger.error(f"Error displaying shot: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())  # Get full traceback
            show_error_message(self, "Display Error", 
                              f"Failed to display shot: {str(e)}")
    
    def _update_joint_angles(self, joint_angles):
        """
        Update the joint angles display.

        Args:
            joint_angles: Dictionary of joint angle measurements
        """
        # Debug the incoming joint_angles
        logger.info(f"Updating joint angles with data: {joint_angles}")

        if not joint_angles or not isinstance(joint_angles, dict):
            # Clear all joint labels if no data or invalid data
            for joint, label in self.angle_labels.items():
                label.setText(f"{joint.replace('_', ' ').title()}: N/A")
                label.setStyleSheet("")
            logger.warning(f"Invalid joint_angles provided: {type(joint_angles)}")
            return

        # Get ideal angles for comparison
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

        # Update each joint label with special handling for different joint name formats
        for joint, label in self.angle_labels.items():
            # Try different possible formats for the joint name in the dictionary
            angle = None

            # Try direct key match
            if joint in joint_angles:
                angle = joint_angles[joint]
            # Try capitalized key
            elif joint.capitalize() in joint_angles:
                angle = joint_angles[joint.capitalize()]
            # Try all uppercase key
            elif joint.upper() in joint_angles:
                angle = joint_angles[joint.upper()]
            # Try with spaces instead of underscores
            elif joint.replace('_', ' ') in joint_angles:
                angle = joint_angles[joint.replace('_', ' ')]

            if angle is not None:
                # Convert to float if it's not already
                try:
                    angle = float(angle)
                except (ValueError, TypeError):
                    logger.warning(f"Non-numeric angle value for {joint}: {angle}")
                    label.setText(f"{joint.replace('_', ' ').title()}: Invalid")
                    continue

                ideal = ideal_angles.get(joint, 0)
                diff = abs(angle - ideal)

                # Set color based on difference
                if diff <= 5:
                    color = COLORS['secondary']  # Green for good
                elif diff <= 15:
                    color = COLORS['warning']  # Orange for fair
                else:
                    color = COLORS['danger']  # Red for poor

                label.setText(f"{joint.replace('_', ' ').title()}: {angle:.1f}° (Ideal: {ideal:.1f}°, Diff: {diff:.1f}°)")
                label.setStyleSheet(f"color: {color};")
            else:
                label.setText(f"{joint.replace('_', ' ').title()}: N/A")
                label.setStyleSheet("")

        # Log the results
        logger.info(f"Updated {len(joint_angles)} joint angles in the display")
    
    def _visualize_pose(self, joint_angles):
        """
        Visualize the 3D pose based on joint angles.

        Args:
            joint_angles: Dictionary of joint angle measurements
        """
        try:
            # Create 3D landmarks based on joint angles
            landmarks = self._convert_angles_to_landmarks(joint_angles)

            # Visualize the pose if we have landmarks
            if landmarks:
                self.pose_visualizer.visualize_pose(landmarks)
                logger.info("Successfully visualized 3D pose")
            else:
                logger.warning("Failed to create landmarks from joint angles")
                self.pose_visualizer.clear()

                # Show message to user
                self.shot_info_label.setText(
                    self.shot_info_label.text() + "\n\nUnable to create 3D visualization from available data."
                )
        except Exception as e:
            import traceback
            logger.error(f"Error visualizing pose: {str(e)}")
            logger.error(traceback.format_exc())
            self.pose_visualizer.clear()
    
    # Replace the entire _convert_angles_to_landmarks function in plot_3d.py with this improved version:

    def _convert_angles_to_landmarks(self, joint_angles):
            """
            Convert joint angles to 3D landmarks for visualization.
            Creates a realistic human model with proper proportions.

            Args:
                joint_angles: Dictionary of measured joint angles

            Returns:
                List of landmarks for 3D visualization
            """
            if not joint_angles:
                logger.warning("Empty joint angles dictionary provided")
                return None

            # Log the joint angles for debugging
            logger.info(f"Converting joint angles to landmarks: {joint_angles}")

            try:
                # Create a Landmark class to match MediaPipe's format
                class Landmark:
                    def __init__(self, x, y, z):
                        self.x = x
                        self.y = y
                        self.z = z
                        self.visibility = 1.0  # MediaPipe compatibility

                # Define body dimensions (realistic proportions)
                head_size = 0.15
                torso_length = 0.35
                upper_arm_length = 0.18
                forearm_length = 0.15
                hand_length = 0.08
                upper_leg_length = 0.30
                lower_leg_length = 0.25
                foot_length = 0.10

                # Body center position - FIXED COORDINATE SYSTEM
                # X: Left/Right (negative is left)
                # Y: Up/Down (negative is down)
                # Z: Front/Back (negative is back)
                center_x = 0.0
                center_y = 0.0
                center_z = 0.0

                # Get joint angles or use defaults if missing
                knees_angle = float(joint_angles.get('knees', 172.5))
                hips_angle = float(joint_angles.get('hips', 180.0))
                left_shoulder_angle = float(joint_angles.get('left_shoulder', 45.0))
                right_shoulder_angle = float(joint_angles.get('right_shoulder', 15.0))
                left_elbow_angle = float(joint_angles.get('left_elbow', 75.0))
                right_elbow_angle = float(joint_angles.get('right_elbow', 90.0))
                wrists_angle = float(joint_angles.get('wrists', 180.0))
                neck_angle = float(joint_angles.get('neck', 12.5))

                # Initialize landmark list
                landmarks = []

                # Build human model bottom-up with fixed coordinate system
                # ===================================

                # Feet positions
                left_foot_x = -0.15  # Left side of body
                right_foot_x = 0.15  # Right side of body
                feet_y = -0.80       # Bottom
                feet_z = 0.0         # Center

                # Ankles
                left_ankle_x = left_foot_x
                right_ankle_x = right_foot_x
                ankles_y = feet_y + 0.10
                ankles_z = feet_z

                # Knees - Position based on knees angle
                knee_bend_factor = (180 - knees_angle) / 180
                knee_forward_offset = knee_bend_factor * 0.1  # How much knees move forward when bent

                left_knee_x = left_ankle_x
                right_knee_x = right_ankle_x
                knees_y = ankles_y + lower_leg_length * (1 - 0.5 * knee_bend_factor)  # Adjust height based on bend
                knees_z = feet_z + knee_forward_offset  # Knees move forward when bent

                # Hips - Position based on hips angle
                hip_bend_factor = (180 - hips_angle) / 180
                hip_forward_offset = hip_bend_factor * 0.1

                left_hip_x = -0.10
                right_hip_x = 0.10
                hips_y = knees_y + upper_leg_length * (1 - 0.3 * hip_bend_factor)
                hips_z = knees_z + hip_forward_offset  # Hips move forward when bent

                # Shoulders
                shoulder_width = 0.25
                left_shoulder_x = -shoulder_width/2
                right_shoulder_x = shoulder_width/2
                shoulders_y = hips_y + torso_length
                shoulders_z = hips_z

                # Neck and Head - Position based on neck angle
                neck_tilt_factor = neck_angle / 90
                neck_forward_offset = neck_tilt_factor * 0.05

                neck_x = 0.0
                neck_y = shoulders_y + 0.05
                neck_z = shoulders_z + neck_forward_offset  # Neck tilts forward based on angle

                head_y = neck_y + head_size/2
                head_z = neck_z + 0.05  # Head position adjusted based on neck

                # LEFT ARM - Properly convert angles using correct trigonometry
                # For left_shoulder_angle: 0° = arm straight down, 90° = arm horizontal
                left_shoulder_rad = np.radians(left_shoulder_angle)
                left_elbow_x = left_shoulder_x - upper_arm_length * np.sin(left_shoulder_rad)
                left_elbow_y = shoulders_y - upper_arm_length * np.cos(left_shoulder_rad)
                left_elbow_z = shoulders_z

                # For left_elbow_angle: 0° = arm straight, 180° = fully bent
                left_elbow_rad = np.radians(left_elbow_angle)
                # Adjust forearm direction based on shoulder angle
                forearm_direction_x = np.sin(left_shoulder_rad)
                forearm_direction_y = np.cos(left_shoulder_rad)

                # Adjusting for anatomical constraints
                left_wrist_x = left_elbow_x - forearm_length * np.sin(left_shoulder_rad) * np.sin(left_elbow_rad)
                left_wrist_y = left_elbow_y - forearm_length * np.cos(left_elbow_rad)
                left_wrist_z = left_elbow_z + forearm_length * np.sin(left_elbow_rad) * 0.2  # Slight forward adjustment

                # RIGHT ARM - Similar approach for right arm
                right_shoulder_rad = np.radians(right_shoulder_angle)
                right_elbow_x = right_shoulder_x + upper_arm_length * np.sin(right_shoulder_rad)
                right_elbow_y = shoulders_y - upper_arm_length * np.cos(right_shoulder_rad)
                right_elbow_z = shoulders_z

                right_elbow_rad = np.radians(right_elbow_angle)
                right_wrist_x = right_elbow_x + forearm_length * np.sin(right_shoulder_rad) * np.sin(right_elbow_rad)
                right_wrist_y = right_elbow_y - forearm_length * np.cos(right_elbow_rad)
                right_wrist_z = right_elbow_z + forearm_length * np.sin(right_elbow_rad) * 0.2

                # Create MediaPipe compatible landmarks in order (total of 33 landmarks)
                # Head landmarks (0-10)
                landmarks.append(Landmark(0.0, head_y, head_z))  # 0: Nose
                landmarks.append(Landmark(0.0, head_y - 0.02, head_z - 0.01))  # 1: Between eyes
                landmarks.append(Landmark(-0.03, head_y - 0.02, head_z - 0.01))  # 2: Left eye
                landmarks.append(Landmark(0.03, head_y - 0.02, head_z - 0.01))  # 3: Right eye
                landmarks.append(Landmark(-0.07, head_y - 0.03, head_z - 0.03))  # 4: Left ear
                landmarks.append(Landmark(0.07, head_y - 0.03, head_z - 0.03))  # 5: Right ear
                landmarks.append(Landmark(-0.02, head_y - 0.08, head_z))  # 6: Left mouth
                landmarks.append(Landmark(0.02, head_y - 0.08, head_z))  # 7: Right mouth
                landmarks.append(Landmark(0.0, head_y - 0.08, head_z))  # 8: Center mouth
                landmarks.append(Landmark(0.0, head_y - 0.12, head_z - 0.01))  # 9: Chin
                landmarks.append(Landmark(neck_x, neck_y, neck_z))  # 10: Neck

                # Torso landmarks (11-16)
                landmarks.append(Landmark(left_shoulder_x, shoulders_y, shoulders_z))  # 11: Left shoulder
                landmarks.append(Landmark(right_shoulder_x, shoulders_y, shoulders_z))  # 12: Right shoulder
                landmarks.append(Landmark(left_elbow_x, left_elbow_y, left_elbow_z))  # 13: Left elbow
                landmarks.append(Landmark(right_elbow_x, right_elbow_y, right_elbow_z))  # 14: Right elbow
                landmarks.append(Landmark(left_wrist_x, left_wrist_y, left_wrist_z))  # 15: Left wrist
                landmarks.append(Landmark(right_wrist_x, right_wrist_y, right_wrist_z))  # 16: Right wrist

                # Hand landmarks (17-22)
                # Left hand
                landmarks.append(Landmark(left_wrist_x - 0.03, left_wrist_y - 0.02, left_wrist_z))  # 17: Left thumb
                landmarks.append(Landmark(left_wrist_x - 0.05, left_wrist_y - 0.04, left_wrist_z))  # 18: Left index
                landmarks.append(Landmark(left_wrist_x - 0.06, left_wrist_y - 0.04, left_wrist_z))  # 19: Left pinky

                # Right hand
                landmarks.append(Landmark(right_wrist_x + 0.03, right_wrist_y - 0.02, right_wrist_z))  # 20: Right thumb
                landmarks.append(Landmark(right_wrist_x + 0.05, right_wrist_y - 0.04, right_wrist_z))  # 21: Right index
                landmarks.append(Landmark(right_wrist_x + 0.06, right_wrist_y - 0.04, right_wrist_z))  # 22: Right pinky

                # Lower body landmarks (23-32)
                landmarks.append(Landmark(left_hip_x, hips_y, hips_z))  # 23: Left hip
                landmarks.append(Landmark(right_hip_x, hips_y, hips_z))  # 24: Right hip
                landmarks.append(Landmark(left_knee_x, knees_y, knees_z))  # 25: Left knee
                landmarks.append(Landmark(right_knee_x, knees_y, knees_z))  # 26: Right knee
                landmarks.append(Landmark(left_ankle_x, ankles_y, ankles_z))  # 27: Left ankle
                landmarks.append(Landmark(right_ankle_x, ankles_y, ankles_z))  # 28: Right ankle
                landmarks.append(Landmark(left_foot_x, feet_y, feet_z + 0.1))  # 29: Left toe
                landmarks.append(Landmark(right_foot_x, feet_y, feet_z + 0.1))  # 30: Right toe
                landmarks.append(Landmark(left_foot_x, feet_y, feet_z - 0.05))  # 31: Left heel
                landmarks.append(Landmark(right_foot_x, feet_y, feet_z - 0.05))  # 32: Right heel

                logger.info(f"Successfully created {len(landmarks)} landmarks from joint angles")
                return landmarks

            except Exception as e:
                import traceback
                logger.error(f"Error converting joint angles to landmarks: {str(e)}")
                logger.error(traceback.format_exc())
                return None
    
    def _clear_display(self):
        """Clear the display when no shot is selected."""
        self.shot_label.setText("No shots available")
        self.shot_info_label.setText("No shot selected")
        
        # Clear joint angles
        for joint, label in self.angle_labels.items():
            label.setText(f"{joint.replace('_', ' ').title()}: N/A")
            label.setStyleSheet("")
        
        # Clear 3D visualization
        self.pose_visualizer.clear()
    
    def _show_previous_shot(self):
        """Show the previous shot in history."""
        if not self.shot_history or self.current_shot_index <= 0:
            return
        
        self.current_shot_index -= 1
        self._display_current_shot()
        self._update_navigation_controls()
    
    def _show_next_shot(self):
        """Show the next shot in history."""
        if not self.shot_history or self.current_shot_index >= len(self.shot_history) - 1:
            return
        
        self.current_shot_index += 1
        self._display_current_shot()
        self._update_navigation_controls()
    
    def _update_navigation_controls(self):
        """Update the navigation controls based on current state."""
        has_shots = bool(self.shot_history)
        
        # Enable/disable Previous button
        self.prev_btn.setEnabled(has_shots and self.current_shot_index > 0)
        
        # Enable/disable Next button
        self.next_btn.setEnabled(has_shots and self.current_shot_index < len(self.shot_history) - 1)
    
    def _reset_camera_view(self):
        """Reset the camera view to default."""
        self.pose_visualizer.set_camera_angle(15, 70)
        logger.info("Reset camera view to default (elev=15, azim=70)")

    def _set_camera_angle(self, elev, azim):
        """
        Set the camera angle for 3D visualization.

        Args:
            elev: Elevation angle
            azim: Azimuth angle
        """
        logger.info(f"Setting camera angle to elev={elev}, azim={azim}")
        self.pose_visualizer.set_camera_angle(elev, azim)

    def _get_session_frame_count(self, session_id):
        """
        Get the number of frames in a session.

        Args:
            session_id: Session ID

        Returns:
            Number of frames in the session
        """
        try:
            conn = self.data_manager._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM session_data 
                WHERE session_id = ?
            """, (session_id,))

            result = cursor.fetchone()
            conn.close()

            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Error getting frame count: {str(e)}")
            return 0

    def force_refresh(self):
        """Force reload of the current session data."""
        logger.info("Force refreshing 3D Plot data")

        # Reload session list
        self._refresh_sessions()

        # If we have a current session ID, try to reload it
        if hasattr(self, 'current_session_id') and self.current_session_id:
            # Find the session in the combo box
            for i in range(self.session_combo.count()):
                if self.session_combo.itemData(i) == self.current_session_id:
                    self.session_combo.setCurrentIndex(i)
                    break
                
            # Load the shots
            self._load_shots()

            # Reset any cached data
            if hasattr(self, 'shot_history'):
                logger.info(f"Clearing cached shot history with {len(self.shot_history)} items")