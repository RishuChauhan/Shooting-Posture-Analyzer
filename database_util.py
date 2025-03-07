#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Utility Script

This script provides utilities for managing the shooting analyzer database,
including viewing, deleting, and cleaning up data.

Usage:
  python database_util.py [command] [options]

Commands:
  list-users            List all users in the database
  list-sessions USER_ID List all sessions for a specific user
  delete-user USER_ID   Delete a user and all their associated data
  delete-session SES_ID Delete a specific session
  delete-all-data       Delete all data (users, sessions, etc.) but keep settings
  view-tables           View all tables in the database
  vacuum                Optimize database size

Author: Claude
Date: March 6, 2025
"""

import os
import sys
import sqlite3
import argparse
import datetime

# Default database path
DB_PATH = os.path.join(os.path.expanduser("~"), ".shooting_analyzer", "data", "shooting_analyzer.db")

def connect_db(db_path):
    """Connect to the database and return connection and cursor."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    cursor = conn.cursor()
    return conn, cursor

def list_users(db_path):
    """List all users in the database."""
    try:
        conn, cursor = connect_db(db_path)
        cursor.execute("SELECT * FROM users ORDER BY name")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"\nUsers in database ({len(users)} total):")
        print("-" * 80)
        print(f"{'ID':<5} {'Name':<20} {'Email':<25} {'Role':<10} {'Created':<20}")
        print("-" * 80)
        
        for user in users:
            print(f"{user['user_id']:<5} {user['name']:<20} {(user['email'] or 'N/A'):<25} "
                  f"{user['role']:<10} {user['created_at']:<20}")
        
        conn.close()
    except Exception as e:
        print(f"Error listing users: {e}")

def list_sessions(db_path, user_id):
    """List all sessions for a specific user."""
    try:
        conn, cursor = connect_db(db_path)
        
        # First verify the user exists
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"User with ID {user_id} not found.")
            conn.close()
            return
        
        # Get the sessions
        cursor.execute("""
            SELECT session_id, name, timestamp, duration, overall_score, posture_quality 
            FROM sessions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        """, (user_id,))
        
        sessions = cursor.fetchall()
        
        if not sessions:
            print(f"No sessions found for user {user['name']} (ID: {user_id}).")
            conn.close()
            return
        
        print(f"\nSessions for user {user['name']} (ID: {user_id}) - {len(sessions)} total:")
        print("-" * 100)
        print(f"{'ID':<5} {'Name':<25} {'Date':<20} {'Duration':<10} {'Score':<8} {'Quality':<15}")
        print("-" * 100)
        
        for session in sessions:
            duration_str = f"{session['duration']} sec" if session['duration'] else "N/A"
            score_str = f"{session['overall_score']:.1f}" if session['overall_score'] else "N/A"
            
            print(f"{session['session_id']:<5} {session['name'][:25]:<25} "
                  f"{session['timestamp']:<20} {duration_str:<10} {score_str:<8} "
                  f"{(session['posture_quality'] or 'N/A'):<15}")
        
        conn.close()
    except Exception as e:
        print(f"Error listing sessions: {e}")

def delete_user(db_path, user_id, confirm=True):
    """Delete a user and all associated data."""
    try:
        conn, cursor = connect_db(db_path)
        
        # First verify the user exists
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"User with ID {user_id} not found.")
            conn.close()
            return
        
        # Get session count
        cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE user_id = ?", (user_id,))
        session_count = cursor.fetchone()['count']
        
        if confirm:
            print(f"\nYou are about to delete user '{user['name']}' (ID: {user_id}) and {session_count} associated sessions.")
            response = input("Are you sure you want to proceed? (yes/no): ")
            
            if response.lower() not in ('yes', 'y'):
                print("Operation cancelled.")
                conn.close()
                return
        
        # Start deletion process
        conn.execute('BEGIN TRANSACTION')
        
        try:
            # Get all sessions for this user
            cursor.execute("SELECT session_id FROM sessions WHERE user_id = ?", (user_id,))
            sessions = cursor.fetchall()
            
            # Delete session data for each session
            for session in sessions:
                session_id = session['session_id']
                cursor.execute("DELETE FROM session_data WHERE session_id = ?", (session_id,))
                print(f"Deleted data for session ID {session_id}")
            
            # Delete all sessions
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            print(f"Deleted {session_count} sessions for user ID {user_id}")
            
            # Delete user settings
            cursor.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
            
            # Delete the user
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            print(f"Deleted user '{user['name']}' (ID: {user_id})")
            
            # Commit transaction
            conn.commit()
            print("All data successfully deleted.")
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error during deletion: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Error deleting user: {e}")

