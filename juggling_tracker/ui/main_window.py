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
        
        # Set up timer for UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(33)  # ~30 FPS
        
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
        
        # Create video display widget
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #000000;")
        
        # Add video display to main layout
        self.main_layout.addWidget(self.video_label)
        
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

        # Add all groups to main layout
        self.main_layout.addWidget(self.feed_source_group)
        self.main_layout.addWidget(self.recording_group) # Add recording group
        self.main_layout.addWidget(self.watch_imu_group) # Add Watch IMU group
        self.main_layout.addWidget(self.ball_controls_container)
        self.main_layout.addWidget(self.simple_tracking_settings_btn)
        self.main_layout.addWidget(self.tracked_balls_scroll)
        
        # Mouse event handling for the video label
        if hasattr(self, 'video_label'):
            self.video_label.mousePressEvent = self.video_label_mouse_press
            self.video_label.mouseMoveEvent = self.video_label_mouse_move
            self.video_label.mouseReleaseEvent = self.video_label_mouse_release
            self.video_label.setMouseTracking(True)  # Important for mouseMoveEvent without button press
        
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
        """
        # This method will be called by the timer to update the UI
        # Update IMU data display if available
        self.update_imu_data_display()
    
    def update_frame(self, color_image, depth_image=None, masks=None, identified_balls=None,
                    hand_positions=None, extension_results=None, debug_info=None, tracked_balls_for_display=None, simple_tracking=None):
        """
        Update the video display with a new frame.
        
        Args:
            color_image: Color image in BGR format
            depth_image: Depth image (optional)
            masks: Dictionary of mask_name -> mask (optional)
            identified_balls: Dictionary of ball_name -> blob (optional) - DEPRECATED, use tracked_balls_for_display instead
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y)) (optional)
            extension_results: Dictionary of extension_name -> results (optional)
            debug_info: Dictionary of debug information (optional)
            tracked_balls_for_display: List of dictionaries containing tracked ball information (optional)
            simple_tracking: Dictionary containing simple tracking results (optional)
        """
        if color_image is None:
            print("Warning: update_frame called with None color_image")
            return
        
        # First, make a copy of the color image to draw on
        display_image = color_image.copy()
        
        # Create a composite view with color and depth images
        composite = self.create_composite_view(color_image, depth_image, masks)
        
        # ------------ TEMPORARY DEBUG START ------------
        if composite is not None:
            print(f"[MainWindow] update_frame: Composite image for QImage: shape={composite.shape}, dtype={composite.dtype}, flags={composite.flags.c_contiguous}")
            # Ensure composite is C-contiguous
            if not composite.flags['C_CONTIGUOUS']:
                print("[MainWindow] update_frame: Composite not C-contiguous, making it so.")
                composite = np.ascontiguousarray(composite)
        else:
            print("[MainWindow] update_frame: Composite is None before QImage creation!")
            return # Can't proceed
        # ------------ TEMPORARY DEBUG END ------------

        # Convert the OpenCV image to a Qt image
        height, width, channel = composite.shape
        bytes_per_line = 3 * width
        q_img = QImage(composite.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        
        # Create a pixmap from the Qt image
        pixmap_to_display = QPixmap.fromImage(q_img)
        
        # Create a copy of the pixmap for drawing
        final_pixmap_for_display = pixmap_to_display.copy()
        painter = QPainter(final_pixmap_for_display)
        
        # Draw tracked balls if available
        if tracked_balls_for_display:
            # Store the tracked balls data for the panel
            self.tracked_balls_data = tracked_balls_for_display
            
            # Update the tracked balls panel
            self.update_tracked_balls_panel()
            
            for ball_info in tracked_balls_for_display:
                # Extract ball information
                pos_x, pos_y = int(ball_info['position_2d'][0]), int(ball_info['position_2d'][1])
                radius = int(ball_info['radius_px'])
                ball_name = ball_info['name']
                ball_id_display = ball_info['id']
                
                # Skip drawing if position is outside the visible area
                # This prevents drawing on the depth image portion if it's shown
                if self.show_depth and pos_x >= color_image.shape[1]:
                    continue
                
                # Set pen color based on profile_id to distinguish different balls
                # Create a simple hash of the profile_id to get a consistent color
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
                
                # Use gray for disappeared balls, otherwise use the profile-specific color
                if ball_info['disappeared_frames'] > 0:
                    pen_color = Qt.GlobalColor.yellow  # Yellow for predicted positions
                else:
                    pen_color = QColor(r, g, b)
                
                # Set up pen for drawing - make it more visible with thicker line
                pen = QPen(pen_color, 3)  # 3px thick line for better visibility
                painter.setPen(pen)
                
                # Draw the ball circle
                if radius > 0:
                    # Draw a more visible circle around the ball
                    painter.drawEllipse(pos_x - radius, pos_y - radius, radius * 2, radius * 2)
                
                # Draw text with contrasting background for better visibility
                text = f"{ball_name} (ID:{ball_id_display})"
                
                # Create a background rectangle for text
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
        
        # Draw simple tracking results if available and enabled
        if simple_tracking and self.show_simple_tracking:
            # Draw average position
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
        
        # Draw ROI rectangle if in ball definition mode
        if self.is_defining_ball_mode and self.defining_roi_current_rect:
            pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            x, y, w, h = self.defining_roi_current_rect
            
            # Only draw ROI on the color image portion if depth is shown
            if self.show_depth and x >= color_image.shape[1]:
                # Skip drawing ROI on depth image portion
                pass
            else:
                painter.drawRect(x, y, w, h)
        
        # End painting and display the result
        painter.end()
        self.video_label.setPixmap(final_pixmap_for_display)
        
        # Update status bar
        if debug_info:
            if 'Num Identified Balls' in debug_info:
                self.balls_label.setText(f"Balls: {debug_info['Num Identified Balls']}")
            
            if 'Mode' in debug_info:
                self.mode_label.setText(f"Mode: {debug_info['Mode']}")
        
        # Update FPS
        if hasattr(self.app, 'fps'):
            self.fps_label.setText(f"FPS: {self.app.fps:.1f}")
    
    def create_composite_view(self, color_image, depth_image=None, masks=None):
        if color_image is None:
            print("[MainWindow] create_composite_view: color_image is None, returning black.")
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Determine what views to show
        views_to_show = []
        
        # Add color view if enabled
        if self.show_color:
            views_to_show.append(('color', color_image.copy()))
            print(f"[MainWindow] create_composite_view: Adding color view: {color_image.shape}")
        
        # Add depth view if enabled and available
        if depth_image is not None and self.show_depth:
            print(f"[MainWindow] create_composite_view: Processing depth image. Shape: {depth_image.shape}, dtype: {depth_image.dtype}")
            try:
                # Ensure depth_image is 2D if it's not already (it should be)
                if len(depth_image.shape) == 3:
                    depth_image_gray = depth_image[:,:,0] # Or handle as error
                    print(f"[MainWindow] Warning: Depth image was 3-channel, took first channel. Shape: {depth_image_gray.shape}")
                else:
                    depth_image_gray = depth_image

                # Normalize depth image for visualization
                # Check for empty or all-zero depth image to avoid errors with convertScaleAbs
                if np.any(depth_image_gray): # Only process if there's some data
                    depth_normalized = cv2.convertScaleAbs(depth_image_gray, alpha=0.03) # Adjust alpha if needed
                else:
                    depth_normalized = np.zeros_like(depth_image_gray, dtype=np.uint8) # Black if empty
                
                print(f"[MainWindow] create_composite_view: Depth normalized. Shape: {depth_normalized.shape}, dtype: {depth_normalized.dtype}")

                depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
                print(f"[MainWindow] create_composite_view: Depth colormap. Shape: {depth_colormap.shape}")
                
                # Resize depth colormap to match color image dimensions
                target_height = color_image.shape[0]
                target_width = color_image.shape[1]
                
                # Ensure depth_colormap is not empty before resizing
                if depth_colormap.size == 0:
                    print("[MainWindow] Error: depth_colormap is empty before resize.")
                    # Fallback: create a black image of target size
                    depth_colormap_resized = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                elif depth_colormap.shape[0] != target_height or depth_colormap.shape[1] != target_width:
                    depth_colormap_resized = cv2.resize(depth_colormap, (target_width, target_height))
                    print(f"[MainWindow] create_composite_view: Depth colormap resized. Shape: {depth_colormap_resized.shape}")
                else:
                    depth_colormap_resized = depth_colormap # No resize needed

                views_to_show.append(('depth', depth_colormap_resized))
                print(f"[MainWindow] create_composite_view: Adding depth view: {depth_colormap_resized.shape}")
                
            except Exception as e:
                print(f"[MainWindow] Error creating depth colormap: {e}")
        
        # Add mask view if enabled and available
        if masks is not None and self.show_masks:
            try:
                # Show only the combined mask (the most relevant one for simple tracking)
                combined_mask = masks.get('Combined')
                if combined_mask is not None:
                    # Convert mask to BGR for visualization
                    mask_bgr = cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR)
                    
                    # Add the mask name
                    cv2.putText(mask_bgr, "Proximity Mask", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Resize mask to match color image dimensions
                    target_height = color_image.shape[0]
                    target_width = color_image.shape[1]
                    mask_resized = cv2.resize(mask_bgr, (target_width, target_height))
                    
                    views_to_show.append(('mask', mask_resized))
                    print(f"[MainWindow] create_composite_view: Adding mask view: {mask_resized.shape}")
                else:
                    print("Warning: Combined mask not found in masks dictionary")
            except Exception as e:
                print(f"[MainWindow] Error processing masks: {e}")
        
        # Add simple tracking mask view if enabled and available
        if self.show_simple_tracking_mask and self.app and hasattr(self.app, 'simple_tracker'):
            try:
                # Generate the proximity mask independently for simple tracking visualization
                proximity_mask = None
                
                # We need to recreate the proximity mask from the depth data
                if hasattr(self.app, 'depth_processor') and hasattr(self.app, 'last_depth_image_for_def') and hasattr(self.app, 'frame_acquisition'):
                    # Get the current depth data
                    depth_image = getattr(self.app, 'last_depth_image_for_def', None)
                    depth_scale = self.app.frame_acquisition.get_depth_scale() if hasattr(self.app.frame_acquisition, 'get_depth_scale') else 0.001
                    
                    if depth_image is not None:
                        # Process depth to meters
                        depth_in_meters = self.app.depth_processor.process_depth_frame(None, depth_image, depth_scale)
                        
                        # Create proximity mask
                        proximity_mask = self.app.depth_processor.create_proximity_mask(depth_in_meters)
                        proximity_mask = self.app.depth_processor.cleanup_mask(proximity_mask)
                        
                        # Apply hand mask removal if available
                        if hasattr(self.app, 'skeleton_detector') and hasattr(self.app, 'last_color_image_for_def'):
                            color_image_for_hands = getattr(self.app, 'last_color_image_for_def', None)
                            if color_image_for_hands is not None:
                                pose_landmarks = self.app.skeleton_detector.detect_skeleton(color_image_for_hands)
                                hand_positions = self.app.skeleton_detector.get_hand_positions(pose_landmarks, color_image_for_hands.shape)
                                hand_mask = self.app.skeleton_detector.create_hand_mask(hand_positions, color_image_for_hands.shape)
                                proximity_mask = cv2.bitwise_and(proximity_mask, cv2.bitwise_not(hand_mask))
                elif masks and 'Combined' in masks:
                    # Fallback to using the existing combined mask if available
                    proximity_mask = masks['Combined']
                
                if proximity_mask is not None:
                    # Get the tracking visualization mask
                    min_size = getattr(self.app.depth_processor, 'min_object_size', 50) if hasattr(self.app, 'depth_processor') else 50
                    max_size = getattr(self.app.depth_processor, 'max_object_size', 5000) if hasattr(self.app, 'depth_processor') else 5000
                    
                    tracking_mask = self.app.simple_tracker.get_tracking_visualization_mask(
                        proximity_mask, min_size, max_size
                    )
                    
                    # Add title to the tracking mask
                    cv2.putText(tracking_mask, "Simple Tracking Mask", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # Resize tracking mask to match color image dimensions
                    target_height = color_image.shape[0]
                    target_width = color_image.shape[1]
                    tracking_mask_resized = cv2.resize(tracking_mask, (target_width, target_height))
                    
                    views_to_show.append(('simple_tracking_mask', tracking_mask_resized))
                    print(f"[MainWindow] create_composite_view: Adding simple tracking mask view: {tracking_mask_resized.shape}")
                else:
                    print("Warning: No depth data available for simple tracking visualization")
            except Exception as e:
                print(f"[MainWindow] Error creating simple tracking mask: {e}")
        
        # Create composite based on enabled views
        if not views_to_show:
            # If no views are enabled, show a black screen with a message
            composite = np.zeros((color_image.shape[0], color_image.shape[1], 3), dtype=np.uint8)
            cv2.putText(composite, "No views enabled", (50, composite.shape[0]//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            print("[MainWindow] create_composite_view: No views enabled, showing message")
        elif len(views_to_show) == 1:
            # Single view - use full size
            composite = views_to_show[0][1]
            print(f"[MainWindow] create_composite_view: Single view ({views_to_show[0][0]}): {composite.shape}")
        else:
            # Multiple views - arrange side by side
            composite = np.hstack([view[1] for view in views_to_show])
            view_names = [view[0] for view in views_to_show]
            print(f"[MainWindow] create_composite_view: Multiple views ({', '.join(view_names)}): {composite.shape}")
        
        print(f"[MainWindow] create_composite_view: Final composite shape for return: {composite.shape}")
        return composite
    
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
                self.app.switch_to_jugvid2cpp_mode()
            self.status_bar.showMessage("Switched to JugVid2cpp 3D Tracking mode.", 3000)
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
        ips_text = self.watch_ips_input.text().strip()
        if not ips_text:
            self.status_bar.showMessage("Please enter watch IP addresses", 3000)
            return
        
        # Parse IP addresses
        ip_list = [ip.strip() for ip in ips_text.split(',') if ip.strip()]
        if not ip_list:
            self.status_bar.showMessage("Please enter valid IP addresses", 3000)
            return
        
        self.status_bar.showMessage("Connecting to watches...", 0)
        self.connect_watches_btn.setEnabled(False)
        
        try:
            # Initialize Watch IMU Manager if it doesn't exist
            if not hasattr(self.app, 'watch_imu_manager') or self.app.watch_imu_manager is None:
                try:
                    from watch_imu_manager import WatchIMUManager
                    self.app.watch_imu_manager = WatchIMUManager(watch_ips=ip_list)
                    print(f"Watch IMU Manager initialized for IPs: {ip_list}")
                except ImportError as import_error:
                    print(f"Failed to import WatchIMUManager: {import_error}")
                    self.status_bar.showMessage(f"Import error: {import_error}", 5000)
                    self.connect_watches_btn.setEnabled(True)
                    return
                except Exception as init_error:
                    print(f"Failed to initialize WatchIMUManager: {init_error}")
                    import traceback
                    traceback.print_exc()
                    self.status_bar.showMessage(f"Initialization failed: {init_error}", 5000)
                    self.connect_watches_btn.setEnabled(True)
                    return
            else:
                # Update the watch IPs in the existing manager
                try:
                    self.app.watch_imu_manager.watch_ips = ip_list
                    if hasattr(self.app.watch_imu_manager, 'controller') and self.app.watch_imu_manager.controller:
                        self.app.watch_imu_manager.controller.watch_ips = ip_list
                except Exception as update_error:
                    print(f"Failed to update watch IPs: {update_error}")
                    self.status_bar.showMessage(f"Update failed: {update_error}", 5000)
                    self.connect_watches_btn.setEnabled(True)
                    return
            
            # Discover and connect
            try:
                discovered = self.app.watch_imu_manager.discover_watches()
            except Exception as discovery_error:
                print(f"Watch discovery failed: {discovery_error}")
                import traceback
                traceback.print_exc()
                self.status_bar.showMessage(f"Discovery failed: {discovery_error}", 5000)
                self.connect_watches_btn.setEnabled(True)
                return
            
            if discovered:
                try:
                    # Start streaming
                    self.app.watch_imu_manager.start_streaming()
                    if hasattr(self.app.watch_imu_manager, 'start_monitoring'):
                        self.app.watch_imu_manager.start_monitoring()
                    
                    self.imu_status_label.setText("Status: Connected")
                    self.imu_status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.connect_watches_btn.setEnabled(False)
                    self.disconnect_watches_btn.setEnabled(True)
                    self.open_imu_monitor_btn.setEnabled(True)  # Enable advanced monitor
                    self.status_bar.showMessage(f"Connected to {len(discovered)} watches", 3000)
                    print(f"🚀 Watch IMU streaming started for {len(discovered)} watches")
                except Exception as streaming_error:
                    print(f"Failed to start streaming: {streaming_error}")
                    import traceback
                    traceback.print_exc()
                    self.status_bar.showMessage(f"Streaming failed: {streaming_error}", 5000)
                    self.connect_watches_btn.setEnabled(True)
                    return
            else:
                self.status_bar.showMessage("Failed to connect to any watches", 5000)
                self.connect_watches_btn.setEnabled(True)
            
            self.update_watch_status_display()
            
        except Exception as e:
            print(f"Watch connection error: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Connection failed: {e}", 5000)
            self.connect_watches_btn.setEnabled(True)
    
    def disconnect_watches(self):
        """Disconnect from all watches."""
        if not self.app or not hasattr(self.app, 'watch_imu_manager'):
            return
        
        try:
            self.app.watch_imu_manager.cleanup()
            
            self.imu_status_label.setText("Status: Disconnected")
            self.imu_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_watches_btn.setEnabled(True)
            self.disconnect_watches_btn.setEnabled(False)
            self.open_imu_monitor_btn.setEnabled(False)  # Disable advanced monitor
            self.imu_data_display.setText("No IMU data received")
            
            self.update_watch_status_display()
            self.status_bar.showMessage("Disconnected from watches", 3000)
            
        except Exception as e:
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
    
    def open_imu_monitoring_window(self):
        """Open the advanced IMU monitoring window."""
        if self.imu_monitoring_window is None:
            self.imu_monitoring_window = IMUMonitoringWindow(self, self.app)
        
        # Show the window
        self.imu_monitoring_window.show()
        self.imu_monitoring_window.raise_()
        self.imu_monitoring_window.activateWindow()