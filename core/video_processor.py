#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Processing Module

This module handles video capture from webcam and processes frames 
using MediaPipe for pose detection.

Author: Claude
Date: March 6, 2025
"""

import cv2
import numpy as np
import mediapipe as mp
import logging
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QMutex, QWaitCondition
from typing import Dict, List, Tuple, Optional, Union

# Initialize logger
logger = logging.getLogger(__name__)

class PoseDetector:
    """
    Handles pose detection using MediaPipe.
    Extracts and processes keypoints for shooting posture analysis.
    """
    
    def __init__(self, 
                 min_detection_confidence: float = 0.5, 
                 min_tracking_confidence: float = 0.5):
        """
        Initialize the pose detector with MediaPipe.
        
        Args:
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
        """
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # Use the most accurate model
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Define ideal angles for shooting stance from configuration
        self.ideal_angles = {
            'knees': 172.5,  # Slightly bent (170°-175°)
            'hips': 180.0,   # Straight (175°-185°)
            'left_shoulder': 45.0,  # Raised to support rifle (30°-60°)
            'right_shoulder': 15.0,  # Closer to body (0°-30°)
            'left_elbow': 75.0,  # Bent to support rifle (60°-90°)
            'right_elbow': 90.0,  # Bent for grip (80°-100°)
            'wrists': 180.0,  # Straight (170°-190°)
            'neck': 12.5,    # Tilted forward (10°-15°)
        }
        
        # Angle ranges for scoring
        self.angle_ranges = {
            'knees': (170.0, 175.0),
            'hips': (175.0, 185.0),
            'left_shoulder': (30.0, 60.0),
            'right_shoulder': (0.0, 30.0),
            'left_elbow': (60.0, 90.0),
            'right_elbow': (80.0, 100.0),
            'wrists': (170.0, 190.0),
            'neck': (10.0, 15.0),
        }
        
        logger.info("PoseDetector initialized")
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict, bool]:
        """
        Process a video frame to detect pose.
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple containing:
                - Annotated frame with pose landmarks
                - Dictionary of joint angles
                - Boolean indicating if pose was detected
        """
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.pose.process(rgb_frame)
        
        # Initialize joint angles dictionary
        joint_angles = {}
        pose_detected = False
        
        # If pose landmarks were detected
        if results.pose_landmarks:
            pose_detected = True
            
            # Draw pose landmarks on the frame
            self.mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)
            )
            
            # Extract landmarks
            landmarks = results.pose_landmarks.landmark
            
            # Calculate joint angles
            joint_angles = self._calculate_joint_angles(landmarks, frame.shape)
            
            # Draw angle annotations on the frame
            frame = self._draw_angle_annotations(frame, joint_angles, landmarks)
        
        return frame, joint_angles, pose_detected
    
    def _calculate_joint_angles(self, landmarks, frame_shape: Tuple[int, int, int]) -> Dict[str, float]:
        """
        Calculate joint angles from pose landmarks.
        
        Args:
            landmarks: MediaPipe pose landmarks
            frame_shape: Shape of the video frame (height, width, channels)
            
        Returns:
            Dictionary of joint angle measurements
        """
        # Convert normalized coordinates to pixel coordinates
        h, w, _ = frame_shape
        
        # Helper function to get coordinates
        def get_coords(landmark_index):
            return (
                int(landmarks[landmark_index].x * w),
                int(landmarks[landmark_index].y * h)
            )
        
        # Calculate angle between three points
        def calculate_angle(a, b, c):
            a = np.array(a)
            b = np.array(b)
            c = np.array(c)
            
            # Calculate vectors
            ba = a - b
            bc = c - b
            
            # Calculate cosine of angle using dot product
            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
            cosine_angle = np.clip(cosine_angle, -1.0, 1.0)  # Avoid numerical errors
            
            # Calculate angle in degrees
            angle = np.degrees(np.arccos(cosine_angle))
            
            return angle
        
        joint_angles = {}
        
        # Calculate knee angles (average of left and right)
        left_knee_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.LEFT_HIP.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_KNEE.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_ANKLE.value)
        )
        
        right_knee_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.RIGHT_HIP.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_KNEE.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_ANKLE.value)
        )
        
        joint_angles['knees'] = (left_knee_angle + right_knee_angle) / 2
        
        # Calculate hip angles
        left_hip_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.LEFT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_HIP.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_KNEE.value)
        )
        
        right_hip_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_HIP.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_KNEE.value)
        )
        
        joint_angles['hips'] = (left_hip_angle + right_hip_angle) / 2
        
        # Calculate shoulder angles
        left_shoulder_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.LEFT_ELBOW.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_HIP.value)
        )
        
        right_shoulder_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.RIGHT_ELBOW.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_HIP.value)
        )
        
        joint_angles['left_shoulder'] = left_shoulder_angle
        joint_angles['right_shoulder'] = right_shoulder_angle
        
        # Calculate elbow angles
        left_elbow_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.LEFT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_ELBOW.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_WRIST.value)
        )
        
        right_elbow_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_ELBOW.value),
            get_coords(self.mp_pose.PoseLandmark.RIGHT_WRIST.value)
        )
        
        joint_angles['left_elbow'] = left_elbow_angle
        joint_angles['right_elbow'] = right_elbow_angle
        
        # Calculate wrist angles (average of left and right)
        # This is simplified as MediaPipe doesn't have detailed wrist landmarks
        joint_angles['wrists'] = 180.0  # Placeholder
        
        # Calculate neck angle
        neck_angle = calculate_angle(
            get_coords(self.mp_pose.PoseLandmark.NOSE.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_SHOULDER.value),
            get_coords(self.mp_pose.PoseLandmark.LEFT_HIP.value)
        )
        
        joint_angles['neck'] = neck_angle
        
        return joint_angles
    
    def _draw_angle_annotations(self, frame: np.ndarray, joint_angles: Dict[str, float], 
                               landmarks) -> np.ndarray:
        """
        Draw angle annotations on the frame.
        
        Args:
            frame: Video frame
            joint_angles: Dictionary of joint angles
            landmarks: MediaPipe pose landmarks
            
        Returns:
            Annotated frame
        """
        h, w, _ = frame.shape
        
        # Helper function to get coordinates
        def get_coords(landmark_index):
            return (
                int(landmarks[landmark_index].x * w),
                int(landmarks[landmark_index].y * h)
            )
        
        # Add angle text near each joint
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        
        # Draw knee angles
        left_knee_pos = get_coords(self.mp_pose.PoseLandmark.LEFT_KNEE.value)
        cv2.putText(frame, f"{joint_angles['knees']:.1f}°", 
                    (left_knee_pos[0] + 10, left_knee_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        # Draw hip angles
        left_hip_pos = get_coords(self.mp_pose.PoseLandmark.LEFT_HIP.value)
        cv2.putText(frame, f"{joint_angles['hips']:.1f}°", 
                    (left_hip_pos[0] + 10, left_hip_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        # Draw shoulder angles
        left_shoulder_pos = get_coords(self.mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        right_shoulder_pos = get_coords(self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value)
        
        cv2.putText(frame, f"{joint_angles['left_shoulder']:.1f}°", 
                    (left_shoulder_pos[0] - 40, left_shoulder_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        cv2.putText(frame, f"{joint_angles['right_shoulder']:.1f}°", 
                    (right_shoulder_pos[0] + 10, right_shoulder_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        # Draw elbow angles
        left_elbow_pos = get_coords(self.mp_pose.PoseLandmark.LEFT_ELBOW.value)
        right_elbow_pos = get_coords(self.mp_pose.PoseLandmark.RIGHT_ELBOW.value)
        
        cv2.putText(frame, f"{joint_angles['left_elbow']:.1f}°", 
                    (left_elbow_pos[0] - 40, left_elbow_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        cv2.putText(frame, f"{joint_angles['right_elbow']:.1f}°", 
                    (right_elbow_pos[0] + 10, right_elbow_pos[1]), 
                    font, font_scale, (0, 0, 255), font_thickness)
        
        return frame

class VideoThread(QThread):
    """
    Thread for capturing video from webcam and processing frames.
    Uses QThread to avoid blocking the UI thread.
    """
    
    # Define signals
    frame_ready = pyqtSignal(np.ndarray)
    pose_data_ready = pyqtSignal(dict, bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, camera_id: int = 0, parent=None):
        """
        Initialize the video capture thread.
        
        Args:
            camera_id: ID of the camera to use (default: 0)
            parent: Parent Qt object
        """
        super().__init__(parent)
        self.camera_id = camera_id
        self.running = False
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.pose_detector = PoseDetector()
        self.recording = False
        self.recorded_frames = []

        self.last_joint_angles = {}
        self.last_frame = None
        
        logger.info(f"VideoThread initialized with camera ID: {camera_id}")
    
    def run(self):
        """Thread's main loop."""
        try:
            # Open webcam
            cap = cv2.VideoCapture(self.camera_id)
            
            if not cap.isOpened():
                self.error_occurred.emit(f"Failed to open camera {self.camera_id}")
                return
            
            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.running = True
            
            while self.running:
                # Capture frame
                ret, frame = cap.read()
                
                if not ret:
                    self.error_occurred.emit("Failed to capture frame")
                    break
                
                # Store original frame before processing
                original_frame = frame.copy()
                self.last_frame = original_frame  # Save the most recent frame
                
                # Process frame with pose detector
                processed_frame, joint_angles, pose_detected = self.pose_detector.process_frame(frame)
                
                # Store the joint angles regardless of pose detection status
                if joint_angles:
                    self.last_joint_angles = joint_angles.copy()
                    logger.debug(f"Updated last_joint_angles: {self.last_joint_angles}")
                
                # Emit signals with results
                self.frame_ready.emit(processed_frame)
                self.pose_data_ready.emit(joint_angles, pose_detected)
                
                # Record frame if recording is active
                if self.recording:
                    # Always store the frame data (even if no pose detected)
                    # This ensures we have continuous video for replay
                    self.recorded_frames.append({
                        'frame': original_frame,  # Original frame
                        'processed_frame': processed_frame,  # Processed frame with overlays
                        'joint_angles': joint_angles.copy() if joint_angles else {},  # Joint angles (safely copied)
                        'pose_detected': pose_detected  # Store the detection state
                    })
                
                # Sleep briefly to reduce CPU usage
                self.msleep(10)
            
            # Release camera when done
            cap.release()
            
        except Exception as e:
            logger.error(f"Error in video thread: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.error_occurred.emit(f"Video processing error: {str(e)}")
        
        finally:
            self.running = False
    
    def stop(self):
        """Stop the video capture thread."""
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()
        self.wait()
    
    def start_recording(self):
        """Start recording video frames and pose data."""
        self.mutex.lock()
        self.recording = True
        self.recorded_frames = []
        self.mutex.unlock()
        logger.info("Started recording")
    
    def stop_recording(self) -> List[Dict]:
        """
        Stop recording and return recorded frames.
        
        Returns:
            List of dictionaries containing frames and pose data
        """
        self.mutex.lock()
        self.recording = False
        frames = self.recorded_frames.copy()
        self.mutex.unlock()
        
        logger.info(f"Stopped recording. Captured {len(frames)} frames")
        return frames


class VideoPlayer:
    """
    Handles playback of recorded video sessions.
    Used in the replay and analysis mode.
    """
    
    def __init__(self):
        """Initialize the video player."""
        self.current_session = None
        self.current_frame_index = 0
        self.playing = False
        
    def load_session(self, session_data: List[Dict]):
        """
        Load a recorded session for playback.
        
        Args:
            session_data: List of dictionaries containing frames and pose data
        """
        self.current_session = session_data
        self.current_frame_index = 0
        self.playing = False
        
    def get_current_frame(self) -> Optional[Dict]:
        """
        Get the current frame data.
        
        Returns:
            Dictionary containing frame and pose data, or None if no session is loaded
        """
        if not self.current_session or self.current_frame_index >= len(self.current_session):
            return None
        
        return self.current_session[self.current_frame_index]
    
    def next_frame(self) -> Optional[Dict]:
        """
        Advance to the next frame.
        
        Returns:
            Dictionary containing frame and pose data, or None if at the end
        """
        if not self.current_session:
            return None
        
        self.current_frame_index = (self.current_frame_index + 1) % len(self.current_session)
        return self.get_current_frame()
    
    def previous_frame(self) -> Optional[Dict]:
        """
        Go back to the previous frame.
        
        Returns:
            Dictionary containing frame and pose data, or None if at the beginning
        """
        if not self.current_session:
            return None
        
        self.current_frame_index = (self.current_frame_index - 1) % len(self.current_session)
        return self.get_current_frame()
    
    def seek(self, position: float) -> Optional[Dict]:
        """
        Seek to a specific position in the session.
        
        Args:
            position: Position in range [0.0, 1.0]
            
        Returns:
            Dictionary containing frame and pose data at the new position
        """
        if not self.current_session:
            return None
        
        position = max(0.0, min(1.0, position))
        self.current_frame_index = int(position * (len(self.current_session) - 1))
        return self.get_current_frame()