def delete_session(db_path, session_id, confirm=True):
    """Delete a specific session and its data."""
    try:
        conn, cursor = connect_db(db_path)
        
        # First verify the session exists
        cursor.execute("""
            SELECT s.session_id, s.name, u.name as user_name, u.user_id 
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.session_id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        
        if not session:
            print(f"Session with ID {session_id} not found.")
            conn.close()
            return
        
        if confirm:
            print(f"\nYou are about to delete session '{session['name']}' (ID: {session_id}) "
                  f"belonging to user '{session['user_name']}' (ID: {session['user_id']}).")
            response = input("Are you sure you want to proceed? (yes/no): ")
            
            if response.lower() not in ('yes', 'y'):
                print("Operation cancelled.")
                conn.close()
                return
        
        # Start deletion process
        conn.execute('BEGIN TRANSACTION')
        
        try:
            # Delete session data
            cursor.execute("DELETE FROM session_data WHERE session_id = ?", (session_id,))
            data_count = cursor.rowcount
            
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            
            # Commit transaction
            conn.commit()
            print(f"Deleted session '{session['name']}' (ID: {session_id}) and {data_count} data frames.")
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error during deletion: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Error deleting session: {e}")

def delete_all_data(db_path, confirm=True):
    """Delete all users, sessions and data but keep settings."""
    try:
        conn, cursor = connect_db(db_path)
        
        # Get counts for confirmation
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM sessions")
        session_count = cursor.fetchone()['count']
        
        if confirm:
            print(f"\n⚠️ WARNING: You are about to delete ALL DATA from the database!")
            print(f"This will remove {user_count} users and {session_count} sessions.")
            print("Application settings will be preserved.")
            print("This action CANNOT be undone!")
            response = input("Type 'DELETE ALL DATA' to confirm: ")
            
            if response != "DELETE ALL DATA":
                print("Operation cancelled.")
                conn.close()
                return
        
        # Start deletion process
        conn.execute('BEGIN TRANSACTION')
        
        try:
            # Delete session data
            cursor.execute("DELETE FROM session_data")
            data_count = cursor.rowcount
            
            # Delete sessions
            cursor.execute("DELETE FROM sessions")
            
            # Delete user settings
            cursor.execute("DELETE FROM settings")
            
            # Delete users
            cursor.execute("DELETE FROM users")
            
            # Commit transaction
            conn.commit()
            print(f"Deleted {user_count} users, {session_count} sessions, and {data_count} data frames.")
            print("All user data has been removed from the database.")
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error during deletion: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Error deleting all data: {e}")

def view_tables(db_path):
    """View all tables in the database and their row counts."""
    try:
        conn, cursor = connect_db(db_path)
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("\nDatabase Tables:")
        print("-" * 50)
        print(f"{'Table Name':<25} {'Row Count':<10} {'Size Estimate':<15}")
        print("-" * 50)
        
        for table in tables:
            table_name = table['name']
            
            # Skip sqlite_sequence table
            if table_name == 'sqlite_sequence':
                continue
                
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']
            
            # Get a size estimate
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                row = cursor.fetchone()
                row_size = sum(len(str(x)) for x in dict(row).values()) / 1024  # KB
                size_estimate = f"{(row_size * count):.2f} KB"
            else:
                size_estimate = "0 KB"
            
            print(f"{table_name:<25} {count:<10} {size_estimate:<15}")
        
        # Get database file size
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        print("-" * 50)
        print(f"Total database file size: {db_size:.2f} MB")
        
        conn.close()
    except Exception as e:
        print(f"Error viewing tables: {e}")

def vacuum_database(db_path):
    """Optimize database size by removing unused space."""
    try:
        # Get current size
        current_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        
        conn, cursor = connect_db(db_path)
        
        print(f"Current database size: {current_size:.2f} MB")
        print("Optimizing database size...")
        
        # Run VACUUM
        cursor.execute("VACUUM")
        conn.close()
        
        # Get new size
        new_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        saved = current_size - new_size
        
        print(f"Optimization complete!")
        print(f"New database size: {new_size:.2f} MB")
        print(f"Space saved: {saved:.2f} MB ({(saved/current_size)*100:.1f}%)")
        
    except Exception as e:
        print(f"Error optimizing database: {e}")

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description="Database Utility for Shooting Analyzer")
    
    # Add global option for database path
    parser.add_argument("--db", help="Path to the database file", default=DB_PATH)
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List users command
    subparsers.add_parser('list-users', help='List all users in the database')
    
    # List sessions command
    sessions_parser = subparsers.add_parser('list-sessions', help='List all sessions for a specific user')
    sessions_parser.add_argument('user_id', type=int, help='User ID')
    
    # Delete user command
    delete_user_parser = subparsers.add_parser('delete-user', help='Delete a user and all associated data')
    delete_user_parser.add_argument('user_id', type=int, help='User ID to delete')
    delete_user_parser.add_argument('--no-confirm', action='store_true', 
                                   help='Skip confirmation prompt')
    
    # Delete session command
    delete_session_parser = subparsers.add_parser('delete-session', help='Delete a specific session')
    delete_session_parser.add_argument('session_id', type=int, help='Session ID to delete')
    delete_session_parser.add_argument('--no-confirm', action='store_true', 
                                      help='Skip confirmation prompt')
    
    # Delete all data command
    delete_all_parser = subparsers.add_parser('delete-all-data', 
                                             help='Delete all users and sessions but keep settings')
    delete_all_parser.add_argument('--no-confirm', action='store_true', 
                                  help='Skip confirmation prompt (DANGEROUS)')
    
    # View tables command
    subparsers.add_parser('view-tables', help='View all tables in the database')
    
    # Vacuum command
    subparsers.add_parser('vacuum', help='Optimize database size')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db):
        print(f"Error: Database file not found at {args.db}")
        return 1
    
    # Execute the appropriate command
    if args.command == 'list-users':
        list_users(args.db)
    elif args.command == 'list-sessions':
        list_sessions(args.db, args.user_id)
    elif args.command == 'delete-user':
        delete_user(args.db, args.user_id, not args.no_confirm)
    elif args.command == 'delete-session':
        delete_session(args.db, args.session_id, not args.no_confirm)
    elif args.command == 'delete-all-data':
        delete_all_data(args.db, not args.no_confirm)
    elif args.command == 'view-tables':
        view_tables(args.db)
    elif args.command == 'vacuum':
        vacuum_database(args.db)
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())