#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Management Module

This module handles database operations for storing and retrieving
user profiles, session data, and application settings.

Author: Claude
Date: March 6, 2025
"""

import sqlite3
import json
import os
import logging
import datetime
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
                
                # Delete session data for each session
                for session in sessions:
                    session_id = session['session_id']
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
                      stability: str = None, summary: Dict = None) -> bool:
        """
        Update session information.
        
        Args:
            session_id: Session ID
            duration: Session duration in seconds
            overall_score: Overall session score
            posture_quality: Posture quality category
            stability: Stability category
            summary: Session summary as JSON-serializable dict
            
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
            cursor.execute('SELECT 1 FROM sessions WHERE session_id = ?', (session_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            # Begin transaction
            conn.execute('BEGIN TRANSACTION')
            
            try:
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
    
    def add_session_data(self, session_id: int, frame_number: int, 
                        joint_angles: Dict, posture_score: float, 
                        feedback: List[str]) -> int:
        """
        Add frame data to a session.
        
        Args:
            session_id: Session ID
            frame_number: Frame number in the session
            joint_angles: Dictionary of joint angles
            posture_score: Posture score for this frame
            feedback: List of feedback messages
            
        Returns:
            ID of the created data entry
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert joint_angles and feedback to JSON
            joint_angles_json = json.dumps(joint_angles)
            feedback_json = json.dumps(feedback)
            
            cursor.execute('''
            INSERT INTO session_data (session_id, frame_number, joint_angles, 
                                     posture_score, feedback)
            VALUES (?, ?, ?, ?, ?)
            ''', (session_id, frame_number, joint_angles_json, posture_score, feedback_json))
            
            data_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return data_id
            
        except sqlite3.Error as e:
            logger.error(f"Error adding session data: {str(e)}")
            raise
    
    def get_session_data(self, session_id: int) -> List[Dict]:
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
                
                # Parse JSON fields
                item_dict['joint_angles'] = json.loads(item_dict['joint_angles'])
                item_dict['feedback'] = json.loads(item_dict['feedback'])
                
                result.append(item_dict)
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Error getting data for session {session_id}: {str(e)}")
            raise
    
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
            
            cursor.execute('''
            SELECT session_id, name, timestamp, overall_score, posture_quality, stability
            FROM sessions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (user_id, limit))
            
            sessions = cursor.fetchall()
            conn.close()
            
            return [dict(session) for session in sessions]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting performance history: {str(e)}")
            raise
    
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Calculate date threshold
            cutoff_date = (datetime.datetime.now() - 
                          datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            cursor.execute('''
            SELECT date(timestamp) as date, AVG(overall_score) as avg_score
            FROM sessions
            WHERE user_id = ? AND date(timestamp) >= ?
            GROUP BY date(timestamp)
            ORDER BY date(timestamp)
            ''', (user_id, cutoff_date))
            
            trend_data = cursor.fetchall()
            conn.close()
            
            return [dict(item) for item in trend_data]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting performance trend: {str(e)}")
            raise
    
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