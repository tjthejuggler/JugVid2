#!/usr/bin/env python3
import os
import cv2
import numpy as np
import time
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu, QToolBar,
    QStatusBar, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QLabel, QFileDialog, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QMessageBox, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QScrollArea, QSlider
)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QIcon, QAction, QPainter, QPen, QColor, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize, QPoint, pyqtSignal, pyqtSlot, QDateTime

# Application's module imports
from juggling_tracker.modules.ball_definer import BallDefiner
from juggling_tracker.modules.ball_profile_manager import BallProfileManager
from .simple_tracking_window import SimpleTrackingWindow
from .imu_monitoring_window import IMUMonitoringWindow
from .video_feed_manager import VideoFeedManager

class MainWindow(QMainWindow):
    """
    Main window for the Juggling Tracker application.
    
    This class provides a professional Qt-based UI for the application, including:
    - Native window appearance with proper menu structure
    - Standard toolbar with common actions
    - Qt's widget system for layout
    - Window state persistence
    - Keyboard shortcuts
    - Status bar for feedback
    """
    
    def __init__(self, app=None, config_dir=None):
        """
        Initialize the main window.
        
        Args:
            app: Reference to the main application
            config_dir (str): Directory to save configuration files
        """
        super().__init__()
        
        # Store references
        self.app = app
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Set window properties
        self.setWindowTitle("Juggling Tracker")
        self.setMinimumSize(1280, 720)
        
        # Initialize UI state
        self.calibration_mode = False
        self.calibration_ball_name = ""
        self.calibration_samples = 0
        self.calibration_max_samples = 30
        self.calibration_start_time = 0
        self.calibration_timeout = 10  # seconds
        
        # Ball definition state
        self.is_defining_ball_mode = False
        self.defining_roi_start_pt = None
        self.defining_roi_current_rect = None  # Store as (x,y,w,h) for drawing
        
        # Initialize display options
        self.show_depth = False
        self.show_masks = False
        self.show_color = True  # Color video feed (always shown by default)
        self.debug_mode = False
        self.show_fps = True
        self.show_extension_results = True
        self.show_simple_tracking = True  # Simple tracking overlay
        self.show_simple_tracking_mask = False  # Simple tracking mask view
        
        # Initialize tracked balls panel data
        self.tracked_balls_data = []
        
        # Initialize simple tracking window reference
        self.simple_tracking_window = None
        
        # Initialize IMU monitoring window reference
        self.imu_monitoring_window = None

        # Feed source state
        self.current_feed_mode = 'live' # 'live' or 'playback'
        self.current_video_path = None
        self.is_app_recording = False # Tracks app's recording state
        
        # Set up the UI
        self.setup_ui()
        
        # Load window state
        self.load_window_state()
        
        # Set up timer for UI updates with adaptive rate
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(50)  # Start at 20 FPS for UI updates (less aggressive)
        
        # Performance monitoring for adaptive UI updates
        self._ui_update_count = 0
        self._last_ui_performance_check = time.time()
        
        # IMU updates are now handled by the main update_ui timer to prevent lag
        # No separate high-frequency timer needed
        
        # Connect ball profile buttons if app is available
        if self.app:
            if hasattr(self.app, 'save_ball_profiles'):
                self.save_balls_button.clicked.connect(self.app.save_ball_profiles)
            if hasattr(self.app, 'load_ball_profiles'):
                self.load_balls_button.clicked.connect(self.app.load_ball_profiles)
    
    def setup_ui(self):
        """
        Set up the user interface.
        """
        # Create central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create video feed manager
        self.video_feed_manager = VideoFeedManager(self)
        self.video_feed_manager.feeds_changed.connect(self.on_feeds_changed)
        
        # Add video feed manager to main layout
        self.main_layout.addWidget(self.video_feed_manager)
        
        # Keep reference to old video_label for compatibility during transition
        self.video_label = None
        
        # Create controls layout for ball definition
        self.ball_controls_layout = QHBoxLayout()
        self.ball_controls_layout.setContentsMargins(5, 5, 5, 5)
        self.ball_controls_layout.setSpacing(5)
        
        # Add new button for "New Ball"
        self.new_ball_button = QPushButton("New Ball")
        self.new_ball_button.clicked.connect(self.toggle_define_ball_mode)
        self.ball_controls_layout.addWidget(self.new_ball_button)
        
        # Add Save/Load Ball Set buttons
        self.save_balls_button = QPushButton("Save Ball Set")
        self.ball_controls_layout.addWidget(self.save_balls_button)
        
        self.load_balls_button = QPushButton("Load Ball Set")
        self.ball_controls_layout.addWidget(self.load_balls_button)
        
        # Add a list widget to display defined balls
        self.defined_balls_list = QListWidget()
        self.defined_balls_list.setMaximumHeight(150)
        
        # Create a container for ball controls and list
        self.ball_controls_container = QWidget()
        ball_container_layout = QVBoxLayout(self.ball_controls_container)
        ball_container_layout.setContentsMargins(0, 0, 0, 0)
        ball_container_layout.addLayout(self.ball_controls_layout)
        ball_container_layout.addWidget(self.defined_balls_list)
        
        # Create tracked balls panel
        self.tracked_balls_panel = QGroupBox("Tracked Balls")
        self.tracked_balls_layout = QVBoxLayout()
        self.tracked_balls_panel.setLayout(self.tracked_balls_layout)
        self.tracked_balls_panel.setMaximumHeight(200)
        
        # Create a scroll area for the tracked balls panel
        self.tracked_balls_scroll = QScrollArea()
        self.tracked_balls_scroll.setWidgetResizable(True)
        self.tracked_balls_scroll.setWidget(self.tracked_balls_panel)
        
        # Create simple tracking settings button
        self.simple_tracking_settings_btn = QPushButton("Simple Tracking Settings")
        self.simple_tracking_settings_btn.clicked.connect(self.open_simple_tracking_settings)
        
        # Create Feed Source GroupBox
        self.feed_source_group = QGroupBox("Feed Source")
        self.feed_source_layout = QFormLayout() # Using QFormLayout for label-widget pairs

        self.feed_mode_combo = QComboBox()
        self.feed_mode_combo.addItems(["Live Feed (Camera)", "Recorded Feed (Video)", "JugVid2cpp 3D Tracking"])
        self.feed_mode_combo.currentIndexChanged.connect(self.on_feed_mode_changed)
        self.feed_source_layout.addRow("Feed Mode:", self.feed_mode_combo)

        self.select_video_button = QPushButton("Select Video File...")
        self.select_video_button.clicked.connect(self.select_video_file)
        self.select_video_button.setEnabled(False) # Initially disabled for Live Feed
        self.video_path_label = QLabel("No video selected")
        self.video_path_label.setWordWrap(True)
        
        video_file_layout = QHBoxLayout()
        video_file_layout.addWidget(self.select_video_button)
        video_file_layout.addWidget(self.video_path_label)
        self.feed_source_layout.addRow(video_file_layout)
        
        self.feed_source_group.setLayout(self.feed_source_layout)

        # Create Recording GroupBox
        self.recording_group = QGroupBox("Recording (RealSense .bag)")
        self.recording_layout = QFormLayout()

        self.start_record_button = QPushButton("Start Recording")
        self.start_record_button.clicked.connect(self.handle_start_recording)
        self.stop_record_button = QPushButton("Stop Recording")
        self.stop_record_button.clicked.connect(self.handle_stop_recording)
        self.stop_record_button.setEnabled(False)

        self.recording_status_label = QLabel("Status: Not Recording")
        self.recording_status_label.setWordWrap(True)

        record_buttons_layout = QHBoxLayout()
        record_buttons_layout.addWidget(self.start_record_button)
        record_buttons_layout.addWidget(self.stop_record_button)
        
        self.recording_layout.addRow(record_buttons_layout)
        self.recording_layout.addRow("File:", self.recording_status_label)
        self.recording_group.setLayout(self.recording_layout)
        
        # Initial check for recording controls enable state
        self.update_recording_controls_state()

        # Create Watch IMU GroupBox
        self.watch_imu_group = QGroupBox("Watch IMU Streaming")
        self.watch_imu_layout = QFormLayout()
        
        # Connection status display
        self.imu_status_label = QLabel("Status: Not Connected")
        self.imu_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.watch_imu_layout.addRow("Connection:", self.imu_status_label)
        
        # Watch IP management
        self.watch_ips_input = QLineEdit()
        self.watch_ips_input.setPlaceholderText("192.168.1.101, 192.168.1.102")
        self.watch_ips_input.textChanged.connect(self.on_watch_ips_changed)
        
        ip_buttons_layout = QHBoxLayout()
        self.discover_watches_btn = QPushButton("Discover")
        self.discover_watches_btn.clicked.connect(self.discover_watches)
        self.connect_watches_btn = QPushButton("Connect")
        self.connect_watches_btn.clicked.connect(self.connect_watches)
        self.disconnect_watches_btn = QPushButton("Disconnect")
        self.disconnect_watches_btn.clicked.connect(self.disconnect_watches)
        self.disconnect_watches_btn.setEnabled(False)
        
        ip_buttons_layout.addWidget(self.discover_watches_btn)
        ip_buttons_layout.addWidget(self.connect_watches_btn)
        ip_buttons_layout.addWidget(self.disconnect_watches_btn)
        
        ip_container = QWidget()
        ip_container_layout = QVBoxLayout(ip_container)
        ip_container_layout.setContentsMargins(0, 0, 0, 0)
        ip_container_layout.addWidget(self.watch_ips_input)
        ip_container_layout.addLayout(ip_buttons_layout)
        
        self.watch_imu_layout.addRow("Watch IPs:", ip_container)
        
        # Real-time data display (simplified for better readability)
        self.imu_data_display = QLabel("No IMU data received")
        self.imu_data_display.setWordWrap(True)
        self.imu_data_display.setMaximumHeight(60)  # Reduced height
        self.imu_data_display.setMinimumHeight(40)
        self.imu_data_display.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.imu_data_display.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; font-size: 11px;")
        self.watch_imu_layout.addRow("Live Data:", self.imu_data_display)
        
        # Watch connection details
        self.watch_details_list = QListWidget()
        self.watch_details_list.setMaximumHeight(100)
        self.watch_imu_layout.addRow("Watches:", self.watch_details_list)
        
        # Advanced IMU monitoring button
        self.open_imu_monitor_btn = QPushButton("Open Advanced IMU Monitor")
        self.open_imu_monitor_btn.clicked.connect(self.open_imu_monitoring_window)
        self.open_imu_monitor_btn.setEnabled(False)  # Enable when connected
        self.watch_imu_layout.addRow("Advanced:", self.open_imu_monitor_btn)
        
        self.watch_imu_group.setLayout(self.watch_imu_layout)

        # Create JugVid2cpp Status GroupBox
        self.jugvid2cpp_group = QGroupBox("JugVid2cpp 3D Tracking Status")
        self.jugvid2cpp_layout = QFormLayout()
        
        # Connection status display
        self.jugvid2cpp_status_label = QLabel("Status: Not Active")
        self.jugvid2cpp_status_label.setStyleSheet("color: gray; font-weight: bold;")
        self.jugvid2cpp_layout.addRow("Connection:", self.jugvid2cpp_status_label)
        
        # Ball tracking status
        self.jugvid2cpp_balls_label = QLabel("No balls detected")
        self.jugvid2cpp_balls_label.setWordWrap(True)
        self.jugvid2cpp_balls_label.setMaximumHeight(60)
        self.jugvid2cpp_balls_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.jugvid2cpp_balls_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; font-size: 11px;")
        self.jugvid2cpp_layout.addRow("Ball Data:", self.jugvid2cpp_balls_label)
        
        # Error display
        self.jugvid2cpp_error_label = QLabel("")
        self.jugvid2cpp_error_label.setWordWrap(True)
        self.jugvid2cpp_error_label.setMaximumHeight(40)
        self.jugvid2cpp_error_label.setStyleSheet("color: red; font-size: 10px;")
        self.jugvid2cpp_layout.addRow("Errors:", self.jugvid2cpp_error_label)
        
        self.jugvid2cpp_group.setLayout(self.jugvid2cpp_layout)
        
        # Initially hide JugVid2cpp group (show only when active)
        self.jugvid2cpp_group.setVisible(False)

        # Add all groups to main layout
        self.main_layout.addWidget(self.feed_source_group)
        self.main_layout.addWidget(self.recording_group) # Add recording group
        self.main_layout.addWidget(self.watch_imu_group) # Add Watch IMU group
        self.main_layout.addWidget(self.jugvid2cpp_group) # Add JugVid2cpp group
        self.main_layout.addWidget(self.ball_controls_container)
        self.main_layout.addWidget(self.simple_tracking_settings_btn)
        self.main_layout.addWidget(self.tracked_balls_scroll)
        
        # Mouse event handling will be handled by individual feed widgets
        # TODO: Implement mouse events for feed widgets if needed for ball definition
        
        # Create status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        
        # Create status labels
        self.fps_label = QLabel("FPS: 0.0")
        self.status_bar.addPermanentWidget(self.fps_label)
        
        self.mode_label = QLabel("Mode: Unknown")
        self.status_bar.addPermanentWidget(self.mode_label)
        
        self.balls_label = QLabel("Balls: 0")
        self.status_bar.addPermanentWidget(self.balls_label)
        
        # Set up menus and toolbar
        self.setup_menus()
        self.setup_toolbar()
    
    def setup_menus(self):
        """
        Set up the menu bar and menus.
        """
        # Create menu bar
        self.menu_bar = self.menuBar()
        
        # File menu
        self.file_menu = self.menu_bar.addMenu("&File")
        
        # Load calibration action
        self.load_calibration_action = QAction("&Load Calibration", self)
        self.load_calibration_action.setShortcut(QKeySequence.StandardKey.Open)
        self.load_calibration_action.triggered.connect(self.load_calibration)
        self.file_menu.addAction(self.load_calibration_action)
        
        # Save calibration action
        self.save_calibration_action = QAction("&Save Calibration", self)
        self.save_calibration_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_calibration_action.triggered.connect(self.save_calibration)
        self.file_menu.addAction(self.save_calibration_action)
        
        # Save calibration as action
        self.save_calibration_as_action = QAction("Save Calibration &As...", self)
        self.save_calibration_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_calibration_as_action.triggered.connect(self.save_calibration_as)
        self.file_menu.addAction(self.save_calibration_as_action)
        
        self.file_menu.addSeparator()
        
        # Exit action
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        # Calibration menu
        self.calibration_menu = self.menu_bar.addMenu("&Calibration")
        
        # New ball action
        self.new_ball_action = QAction("&New Ball", self)
        self.new_ball_action.setShortcut(QKeySequence("Ctrl+N"))
        self.new_ball_action.triggered.connect(self.new_ball)
        self.calibration_menu.addAction(self.new_ball_action)
        
        # Edit ball action
        self.edit_ball_action = QAction("&Edit Ball", self)
        self.edit_ball_action.setShortcut(QKeySequence("Ctrl+E"))
        self.edit_ball_action.triggered.connect(self.edit_ball)
        self.calibration_menu.addAction(self.edit_ball_action)
        
        # Remove ball action
        self.remove_ball_action = QAction("&Remove Ball", self)
        self.remove_ball_action.setShortcut(QKeySequence("Ctrl+R"))
        self.remove_ball_action.triggered.connect(self.remove_ball)
        self.calibration_menu.addAction(self.remove_ball_action)
        
        # View menu
        self.view_menu = self.menu_bar.addMenu("&View")
        
        # Toggle color action
        self.toggle_color_action = QAction("Toggle &Color View", self)
        self.toggle_color_action.setShortcut(QKeySequence("C"))
        self.toggle_color_action.setCheckable(True)
        self.toggle_color_action.setChecked(self.show_color)
        self.toggle_color_action.triggered.connect(self.toggle_color)
        self.view_menu.addAction(self.toggle_color_action)
        
        # Toggle depth action
        self.toggle_depth_action = QAction("Toggle &Depth View", self)
        self.toggle_depth_action.setShortcut(QKeySequence("D"))
        self.toggle_depth_action.setCheckable(True)
        self.toggle_depth_action.setChecked(self.show_depth)
        self.toggle_depth_action.triggered.connect(self.toggle_depth)
        self.view_menu.addAction(self.toggle_depth_action)
        
        # Toggle masks action
        self.toggle_masks_action = QAction("Toggle &Masks View", self)
        self.toggle_masks_action.setShortcut(QKeySequence("M"))
        self.toggle_masks_action.setCheckable(True)
        self.toggle_masks_action.setChecked(self.show_masks)
        self.toggle_masks_action.triggered.connect(self.toggle_masks)
        self.view_menu.addAction(self.toggle_masks_action)
        
        # Toggle simple tracking action
        self.toggle_simple_tracking_action = QAction("Toggle &Simple Tracking", self)
        self.toggle_simple_tracking_action.setShortcut(QKeySequence("S"))
        self.toggle_simple_tracking_action.setCheckable(True)
        self.toggle_simple_tracking_action.setChecked(self.show_simple_tracking)
        self.toggle_simple_tracking_action.triggered.connect(self.toggle_simple_tracking)
        self.view_menu.addAction(self.toggle_simple_tracking_action)
        
        # Toggle simple tracking mask action
        self.toggle_simple_tracking_mask_action = QAction("Toggle Simple Tracking &Mask", self)
        self.toggle_simple_tracking_mask_action.setShortcut(QKeySequence("T"))
        self.toggle_simple_tracking_mask_action.setCheckable(True)
        self.toggle_simple_tracking_mask_action.setChecked(self.show_simple_tracking_mask)
        self.toggle_simple_tracking_mask_action.triggered.connect(self.toggle_simple_tracking_mask)
        self.view_menu.addAction(self.toggle_simple_tracking_mask_action)
        
        # Toggle debug action
        self.toggle_debug_action = QAction("Toggle &Debug Info", self)
        self.toggle_debug_action.setShortcut(QKeySequence("B"))
        self.toggle_debug_action.setCheckable(True)
        self.toggle_debug_action.setChecked(self.debug_mode)
        self.toggle_debug_action.triggered.connect(self.toggle_debug)
        self.view_menu.addAction(self.toggle_debug_action)
        
        # Toggle FPS action
        self.toggle_fps_action = QAction("Toggle &FPS Display", self)
        self.toggle_fps_action.setShortcut(QKeySequence("F"))
        self.toggle_fps_action.setCheckable(True)
        self.toggle_fps_action.setChecked(self.show_fps)
        self.toggle_fps_action.triggered.connect(self.toggle_fps)
        self.view_menu.addAction(self.toggle_fps_action)
        
        self.view_menu.addSeparator()
        
        # Reset view action
        self.reset_view_action = QAction("&Reset View", self)
        self.reset_view_action.setShortcut(QKeySequence("R"))
        self.reset_view_action.triggered.connect(self.reset_view)
        self.view_menu.addAction(self.reset_view_action)
        
        self.view_menu.addSeparator()
        
        # Demo feed configurations action
        self.demo_feeds_action = QAction("Demo &Feed Configurations", self)
        self.demo_feeds_action.setShortcut(QKeySequence("Ctrl+F"))
        self.demo_feeds_action.triggered.connect(self.demo_feed_configurations)
        self.view_menu.addAction(self.demo_feeds_action)
        
        self.view_menu.addSeparator()
        
        # IMU feed actions
        self.toggle_imu_feeds_action = QAction("Toggle &IMU Feeds", self)
        self.toggle_imu_feeds_action.setShortcut(QKeySequence("Ctrl+I"))
        self.toggle_imu_feeds_action.setCheckable(True)
        self.toggle_imu_feeds_action.setChecked(True)  # Default enabled
        self.toggle_imu_feeds_action.triggered.connect(self.toggle_imu_feeds)
        self.view_menu.addAction(self.toggle_imu_feeds_action)
        
        self.clear_imu_feeds_action = QAction("Clear IMU Feed &Data", self)
        self.clear_imu_feeds_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        self.clear_imu_feeds_action.triggered.connect(self.clear_all_imu_feed_data)
        self.view_menu.addAction(self.clear_imu_feeds_action)
        
        # Extensions menu
        self.extensions_menu = self.menu_bar.addMenu("&Extensions")
        
        # Toggle extensions results action
        self.toggle_extensions_action = QAction("Toggle &Extensions Results", self)
        self.toggle_extensions_action.setShortcut(QKeySequence("E"))
        self.toggle_extensions_action.setCheckable(True)
        self.toggle_extensions_action.setChecked(self.show_extension_results)
        self.toggle_extensions_action.triggered.connect(self.toggle_extension_results)
        self.extensions_menu.addAction(self.toggle_extensions_action)
        
        self.extensions_menu.addSeparator()
        
        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        
        # About action
        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(self.about_action)
    
    def setup_toolbar(self):
        """
        Set up the toolbar.
        """
        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setObjectName("MainToolbar") # For QMainWindow::saveState warning
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)
        
        # Add actions to toolbar
        self.toolbar.addAction(self.load_calibration_action)
        self.toolbar.addAction(self.save_calibration_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.new_ball_action)
        self.toolbar.addAction(self.edit_ball_action)
        self.toolbar.addAction(self.remove_ball_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.toggle_depth_action)
        self.toolbar.addAction(self.toggle_masks_action)
        self.toolbar.addAction(self.toggle_debug_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.reset_view_action)
    
    def update_extensions_menu(self, extension_manager):
        """
        Update the extensions menu with available extensions.
        
        Args:
            extension_manager: ExtensionManager instance
        """
        # Clear existing extension actions
        for action in self.extensions_menu.actions():
            if action != self.toggle_extensions_action and not action.isSeparator():
                self.extensions_menu.removeAction(action)
        
        # Add extensions
        extensions = extension_manager.get_registered_extensions()
        enabled_extensions = extension_manager.get_enabled_extensions()
        
        for name in extensions:
            # Create a closure to capture the extension name
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name in enabled_extensions)
            
            # Connect to a lambda that captures the current name
            action.triggered.connect(lambda checked, n=name: self.toggle_extension(n, checked))
            
            self.extensions_menu.addAction(action)
    
    def toggle_extension(self, name, checked):
        """
        Toggle an extension.
        
        Args:
            name (str): Name of the extension
            checked (bool): Whether the extension should be enabled
        """
        if self.app and hasattr(self.app, 'extension_manager'):
            if checked:
                self.app.extension_manager.enable_extension(name)
            else:
                self.app.extension_manager.disable_extension(name)
    
    def update_ui(self):
        """
        Update the UI with the latest data.
        Optimized to reduce unnecessary updates.
        """
        self._ui_update_count += 1
        
        # Adaptive UI update rate based on performance
        current_time = time.time()
        if current_time - self._last_ui_performance_check > 5.0:  # Check every 5 seconds
            # If we're running slow, reduce UI update frequency
            if hasattr(self.app, 'fps') and self.app.fps < 25:
                self.update_timer.setInterval(66)  # 15 FPS for UI updates
            elif hasattr(self.app, 'fps') and self.app.fps > 28:
                self.update_timer.setInterval(50)  # 20 FPS for UI updates
            self._last_ui_performance_check = current_time
        
        # Update IMU data display less frequently to reduce load
        if self._ui_update_count % 2 == 0:  # Every other UI update
            self.update_imu_data_display()
        
        # Update JugVid2cpp status display even less frequently
        if self._ui_update_count % 4 == 0:  # Every 4th UI update
            self.update_jugvid2cpp_status_display()
    
    def on_feeds_changed(self, feed_count):
        """
        Handle changes in the number of video feeds.
        
        Args:
            feed_count (int): New number of feeds
        """
        print(f"Feed count changed to: {feed_count}")
        
        # Update window title to show feed count
        base_title = "Juggling Tracker"
        if feed_count > 0:
            self.setWindowTitle(f"{base_title} - {feed_count} Feed{'s' if feed_count != 1 else ''}")
        else:
            self.setWindowTitle(base_title)
        
        # Adjust minimum window size based on feed count
        if feed_count <= 3:
            # Single row layout
            min_width = max(1280, feed_count * 320)
            min_height = 720
        else:
            # Two row layout
            min_width = max(1280, 3 * 320)
            min_height = 900  # Taller for two rows
            
        self.setMinimumSize(min_width, min_height)
    
    def update_frame(self, color_image, depth_image=None, masks=None, identified_balls=None,
                    hand_positions=None, extension_results=None, debug_info=None, tracked_balls_for_display=None, simple_tracking=None):
        """
        Update the video display with a new frame.
        Optimized to reduce unnecessary processing and memory allocations.
        """
        if color_image is None:
            # Reduce warning spam
            if not hasattr(self, '_none_image_warning_count'):
                self._none_image_warning_count = 0
            self._none_image_warning_count += 1
            if self._none_image_warning_count % 30 == 1:  # Log every 30th occurrence
                print(f"Warning: update_frame called with None color_image (#{self._none_image_warning_count})")
            return
        
        # Initialize frame update counter for optimization
        if not hasattr(self, '_frame_update_count'):
            self._frame_update_count = 0
        self._frame_update_count += 1
        
        # Store the tracked balls data for the panel (less frequent updates)
        if tracked_balls_for_display and self._frame_update_count % 3 == 0:  # Every 3rd frame
            self.tracked_balls_data = tracked_balls_for_display
            self.update_tracked_balls_panel()
        
        # Ensure we have at least one feed for the main display
        if self.video_feed_manager.get_feed_count() == 0:
            # Add the main feed
            main_feed_id = self.video_feed_manager.add_feed("Main Feed", "main")
        
        # Create different feed views with caching
        feeds_to_update = self._create_feed_views(color_image, depth_image, masks,
                                                 tracked_balls_for_display, simple_tracking,
                                                 hand_positions, debug_info)
        
        # Update each feed (only if we have valid content)
        if feeds_to_update:
            for feed_id, pixmap in feeds_to_update.items():
                if pixmap and not pixmap.isNull():
                    self.video_feed_manager.update_feed(feed_id, pixmap)
        else:
            # Create a status feed showing camera issues (less frequently)
            if self._frame_update_count % 10 == 0:  # Every 10th frame
                self._create_camera_error_feed()
        
        # Update status bar less frequently to reduce UI load
        if debug_info and self._frame_update_count % 5 == 0:  # Every 5th frame
            if 'Num Identified Balls' in debug_info:
                self.balls_label.setText(f"Balls: {debug_info['Num Identified Balls']}")
            
            if 'Mode' in debug_info:
                self.mode_label.setText(f"Mode: {debug_info['Mode']}")
        
        # Update FPS less frequently
        if hasattr(self.app, 'fps') and self._frame_update_count % 10 == 0:  # Every 10th frame
            self.fps_label.setText(f"FPS: {self.app.fps:.1f}")
    
    def _create_feed_views(self, color_image, depth_image, masks, tracked_balls_for_display,
                          simple_tracking, hand_positions, debug_info):
        """
        Create different feed views based on current display settings.
        
        Returns:
            dict: feed_id -> QPixmap mapping
        """
        feeds = {}
        
        # Always create main composite view
        composite = self.create_composite_view(color_image, depth_image, masks)
        if composite is not None:
            # Ensure composite is C-contiguous
            if not composite.flags['C_CONTIGUOUS']:
                composite = np.ascontiguousarray(composite)
            
            # Create pixmap with overlays
            pixmap = self._create_pixmap_with_overlays(composite, color_image, tracked_balls_for_display,
                                                     simple_tracking, hand_positions)
            feeds["main"] = pixmap
        
        # Create additional feeds based on settings
        if self.show_depth and depth_image is not None:
            # Add separate depth feed if not already in composite
            if not self._is_depth_in_composite():
                depth_pixmap = self._create_depth_pixmap(depth_image)
                if depth_pixmap:
                    feeds["depth"] = depth_pixmap
        
        if self.show_masks and masks:
            # Add separate mask feeds
            for mask_name, mask in masks.items():
                if mask is not None:
                    mask_pixmap = self._create_mask_pixmap(mask, mask_name)
                    if mask_pixmap:
                        feeds[f"mask_{mask_name.lower()}"] = mask_pixmap
        
        if self.show_simple_tracking_mask and hasattr(self.app, 'simple_tracker'):
            # Add simple tracking mask feed
            tracking_mask_pixmap = self._create_simple_tracking_mask_pixmap(color_image)
            if tracking_mask_pixmap:
                feeds["simple_tracking_mask"] = tracking_mask_pixmap
        
        return feeds
    
    def _create_pixmap_with_overlays(self, composite_image, color_image, tracked_balls_for_display,
                                   simple_tracking, hand_positions):
        """Create a QPixmap from composite image with overlays."""
        # Convert the OpenCV image to a Qt image
        height, width, channel = composite_image.shape
        bytes_per_line = 3 * width
        q_img = QImage(composite_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        
        # Create a pixmap from the Qt image
        pixmap = QPixmap.fromImage(q_img)
        
        # Create a copy for drawing overlays
        final_pixmap = pixmap.copy()
        painter = QPainter(final_pixmap)
        
        # Draw tracked balls if available
        if tracked_balls_for_display:
            self._draw_tracked_balls(painter, tracked_balls_for_display, color_image)
        
        # Draw simple tracking results if available and enabled
        if simple_tracking and self.show_simple_tracking:
            self._draw_simple_tracking(painter, simple_tracking)
        
        # Draw ROI rectangle if in ball definition mode
        if self.is_defining_ball_mode and self.defining_roi_current_rect:
            self._draw_roi_rectangle(painter, color_image)
        
        painter.end()
        return final_pixmap
    
    def _draw_tracked_balls(self, painter, tracked_balls_for_display, color_image):
        """Draw tracked balls on the painter."""
        for ball_info in tracked_balls_for_display:
            # Extract ball information
            pos_x, pos_y = int(ball_info['position_2d'][0]), int(ball_info['position_2d'][1])
            radius = int(ball_info['radius_px'])
            ball_name = ball_info['name']
            ball_id_display = ball_info['id']
            
            # Skip drawing if position is outside the visible area
            if self.show_depth and pos_x >= color_image.shape[1]:
                continue
            
            # Set pen color based on profile_id to distinguish different balls
            profile_id = ball_info.get('profile_id', '')
            color_hash = hash(profile_id) % 0xFFFFFF
            r = (color_hash & 0xFF0000) >> 16
            g = (color_hash & 0x00FF00) >> 8
            b = color_hash & 0x0000FF
            
            # Make sure the color is bright enough to be visible
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 128:  # If too dark
                r = min(255, r + 100)
                g = min(255, g + 100)
                b = min(255, b + 100)
            
            # Use yellow for disappeared balls, otherwise use the profile-specific color
            if ball_info['disappeared_frames'] > 0:
                pen_color = Qt.GlobalColor.yellow
            else:
                pen_color = QColor(r, g, b)
            
            # Set up pen for drawing
            pen = QPen(pen_color, 3)
            painter.setPen(pen)
            
            # Draw the ball circle
            if radius > 0:
                painter.drawEllipse(pos_x - radius, pos_y - radius, radius * 2, radius * 2)
            
            # Draw text with contrasting background
            text = f"{ball_name} (ID:{ball_id_display})"
            font = painter.font()
            font_metrics = QFontMetrics(font)
            text_width = font_metrics.horizontalAdvance(text)
            text_height = font_metrics.height()
            
            # Draw text background
            painter.fillRect(pos_x - text_width//2, pos_y + radius + 5,
                            text_width + 10, text_height + 5, QColor(0, 0, 0, 180))
            
            # Draw text in bright color
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(pos_x - text_width//2 + 5, pos_y + radius + text_height + 5, text)
    
    def _draw_simple_tracking(self, painter, simple_tracking):
        """Draw simple tracking overlays on the painter."""
        avg_pos = simple_tracking.get('average_position')
        if avg_pos:
            # Draw a large cross at the average position
            cross_size = 20
            painter.setPen(QPen(Qt.GlobalColor.cyan, 4))
            painter.drawLine(avg_pos[0] - cross_size, avg_pos[1], avg_pos[0] + cross_size, avg_pos[1])
            painter.drawLine(avg_pos[0], avg_pos[1] - cross_size, avg_pos[0], avg_pos[1] + cross_size)
            
            # Draw a circle around the average position
            painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
            painter.drawEllipse(avg_pos[0] - 15, avg_pos[1] - 15, 30, 30)
            
            # Draw text showing tracking info
            tracking_text = f"Avg: ({avg_pos[0]}, {avg_pos[1]})"
            object_count = simple_tracking.get('object_count', 0)
            total_area = simple_tracking.get('total_area', 0)
            info_text = f"Objects: {object_count}, Area: {total_area:.0f}px"
            
            # Draw text background
            font = painter.font()
            font_metrics = QFontMetrics(font)
            text_width = max(font_metrics.horizontalAdvance(tracking_text), font_metrics.horizontalAdvance(info_text))
            text_height = font_metrics.height()
            
            painter.fillRect(avg_pos[0] - text_width//2 - 5, avg_pos[1] - 40,
                            text_width + 10, text_height * 2 + 10, QColor(0, 0, 0, 180))
            
            # Draw text
            painter.setPen(QPen(Qt.GlobalColor.cyan))
            painter.drawText(avg_pos[0] - text_width//2, avg_pos[1] - 25, tracking_text)
            painter.drawText(avg_pos[0] - text_width//2, avg_pos[1] - 10, info_text)
        
        # Draw individual object positions
        individual_positions = simple_tracking.get('individual_positions', [])
        for i, pos in enumerate(individual_positions):
            painter.setPen(QPen(Qt.GlobalColor.magenta, 2))
            painter.drawEllipse(pos[0] - 5, pos[1] - 5, 10, 10)
            
            # Draw small number label
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(pos[0] + 8, pos[1] - 8, str(i + 1))
    
    def _draw_roi_rectangle(self, painter, color_image):
        """Draw ROI rectangle for ball definition."""
        pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        x, y, w, h = self.defining_roi_current_rect
        
        # Only draw ROI on the color image portion if depth is shown
        if self.show_depth and x >= color_image.shape[1]:
            pass  # Skip drawing ROI on depth image portion
        else:
            painter.drawRect(x, y, w, h)
    
    def _is_depth_in_composite(self):
        """Check if depth is already included in the composite view."""
        return self.show_depth
    
    def _create_depth_pixmap(self, depth_image):
        """Create a pixmap from depth image."""
        try:
            if len(depth_image.shape) == 3:
                depth_image_gray = depth_image[:,:,0]
            else:
                depth_image_gray = depth_image
            
            if np.any(depth_image_gray):
                depth_normalized = cv2.convertScaleAbs(depth_image_gray, alpha=0.03)
            else:
                depth_normalized = np.zeros_like(depth_image_gray, dtype=np.uint8)
            
            depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
            
            # Convert to QPixmap
            height, width, channel = depth_colormap.shape
            bytes_per_line = 3 * width
            q_img = QImage(depth_colormap.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            return QPixmap.fromImage(q_img)
        except Exception as e:
            print(f"Error creating depth pixmap: {e}")
            return None
    
    def _create_mask_pixmap(self, mask, mask_name):
        """Create a pixmap from mask."""
        try:
            # Convert mask to BGR for visualization
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            
            # Add the mask name
            cv2.putText(mask_bgr, f"{mask_name} Mask", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Convert to QPixmap
            height, width, channel = mask_bgr.shape
            bytes_per_line = 3 * width
            q_img = QImage(mask_bgr.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            return QPixmap.fromImage(q_img)
        except Exception as e:
            print(f"Error creating mask pixmap for {mask_name}: {e}")
            return None
    
    def _create_simple_tracking_mask_pixmap(self, color_image):
        """Create a pixmap for simple tracking mask."""
        try:
            # This is a simplified version - in practice you'd recreate the tracking mask
            # For now, create a placeholder
            placeholder = np.zeros((color_image.shape[0], color_image.shape[1], 3), dtype=np.uint8)
            cv2.putText(placeholder, "Simple Tracking Mask", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Convert to QPixmap
            height, width, channel = placeholder.shape
            bytes_per_line = 3 * width
            q_img = QImage(placeholder.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            return QPixmap.fromImage(q_img)
        except Exception as e:
            print(f"Error creating simple tracking mask pixmap: {e}")
            return None
    
    def _create_error_status_image(self, debug_info):
        """Create an error status image when camera fails."""
        try:
            # Create a 640x480 error image
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (40, 40, 40)  # Dark gray background
            
            # Add error message
            cv2.putText(img, "CAMERA ERROR", (200, 200),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.putText(img, "No frames received from camera", (150, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Add mode information if available
            if debug_info and 'Mode' in debug_info:
                cv2.putText(img, f"Mode: {debug_info['Mode']}", (50, 300),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Add troubleshooting info
            cv2.putText(img, "Try:", (50, 350),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(img, "1. Check camera connection", (70, 380),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(img, "2. Switch to webcam mode", (70, 400),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(img, "3. Use video playback mode", (70, 420),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return img
        except Exception as e:
            print(f"Error creating error status image: {e}")
            return None
    
    def _numpy_to_pixmap(self, img):
        """Convert numpy array to QPixmap."""
        try:
            height, width, channel = img.shape
            bytes_per_line = 3 * width
            q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error converting numpy to pixmap: {e}")
            return QPixmap()
    
    def _create_camera_error_feed(self):
        """Create a camera error feed when no valid frames are available."""
        try:
            error_image = self._create_error_status_image({"Mode": "Camera Error"})
            if error_image is not None:
                pixmap = self._numpy_to_pixmap(error_image)
                if self.video_feed_manager.get_feed_count() == 0:
                    self.video_feed_manager.add_feed("Camera Error", "error")
                self.video_feed_manager.update_feed("main", pixmap)
        except Exception as e:
            print(f"Error creating camera error feed: {e}")
    
    def create_composite_view(self, color_image, depth_image=None, masks=None):
        """
        Create composite view with performance optimizations.
        Reduced debug output and optimized processing.
        """
        if color_image is None:
            # Return cached black image to avoid repeated allocation
            if not hasattr(self, '_cached_black_image'):
                self._cached_black_image = np.zeros((480, 640, 3), dtype=np.uint8)
            return self._cached_black_image
        
        # Cache view settings to avoid repeated checks
        if not hasattr(self, '_last_view_settings'):
            self._last_view_settings = None
            self._cached_composite = None
            self._cached_views = {}
        
        current_settings = (self.show_color, self.show_depth, self.show_masks, self.show_simple_tracking_mask)
        
        # Determine what views to show
        views_to_show = []
        
        # Add color view if enabled (avoid unnecessary copy for single view)
        if self.show_color:
            if len(current_settings) == 1 and current_settings[0]:  # Only color enabled
                return color_image  # Direct return for single color view
            views_to_show.append(('color', color_image))
        
        # Add depth view if enabled and available
        if depth_image is not None and self.show_depth:
            try:
                # Cache depth processing to avoid repeated computation
                depth_cache_key = id(depth_image)
                if not hasattr(self, '_depth_cache') or self._depth_cache.get('key') != depth_cache_key:
                    # Ensure depth_image is 2D
                    if len(depth_image.shape) == 3:
                        depth_image_gray = depth_image[:,:,0]
                    else:
                        depth_image_gray = depth_image

                    # Optimize depth normalization
                    if np.any(depth_image_gray):
                        depth_normalized = cv2.convertScaleAbs(depth_image_gray, alpha=0.03)
                    else:
                        depth_normalized = np.zeros_like(depth_image_gray, dtype=np.uint8)
                    
                    depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
                    
                    # Resize only if necessary
                    target_height, target_width = color_image.shape[:2]
                    if depth_colormap.shape[:2] != (target_height, target_width):
                        depth_colormap_resized = cv2.resize(depth_colormap, (target_width, target_height))
                    else:
                        depth_colormap_resized = depth_colormap
                    
                    # Cache the result
                    self._depth_cache = {'key': depth_cache_key, 'result': depth_colormap_resized}
                
                views_to_show.append(('depth', self._depth_cache['result']))
                
            except Exception as e:
                # Reduce debug spam - only log errors occasionally
                if not hasattr(self, '_depth_error_count'):
                    self._depth_error_count = 0
                self._depth_error_count += 1
                if self._depth_error_count % 30 == 1:  # Log every 30th error
                    print(f"[MainWindow] Depth processing error (#{self._depth_error_count}): {e}")
        
        # Add mask view if enabled and available
        if masks is not None and self.show_masks:
            try:
                combined_mask = masks.get('Combined')
                if combined_mask is not None:
                    # Cache mask processing
                    mask_cache_key = id(combined_mask)
                    if not hasattr(self, '_mask_cache') or self._mask_cache.get('key') != mask_cache_key:
                        mask_bgr = cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR)
                        cv2.putText(mask_bgr, "Proximity Mask", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        target_height, target_width = color_image.shape[:2]
                        if mask_bgr.shape[:2] != (target_height, target_width):
                            mask_resized = cv2.resize(mask_bgr, (target_width, target_height))
                        else:
                            mask_resized = mask_bgr
                        
                        self._mask_cache = {'key': mask_cache_key, 'result': mask_resized}
                    
                    views_to_show.append(('mask', self._mask_cache['result']))
            except Exception as e:
                # Reduce debug spam for mask errors
                if not hasattr(self, '_mask_error_count'):
                    self._mask_error_count = 0
                self._mask_error_count += 1
                if self._mask_error_count % 30 == 1:
                    print(f"[MainWindow] Mask processing error (#{self._mask_error_count}): {e}")
        
        # Simplified simple tracking mask (remove expensive recomputation)
        if self.show_simple_tracking_mask and masks and 'Combined' in masks:
            try:
                # Use existing combined mask instead of recomputing
                proximity_mask = masks['Combined']
                if proximity_mask is not None and hasattr(self.app, 'simple_tracker'):
                    tracking_cache_key = id(proximity_mask)
                    if not hasattr(self, '_tracking_cache') or self._tracking_cache.get('key') != tracking_cache_key:
                        min_size = getattr(self.app.depth_processor, 'min_object_size', 50) if hasattr(self.app, 'depth_processor') else 50
                        max_size = getattr(self.app.depth_processor, 'max_object_size', 5000) if hasattr(self.app, 'depth_processor') else 5000
                        
                        tracking_mask = self.app.simple_tracker.get_tracking_visualization_mask(
                            proximity_mask, min_size, max_size
                        )
                        
                        cv2.putText(tracking_mask, "Simple Tracking Mask", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                        
                        target_height, target_width = color_image.shape[:2]
                        if tracking_mask.shape[:2] != (target_height, target_width):
                            tracking_mask_resized = cv2.resize(tracking_mask, (target_width, target_height))
                        else:
                            tracking_mask_resized = tracking_mask
                        
                        self._tracking_cache = {'key': tracking_cache_key, 'result': tracking_mask_resized}
                    
                    views_to_show.append(('simple_tracking_mask', self._tracking_cache['result']))
            except Exception as e:
                # Reduce debug spam for tracking errors
                if not hasattr(self, '_tracking_error_count'):
                    self._tracking_error_count = 0
                self._tracking_error_count += 1
                if self._tracking_error_count % 30 == 1:
                    print(f"[MainWindow] Tracking mask error (#{self._tracking_error_count}): {e}")
        
        # Create composite based on enabled views
        if not views_to_show:
            # Cache "no views" message
            if not hasattr(self, '_cached_no_views_image'):
                self._cached_no_views_image = np.zeros((color_image.shape[0], color_image.shape[1], 3), dtype=np.uint8)
                cv2.putText(self._cached_no_views_image, "No views enabled", (50, self._cached_no_views_image.shape[0]//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            return self._cached_no_views_image
        elif len(views_to_show) == 1:
            # Single view - return directly
            return views_to_show[0][1]
        else:
            # Multiple views - optimize horizontal stacking
            try:
                # Use efficient numpy concatenation
                composite = np.concatenate([view[1] for view in views_to_show], axis=1)
                return composite
            except Exception as e:
                print(f"[MainWindow] Error creating composite: {e}")
                # Fallback to first view
                return views_to_show[0][1]
    
    def load_window_state(self):
        """
        Load the window state from settings.
        """
        settings = QSettings("JugglingTracker", "JugglingTracker")
        
        # Restore window geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state (toolbar positions, etc.)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
        
        # Restore view settings
        self.show_color = settings.value("show_color", True, type=bool)
        self.show_depth = settings.value("show_depth", False, type=bool)
        self.show_masks = settings.value("show_masks", False, type=bool)
        self.show_simple_tracking = settings.value("show_simple_tracking", True, type=bool)
        self.show_simple_tracking_mask = settings.value("show_simple_tracking_mask", False, type=bool)
        self.debug_mode = settings.value("debug_mode", False, type=bool)
        self.show_fps = settings.value("show_fps", True, type=bool)
        self.show_extension_results = settings.value("show_extension_results", True, type=bool)
        
        # Restore feed source settings
        self.current_feed_mode = settings.value("feed_mode", "live", type=str)
        self.current_video_path = settings.value("video_path", None, type=str)

        # Update actions to match settings
        self.toggle_color_action.setChecked(self.show_color)
        self.toggle_depth_action.setChecked(self.show_depth)
        self.toggle_masks_action.setChecked(self.show_masks)
        self.toggle_simple_tracking_action.setChecked(self.show_simple_tracking)
        self.toggle_simple_tracking_mask_action.setChecked(self.show_simple_tracking_mask) # Added this line
        self.toggle_debug_action.setChecked(self.debug_mode)
        self.toggle_fps_action.setChecked(self.show_fps)
        self.toggle_extensions_action.setChecked(self.show_extension_results)

        # Update feed mode UI based on loaded settings from QSettings
        # We will not trigger app mode switches here.
        # App will initialize to its default/arg-specified mode.
        # sync_ui_to_app_state() will be called later by JugglingTracker to align UI.

        if self.current_feed_mode == "playback":
            self.feed_mode_combo.blockSignals(True) # Prevent premature signal on_feed_mode_changed
            self.feed_mode_combo.setCurrentIndex(1)
            self.feed_mode_combo.blockSignals(False)
            self.select_video_button.setEnabled(True)
            if self.current_video_path:
                self.video_path_label.setText(os.path.basename(self.current_video_path))
            else:
                self.video_path_label.setText("No video selected")
        else: # live
            self.feed_mode_combo.blockSignals(True)
            self.feed_mode_combo.setCurrentIndex(0)
            self.feed_mode_combo.blockSignals(False)
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("")
        
        # self.update_recording_controls_state() will be called by sync_ui_to_app_state

        # Update the defined balls list if app is available
        if self.app and hasattr(self.app, 'ball_profile_manager'):
            self.update_defined_balls_list()
    
    def save_window_state(self):
        """
        Save the window state to settings.
        """
        settings = QSettings("JugglingTracker", "JugglingTracker")
        
        # Save window geometry
        settings.setValue("geometry", self.saveGeometry())
        
        # Save window state (toolbar positions, etc.)
        settings.setValue("windowState", self.saveState())
        
        # Save view settings
        settings.setValue("show_color", self.show_color)
        settings.setValue("show_depth", self.show_depth)
        settings.setValue("show_masks", self.show_masks)
        settings.setValue("show_simple_tracking", self.show_simple_tracking)
        settings.setValue("show_simple_tracking_mask", self.show_simple_tracking_mask)
        settings.setValue("debug_mode", self.debug_mode)
        settings.setValue("show_fps", self.show_fps)
        settings.setValue("show_extension_results", self.show_extension_results)

        # Save feed source settings
        settings.setValue("feed_mode", self.current_feed_mode)
        settings.setValue("video_path", self.current_video_path)
    
    def closeEvent(self, event):
        """
        Handle the window close event.
        
        Args:
            event: Close event
        """
        # Save window state
        self.save_window_state()
        
        # Stop the application
        if self.app:
            self.app.running = False
        
        # Accept the close event
        event.accept()
    
    # Menu action handlers
    
    def load_calibration(self):
        """
        Load a color calibration.
        """
        # Open a file dialog to select a calibration file
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Calibration", self.config_dir, "Calibration Files (*.json)"
        )
        
        if file_path and self.app and hasattr(self.app, 'color_calibration'):
            # Load the calibration
            self.app.color_calibration.load(file_path)
            self.status_bar.showMessage(f"Loaded calibration from {file_path}", 3000)
    
    def save_calibration(self):
        """
        Save the current color calibration.
        """
        if self.app and hasattr(self.app, 'color_calibration'):
            # Save the calibration
            file_path = self.app.color_calibration.get_current_file()
            
            if file_path:
                self.app.color_calibration.save(file_path)
                self.status_bar.showMessage(f"Saved calibration to {file_path}", 3000)
            else:
                # If no current file, use save as
                self.save_calibration_as()
    
    def save_calibration_as(self):
        """
        Save the current color calibration with a new name.
        """
        # Open a file dialog to select a new file name
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Calibration As", self.config_dir, "Calibration Files (*.json)"
        )
        
        if file_path and self.app and hasattr(self.app, 'color_calibration'):
            # Save the calibration
            self.app.color_calibration.save(file_path)
            self.status_bar.showMessage(f"Saved calibration to {file_path}", 3000)
    
    def new_ball(self):
        """
        Start calibration for a new ball.
        """
        # Create a dialog to enter the ball name
        dialog = QDialog(self)
        dialog.setWindowTitle("New Ball")
        
        # Create layout
        layout = QFormLayout(dialog)
        
        # Create name field
        name_edit = QLineEdit(dialog)
        name_edit.setText(f"Ball {len(self.get_calibrated_balls()) + 1}")
        layout.addRow("Ball Name:", name_edit)
        
        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        # Show the dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Start calibration
            self.calibration_ball_name = name_edit.text()
            self.start_calibration()
    
    def edit_ball(self):
        """
        Edit an existing ball calibration.
        """
        # Get the list of calibrated balls
        balls = self.get_calibrated_balls()
        
        if not balls:
            self.status_bar.showMessage("No calibrated balls to edit", 3000)
            return
        
        # Create a dialog to select a ball
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Ball")
        
        # Create layout
        layout = QFormLayout(dialog)
        
        # Create ball selection combo box
        ball_combo = QComboBox(dialog)
        ball_combo.addItems(balls)
        layout.addRow("Ball:", ball_combo)
        
        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        # Show the dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Start calibration for the selected ball
            self.calibration_ball_name = ball_combo.currentText()
            self.start_calibration()
    
    def remove_ball(self):
        """
        Remove an existing ball calibration.
        """
        # Get the list of calibrated balls
        balls = self.get_calibrated_balls()
        
        if not balls:
            self.status_bar.showMessage("No calibrated balls to remove", 3000)
            return
        
        # Create a dialog to select a ball
        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Ball")
        
        # Create layout
        layout = QFormLayout(dialog)
        
        # Create ball selection combo box
        ball_combo = QComboBox(dialog)
        ball_combo.addItems(balls)
        layout.addRow("Ball:", ball_combo)
        
        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        # Show the dialog
        if dialog.exec() == QDialog.DialogCode.Accepted and self.app and hasattr(self.app, 'color_calibration'):
            # Remove the selected ball
            ball_name = ball_combo.currentText()
            self.app.color_calibration.remove_ball(ball_name)
            self.status_bar.showMessage(f"Removed ball {ball_name}", 3000)
    
    def toggle_depth(self, checked=None):
        """
        Toggle depth view.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_depth = checked
        else:
            self.show_depth = not self.show_depth
            self.toggle_depth_action.setChecked(self.show_depth)
        
        self.status_bar.showMessage(f"Depth view {'enabled' if self.show_depth else 'disabled'}", 3000)
    
    def toggle_masks(self, checked=None):
        """
        Toggle masks view.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_masks = checked
        else:
            self.show_masks = not self.show_masks
            self.toggle_masks_action.setChecked(self.show_masks)
        
        self.status_bar.showMessage(f"Masks view {'enabled' if self.show_masks else 'disabled'}", 3000)
    
    def toggle_debug(self, checked=None):
        """
        Toggle debug mode.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.debug_mode = checked
        else:
            self.debug_mode = not self.debug_mode
            self.toggle_debug_action.setChecked(self.debug_mode)
        
        self.status_bar.showMessage(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}", 3000)
    
    def toggle_fps(self, checked=None):
        """
        Toggle FPS display.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_fps = checked
        else:
            self.show_fps = not self.show_fps
            self.toggle_fps_action.setChecked(self.show_fps)
        
        self.status_bar.showMessage(f"FPS display {'enabled' if self.show_fps else 'disabled'}", 3000)
    
    def toggle_extension_results(self, checked=None):
        """
        Toggle extension results display.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_extension_results = checked
        else:
            self.show_extension_results = not self.show_extension_results
            self.toggle_extensions_action.setChecked(self.show_extension_results)
        
        self.status_bar.showMessage(f"Extension results {'enabled' if self.show_extension_results else 'disabled'}", 3000)
    
    def reset_view(self):
        """
        Reset the view.
        """
        # Reset view settings
        self.show_color = True
        self.show_depth = False
        self.show_masks = False
        self.show_simple_tracking = True
        self.debug_mode = False
        self.show_fps = True
        self.show_extension_results = True
        
        # Update actions
        self.toggle_color_action.setChecked(self.show_color)
        self.toggle_depth_action.setChecked(self.show_depth)
        self.toggle_masks_action.setChecked(self.show_masks)
        self.toggle_simple_tracking_action.setChecked(self.show_simple_tracking)
        self.toggle_simple_tracking_mask_action.setChecked(self.show_simple_tracking_mask)
        self.toggle_debug_action.setChecked(self.debug_mode)
        self.toggle_fps_action.setChecked(self.show_fps)
        self.toggle_extensions_action.setChecked(self.show_extension_results)
        
        # Reset the application
        if self.app and hasattr(self.app, 'ball_tracker'):
            self.app.ball_tracker.reset()
            self.app.frame_count = 0
            self.app.start_time = time.time()
        
        self.status_bar.showMessage("View reset", 3000)
    
    def show_about(self):
        """
        Show the about dialog.
        """
        QMessageBox.about(self, "About Juggling Tracker",
                         "Juggling Tracker\n\n"
                         "A robust juggling ball tracking system\n\n"
                         "Version 1.0.0")
    
    def start_calibration(self):
        """
        Start the calibration process.
        """
        self.calibration_mode = True
        self.calibration_samples = 0
        self.calibration_start_time = time.time()
        
        self.status_bar.showMessage(f"Calibrating {self.calibration_ball_name}...", 0)
    
    def update_calibration(self, blob=None, color_image=None):
        """
        Update the calibration with a new sample.
        
        Args:
            blob: Blob information (optional)
            color_image: Color image in BGR format (optional)
            
        Returns:
            bool: True if calibration is complete, False otherwise
        """
        if not self.calibration_mode:
            return False
        
        if blob is not None and color_image is not None and self.app and hasattr(self.app, 'color_calibration'):
            # Extract the average color of the blob
            mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
            cv2.drawContours(mask, [blob['contour']], -1, 255, -1)
            mean_color = cv2.mean(color_image, mask=mask)[:3]  # BGR format
            
            # Update the calibration
            self.app.color_calibration.add_sample(self.calibration_ball_name, mean_color)
            
            self.calibration_samples += 1
            
            # Update status bar
            progress = min(100, int(100 * self.calibration_samples / self.calibration_max_samples))
            self.status_bar.showMessage(f"Calibrating {self.calibration_ball_name}... {progress}%", 0)
            
            # Check if calibration is complete
            if self.calibration_samples >= self.calibration_max_samples:
                self.complete_calibration()
                return True
            
            # Check for timeout
            if time.time() - self.calibration_start_time > self.calibration_timeout:
                self.cancel_calibration()
        
        return False
    
    def complete_calibration(self):
        """
        Complete the calibration process.
        """
        self.calibration_mode = False
        
        if self.app and hasattr(self.app, 'color_calibration'):
            # Finalize the calibration
            self.app.color_calibration.finalize_ball(self.calibration_ball_name)
            
            self.status_bar.showMessage(f"Calibration of {self.calibration_ball_name} complete", 3000)
    
    def cancel_calibration(self):
        """
        Cancel the calibration process.
        """
        self.calibration_mode = False
        self.status_bar.showMessage("Calibration cancelled", 3000)
    
    def get_calibrated_balls(self):
        """
        Get the list of calibrated balls.
        
        Returns:
            list: List of ball names
        """
        if self.app and hasattr(self.app, 'color_calibration'):
            return self.app.color_calibration.get_ball_names()
        return []
    
    def is_calibrating(self):
        """
        Check if calibration is in progress.
        
        Returns:
            bool: True if calibration is in progress, False otherwise
        """
        return self.calibration_mode
    
    def get_calibration_ball_name(self):
        """
        Get the name of the ball being calibrated.
        
        Returns:
            str: Name of the ball being calibrated
        """
        return self.calibration_ball_name
    
    def open_simple_tracking_settings(self):
        """
        Open the Simple Tracking Settings window.
        """
        if self.simple_tracking_window is None:
            self.simple_tracking_window = SimpleTrackingWindow(self, self.app, self.config_dir)
        
        # Show the window (it will be created if it doesn't exist)
        self.simple_tracking_window.show()
        self.simple_tracking_window.raise_()
        self.simple_tracking_window.activateWindow()
        
    # Ball definition methods
    
    def toggle_define_ball_mode(self):
        """
        Toggle ball definition mode.
        """
        self.is_defining_ball_mode = not self.is_defining_ball_mode
        if self.is_defining_ball_mode:
            self.new_ball_button.setText("Cancel Defining")
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("Click and drag on the video to define a new ball.")
            QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
        else:
            self.new_ball_button.setText("New Ball")
            if hasattr(self, 'statusBar'):
                self.statusBar().clearMessage()
            QApplication.restoreOverrideCursor()
            self.defining_roi_start_pt = None
            self.defining_roi_current_rect = None
        if hasattr(self, 'video_label'):
            self.video_label.update()
    
    def video_label_mouse_press(self, event):
        """
        Handle mouse press events on the video label.
        
        Args:
            event: Mouse event
        """
        if hasattr(self, 'video_label') and self.is_defining_ball_mode and event.button() == Qt.MouseButton.LeftButton:
            self.defining_roi_start_pt = event.pos()
            self.defining_roi_current_rect = None  # Reset current rect
            self.video_label.update()  # Trigger repaint
    
    def video_label_mouse_move(self, event):
        """
        Handle mouse move events on the video label.
        
        Args:
            event: Mouse event
        """
        if hasattr(self, 'video_label') and self.is_defining_ball_mode and self.defining_roi_start_pt:
            x1, y1 = self.defining_roi_start_pt.x(), self.defining_roi_start_pt.y()
            x2, y2 = event.pos().x(), event.pos().y()
            # Ensure correct rectangle coordinates regardless of drag direction
            self.defining_roi_current_rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            self.video_label.update()  # Trigger repaint
    
    def video_label_mouse_release(self, event):
        """
        Handle mouse release events on the video label.
        
        Args:
            event: Mouse event
        """
        if hasattr(self, 'video_label') and self.is_defining_ball_mode and self.defining_roi_start_pt and event.button() == Qt.MouseButton.LeftButton:
            if self.defining_roi_current_rect and self.defining_roi_current_rect[2] > 5 and self.defining_roi_current_rect[3] > 5:  # Min size
                # Scale ROI coordinates if video_label displays a scaled QPixmap
                # This is a simplified approach - in a real implementation, you would need to
                # calculate the scaling factor based on the original image size and the displayed size
                scaled_roi = self.defining_roi_current_rect
                
                # Trigger ball definition in the app
                if self.app and hasattr(self.app, 'define_new_ball'):
                    self.app.define_new_ball(scaled_roi)
                    # Update the defined balls list after defining a new ball
                    if hasattr(self.app, 'ball_profile_manager'):
                        self.update_defined_balls_list()
                else:
                    print("Error: app does not have define_new_ball method.")
            
            self.toggle_define_ball_mode()  # Exit defining mode after attempt
    
    def update_defined_balls_list(self):
        """
        Update the list of defined balls.
        """
        if not hasattr(self, 'defined_balls_list'):
            print("WARN: defined_balls_list not found in MainWindow.")
            return
            
        self.defined_balls_list.clear()
        if self.app and hasattr(self.app, 'ball_profile_manager'):
            profiles = self.app.ball_profile_manager.get_all_profiles()
            for profile in profiles:
                item_text = f"{profile.name} (ID: {profile.profile_id[:8]})"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.ItemDataRole.UserRole, profile.profile_id)  # Store ID for later
                self.defined_balls_list.addItem(list_item)
        else:
            print("WARN: app.ball_profile_manager not found for updating defined balls list.")
    
    def update_tracked_balls_panel(self):
        """
        Update the tracked balls panel with current tracking information.
        """
        # Clear existing widgets
        while self.tracked_balls_layout.count():
            item = self.tracked_balls_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Add a widget for each tracked ball
        for ball in self.tracked_balls_data:
            ball_widget = QWidget()
            ball_layout = QHBoxLayout()
            ball_widget.setLayout(ball_layout)
            
            # Ball info
            ball_id = ball.get('id', 'Unknown')
            ball_name = ball.get('name', 'Unknown')
            pos_3d = ball.get('position_3d_kf', [0, 0, 0])
            
            # Create labels
            name_label = QLabel(f"{ball_name} (ID: {ball_id})")
            coords_label = QLabel(f"X: {pos_3d[0]:.2f}, Y: {pos_3d[1]:.2f}, Z: {pos_3d[2]:.2f}")
            
            # Add time since first tracked
            # This would require tracking when the ball was first seen
            # For now, we'll just show if it's currently visible or predicted
            status_text = "Visible" if ball.get('disappeared_frames', 0) == 0 else f"Predicted ({ball.get('disappeared_frames', 0)})"
            status_label = QLabel(f"Status: {status_text}")
            
            # Create untrack button
            untrack_button = QPushButton("Untrack")
            untrack_button.clicked.connect(lambda checked, bid=ball_id: self.untrack_ball(bid))
            
            # Add to layout
            ball_layout.addWidget(name_label)
            ball_layout.addWidget(coords_label)
            ball_layout.addWidget(status_label)
            ball_layout.addWidget(untrack_button)
            
            # Add to panel
            self.tracked_balls_layout.addWidget(ball_widget)
        
        # If no balls are tracked, show a message
        if not self.tracked_balls_data:
            no_balls_label = QLabel("No balls currently being tracked")
            self.tracked_balls_layout.addWidget(no_balls_label)
    
    def untrack_ball(self, ball_id):
        """
        Remove a ball from tracking.
        
        Args:
            ball_id: ID of the ball to untrack
        """
        if hasattr(self, 'app') and self.app:
            if hasattr(self.app, 'untrack_ball'):
                self.app.untrack_ball(ball_id)
                # The panel will be updated on the next frame update
            else:
                print("Error: app does not have untrack_ball method.")
    
    
    def toggle_color(self, checked=None):
        """
        Toggle color view.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_color = checked
        else:
            self.show_color = not self.show_color
            self.toggle_color_action.setChecked(self.show_color)
        
        self.status_bar.showMessage(f"Color view {'enabled' if self.show_color else 'disabled'}", 3000)
    
    def toggle_simple_tracking(self, checked=None):
        """
        Toggle simple tracking overlay.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_simple_tracking = checked
        else:
            self.show_simple_tracking = not self.show_simple_tracking
            self.toggle_simple_tracking_action.setChecked(self.show_simple_tracking)
        
        self.status_bar.showMessage(f"Simple tracking {'enabled' if self.show_simple_tracking else 'disabled'}", 3000)
    
    def toggle_simple_tracking_mask(self, checked=None):
        """
        Toggle simple tracking mask view.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is not None:
            self.show_simple_tracking_mask = checked
        else:
            self.show_simple_tracking_mask = not self.show_simple_tracking_mask
            self.toggle_simple_tracking_mask_action.setChecked(self.show_simple_tracking_mask)
        
        # Update the button in the simple tracking window if it's open
        if self.simple_tracking_window is not None:
            self.simple_tracking_window.show_tracking_mask_btn.setChecked(self.show_simple_tracking_mask)
            if self.show_simple_tracking_mask:
                self.simple_tracking_window.show_tracking_mask_btn.setText("Hide Simple Tracking Mask")
            else:
                self.simple_tracking_window.show_tracking_mask_btn.setText("Show Simple Tracking Mask")
        
        self.status_bar.showMessage(f"Simple tracking mask {'enabled' if self.show_simple_tracking_mask else 'disabled'}", 3000)
    
    def update_tracking_position_display(self, simple_tracking_result):
        """Update the position display in the simple tracking window if it's open."""
        if self.simple_tracking_window is not None:
            self.simple_tracking_window.update_tracking_position_display(simple_tracking_result)

    def on_feed_mode_changed(self, index):
        """
        Handle changes in the feed mode combo box.
        """
        if index == 0: # Live Feed
            self.current_feed_mode = "live"
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("") # Clear video path label
            if self.app and hasattr(self.app, 'switch_to_live_mode'):
                self.app.switch_to_live_mode()
            self.status_bar.showMessage("Switched to Live Feed mode.", 3000)
        elif index == 1: # Recorded Feed
            self.current_feed_mode = "playback"
            self.select_video_button.setEnabled(True)
            if self.current_video_path:
                self.video_path_label.setText(os.path.basename(self.current_video_path))
                if self.app and hasattr(self.app, 'switch_to_playback_mode'):
                    self.app.switch_to_playback_mode(self.current_video_path)
                self.status_bar.showMessage(f"Switched to Recorded Feed. Video: {os.path.basename(self.current_video_path)}", 3000)
            else:
                self.video_path_label.setText("No video selected")
                self.status_bar.showMessage("Switched to Recorded Feed. Select a video file.", 3000)
                # Optionally, prompt to select a file immediately
                # self.select_video_file()
        elif index == 2: # JugVid2cpp 3D Tracking
            self.current_feed_mode = "jugvid2cpp"
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("JugVid2cpp provides 3D ball positions directly")
            if self.app and hasattr(self.app, 'switch_to_jugvid2cpp_mode'):
                success = self.app.switch_to_jugvid2cpp_mode()
                if success:
                    self.status_bar.showMessage("Switched to JugVid2cpp 3D Tracking mode.", 3000)
                else:
                    self.status_bar.showMessage("Failed to initialize JugVid2cpp. Check that the executable is available.", 5000)
            else:
                self.status_bar.showMessage("JugVid2cpp integration not available.", 3000)
        self.update_recording_controls_state() # Update recording button states based on new mode

    def select_video_file(self):
        """
        Open a dialog to select a video file for playback.
        """
        # Sensible default directory could be user's Videos folder or last used path
        # For now, using self.config_dir as a placeholder if no better option.
        # A more robust approach would save/load last used video directory.
        start_dir = os.path.dirname(self.current_video_path) if self.current_video_path else self.config_dir

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", start_dir,
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        
        if file_path:
            self.current_video_path = file_path
            self.video_path_label.setText(os.path.basename(file_path))
            if self.app and hasattr(self.app, 'switch_to_playback_mode'):
                self.app.switch_to_playback_mode(self.current_video_path)
            self.status_bar.showMessage(f"Selected video: {os.path.basename(file_path)}", 3000)
        else:
            self.status_bar.showMessage("Video selection cancelled.", 3000)
        self.update_recording_controls_state()

    def handle_start_recording(self):
        """
        Handle the "Start Recording" button click.
        Prompts for a .bag file path and tells the app to start recording.
        """
        if not self.app or not hasattr(self.app, 'start_video_recording'):
            self.status_bar.showMessage("Error: Recording function not available in app.", 3000)
            return

        # Check if currently in live RealSense mode
        if not (self.app.frame_acquisition and self.app.frame_acquisition.mode == 'live'):
            QMessageBox.warning(self, "Recording Error", "Recording is only available when in Live Feed (Camera) mode with a RealSense camera active.")
            return

        # Suggest a filename, e.g., in config_dir or a dedicated recordings directory
        default_dir = os.path.join(self.config_dir, "recordings")
        os.makedirs(default_dir, exist_ok=True)
        default_filename = os.path.join(default_dir, f"recording_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.bag")

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save RealSense Recording", default_filename, "BAG files (*.bag)"
        )

        if filepath:
            if not filepath.endswith(".bag"):
                filepath += ".bag"
            self.app.start_video_recording(filepath)
            # UI update will be handled by update_recording_status callback from JugglingTracker

    def handle_stop_recording(self):
        """
        Handle the "Stop Recording" button click.
        Tells the app to stop recording.
        """
        if not self.app or not hasattr(self.app, 'stop_video_recording'):
            self.status_bar.showMessage("Error: Recording function not available in app.", 3000)
            return
        
        self.app.stop_video_recording()
        # UI update will be handled by update_recording_status callback

    def update_recording_status(self, is_recording, filepath=None):
        """
        Callback for JugglingTracker to update the UI about recording status.
        """
        self.is_app_recording = is_recording
        if is_recording:
            self.start_record_button.setEnabled(False)
            self.stop_record_button.setEnabled(True)
            self.feed_mode_combo.setEnabled(False) # Disable mode switching during recording
            self.select_video_button.setEnabled(False)
            base_filepath = os.path.basename(filepath) if filepath else "Unknown file"
            self.recording_status_label.setText(f"Status: Recording to {base_filepath}")
            self.status_bar.showMessage(f"Recording to {base_filepath}...", 0) # Persistent message
        else:
            self.start_record_button.setEnabled(True)
            self.stop_record_button.setEnabled(False)
            self.feed_mode_combo.setEnabled(True) # Re-enable mode switching
            # select_video_button state depends on feed_mode_combo, handled by on_feed_mode_changed
            self.on_feed_mode_changed(self.feed_mode_combo.currentIndex()) # Refresh video button state
            
            final_message = "Status: Not Recording"
            if filepath: # This means recording just stopped
                final_message = f"Status: Recording stopped. Saved to {os.path.basename(filepath)}"
                self.status_bar.showMessage(f"Recording saved: {os.path.basename(filepath)}", 5000)
            else: # Recording failed to start or general update
                 self.status_bar.clearMessage() # Or restore previous message

            self.recording_status_label.setText(final_message)
        self.update_recording_controls_state()


    def update_recording_controls_state(self):
        """
        Enables or disables recording controls based on current feed mode and app state.
        """
        can_record = False
        if self.app and hasattr(self.app, 'is_realsense_live_active'):
            can_record = self.app.is_realsense_live_active

        # Recording is only possible if live RealSense is active AND we are in "Live Feed" mode UI-wise.
        # The self.current_feed_mode check ensures UI consistency.
        # JugVid2cpp mode doesn't support recording since it's already processed data
        allow_recording_controls = (self.current_feed_mode == "live") and can_record

        if self.is_app_recording: # If app says it's recording
            self.start_record_button.setEnabled(False)
            self.stop_record_button.setEnabled(allow_recording_controls) # Should be true if recording
            self.feed_mode_combo.setEnabled(False) # Don't allow mode switch while recording
            self.select_video_button.setEnabled(False)
        else: # Not currently recording
            self.start_record_button.setEnabled(allow_recording_controls)
            self.stop_record_button.setEnabled(False)
            self.feed_mode_combo.setEnabled(True) # Allow mode switch
            # select_video_button state depends on current feed_mode_combo selection
            if self.feed_mode_combo.currentIndex() == 1: # "Recorded Feed"
                self.select_video_button.setEnabled(True)
            else:
                self.select_video_button.setEnabled(False)

    def sync_ui_to_app_state(self):
        """
        Synchronizes the UI elements (like feed mode combo) with the actual
        state of the JugglingTracker application's frame_acquisition module.
        This is crucial after app initialization or mode changes that might involve fallbacks.
        """
        if not self.app or not hasattr(self.app, 'frame_acquisition'):
            print("[MainWindow] sync_ui_to_app_state: App or frame_acquisition not available.")
            return

        app_fa_mode = self.app.frame_acquisition.mode
        app_video_path = getattr(self.app.frame_acquisition, 'video_path', None) # For playback

        print(f"[MainWindow] sync_ui_to_app_state: App FA mode='{app_fa_mode}', App video_path='{app_video_path}'")

        # Block signals to prevent on_feed_mode_changed from firing during sync
        self.feed_mode_combo.blockSignals(True)

        if app_fa_mode == 'playback':
            self.current_feed_mode = "playback"
            self.feed_mode_combo.setCurrentIndex(1) # "Recorded Feed (Video)"
            self.select_video_button.setEnabled(True)
            self.current_video_path = app_video_path # Sync video path
            if self.current_video_path:
                self.video_path_label.setText(os.path.basename(self.current_video_path))
            else:
                self.video_path_label.setText("No video selected")
        elif app_fa_mode == 'jugvid2cpp': # JugVid2cpp 3D Tracking
            self.current_feed_mode = "jugvid2cpp"
            self.feed_mode_combo.setCurrentIndex(2) # "JugVid2cpp 3D Tracking"
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("JugVid2cpp provides 3D ball positions directly")
        elif app_fa_mode == 'live': # RealSense
            self.current_feed_mode = "live"
            self.feed_mode_combo.setCurrentIndex(0) # "Live Feed (Camera)"
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("")
        elif app_fa_mode == 'live_webcam': # Webcam
            # Assuming 'Live Feed (Camera)' also covers webcam for simplicity in this UI.
            # If a dedicated "Webcam" option were in the combo, we'd select that.
            self.current_feed_mode = "live" # Treat as 'live' for UI's current_feed_mode logic
            self.feed_mode_combo.setCurrentIndex(0) # "Live Feed (Camera)"
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("")
        else:
            print(f"[MainWindow] sync_ui_to_app_state: Unknown app_fa_mode '{app_fa_mode}'")
            # Default to live if mode is unknown
            self.current_feed_mode = "live"
            self.feed_mode_combo.setCurrentIndex(0)
            self.select_video_button.setEnabled(False)
            self.video_path_label.setText("")

        self.feed_mode_combo.blockSignals(False)

        # Crucially, update recording controls based on the now-synced state
        self.update_recording_controls_state()

        # Update recording status display based on app's actual recording state
        if hasattr(self.app, 'is_currently_recording') and \
           hasattr(self.app.frame_acquisition, 'recording_filepath'):
            self.update_recording_status(self.app.is_currently_recording, self.app.frame_acquisition.recording_filepath)
        
        print(f"[MainWindow] sync_ui_to_app_state: UI synced. current_feed_mode='{self.current_feed_mode}', combo_index={self.feed_mode_combo.currentIndex()}")
        
        # Show/hide JugVid2cpp status panel based on current mode
        self.jugvid2cpp_group.setVisible(self.current_feed_mode == "jugvid2cpp")
    
    # Watch IMU Methods
    
    def on_watch_ips_changed(self):
        """Handle changes to the watch IPs input field."""
        # Enable/disable connect button based on input
        ips_text = self.watch_ips_input.text().strip()
        self.connect_watches_btn.setEnabled(bool(ips_text))
    
    def discover_watches(self):
        """Discover watches on the network."""
        if not self.app or not hasattr(self.app, 'watch_imu_manager'):
            self.status_bar.showMessage("Watch IMU Manager not available", 3000)
            return
        
        self.status_bar.showMessage("Discovering watches...", 0)
        self.discover_watches_btn.setEnabled(False)
        
        try:
            # Run discovery in a separate thread to avoid blocking UI
            import threading
            def discovery_thread():
                try:
                    discovered = self.app.watch_imu_manager.discover_watches()
                    # Update UI in main thread
                    self.update_watch_discovery_results(discovered)
                except Exception as e:
                    self.update_watch_discovery_results({}, str(e))
            
            thread = threading.Thread(target=discovery_thread, daemon=True)
            thread.start()
        except Exception as e:
            self.status_bar.showMessage(f"Discovery failed: {e}", 5000)
            self.discover_watches_btn.setEnabled(True)
    
    def update_watch_discovery_results(self, discovered_watches, error=None):
        """Update UI with discovery results (called from discovery thread)."""
        if error:
            self.status_bar.showMessage(f"Discovery failed: {error}", 5000)
            self.discover_watches_btn.setEnabled(True)
            return
        
        if discovered_watches:
            # Update the IP input field with discovered IPs
            ip_list = list(discovered_watches.keys())
            self.watch_ips_input.setText(", ".join(ip_list))
            self.status_bar.showMessage(f"Discovered {len(discovered_watches)} watches", 3000)
        else:
            self.status_bar.showMessage("No watches discovered", 3000)
        
        self.discover_watches_btn.setEnabled(True)
        self.update_watch_status_display()
    
    def connect_watches(self):
        """Connect to the specified watches."""
        # Debug mode check
        debug_imu = getattr(self.app, 'debug_imu', False) if self.app else False
        
        if debug_imu:
            print("📱 [DEBUG] connect_watches() called")
        
        ips_text = self.watch_ips_input.text().strip()
        if debug_imu:
            print(f"📱 [DEBUG] Raw IP input: '{ips_text}'")
        
        if not ips_text:
            if debug_imu:
                print("📱 [DEBUG] No IP addresses entered")
            self.status_bar.showMessage("Please enter watch IP addresses", 3000)
            return
        
        # Parse IP addresses
        ip_list = [ip.strip() for ip in ips_text.split(',') if ip.strip()]
        if debug_imu:
            print(f"📱 [DEBUG] Parsed IP list: {ip_list}")
        
        if not ip_list:
            if debug_imu:
                print("📱 [DEBUG] No valid IP addresses found")
            self.status_bar.showMessage("Please enter valid IP addresses", 3000)
            return
        
        self.status_bar.showMessage("Connecting to watches...", 0)
        self.connect_watches_btn.setEnabled(False)
        
        try:
            # Initialize or recreate Watch IMU Manager with the GUI-provided IPs
            try:
                if debug_imu:
                    print("📱 [DEBUG] Importing WatchIMUManager...")
                from core.imu.smart_imu_manager import WatchIMUManager  # Use the high-performance version
                
                # Clean up existing manager if it exists
                if hasattr(self.app, 'watch_imu_manager') and self.app.watch_imu_manager is not None:
                    if debug_imu:
                        print("📱 [DEBUG] Cleaning up existing watch manager...")
                    self.app.watch_imu_manager.cleanup()
                
                # Create new manager with GUI-provided IPs
                if debug_imu:
                    print(f"📱 [DEBUG] Creating WatchIMUManager with IPs: {ip_list}")
                self.app.watch_imu_manager = WatchIMUManager(watch_ips=ip_list)
                print(f"📱 Watch IMU Manager initialized for IPs: {ip_list}")
                
            except ImportError as import_error:
                print(f"📱 [ERROR] Failed to import WatchIMUManager: {import_error}")
                self.status_bar.showMessage(f"Import error: {import_error}", 5000)
                self.connect_watches_btn.setEnabled(True)
                return
            except Exception as init_error:
                print(f"📱 [ERROR] Failed to initialize WatchIMUManager: {init_error}")
                import traceback
                traceback.print_exc()
                self.status_bar.showMessage(f"Initialization failed: {init_error}", 5000)
                self.connect_watches_btn.setEnabled(True)
                return
            
            # Discover and connect
            try:
                if debug_imu:
                    print("📱 [DEBUG] Starting watch discovery...")
                discovered = self.app.watch_imu_manager.discover_watches()
                print(f"📱 Discovered watches: {discovered}")
            except Exception as discovery_error:
                print(f"📱 [ERROR] Watch discovery failed: {discovery_error}")
                import traceback
                traceback.print_exc()
                self.status_bar.showMessage(f"Discovery failed: {discovery_error}", 5000)
                self.connect_watches_btn.setEnabled(True)
                return
            
            if discovered:
                try:
                    if debug_imu:
                        print("📱 [DEBUG] Starting streaming...")
                    # Start streaming
                    self.app.watch_imu_manager.start_streaming()
                    if hasattr(self.app.watch_imu_manager, 'start_monitoring'):
                        if debug_imu:
                            print("📱 [DEBUG] Starting monitoring...")
                        self.app.watch_imu_manager.start_monitoring()
                    
                    self.imu_status_label.setText("Status: Connected")
                    self.imu_status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.connect_watches_btn.setEnabled(False)
                    self.disconnect_watches_btn.setEnabled(True)
                    self.open_imu_monitor_btn.setEnabled(True)  # Enable advanced monitor
                    self.status_bar.showMessage(f"Connected to {len(discovered)} watches", 3000)
                    print(f"🚀 Watch IMU streaming started for {len(discovered)} watches")
                except Exception as streaming_error:
                    print(f"📱 [ERROR] Failed to start streaming: {streaming_error}")
                    import traceback
                    traceback.print_exc()
                    self.status_bar.showMessage(f"Streaming failed: {streaming_error}", 5000)
                    self.connect_watches_btn.setEnabled(True)
                    return
            else:
                print("📱 [WARNING] No watches discovered")
                self.status_bar.showMessage("Failed to connect to any watches", 5000)
                self.connect_watches_btn.setEnabled(True)
            
            self.update_watch_status_display()
            
        except Exception as e:
            print(f"📱 [ERROR] Watch connection error: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Connection failed: {e}", 5000)
            self.connect_watches_btn.setEnabled(True)
    
    def disconnect_watches(self):
        """Disconnect from all watches."""
        if not self.app or not hasattr(self.app, 'watch_imu_manager') or self.app.watch_imu_manager is None:
            self.status_bar.showMessage("No watch connection to disconnect", 3000)
            return
        
        try:
            # Clean up the watch IMU manager
            self.app.watch_imu_manager.cleanup()
            self.app.watch_imu_manager = None  # Clear the reference
            
            # Update UI to reflect disconnected state
            self.imu_status_label.setText("Status: Disconnected")
            self.imu_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_watches_btn.setEnabled(True)
            self.disconnect_watches_btn.setEnabled(False)
            self.open_imu_monitor_btn.setEnabled(False)  # Disable advanced monitor
            self.imu_data_display.setText("No IMU data received")
            self.imu_data_display.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
            
            # Clear watch details list
            self.watch_details_list.clear()
            
            self.status_bar.showMessage("Disconnected from watches", 3000)
            print("🔌 Watch IMU connections closed")
            
        except Exception as e:
            print(f"Error during disconnect: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Disconnect failed: {e}", 5000)
    
    def update_watch_status_display(self):
        """Update the watch details list with current status."""
        self.watch_details_list.clear()
        
        if not self.app or not hasattr(self.app, 'watch_imu_manager'):
            return
        
        # Get status from the manager
        try:
            if hasattr(self.app.watch_imu_manager, 'controller') and self.app.watch_imu_manager.controller.watch_ports:
                for ip, port in self.app.watch_imu_manager.controller.watch_ports.items():
                    status_text = f"{ip}:{port} - Connected"
                    item = QListWidgetItem(status_text)
                    item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton))
                    self.watch_details_list.addItem(item)
            elif self.app.watch_imu_manager.watch_ips:
                for ip in self.app.watch_imu_manager.watch_ips:
                    status_text = f"{ip} - Disconnected"
                    item = QListWidgetItem(status_text)
                    item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCancelButton))
                    self.watch_details_list.addItem(item)
        except Exception as e:
            print(f"Error updating watch status display: {e}")
    
    def update_imu_data_display(self):
        """Update the IMU data display with latest data (simplified for better performance)."""
        if not self.app:
            return
        
        try:
            # Get processed IMU data from the main tracker (not directly from watch manager)
            latest_imu_data = getattr(self.app, 'latest_imu_data', {})
            
            # Check if watch manager exists and has active connections
            has_watch_manager = hasattr(self.app, 'watch_imu_manager') and self.app.watch_imu_manager
            has_connection = False
            
            if has_watch_manager:
                # Check if high-performance system is connected (even without data)
                if hasattr(self.app.watch_imu_manager, 'high_perf_manager'):
                    # High-performance system - check if streaming is active
                    has_connection = getattr(self.app.watch_imu_manager.high_perf_manager, 'running', False)
                elif hasattr(self.app.watch_imu_manager, 'controller'):
                    # Legacy system - check if controller has connections
                    has_connection = bool(getattr(self.app.watch_imu_manager.controller, 'watch_ports', {}))
            
            if latest_imu_data:
                # Enable Advanced IMU Monitor button when we have IMU data
                if not self.open_imu_monitor_btn.isEnabled():
                    self.open_imu_monitor_btn.setEnabled(True)
                    self.imu_status_label.setText("Status: Connected (High-Performance)")
                    self.imu_status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Update IMU feeds with latest data
                self._update_imu_feeds(latest_imu_data)
                
                # Simplified display - show only key information to prevent clutter
                watch_count = len(latest_imu_data)
                if watch_count == 1:
                    # Single watch - show more detail
                    watch_name, data = next(iter(latest_imu_data.items()))
                    accel_magnitude = data.get('accel_magnitude', 0)
                    gyro_magnitude = data.get('gyro_magnitude', 0)
                    data_age_ms = data.get('data_age', 0) * 1000
                    
                    display_text = (
                        f"Watch: {watch_name.upper()} | "
                        f"Accel: {accel_magnitude:.2f} m/s² | "
                        f"Gyro: {gyro_magnitude:.2f} rad/s | "
                        f"Age: {data_age_ms:.0f}ms"
                    )
                else:
                    # Multiple watches - show summary
                    total_accel = sum(data.get('accel_magnitude', 0) for data in latest_imu_data.values())
                    total_gyro = sum(data.get('gyro_magnitude', 0) for data in latest_imu_data.values())
                    avg_age = sum(data.get('data_age', 0) for data in latest_imu_data.values()) / watch_count * 1000
                    
                    display_text = (
                        f"{watch_count} Watches Connected | "
                        f"Total Motion: A={total_accel:.2f} G={total_gyro:.2f} | "
                        f"Avg Age: {avg_age:.0f}ms"
                    )
                
                self.imu_data_display.setText(display_text)
                self.imu_data_display.setStyleSheet("background-color: #e8f5e8; padding: 5px; border: 1px solid #4CAF50;")
            elif has_connection:
                # Enable Advanced IMU Monitor button when connected (even without data)
                if not self.open_imu_monitor_btn.isEnabled():
                    self.open_imu_monitor_btn.setEnabled(True)
                    self.imu_status_label.setText("Status: Connected (High-Performance)")
                    self.imu_status_label.setStyleSheet("color: green; font-weight: bold;")
                
                self.imu_data_display.setText("Connected - Waiting for sensor data... (Use Advanced Monitor for details)")
                self.imu_data_display.setStyleSheet("background-color: #fff3cd; padding: 5px; border: 1px solid #ffc107;")
            else:
                # Disable Advanced IMU Monitor button when no connection
                if self.open_imu_monitor_btn.isEnabled():
                    self.open_imu_monitor_btn.setEnabled(False)
                
                if has_watch_manager:
                    self.imu_status_label.setText("Status: Not Connected")
                    self.imu_status_label.setStyleSheet("color: red; font-weight: bold;")
                    self.imu_data_display.setText("No IMU data - Connect watches to see live sensor data")
                    self.imu_data_display.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
                else:
                    self.imu_status_label.setText("Status: Not Available")
                    self.imu_status_label.setStyleSheet("color: red; font-weight: bold;")
                    self.imu_data_display.setText("Watch IMU Manager not available")
                    self.imu_data_display.setStyleSheet("background-color: #f8d7da; padding: 5px; border: 1px solid #dc3545;")
        except Exception as e:
            print(f"Error updating IMU data display: {e}")
            self.imu_data_display.setText(f"Error: {str(e)}")
            self.imu_data_display.setStyleSheet("background-color: #f8d7da; padding: 5px; border: 1px solid #dc3545;")
    
    def _update_imu_feeds(self, latest_imu_data):
        """Update IMU feeds with the latest sensor data."""
        try:
            # Get current IMU feed IDs
            imu_feeds = self.video_feed_manager.get_imu_feeds()
            
            # Create IMU feeds for new watches if they don't exist
            for watch_name, data in latest_imu_data.items():
                feed_id = f"imu_{watch_name}"
                
                if feed_id not in imu_feeds:
                    # Create new IMU feed for this watch
                    feed_name = f"{watch_name.upper()} Watch IMU"
                    self.video_feed_manager.add_imu_feed(feed_name, feed_id, watch_name)
                    print(f"Created IMU feed for {watch_name} watch")
                
                # Update the feed with latest data
                # Convert the processed data back to the expected format
                imu_data_for_feed = {
                    'timestamp': data.get('timestamp', time.time()),
                    'accel_x': data.get('accel_x', 0.0),
                    'accel_y': data.get('accel_y', 0.0),
                    'accel_z': data.get('accel_z', 0.0),
                    'gyro_x': data.get('gyro_x', 0.0),
                    'gyro_y': data.get('gyro_y', 0.0),
                    'gyro_z': data.get('gyro_z', 0.0),
                    'watch_name': watch_name
                }
                
                self.video_feed_manager.update_imu_feed(feed_id, imu_data_for_feed)
            
            # Remove feeds for watches that are no longer active
            active_watch_names = set(latest_imu_data.keys())
            for feed_id in imu_feeds[:]:  # Create a copy to iterate over
                if feed_id.startswith("imu_"):
                    watch_name = feed_id[4:]  # Remove "imu_" prefix
                    if watch_name not in active_watch_names:
                        print(f"Removing IMU feed for inactive {watch_name} watch")
                        self.video_feed_manager.remove_feed(feed_id)
                        
        except Exception as e:
            print(f"Error updating IMU feeds: {e}")
            import traceback
            traceback.print_exc()
    
    def open_imu_monitoring_window(self):
        """Open the advanced IMU monitoring window."""
        if self.imu_monitoring_window is None:
            self.imu_monitoring_window = IMUMonitoringWindow(self, self.app)
        
        # Show the window
        self.imu_monitoring_window.show()
        self.imu_monitoring_window.raise_()
        self.imu_monitoring_window.activateWindow()
    
    # Video Feed Management Methods
    
    def add_video_feed(self, feed_name, feed_id=None):
        """
        Add a new video feed to the display.
        
        Args:
            feed_name (str): Display name for the feed
            feed_id (str, optional): Unique ID for the feed
            
        Returns:
            str: The feed ID
        """
        return self.video_feed_manager.add_feed(feed_name, feed_id)
    
    def remove_video_feed(self, feed_id):
        """
        Remove a video feed from the display.
        
        Args:
            feed_id (str): ID of the feed to remove
            
        Returns:
            bool: True if feed was removed, False if not found
        """
        return self.video_feed_manager.remove_feed(feed_id)
    
    def get_feed_latencies(self):
        """
        Get latency information for all active feeds.
        
        Returns:
            dict: feed_id -> latency_ms
        """
        return self.video_feed_manager.get_feed_latencies()
    
    def get_feed_fps(self):
        """
        Get FPS information for all active feeds.
        
        Returns:
            dict: feed_id -> fps
        """
        return self.video_feed_manager.get_feed_fps()
    
    def set_feed_name(self, feed_id, name):
        """
        Set the display name for a feed.
        
        Args:
            feed_id (str): ID of the feed
            name (str): New display name
        """
        self.video_feed_manager.set_feed_name(feed_id, name)
    
    def clear_all_feeds(self):
        """Remove all video feeds."""
        self.video_feed_manager.clear_all_feeds()
    
    # Testing and Demo Methods
    
    def demo_feed_configurations(self):
        """Demo method to test different feed configurations."""
        print("Starting feed configuration demo...")
        
        # Clear existing feeds
        self.clear_all_feeds()
        
        # Test 1 feed
        print("Testing 1 feed...")
        self.add_video_feed("Main Camera", "main")
        
        # Test 3 feeds (single row)
        QTimer.singleShot(2000, lambda: self._demo_add_feeds(3))
        
        # Test 6 feeds (two rows)
        QTimer.singleShot(4000, lambda: self._demo_add_feeds(6))
        
        # Test back to 2 feeds
        QTimer.singleShot(6000, lambda: self._demo_add_feeds(2))
    
    def _demo_add_feeds(self, target_count):
        """Helper method for demo."""
        current_count = self.video_feed_manager.get_feed_count()
        
        if target_count > current_count:
            # Add feeds
            for i in range(current_count, target_count):
                feed_names = ["Main Camera", "Depth View", "Mask View", "Tracking View", "Debug View", "Analysis View"]
                name = feed_names[i] if i < len(feed_names) else f"Feed {i+1}"
                self.add_video_feed(name, f"feed_{i}")
        elif target_count < current_count:
            # Remove feeds
            feed_ids = self.video_feed_manager.get_feed_ids()
            for i in range(target_count, current_count):
                if i < len(feed_ids):
                    self.remove_video_feed(feed_ids[i])
        
        print(f"Updated to {target_count} feeds")
    
    def get_latency_summary(self):
        """
        Get a summary of latency information for display.
        
        Returns:
            str: Formatted latency summary
        """
        latencies = self.get_feed_latencies()
        fps_data = self.get_feed_fps()
        
        if not latencies:
            return "No active feeds"
        
        summary_lines = []
        for feed_id, latency in latencies.items():
            fps = fps_data.get(feed_id, 0.0)
            summary_lines.append(f"{feed_id}: {latency:.1f}ms, {fps:.1f}fps")
        
        return " | ".join(summary_lines)
    
    def update_jugvid2cpp_status_display(self):
        """Update the JugVid2cpp status display with latest information."""
        if not self.app or self.current_feed_mode != "jugvid2cpp":
            return
        
        try:
            # Check if JugVid2cpp interface is available and get status
            if hasattr(self.app, 'frame_acquisition') and hasattr(self.app.frame_acquisition, 'get_status'):
                status = self.app.frame_acquisition.get_status()
                
                # Update connection status
                if status.get('is_running', False):
                    if status.get('error_state', False):
                        self.jugvid2cpp_status_label.setText("Status: Error")
                        self.jugvid2cpp_status_label.setStyleSheet("color: red; font-weight: bold;")
                        self.jugvid2cpp_error_label.setText(status.get('error_message', 'Unknown error'))
                    else:
                        self.jugvid2cpp_status_label.setText("Status: Connected")
                        self.jugvid2cpp_status_label.setStyleSheet("color: green; font-weight: bold;")
                        self.jugvid2cpp_error_label.setText("")
                else:
                    self.jugvid2cpp_status_label.setText("Status: Not Running")
                    self.jugvid2cpp_status_label.setStyleSheet("color: red; font-weight: bold;")
                    self.jugvid2cpp_error_label.setText(status.get('error_message', ''))
                
                # Update ball tracking information
                ball_count = status.get('last_frame_ball_count', 0)
                queue_size = status.get('queue_size', 0)
                
                if ball_count > 0:
                    # Get actual ball data for display
                    if hasattr(self.app.frame_acquisition, 'get_identified_balls'):
                        balls = self.app.frame_acquisition.get_identified_balls()
                        ball_info_lines = []
                        for ball in balls[:3]:  # Show up to 3 balls to avoid clutter
                            if 'original_3d' in ball:
                                x, y, z = ball['original_3d']
                                ball_info_lines.append(f"{ball['name']}: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
                        
                        if len(balls) > 3:
                            ball_info_lines.append(f"... and {len(balls) - 3} more")
                        
                        display_text = f"Tracking {ball_count} balls | Queue: {queue_size}\n" + "\n".join(ball_info_lines)
                    else:
                        display_text = f"Tracking {ball_count} balls | Queue: {queue_size}"
                    
                    self.jugvid2cpp_balls_label.setText(display_text)
                    self.jugvid2cpp_balls_label.setStyleSheet("background-color: #e8f5e8; padding: 5px; border: 1px solid #4CAF50; font-size: 11px;")
                else:
                    self.jugvid2cpp_balls_label.setText(f"No balls detected | Queue: {queue_size}")
                    self.jugvid2cpp_balls_label.setStyleSheet("background-color: #fff3cd; padding: 5px; border: 1px solid #ffc107; font-size: 11px;")
            
            else:
                # JugVid2cpp interface not available
                self.jugvid2cpp_status_label.setText("Status: Interface Not Available")
                self.jugvid2cpp_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.jugvid2cpp_balls_label.setText("JugVid2cpp interface not initialized")
                self.jugvid2cpp_balls_label.setStyleSheet("background-color: #f8d7da; padding: 5px; border: 1px solid #dc3545; font-size: 11px;")
                self.jugvid2cpp_error_label.setText("Check that JugVid2cpp executable is available")
        
        except Exception as e:
            print(f"Error updating JugVid2cpp status display: {e}")
            self.jugvid2cpp_status_label.setText("Status: Display Error")
            self.jugvid2cpp_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.jugvid2cpp_error_label.setText(f"Display error: {str(e)}")
    
    # IMU Feed Management Methods
    
    def toggle_imu_feeds(self, checked=None):
        """
        Toggle IMU feeds visibility.
        
        Args:
            checked (bool): New state (optional)
        """
        if checked is None:
            checked = self.toggle_imu_feeds_action.isChecked()
        
        if checked:
            # Enable IMU feeds - they will be created automatically when data arrives
            self.status_bar.showMessage("IMU feeds enabled", 3000)
        else:
            # Disable IMU feeds - remove all existing IMU feeds
            imu_feeds = self.video_feed_manager.get_imu_feeds()
            for feed_id in imu_feeds:
                self.video_feed_manager.remove_feed(feed_id)
            self.status_bar.showMessage("IMU feeds disabled", 3000)
        
        self.toggle_imu_feeds_action.setChecked(checked)
    
    def clear_all_imu_feed_data(self):
        """Clear data from all IMU feeds."""
        imu_feeds = self.video_feed_manager.get_imu_feeds()
        for feed_id in imu_feeds:
            self.video_feed_manager.clear_imu_feed_data(feed_id)
        
        self.status_bar.showMessage(f"Cleared data from {len(imu_feeds)} IMU feeds", 3000)
    
    def add_imu_feed_for_watch(self, watch_name):
        """
        Add an IMU feed for a specific watch.
        
        Args:
            watch_name (str): Name of the watch (left, right, etc.)
            
        Returns:
            str: The feed ID
        """
        if not self.toggle_imu_feeds_action.isChecked():
            return None  # IMU feeds are disabled
        
        feed_id = f"imu_{watch_name}"
        feed_name = f"{watch_name.upper()} Watch IMU"
        
        # Check if feed already exists
        if feed_id in self.video_feed_manager.feeds:
            return feed_id
        
        # Create the IMU feed
        return self.video_feed_manager.add_imu_feed(feed_name, feed_id, watch_name)
    
    def remove_imu_feed_for_watch(self, watch_name):
        """
        Remove an IMU feed for a specific watch.
        
        Args:
            watch_name (str): Name of the watch
            
        Returns:
            bool: True if feed was removed
        """
        feed_id = f"imu_{watch_name}"
        return self.video_feed_manager.remove_feed(feed_id)
    
    def configure_imu_feed_settings(self, history_length=100, auto_scale=True):
        """
        Configure settings for all IMU feeds.
        
        Args:
            history_length (int): Number of data points to keep in history
            auto_scale (bool): Enable auto-scaling of graphs
        """
        imu_feeds = self.video_feed_manager.get_imu_feeds()
        for feed_id in imu_feeds:
            self.video_feed_manager.set_imu_feed_settings(
                feed_id,
                history_length=history_length,
                auto_scale=auto_scale
            )
        
        self.status_bar.showMessage(f"Updated settings for {len(imu_feeds)} IMU feeds", 3000)
    
    def get_imu_feed_latencies(self):
        """
        Get latency information for all IMU feeds.
        
        Returns:
            dict: feed_id -> latency_ms
        """
        imu_feeds = self.video_feed_manager.get_imu_feeds()
        latencies = {}
        
        for feed_id in imu_feeds:
            if feed_id in self.video_feed_manager.feeds:
                latencies[feed_id] = self.video_feed_manager.feeds[feed_id].get_latency()
        
        return latencies
    
    def get_imu_feed_fps(self):
        """
        Get FPS information for all IMU feeds.
        
        Returns:
            dict: feed_id -> fps
        """
        imu_feeds = self.video_feed_manager.get_imu_feeds()
        fps_data = {}
        
        for feed_id in imu_feeds:
            if feed_id in self.video_feed_manager.feeds:
                fps_data[feed_id] = self.video_feed_manager.feeds[feed_id].get_fps()
        
        return fps_data