#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Schema Update Utility

This script updates the session_data table to store file paths
instead of binary data for better performance and database size.

Author: Claude
Date: March 7, 2025
"""

import os
import sqlite3
import logging
import sys

# Initialize logger
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db_schema_updater")

# Database path - adjust if needed
DB_PATH = os.path.join(os.path.expanduser("~"), ".shooting_analyzer", "data", "shooting_analyzer.db")

def update_schema():
    """Update the database schema to use file paths instead of BLOBs."""
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found at {DB_PATH}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if frame_path column already exists
        cursor.execute("PRAGMA table_info(session_data)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'frame_path' not in columns:
            logger.info("Adding frame_path column to session_data table...")
            
            # Create a backup first
            backup_path = DB_PATH + ".backup"
            with open(DB_PATH, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            logger.info(f"Database backup created at {backup_path}")
            
            # Add the new column for file paths
            cursor.execute('''
            ALTER TABLE session_data ADD COLUMN frame_path TEXT
            ''')
            
            # If frame_data column exists, we need to migrate data
            # But since it doesn't exist yet in our case, we skip this step
            
            logger.info("Schema updated successfully")
        else:
            logger.info("frame_path column already exists.")
        
        # Create the required directories for storing frames and videos
        data_dir = os.path.dirname(DB_PATH)
        frames_dir = os.path.join(data_dir, "frames")
        videos_dir = os.path.join(data_dir, "videos")
        
        for directory in [frames_dir, videos_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            else:
                logger.info(f"Directory already exists: {directory}")
        
        conn.commit()
        conn.close()
        
        return True
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error updating schema: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database schema update...")
    
    if update_schema():
        logger.info("Database schema updated successfully!")
    else:
        logger.error("Failed to update database schema.")
        sys.exit(1)