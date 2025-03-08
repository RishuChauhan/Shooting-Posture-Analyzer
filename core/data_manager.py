import sqlite3
import json
import os
import logging
import datetime
import time
import uuid
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any

# Initialize logger
logger = logging.getLogger(__name__)

class DataManager:
    """
    Manages all database operations for the application.
    Handles user profiles, session data, and application settings.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the data manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        logger.info(f"DataManager initialized with database at: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
        return conn
    
    def initialize_database(self):
        """
        Initialize the database schema if it doesn't exist.
        Creates tables for users, sessions, and settings.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                role TEXT CHECK (role IN ('shooter', 'coach')) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create sessions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration INTEGER,
                overall_score REAL,
                posture_quality TEXT,
                stability TEXT,
                summary TEXT,
                video_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            ''')

            # Create session_data table for detailed session data
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_data (
                data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                frame_number INTEGER NOT NULL,
                joint_angles TEXT NOT NULL,
                posture_score REAL,
                feedback TEXT,
                frame_path TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
            ''')

            # Create settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE (user_id, setting_key)
            )
            ''')

            # Create app_settings table for global settings
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
            ''')

            conn.commit()
            conn.close()

            # Create directory structure
            data_dir = os.path.dirname(self.db_path)
            frames_dir = os.path.join(data_dir, "frames")
            videos_dir = os.path.join(data_dir, "videos")
            
            for directory in [frames_dir, videos_dir]:
                if not os.path.exists(directory):
                    os.makedirs(directory)
                    logger.info(f"Created directory: {directory}")

            # Populate default settings if needed
            self._initialize_default_settings()

            logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def _initialize_default_settings(self):
        """Initialize default application settings."""
        default_settings = {
            'camera_id': '0',
            'theme': 'light',
            'posture_sensitivity': '0.5',
            'recording_fps': '15',
            'recording_duration_limit': '300',  # 5 minutes in seconds
            'show_angles': 'true',
            'show_feedback': 'true',
            'analysis_delay': '1.0'  # Seconds between analyses
        }
        
        for key, value in default_settings.items():
            # Check if setting exists
            exists = self.get_app_setting(key)
            
            # If not, create it
            if exists is None:
                self.set_app_setting(key, value)
    
    def create_user(self, name: str, email: str = None, role: str = 'shooter') -> int:
        """
        Create a new user.
        
        Args:
            name: User's name
            email: User's email (optional)
            role: User role ('shooter' or 'coach')
            
        Returns:
            ID of the created user
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO users (name, email, role)
            VALUES (?, ?, ?)
            ''', (name, email, role))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created user {name} with ID {user_id}")
            return user_id
            
        except sqlite3.Error as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def get_user(self, user_id: int) -> Dict:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing user data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            else:
                return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise
    
    def get_all_users(self) -> List[Dict]:
        """
        Get all users.
        
        Returns:
            List of dictionaries containing user data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM users ORDER BY name
            ''')
            
            users = cursor.fetchall()
            conn.close()
            
            return [dict(user) for user in users]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting all users: {str(e)}")
            raise
    
    def update_user(self, user_id: int, name: str = None, email: str = None, 
                   role: str = None) -> bool:
        """
        Update user information.
        
        Args:
            user_id: User ID
            name: New name (or None to keep existing)
            email: New email (or None to keep existing)
            role: New role (or None to keep existing)
            
        Returns:
            True if successful, False if user not found
        """
        try:
            # Get current user data
            current_user = self.get_user(user_id)
            if not current_user:
                return False
            
            # Use existing values if new ones not provided
            name = name if name is not None else current_user['name']
            email = email if email is not None else current_user['email']
            role = role if role is not None else current_user['role']
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE users 
            SET name = ?, email = ?, role = ?, modified_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
            ''', (name, email, role, user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated user ID {user_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user and all associated data.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False if user not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            # Begin transaction
            conn.execute('BEGIN TRANSACTION')
            
            try:
                # Delete user settings
                cursor.execute('DELETE FROM settings WHERE user_id = ?', (user_id,))
                
                # Get all sessions for this user
                cursor.execute('SELECT session_id FROM sessions WHERE user_id = ?', (user_id,))
                sessions = cursor.fetchall()
                
                # Delete session data and related files for each session
                for session in sessions:
                    session_id = session['session_id']
                    
                    # Get frame paths before deleting
                    cursor.execute('SELECT frame_path FROM session_data WHERE session_id = ? AND frame_path IS NOT NULL', 
                                  (session_id,))
                    frame_paths = cursor.fetchall()
                    
                    # Delete physical files
                    data_dir = os.path.dirname(self.db_path)
                    for path_row in frame_paths:
                        if path_row['frame_path']:
                            try:
                                file_path = os.path.join(data_dir, path_row['frame_path'])
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception as e:
                                logger.warning(f"Failed to delete file {path_row['frame_path']}: {str(e)}")
                    
                    # Get session video path
                    cursor.execute('SELECT video_path FROM sessions WHERE session_id = ? AND video_path IS NOT NULL', 
                                  (session_id,))
                    video_path_row = cursor.fetchone()
                    
                    # Delete video file if exists
                    if video_path_row and video_path_row['video_path']:
                        try:
                            video_path = os.path.join(data_dir, video_path_row['video_path'])
                            if os.path.exists(video_path):
                                os.remove(video_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete video {video_path_row['video_path']}: {str(e)}")
                    
                    # Delete session data
                    cursor.execute('DELETE FROM session_data WHERE session_id = ?', (session_id,))
                
                # Delete all sessions
                cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
                
                # Finally, delete the user
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                
                # Commit transaction
                conn.commit()
                logger.info(f"Deleted user ID {user_id} and all associated data")
                
            except sqlite3.Error as e:
                # Rollback in case of error
                conn.rollback()
                logger.error(f"Transaction failed when deleting user {user_id}: {str(e)}")
                raise
            
            finally:
                conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise
    
    def create_session(self, user_id: int, name: str, overall_score: float = None,
                      posture_quality: str = None, stability: str = None,
                      summary: Dict = None) -> int:
        """
        Create a new session.
        
        Args:
            user_id: User ID
            name: Session name
            overall_score: Overall session score
            posture_quality: Posture quality category
            stability: Stability category
            summary: Session summary as JSON-serializable dict
            
        Returns:
            ID of the created session
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert summary to JSON if provided
            summary_json = json.dumps(summary) if summary else None
            
            cursor.execute('''
            INSERT INTO sessions (user_id, name, overall_score, posture_quality, 
                                stability, summary, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, name, overall_score, posture_quality, stability, summary_json))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created session '{name}' with ID {session_id} for user {user_id}")
            return session_id
            
        except sqlite3.Error as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def update_session(self, session_id: int, duration: int = None, 
                      overall_score: float = None, posture_quality: str = None,
                      stability: str = None, summary: Dict = None, video_path: str = None) -> bool:
        """
        Update session information.
        
        Args:
            session_id: Session ID
            duration: Session duration in seconds
            overall_score: Overall session score
            posture_quality: Posture quality category
            stability: Stability category
            summary: Session summary as JSON-serializable dict
            video_path: Path to session video file
            
        Returns:
            True if successful, False if session not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute('SELECT 1 FROM sessions WHERE session_id = ?', (session_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            # Prepare update fields
            update_fields = []
            params = []
            
            if duration is not None:
                update_fields.append('duration = ?')
                params.append(duration)
                
            if overall_score is not None:
                update_fields.append('overall_score = ?')
                params.append(overall_score)
                
            if posture_quality is not None:
                update_fields.append('posture_quality = ?')
                params.append(posture_quality)
                
            if stability is not None:
                update_fields.append('stability = ?')
                params.append(stability)
                
            if summary is not None:
                update_fields.append('summary = ?')
                params.append(json.dumps(summary))
                
            if video_path is not None:
                update_fields.append('video_path = ?')
                params.append(video_path)
            
            # If no fields to update, return success
            if not update_fields:
                conn.close()
                return True
            
            # Build and execute query
            query = f'''
            UPDATE sessions 
            SET {', '.join(update_fields)}
            WHERE session_id = ?
            '''
            
            params.append(session_id)
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated session ID {session_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating session {session_id}: {str(e)}")
            raise
    
    def get_session(self, session_id: int) -> Dict:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary containing session data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM sessions WHERE session_id = ?
            ''', (session_id,))
            
            session = cursor.fetchone()
            conn.close()
            
            if session:
                # Convert session to dict
                session_dict = dict(session)
                
                # Parse JSON summary if it exists
                if session_dict.get('summary'):
                    session_dict['summary'] = json.loads(session_dict['summary'])
                
                return session_dict
            else:
                return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting session {session_id}: {str(e)}")
            raise
    
    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of dictionaries containing session data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM sessions WHERE user_id = ? ORDER BY timestamp DESC
            ''', (user_id,))
            
            sessions = cursor.fetchall()
            conn.close()
            
            result = []
            for session in sessions:
                session_dict = dict(session)
                
                # Parse JSON summary if it exists
                if session_dict.get('summary'):
                    session_dict['summary'] = json.loads(session_dict['summary'])
                
                result.append(session_dict)
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Error getting sessions for user {user_id}: {str(e)}")
            raise
    
    def delete_session(self, session_id: int) -> bool:
        """
        Delete a session and all associated data.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False if session not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute('SELECT video_path FROM sessions WHERE session_id = ?', (session_id,))
            session = cursor.fetchone()
            if not session:
                conn.close()
                return False
            
            # Begin transaction
            conn.execute('BEGIN TRANSACTION')
            
            try:
                # Get frame paths before deleting
                cursor.execute('SELECT frame_path FROM session_data WHERE session_id = ? AND frame_path IS NOT NULL', 
                              (session_id,))
                frame_paths = cursor.fetchall()
                
                # Delete frame files
                data_dir = os.path.dirname(self.db_path)
                for path_row in frame_paths:
                    if path_row['frame_path']:
                        try:
                            file_path = os.path.join(data_dir, path_row['frame_path'])
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete file {path_row['frame_path']}: {str(e)}")
                
                # Delete video file if exists
                if session['video_path']:
                    try:
                        video_path = os.path.join(data_dir, session['video_path'])
                        if os.path.exists(video_path):
                            os.remove(video_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete video {session['video_path']}: {str(e)}")
                
                # Delete session data
                cursor.execute('DELETE FROM session_data WHERE session_id = ?', (session_id,))
                
                # Delete session
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                
                # Commit transaction
                conn.commit()
                logger.info(f"Deleted session ID {session_id} and all associated data")
                
            except sqlite3.Error as e:
                # Rollback in case of error
                conn.rollback()
                logger.error(f"Transaction failed when deleting session {session_id}: {str(e)}")
                raise
            
            finally:
                conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            raise
    
    def _save_frame_to_disk(self, session_id: int, frame_number: int, frame) -> Optional[str]:
        """
        Save a frame to disk and return its relative path.
        
        Args:
            session_id: Session ID
            frame_number: Frame number
            frame: OpenCV image
            
        Returns:
            Relative path to the saved frame, or None if saving failed
        """
        try:
            # Create directory path
            data_dir = os.path.dirname(self.db_path)
            frames_dir = os.path.join(data_dir, "frames")
            session_dir = os.path.join(frames_dir, f"session_{session_id}")
            
            # Create directories if they don't exist
            os.makedirs(session_dir, exist_ok=True)
            
            # Create a unique filename
            timestamp = int(time.time())
            filename = f"frame_{frame_number}_{timestamp}.jpg"
            filepath = os.path.join(session_dir, filename)
            
            # Save the frame as JPEG
            success = cv2.imwrite(filepath, frame)
            
            if success:
                # Return relative path from data directory
                rel_path = os.path.relpath(filepath, data_dir)
                logger.debug(f"Saved frame to {rel_path}")
                return rel_path
            else:
                logger.error(f"Failed to save frame to {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving frame to disk: {str(e)}")
            return None
    
    def add_session_data(self, session_id: int, frame_number: int, 
                joint_angles: Dict, posture_score: float, 
                feedback: List[str], frame=None) -> int:
        """
        Add frame data to a session.

        Args:
            session_id: Session ID
            frame_number: Frame number in the session
            joint_angles: Dictionary of joint angles
            posture_score: Posture score for this frame
            feedback: List of feedback messages
            frame: Optional frame image (OpenCV format)

        Returns:
            ID of the created data entry
        """
        try:
            # Save frame to disk if provided
            frame_path = None
            if frame is not None:
                frame_path = self._save_frame_to_disk(session_id, frame_number, frame)
                if not frame_path:
                    logger.warning(f"Failed to save frame for session {session_id}, frame {frame_number}")

            # Ensure joint_angles is a properly formatted dictionary
            if not isinstance(joint_angles, dict):
                logger.warning(f"joint_angles is not a dictionary: {type(joint_angles)}")
                joint_angles = {}

            # Log the joint angles for debugging
            logger.info(f"Saving joint angles: {joint_angles}")

            conn = self._get_connection()
            cursor = conn.cursor()

            # Convert joint_angles and feedback to JSON
            # Make sure to use dumps (not dump) for converting to JSON string
            joint_angles_json = json.dumps(joint_angles, ensure_ascii=False)
            feedback_json = json.dumps(feedback, ensure_ascii=False)

            # Insert data with file path
            cursor.execute('''
            INSERT INTO session_data (session_id, frame_number, joint_angles, 
                                     posture_score, feedback, frame_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, frame_number, joint_angles_json, posture_score, 
                 feedback_json, frame_path))

            data_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Added session data with ID {data_id} for session {session_id}, frame {frame_number}")
            return data_id

        except Exception as e:
            logger.error(f"Error adding session data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def get_session_data(self, session_id) -> List[Dict]:
        """
        Get all frame data for a session.

        Args:
            session_id: Session ID

        Returns:
            List of dictionaries containing frame data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM session_data WHERE session_id = ? ORDER BY frame_number
            ''', (session_id,))

            data = cursor.fetchall()
            conn.close()

            result = []
            for item in data:
                item_dict = dict(item)

                # Parse JSON fields - CRITICAL FIX FOR JOINT ANGLES
                try:
                    # Print raw joint_angles string for debugging
                    logger.debug(f"Raw joint_angles from DB: {item_dict['joint_angles']}")

                    if isinstance(item_dict['joint_angles'], str) and item_dict['joint_angles'].strip():
                        try:
                            # First try normal json parsing
                            item_dict['joint_angles'] = json.loads(item_dict['joint_angles'])
                        except json.JSONDecodeError:
                            # Some databases might store with single quotes instead of double quotes
                            # Try to fix this by replacing single quotes with double quotes
                            fixed_json = item_dict['joint_angles'].replace("'", "\"")
                            try:
                                item_dict['joint_angles'] = json.loads(fixed_json)
                            except json.JSONDecodeError:
                                # If still failing, try ast.literal_eval which can handle Python dict literals
                                import ast
                                item_dict['joint_angles'] = ast.literal_eval(item_dict['joint_angles'])

                        # Ensure all values are floats for consistency
                        if isinstance(item_dict['joint_angles'], dict):
                            item_dict['joint_angles'] = {k: float(v) if isinstance(v, (int, float)) else v 
                                                        for k, v in item_dict['joint_angles'].items()}
                    else:
                        logger.warning(f"Empty joint_angles for frame {item_dict.get('frame_number', 'unknown')}")
                        item_dict['joint_angles'] = {}
                except Exception as e:
                    logger.error(f"Error parsing joint_angles: {str(e)}, raw value: {item_dict.get('joint_angles', 'None')}")
                    item_dict['joint_angles'] = {}

                try:
                    if isinstance(item_dict['feedback'], str):
                        item_dict['feedback'] = json.loads(item_dict['feedback'])
                    else:
                        item_dict['feedback'] = []
                except Exception as e:
                    logger.error(f"Error parsing feedback: {str(e)}")
                    item_dict['feedback'] = []

                # Load frame image from disk if path exists
                if 'frame_path' in item_dict and item_dict['frame_path']:
                    try:
                        # Construct absolute path
                        data_dir = os.path.dirname(self.db_path)
                        abs_path = os.path.join(data_dir, item_dict['frame_path'])

                        if os.path.exists(abs_path):
                            item_dict['frame_image'] = cv2.imread(abs_path)

                            if item_dict['frame_image'] is None:
                                logger.warning(f"Failed to load image at {abs_path}")
                        else:
                            logger.warning(f"Image file not found at {abs_path}")
                            item_dict['frame_image'] = None
                    except Exception as e:
                        logger.error(f"Error loading frame image: {str(e)}")
                        item_dict['frame_image'] = None
                else:
                    item_dict['frame_image'] = None

                result.append(item_dict)

            logger.info(f"Retrieved {len(result)} data frames for session {session_id}")
            # Debug output for the first frame's joint angles
            if result and len(result) > 0 and 'joint_angles' in result[0]:
                logger.info(f"First frame joint angles: {result[0]['joint_angles']}")

            return result

        except Exception as e:
            logger.error(f"Error getting data for session {session_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def save_session_video(self, session_id: int, frames: List) -> Optional[str]:
        """
        Save session frames as a video file.
        
        Args:
            session_id: Session ID
            frames: List of OpenCV frames
            
        Returns:
            Relative path to the saved video, or None if saving failed
        """
        if not frames:
            logger.warning(f"No frames to save for session {session_id}")
            return None
        
        try:
            # Create video directory
            data_dir = os.path.dirname(self.db_path)
            videos_dir = os.path.join(data_dir, "videos")
            os.makedirs(videos_dir, exist_ok=True)
            
            # Create a unique filename
            timestamp = int(time.time())
            filename = f"session_{session_id}_{timestamp}.mp4"
            filepath = os.path.join(videos_dir, filename)
            
            # Get frame dimensions from the first frame
            height, width = frames[0].shape[:2]
            
            # Create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 codec
            fps = 15.0  # Default FPS (adjust as needed)
            video_writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
            
            # Write each frame to the video
            for frame in frames:
                video_writer.write(frame)
            
            # Release the writer
            video_writer.release()
            
            # Return relative path from data directory
            rel_path = os.path.relpath(filepath, data_dir)
            
            # Update the session with the video path
            self.update_session(session_id, video_path=rel_path)
            
            logger.info(f"Saved session video to {rel_path}")
            return rel_path
            
        except Exception as e:
            logger.error(f"Error saving session video: {str(e)}")
            return None
    
    def set_user_setting(self, user_id: int, key: str, value: str) -> bool:
        """
        Set a user-specific setting.
        
        Args:
            user_id: User ID
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if setting exists
            cursor.execute('''
            SELECT 1 FROM settings WHERE user_id = ? AND setting_key = ?
            ''', (user_id, key))
            
            if cursor.fetchone():
                # Update existing setting
                cursor.execute('''
                UPDATE settings SET setting_value = ? 
                WHERE user_id = ? AND setting_key = ?
                ''', (value, user_id, key))
            else:
                # Insert new setting
                cursor.execute('''
                INSERT INTO settings (user_id, setting_key, setting_value)
                VALUES (?, ?, ?)
                ''', (user_id, key, value))
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error setting user setting: {str(e)}")
            raise
    
    def get_user_setting(self, user_id: int, key: str) -> Optional[str]:
        """
        Get a user-specific setting.
        
        Args:
            user_id: User ID
            key: Setting key
            
        Returns:
            Setting value or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT setting_value FROM settings 
            WHERE user_id = ? AND setting_key = ?
            ''', (user_id, key))
            
            result = cursor.fetchone()
            conn.close()
            
            return result['setting_value'] if result else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user setting: {str(e)}")
            raise
    
    def get_user_settings(self, user_id: int) -> Dict[str, str]:
        """
        Get all settings for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of settings
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT setting_key, setting_value FROM settings 
            WHERE user_id = ?
            ''', (user_id,))
            
            settings = cursor.fetchall()
            conn.close()
            
            return {s['setting_key']: s['setting_value'] for s in settings}
            
        except sqlite3.Error as e:
            logger.error(f"Error getting user settings: {str(e)}")
            raise
    
    def set_app_setting(self, key: str, value: str) -> bool:
        """
        Set a global application setting.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if setting exists
            cursor.execute('''
            SELECT 1 FROM app_settings WHERE setting_key = ?
            ''', (key,))
            
            if cursor.fetchone():
                # Update existing setting
                cursor.execute('''
                UPDATE app_settings SET setting_value = ? 
                WHERE setting_key = ?
                ''', (value, key))
            else:
                # Insert new setting
                cursor.execute('''
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES (?, ?)
                ''', (key, value))
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error setting app setting: {str(e)}")
            raise
    
    def get_app_setting(self, key: str) -> Optional[str]:
        """
        Get a global application setting.
        
        Args:
            key: Setting key
            
        Returns:
            Setting value or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT setting_value FROM app_settings 
            WHERE setting_key = ?
            ''', (key,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result['setting_value'] if result else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting app setting: {str(e)}")
            raise
    
    def get_app_settings(self) -> Dict[str, str]:
        """
        Get all global application settings.
        
        Returns:
            Dictionary of settings
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT setting_key, setting_value FROM app_settings
            ''')
            
            settings = cursor.fetchall()
            conn.close()
            
            return {s['setting_key']: s['setting_value'] for s in settings}
            
        except sqlite3.Error as e:
            logger.error(f"Error getting app settings: {str(e)}")
            raise
    
    def get_user_performance_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get performance history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to return

        Returns:
            List of dictionaries containing session performance data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Modified query to ensure we get ALL sessions even if some fields are NULL
            # This is crucial - the original query might have been filtering out sessions
            cursor.execute('''
            SELECT session_id, name, timestamp, duration, 
                   overall_score, posture_quality, stability
            FROM sessions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (user_id, limit))

            sessions = cursor.fetchall()
            conn.close()

            # Convert to list of dicts and set default values for missing fields
            result = []
            for session in sessions:
                session_dict = dict(session)

                # Ensure these fields have default values if NULL
                if session_dict.get('overall_score') is None:
                    # If overall_score is NULL, calculate it from session_data
                    avg_score = self._calculate_avg_session_score(session_dict['session_id'])
                    session_dict['overall_score'] = avg_score

                    # Update the session record with the calculated score
                    if avg_score is not None:
                        self.update_session(session_dict['session_id'], overall_score=avg_score)

                if session_dict.get('posture_quality') is None:
                    # Assign quality based on score
                    score = session_dict.get('overall_score', 0)
                    if score >= 85:
                        quality = "Excellent"
                    elif score >= 70:
                        quality = "Good"
                    elif score >= 50:
                        quality = "Fair"
                    else:
                        quality = "Needs Improvement"

                    session_dict['posture_quality'] = quality

                    # Update the session record
                    self.update_session(session_dict['session_id'], posture_quality=quality)

                if session_dict.get('stability') is None:
                    session_dict['stability'] = "Not Analyzed"

                result.append(session_dict)

            return result

        except sqlite3.Error as e:
            logger.error(f"Error getting performance history: {str(e)}")
            raise
    
    def _calculate_avg_session_score(self, session_id: int) -> Optional[float]:
        """
        Calculate average posture score for a session from session_data.

        Args:
            session_id: Session ID

        Returns:
            Average score or None if no data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT AVG(posture_score) as avg_score 
            FROM session_data 
            WHERE session_id = ? AND posture_score IS NOT NULL
            ''', (session_id,))

            result = cursor.fetchone()
            conn.close()

            if result and result['avg_score'] is not None:
                return float(result['avg_score'])
            return None

        except sqlite3.Error as e:
            logger.error(f"Error calculating session score: {str(e)}")
            return None

    def get_performance_trend(self, user_id: int, days: int = 30) -> List[Dict]:
        """
        Get performance trend over time.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of dictionaries with date and average score
        """
        try:
            logger.info(f"Getting performance trend for user {user_id} over {days} days")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Calculate date threshold
            import datetime
            cutoff_date = (datetime.datetime.now() - 
                          datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get session data with scores directly from session_data
            cursor.execute('''
            SELECT s.session_id, date(s.timestamp) as date, s.overall_score
            FROM sessions s
            WHERE s.user_id = ? AND date(s.timestamp) >= ?
            ORDER BY date(s.timestamp)
            ''', (user_id, cutoff_date))
            
            sessions = cursor.fetchall()
            
            # If we don't have session data with scores, try the alternative approach
            if not sessions or all(s['overall_score'] is None for s in sessions):
                logger.info("No session scores found, calculating from session_data")
                
                # Get session IDs and dates
                cursor.execute('''
                SELECT s.session_id, date(s.timestamp) as date
                FROM sessions s
                WHERE s.user_id = ? AND date(s.timestamp) >= ?
                ORDER BY date(s.timestamp)
                ''', (user_id, cutoff_date))
                
                sessions = cursor.fetchall()
                
                if not sessions:
                    logger.info("No sessions found in specified time period")
                    conn.close()
                    return []
                
                # Prepare to calculate average scores
                date_groups = {}
                
                for session in sessions:
                    session_id = session['session_id']
                    date_str = session['date']
                    
                    # Get session data for this session
                    cursor.execute('''
                    SELECT AVG(sd.posture_score) as avg_score
                    FROM session_data sd
                    WHERE sd.session_id = ? AND sd.posture_score IS NOT NULL
                    ''', (session_id,))
                    
                    result = cursor.fetchone()
                    
                    if result and result['avg_score'] is not None:
                        # Store session score by date
                        if date_str not in date_groups:
                            date_groups[date_str] = []
                        
                        date_groups[date_str].append(result['avg_score'])
                
                # Calculate average score for each date
                trend_data = []
                
                for date_str, scores in date_groups.items():
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        trend_data.append({
                            'date': date_str,
                            'avg_score': avg_score
                        })
                
                # Sort by date
                trend_data.sort(key=lambda x: x['date'])
                
                conn.close()
                
                # If we only have one data point, create a second one for better visualization
                if len(trend_data) == 1:
                    today_date = datetime.datetime.strptime(trend_data[0]['date'], '%Y-%m-%d')
                    yesterday = today_date - datetime.timedelta(days=1)
                    yesterday_str = yesterday.strftime('%Y-%m-%d')
                    
                    trend_data.append({
                        'date': yesterday_str,
                        'avg_score': trend_data[0]['avg_score']
                    })
                    
                    # Resort by date
                    trend_data.sort(key=lambda x: x['date'])
                
                logger.info(f"Generated {len(trend_data)} trend data points via session_data approach")
                return trend_data
            
            # Original approach for when we have direct overall_score values
            date_groups = {}
            
            for session in sessions:
                date_str = session['date']
                overall_score = session['overall_score']
                
                if overall_score is not None:
                    if date_str not in date_groups:
                        date_groups[date_str] = []
                    
                    date_groups[date_str].append(overall_score)
            
            # Calculate average score for each date
            trend_data = []
            
            for date_str, scores in date_groups.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    trend_data.append({
                        'date': date_str,
                        'avg_score': avg_score
                    })
            
            # Sort by date
            trend_data.sort(key=lambda x: x['date'])
            
            conn.close()
            
            # If we only have one data point, create a second one for better visualization
            if len(trend_data) == 1:
                today_date = datetime.datetime.strptime(trend_data[0]['date'], '%Y-%m-%d')
                yesterday = today_date - datetime.timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                
                trend_data.append({
                    'date': yesterday_str,
                    'avg_score': trend_data[0]['avg_score']
                })
                
                # Resort by date
                trend_data.sort(key=lambda x: x['date'])
            
            logger.info(f"Generated {len(trend_data)} trend data points via overall_score approach")
            return trend_data
            
        except Exception as e:
            logger.error(f"Error getting performance trend: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_joint_improvement(self, user_id: int, sessions: int = 5) -> Dict[str, Dict]:
        """
        Get improvement in joint postures over recent sessions.
        
        Args:
            user_id: User ID
            sessions: Number of recent sessions to analyze
            
        Returns:
            Dictionary with joint names as keys and improvement metrics as values
        """
        try:
            # Get recent sessions
            recent_sessions = self.get_user_performance_history(user_id, sessions)
            
            if not recent_sessions:
                return {}
            
            # Initialize result structure
            joints = ['knees', 'hips', 'left_shoulder', 'right_shoulder', 
                     'left_elbow', 'right_elbow', 'wrists', 'neck']
            
            result = {joint: {'sessions': [], 'trend': None} for joint in joints}
            
            # Process each session
            for session in recent_sessions:
                session_id = session['session_id']
                
                # Get session data
                session_data = self.get_session_data(session_id)
                
                if not session_data:
                    continue
                
                # Extract joint scores
                for joint in joints:
                    scores = []
                    
                    for frame in session_data:
                        joint_angles = frame['joint_angles']
                        
                        if joint in joint_angles:
                            # For this simplified version, we'll use presence of joint as indicator
                            # In a real implementation, you would calculate deviation from ideal
                            scores.append(1)
                    
                    # Calculate average score for this joint in this session
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        result[joint]['sessions'].append({
                            'session_id': session_id,
                            'timestamp': session['timestamp'],
                            'score': avg_score
                        })
            
            # Calculate improvement trends
            for joint, data in result.items():
                if len(data['sessions']) >= 2:
                    # Sort by timestamp
                    sessions_sorted = sorted(data['sessions'], 
                                           key=lambda x: x['timestamp'])
                    
                    # Calculate trend (positive = improvement)
                    first_score = sessions_sorted[0]['score']
                    last_score = sessions_sorted[-1]['score']
                    
                    trend = last_score - first_score
                    data['trend'] = trend
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting joint improvement: {str(e)}")
            raise

    def get_performance_data_from_session_data(self, user_id, limit=10):
        """
        Generate performance metrics directly from session_data.
        Use this when regular performance history is not available.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to process

        Returns:
            List of dictionaries with performance metrics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get session IDs for this user
            cursor.execute('''
            SELECT session_id, name, timestamp
            FROM sessions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (user_id, limit))

            sessions = cursor.fetchall()

            if not sessions:
                return []

            performance_data = []

            for session in sessions:
                session_id = session['session_id']

                # Get session data
                cursor.execute('''
                SELECT posture_score, joint_angles
                FROM session_data
                WHERE session_id = ?
                ORDER BY frame_number
                ''', (session_id,))

                frames = cursor.fetchall()

                if not frames:
                    continue
                
                # Calculate metrics
                scores = []
                all_joint_angles = []

                for frame in frames:
                    if frame['posture_score'] is not None:
                        scores.append(frame['posture_score'])

                    if frame['joint_angles']:
                        try:
                            joint_angles = json.loads(frame['joint_angles'])
                            if isinstance(joint_angles, dict):
                                all_joint_angles.append(joint_angles)
                        except:
                            pass
                        
                # Calculate overall score
                overall_score = None
                if scores:
                    overall_score = sum(scores) / len(scores)

                # Determine posture quality
                posture_quality = None
                if overall_score is not None:
                    if overall_score >= 85:
                        posture_quality = "Excellent"
                    elif overall_score >= 70:
                        posture_quality = "Good"
                    elif overall_score >= 50:
                        posture_quality = "Fair"
                    else:
                        posture_quality = "Needs Improvement"

                # Determine stability
                stability = "Not Analyzed"
                if len(all_joint_angles) >= 2:
                    # Simple stability measure based on joint angle variance
                    joint_variances = {}
                    for joint in ['knees', 'hips', 'left_shoulder', 'right_shoulder', 
                                 'left_elbow', 'right_elbow', 'wrists', 'neck']:
                        values = []
                        for angles in all_joint_angles:
                            if joint in angles:
                                values.append(angles[joint])

                        if len(values) >= 2:
                            variance = np.var(values)
                            joint_variances[joint] = variance

                    if joint_variances:
                        avg_variance = sum(joint_variances.values()) / len(joint_variances)
                        if avg_variance < 5:
                            stability = "Very Stable"
                        elif avg_variance < 15:
                            stability = "Stable"
                        elif avg_variance < 30:
                            stability = "Moderately Stable"
                        else:
                            stability = "Unstable"

                # Create performance data entry
                entry = {
                    'session_id': session_id,
                    'name': session['name'],
                    'timestamp': session['timestamp'],
                    'overall_score': overall_score,
                    'posture_quality': posture_quality,
                    'stability': stability
                }

                # Also update the session record with these metrics
                self.update_session(
                    session_id,
                    overall_score=overall_score,
                    posture_quality=posture_quality,
                    stability=stability
                )

                performance_data.append(entry)

            conn.close()
            return performance_data

        except Exception as e:
            logger.error(f"Error generating performance data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []