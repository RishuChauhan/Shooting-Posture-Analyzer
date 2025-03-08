import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QStackedWidget, QStatusBar, QToolBar, QMessageBox,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction, QFont

from utils.constants import (
    UI_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, 
    STYLESHEET_LIGHT, STYLESHEET_DARK
)
from utils.helpers import show_info_message, show_error_message, get_icon

# Import UI component modules
from ui.live_analysis import LiveAnalysisWidget
from ui.profiles import ProfilesWidget
from ui.performance import PerformanceWidget
from ui.replay import ReplayWidget
from ui.settings import SettingsWidget
from ui.plot_3d import Plot3DWidget

# Initialize logger
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Main application window.
    Contains navigation and hosts all other UI components.
    """
    
    def __init__(self, data_manager):
        """
        Initialize the main window.
        
        Args:
            data_manager: DataManager instance for database operations
        """
        super().__init__()
        
        # Store data manager
        self.data_manager = data_manager
        
        # Current user ID (None if no user selected)
        self.current_user_id = None
        
        # Initialize UI
        self._init_ui()
        
        # Apply theme
        self._apply_theme()
        
        # Check for users on startup
        self._check_for_users()
        
        logger.info("MainWindow initialized")
    
    def _init_ui(self):

    # Set window properties
        self.setWindowTitle(UI_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(800, 600)
    
    # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
    
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
    
    # Create sidebar
        self._create_sidebar()
    
    # Create main content area
        self._create_content_area()
    
    # Create status bar - MOVED THIS UP
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    # Initialize toolbar
        self._create_toolbar()
    
    # Create timer for status updates
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
    
    # Set default page - MOVED THIS DOWN
        self._navigate('profiles')
    
    def _create_sidebar(self):
        """Create the sidebar with navigation buttons."""
        # Create sidebar widget and layout
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(250)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)
        


# With this improved version:
        title_label = QLabel("Rifle Shooting\nPosture Analyzer")  # Add line break
        title_label.setObjectName("sidebar-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))  # Slightly smaller font
        title_label.setWordWrap(True)  # Enable word wrapping
        sidebar_layout.addWidget(title_label)
        
        # Add spacer
        sidebar_layout.addSpacing(20)
        
        # Create navigation buttons
        self.nav_buttons = {}
        
        # Live Analysis button
        self.nav_buttons['live'] = QPushButton("Live Analysis")
        self.nav_buttons['live'].setObjectName("nav-button")
        self.nav_buttons['live'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['live'])
        
        # Profiles button
        self.nav_buttons['profiles'] = QPushButton("Shooter Profiles")
        self.nav_buttons['profiles'].setObjectName("nav-button")
        self.nav_buttons['profiles'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['profiles'])
        
        # Performance button
        self.nav_buttons['performance'] = QPushButton("Performance Dashboard")
        self.nav_buttons['performance'].setObjectName("nav-button")
        self.nav_buttons['performance'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['performance'])
        
        # Replay button
        self.nav_buttons['replay'] = QPushButton("Replay Analysis")
        self.nav_buttons['replay'].setObjectName("nav-button")
        self.nav_buttons['replay'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['replay'])
        
        # 3D Plot Analysis button
        self.nav_buttons['plot3d'] = QPushButton("3D Plot Analysis")
        self.nav_buttons['plot3d'].setObjectName("nav-button")
        self.nav_buttons['plot3d'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['plot3d'])

        # Settings button
        self.nav_buttons['settings'] = QPushButton("Settings")
        self.nav_buttons['settings'].setObjectName("nav-button")
        self.nav_buttons['settings'].setMinimumHeight(50)
        sidebar_layout.addWidget(self.nav_buttons['settings'])
        
        # Add vertical spacer to push content to top
        sidebar_layout.addStretch()
        
        # Current user display
        self.user_frame = QFrame()
        user_layout = QVBoxLayout(self.user_frame)
        user_layout.setContentsMargins(5, 10, 5, 10)
        
        self.user_label = QLabel("Current Shooter:")
        self.user_label.setObjectName("user-label")
        
        self.current_user_name = QLabel("None Selected")
        self.current_user_name.setObjectName("current-user")
        self.current_user_name.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        user_layout.addWidget(self.user_label)
        user_layout.addWidget(self.current_user_name)
        
        sidebar_layout.addWidget(self.user_frame)
        
        # Add sidebar to main layout
        self.main_layout.addWidget(self.sidebar)
        
        # Connect button signals
        for name, button in self.nav_buttons.items():
            button.clicked.connect(lambda checked, n=name: self._navigate(n))
    
    def _create_content_area(self):
        """Create the main content area with stacked widget."""
        # Create content widget
        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create stacked widget
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Create widgets for each page
        self.widgets = {}
        
        # Live Analysis
        self.widgets['live'] = LiveAnalysisWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['live'])
        
        # Profiles
        self.widgets['profiles'] = ProfilesWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['profiles'])
        
        # Connect profile selection signal
        self.widgets['profiles'].user_selected.connect(self.set_current_user)
        
        # Performance
        self.widgets['performance'] = PerformanceWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['performance'])
        
        # Replay
        self.widgets['replay'] = ReplayWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['replay'])
        
        # 3D Plot
        self.widgets['plot3d'] = Plot3DWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['plot3d'])

        # Settings
        self.widgets['settings'] = SettingsWidget(self.data_manager)
        self.stacked_widget.addWidget(self.widgets['settings'])
        
        # Add content to main layout
        self.main_layout.addWidget(self.content)
        
        # Set default page
        self._navigate('profiles')
    
    def _create_toolbar(self):
        """Create the application toolbar."""
        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Create actions
        # New Session action
        self.new_session_action = QAction("New Session", self)
        self.new_session_action.setStatusTip("Start a new shooting session")
        self.new_session_action.triggered.connect(self._new_session)
        self.toolbar.addAction(self.new_session_action)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # Generate Report action
        self.report_action = QAction("Generate Report", self)
        self.report_action.setStatusTip("Generate a performance report")
        self.report_action.triggered.connect(self._generate_report)
        self.toolbar.addAction(self.report_action)
        
        # Add separator
        self.toolbar.addSeparator()
        
        # Help action
        self.help_action = QAction("Help", self)
        self.help_action.setStatusTip("Show help")
        self.help_action.triggered.connect(self._show_help)
        self.toolbar.addAction(self.help_action)
        
        # About action
        self.about_action = QAction("About", self)
        self.about_action.setStatusTip("Show information about the application")
        self.about_action.triggered.connect(self._show_about)
        self.toolbar.addAction(self.about_action)
        
        # Update action states
        self._update_action_states()
    
    def _navigate(self, page_name):
        """Navigate to a specific page.

        Args:
            page_name: Name of the page to navigate to
        """
        # Create a status bar if it doesn't exist yet
        if not hasattr(self, 'status_bar'):
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)

        if page_name not in self.widgets:
            logger.error(f"Page '{page_name}' not found")
            return

        # Get index of the widget in the stacked widget
        index = self.stacked_widget.indexOf(self.widgets[page_name])

        # Set the current index
        self.stacked_widget.setCurrentIndex(index)

        # Update button styles
        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.setProperty("active", True)
            else:
                button.setProperty("active", False)

            # Force style update
            button.style().unpolish(button)
            button.style().polish(button)

        # Update status bar
        self.status_bar.showMessage(f"Viewing {page_name.replace('_', ' ').title()}")

        # Update action states
        self._update_action_states()

        # If navigating to profiles, refresh the data
        if page_name == 'profiles':
            self.widgets['profiles'].refresh_data()

        # If navigating to performance, update with current user and refresh data
        if page_name == 'performance' and self.current_user_id:
            self.widgets['performance'].set_user(self.current_user_id)

        # If navigating to replay, update with current user and refresh data
        if page_name == 'replay' and self.current_user_id:
            self.widgets['replay'].set_user(self.current_user_id)

        # If navigating to 3D Plot, update with current user and refresh data
        if page_name == 'plot3d' and self.current_user_id:
            logger.info("Refreshing 3D Plot Analysis with current user")
            self.widgets['plot3d'].set_user(self.current_user_id)

            # Force refresh of session data if available
            if hasattr(self.widgets['plot3d'], 'current_session_id') and self.widgets['plot3d'].current_session_id:
                logger.info(f"Forcing reload of session {self.widgets['plot3d'].current_session_id}")
                self.widgets['plot3d']._load_shots()

        logger.info(f"Navigated to {page_name}")
    
    def set_current_user(self, user_id, user_name):
        """
        Set the current user.
        
        Args:
            user_id: User ID
            user_name: User name
        """
        self.current_user_id = user_id
        self.current_user_name.setText(user_name)
        
        # Update widgets with current user
        self.widgets['live'].set_user(user_id)
        self.widgets['performance'].set_user(user_id)
        self.widgets['replay'].set_user(user_id)
        self.widgets['plot3d'].set_user(user_id)
        
        logger.info(f"Set current user to {user_name} (ID: {user_id})")
        
        # Update action states
        self._update_action_states()
    
    def _update_action_states(self):
    
    # Skip if actions don't exist yet
        if not hasattr(self, 'new_session_action') or not hasattr(self, 'report_action'):
            return
        
    # Enable/disable actions that require a user to be selected
        user_selected = self.current_user_id is not None
        self.new_session_action.setEnabled(user_selected)
        self.report_action.setEnabled(user_selected)
    
    def _update_status(self):
        """Update status bar with current information."""
        # This is called by the timer
        # In a real application, you might show system status, current user, etc.
        pass
    
    def _apply_theme(self):
        """Apply the current theme stylesheet."""
        # Get theme setting from database
        theme = self.data_manager.get_app_setting('theme') or 'light'
        
        if theme == 'dark':
            self.setStyleSheet(STYLESHEET_DARK)
        else:
            self.setStyleSheet(STYLESHEET_LIGHT)
    
    def _check_for_users(self):
        """Check if any users exist in the database."""
        users = self.data_manager.get_all_users()
        
        if not users:
            # No users exist, show a message and navigate to profiles
            QMessageBox.information(
                self, 
                "Welcome", 
                "Welcome to the Rifle Shooting Posture Analyzer!\n\n"
                "To get started, please create a shooter profile."
            )
            self._navigate('profiles')
    
    def _new_session(self):
        """Start a new shooting session."""
        if self.current_user_id is None:
            QMessageBox.warning(
                self, 
                "No Shooter Selected", 
                "Please select a shooter profile before starting a new session."
            )
            self._navigate('profiles')
            return
        
        # Navigate to live analysis
        self._navigate('live')
        
        # Trigger new session in live analysis widget
        self.widgets['live'].start_new_session()
    
    def _generate_report(self):
        """Generate a performance report."""
        if self.current_user_id is None:
            QMessageBox.warning(
                self, 
                "No Shooter Selected", 
                "Please select a shooter profile before generating a report."
            )
            self._navigate('profiles')
            return
        
        # Navigate to performance dashboard
        self._navigate('performance')
        
        # Trigger report generation in performance widget
        self.widgets['performance'].generate_report()
    
    def _show_help(self):
        """Show help information."""
        QMessageBox.information(
            self, 
            "Help", 
            "Rifle Shooting Posture Analyzer Help\n\n"
            "1. Create a shooter profile in 'Shooter Profiles'\n"
            "2. Select a profile and start a new session\n"
            "3. Use the live analysis to monitor and improve your posture\n"
            "4. View performance reports in the 'Performance Dashboard'\n"
            "5. Review recorded sessions in 'Replay & Analysis'\n"
            "6. Analyze 3D plots in '3D Plot Analysis'\n"
            "7. Adjust application settings in 'Settings'"
        )
    
    def _show_about(self):
        """Show about information."""
        QMessageBox.about(
            self, 
            "About", 
            f"{UI_TITLE}\n\n"
            "A computer vision application for analyzing and improving "
            "rifle shooting posture.\n\n"
            "Using OpenCV, MediaPipe, and Fuzzy Logic for posture analysis."
        )
    
    def closeEvent(self, event):
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        # Clean up resources
        for widget in self.widgets.values():
            if hasattr(widget, 'cleanup') and callable(widget.cleanup):
                widget.cleanup()
        
        logger.info("Application closing")
        event.accept()