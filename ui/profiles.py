#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profiles Module

This module implements the user profile management screen
for creating, editing, and selecting shooter profiles.

Author: Claude
Date: March 6, 2025
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout, QMessageBox,
    QDialog, QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon

from utils.helpers import (
    show_error_message, show_info_message, show_question_message
)

# Initialize logger
logger = logging.getLogger(__name__)

class UserDialog(QDialog):
    """Dialog for creating or editing a user profile."""
    
    def __init__(self, parent=None, user_data=None):
        """
        Initialize the user dialog.
        
        Args:
            parent: Parent widget
            user_data: User data for editing (None for new user)
        """
        super().__init__(parent)
        
        self.user_data = user_data
        self.is_edit_mode = user_data is not None
        
        if self.is_edit_mode:
            self.setWindowTitle("Edit Shooter Profile")
        else:
            self.setWindowTitle("Create New Shooter Profile")
            
        self.setMinimumWidth(400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create form
        form = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit()
        if self.is_edit_mode and self.user_data['name']:
            self.name_input.setText(self.user_data['name'])
        form.addRow("Name:", self.name_input)
        
        # Email field
        self.email_input = QLineEdit()
        if self.is_edit_mode and self.user_data['email']:
            self.email_input.setText(self.user_data['email'])
        form.addRow("Email:", self.email_input)
        
        # Role field
        self.role_combo = QComboBox()
        self.role_combo.addItem("Shooter", "shooter")
        self.role_combo.addItem("Coach", "coach")
        
        if self.is_edit_mode and self.user_data['role']:
            index = self.role_combo.findData(self.user_data['role'])
            if index >= 0:
                self.role_combo.setCurrentIndex(index)
                
        form.addRow("Role:", self.role_combo)
        
        layout.addLayout(form)
        
        # Add button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_user_data(self):
        """
        Get user data from the dialog.
        
        Returns:
            Dictionary with user data
        """
        return {
            'name': self.name_input.text().strip(),
            'email': self.email_input.text().strip(),
            'role': self.role_combo.currentData()
        }
    
    def validate(self):
        """
        Validate user input.
        
        Returns:
            True if valid, False otherwise
        """
        # Check for required fields
        if not self.name_input.text().strip():
            show_error_message(self, "Validation Error", "Name is required.")
            return False
        
        return True
    
    def accept(self):
        """Handle dialog acceptance."""
        if self.validate():
            super().accept()

class ProfilesWidget(QWidget):
    """
    Widget for user profile management screen.
    Allows creating, editing, and selecting shooter profiles.
    """
    
    # Signal emitted when a user is selected
    user_selected = pyqtSignal(int, str)
    
    def __init__(self, data_manager):
        """
        Initialize the profiles widget.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Current selection
        self.selected_user_id = None
        
        # Initialize UI
        self._init_ui()
        
        # Load data
        self.refresh_data()
        
        logger.info("ProfilesWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title_label = QLabel("Shooter Profiles")
        title_label.setObjectName("page-title")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel(
            "Create and manage shooter profiles. Select a profile to use for analysis sessions."
        )
        desc_label.setWordWrap(True)
        self.main_layout.addWidget(desc_label)
        
        # Create top controls
        controls_layout = QHBoxLayout()
        
        self.new_user_btn = QPushButton("New Profile")
        self.new_user_btn.clicked.connect(self._create_user)
        controls_layout.addWidget(self.new_user_btn)
        
        self.edit_user_btn = QPushButton("Edit Profile")
        self.edit_user_btn.clicked.connect(self._edit_user)
        self.edit_user_btn.setEnabled(False)
        controls_layout.addWidget(self.edit_user_btn)
        
        self.delete_user_btn = QPushButton("Delete Profile")
        self.delete_user_btn.clicked.connect(self._delete_user)
        self.delete_user_btn.setEnabled(False)
        controls_layout.addWidget(self.delete_user_btn)
        
        controls_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.main_layout.addLayout(controls_layout)
        
        # Create user table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Name", "Email", "Role", "Created"])
        
        # Set column properties
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect selection signal
        self.user_table.itemSelectionChanged.connect(self._selection_changed)
        
        # Connect double-click signal
        self.user_table.cellDoubleClicked.connect(self._user_double_clicked)
        
        self.main_layout.addWidget(self.user_table)
        
        # Create selected user details group
        self.details_group = QGroupBox("Selected Profile")
        details_layout = QVBoxLayout(self.details_group)
        
        # Details content
        self.details_content = QWidget()
        form_layout = QFormLayout(self.details_content)
        
        self.details_name = QLabel("No profile selected")
        self.details_email = QLabel("")
        self.details_role = QLabel("")
        self.details_created = QLabel("")
        
        form_layout.addRow("Name:", self.details_name)
        form_layout.addRow("Email:", self.details_email)
        form_layout.addRow("Role:", self.details_role)
        form_layout.addRow("Created:", self.details_created)
        
        details_layout.addWidget(self.details_content)
        
        # Select profile button
        select_layout = QHBoxLayout()
        select_layout.addStretch()
        
        self.select_btn = QPushButton("Select Profile")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.setMinimumWidth(200)
        self.select_btn.clicked.connect(self._select_user)
        self.select_btn.setEnabled(False)
        
        select_layout.addWidget(self.select_btn)
        select_layout.addStretch()
        
        details_layout.addLayout(select_layout)
        
        self.main_layout.addWidget(self.details_group)
    
    def refresh_data(self):
        """Refresh data from the database."""
        try:
            # Get all users
            users = self.data_manager.get_all_users()
            
            # Update table
            self.user_table.setRowCount(0)
            
            for user in users:
                row = self.user_table.rowCount()
                self.user_table.insertRow(row)
                
                # Create items
                id_item = QTableWidgetItem(str(user['user_id']))
                name_item = QTableWidgetItem(user['name'])
                email_item = QTableWidgetItem(user['email'] or "")
                role_item = QTableWidgetItem(user['role'].title())
                created_item = QTableWidgetItem(user['created_at'])
                
                # Set items as non-editable
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                created_item.setFlags(created_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Add items to table
                self.user_table.setItem(row, 0, id_item)
                self.user_table.setItem(row, 1, name_item)
                self.user_table.setItem(row, 2, email_item)
                self.user_table.setItem(row, 3, role_item)
                self.user_table.setItem(row, 4, created_item)
            
            # Clear selection
            self.user_table.clearSelection()
            self._clear_details()
            
            logger.info(f"Loaded {len(users)} users")
            
        except Exception as e:
            logger.error(f"Error refreshing data: {str(e)}")
            show_error_message(self, "Data Error", 
                              f"Failed to load user profiles: {str(e)}")
    
    def _selection_changed(self):
        """Handle selection change in the user table."""
        selected_items = self.user_table.selectedItems()
        
        if not selected_items:
            self._clear_details()
            return
        
        # Get the first selected row
        row = selected_items[0].row()
        
        # Get user ID from the first column
        user_id_item = self.user_table.item(row, 0)
        if not user_id_item:
            self._clear_details()
            return
        
        user_id = int(user_id_item.text())
        
        # Load user details
        self._load_user_details(user_id)
    
    def _load_user_details(self, user_id):
        """
        Load and display user details.
        
        Args:
            user_id: User ID to load
        """
        try:
            # Get user data
            user = self.data_manager.get_user(user_id)
            
            if not user:
                self._clear_details()
                return
            
            # Store selected user ID
            self.selected_user_id = user_id
            
            # Update details
            self.details_name.setText(user['name'])
            self.details_email.setText(user['email'] or "N/A")
            self.details_role.setText(user['role'].title())
            self.details_created.setText(user['created_at'])
            
            # Enable buttons
            self.edit_user_btn.setEnabled(True)
            self.delete_user_btn.setEnabled(True)
            self.select_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error loading user details: {str(e)}")
            self._clear_details()
    
    def _clear_details(self):
        """Clear user details display."""
        self.selected_user_id = None
        
        self.details_name.setText("No profile selected")
        self.details_email.setText("")
        self.details_role.setText("")
        self.details_created.setText("")
        
        # Disable buttons
        self.edit_user_btn.setEnabled(False)
        self.delete_user_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
    
    def _create_user(self):
        """Create a new user profile."""
        dialog = UserDialog(self)
        
        if dialog.exec():
            try:
                # Get user data from dialog
                user_data = dialog.get_user_data()
                
                # Create user in database
                user_id = self.data_manager.create_user(
                    user_data['name'],
                    user_data['email'],
                    user_data['role']
                )
                
                # Refresh data
                self.refresh_data()
                
                # Show success message
                show_info_message(self, "Profile Created", 
                                 f"Profile '{user_data['name']}' created successfully.")
                
                # Select the new user
                self._find_and_select_user(user_id)
                
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                show_error_message(self, "Creation Error", 
                                  f"Failed to create profile: {str(e)}")
    
    def _edit_user(self):
        """Edit the selected user profile."""
        if not self.selected_user_id:
            show_error_message(self, "No Selection", 
                              "Please select a profile to edit.")
            return
        
        try:
            # Get user data
            user = self.data_manager.get_user(self.selected_user_id)
            
            if not user:
                show_error_message(self, "User Not Found", 
                                  "The selected profile could not be found.")
                self.refresh_data()
                return
            
            # Create and show dialog
            dialog = UserDialog(self, user)
            
            if dialog.exec():
                # Get updated data
                updated_data = dialog.get_user_data()
                
                # Update user in database
                success = self.data_manager.update_user(
                    self.selected_user_id,
                    updated_data['name'],
                    updated_data['email'],
                    updated_data['role']
                )
                
                if success:
                    # Refresh data
                    self.refresh_data()
                    
                    # Show success message
                    show_info_message(self, "Profile Updated", 
                                     f"Profile '{updated_data['name']}' updated successfully.")
                    
                    # Reselect the user
                    self._find_and_select_user(self.selected_user_id)
                else:
                    show_error_message(self, "Update Error", 
                                      "Failed to update profile. Profile not found.")
                
        except Exception as e:
            logger.error(f"Error editing user: {str(e)}")
            show_error_message(self, "Edit Error", 
                              f"Failed to edit profile: {str(e)}")
    
    def _delete_user(self):
        """Delete the selected user profile."""
        if not self.selected_user_id:
            show_error_message(self, "No Selection", 
                              "Please select a profile to delete.")
            return
        
        try:
            # Get user data
            user = self.data_manager.get_user(self.selected_user_id)
            
            if not user:
                show_error_message(self, "User Not Found", 
                                  "The selected profile could not be found.")
                self.refresh_data()
                return
            
            # Confirm deletion
            confirmed = show_question_message(
                self, 
                "Confirm Deletion", 
                f"Are you sure you want to delete the profile '{user['name']}'?\n\n"
                "This will also delete all sessions and data associated with this profile."
            )
            
            if not confirmed:
                return
            
            # Delete user from database
            success = self.data_manager.delete_user(self.selected_user_id)
            
            if success:
                # Refresh data
                self.refresh_data()
                
                # Show success message
                show_info_message(self, "Profile Deleted", 
                                 f"Profile '{user['name']}' deleted successfully.")
            else:
                show_error_message(self, "Delete Error", 
                                  "Failed to delete profile. Profile not found.")
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            show_error_message(self, "Delete Error", 
                              f"Failed to delete profile: {str(e)}")
    
    def _select_user(self):
        """Select the current user profile for use."""
        if not self.selected_user_id:
            show_error_message(self, "No Selection", 
                              "Please select a profile first.")
            return
        
        try:
            # Get user data
            user = self.data_manager.get_user(self.selected_user_id)
            
            if not user:
                show_error_message(self, "User Not Found", 
                                  "The selected profile could not be found.")
                self.refresh_data()
                return
            
            # Emit signal with user ID and name
            self.user_selected.emit(self.selected_user_id, user['name'])
            
            # Show success message
            show_info_message(self, "Profile Selected", 
                             f"Profile '{user['name']}' selected successfully.")
            
        except Exception as e:
            logger.error(f"Error selecting user: {str(e)}")
            show_error_message(self, "Selection Error", 
                              f"Failed to select profile: {str(e)}")
    
    def _user_double_clicked(self, row, column):
        """
        Handle double-click on a user in the table.
        
        Args:
            row: Row index
            column: Column index
        """
        # Get user ID from the first column
        user_id_item = self.user_table.item(row, 0)
        if not user_id_item:
            return
        
        user_id = int(user_id_item.text())
        
        # Load user details
        self._load_user_details(user_id)
        
        # Select the user
        self._select_user()
    
    def _find_and_select_user(self, user_id):
        """
        Find and select a user in the table by ID.
        
        Args:
            user_id: User ID to find and select
        """
        # Find the row with the user ID
        for row in range(self.user_table.rowCount()):
            id_item = self.user_table.item(row, 0)
            if id_item and int(id_item.text()) == user_id:
                # Select the row
                self.user_table.selectRow(row)
                break