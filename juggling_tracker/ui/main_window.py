#!/usr/bin/env python3
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu, QToolBar,
    QStatusBar, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QLabel, QFileDialog, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QMessageBox, QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QIcon, QAction, QPainter, QPen
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize, QPoint, pyqtSignal, pyqtSlot

# Application's module imports
from juggling_tracker.modules.ball_definer import BallDefiner
from juggling_tracker.modules.ball_profile_manager import BallProfileManager

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
        self.debug_mode = False
        self.show_fps = True
        self.show_extension_results = True
        
        # Set up the UI
        self.setup_ui()
        
        # Load window state
        self.load_window_state()
        
        # Set up timer for UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(33)  # ~30 FPS
        
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
        
        # Add ball controls container to main layout
        self.main_layout.addWidget(self.ball_controls_container)
        
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
        # In a real implementation, it would update the video display and status bar
        pass
    
    def update_frame(self, color_image, depth_image=None, masks=None, identified_balls=None,
                    hand_positions=None, extension_results=None, debug_info=None, tracked_balls_for_display=None):
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
                
                # Set pen color based on disappeared status
                if ball_info['disappeared_frames'] > 0:
                    # Use gray for disappeared balls
                    pen_color = Qt.GlobalColor.gray
                else:
                    # Use green for visible balls
                    pen_color = Qt.GlobalColor.green
                
                # Set up pen for drawing
                pen = QPen(pen_color, 2)
                painter.setPen(pen)
                
                # Draw the ball circle
                if radius > 0:
                    painter.drawEllipse(pos_x - radius, pos_y - radius, radius * 2, radius * 2)
                
                # Draw text (name and ID)
                text_y_offset = radius + 15  # Place text below the ball
                display_text = f"{ball_name} (TID:{ball_id_display})"
                painter.drawText(pos_x - radius, pos_y + text_y_offset, display_text)
        
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
            
        composite = color_image.copy()
        print(f"[MainWindow] create_composite_view: Initial composite (color) shape: {composite.shape}")

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
                
                # Resize depth colormap to match color image height, maintain aspect for width if different
                target_height = color_image.shape[0]
                target_width = color_image.shape[1] # Assuming we want depth map to be same width as color for hstack
                
                # Ensure depth_colormap is not empty before resizing
                if depth_colormap.size == 0:
                    print("[MainWindow] Error: depth_colormap is empty before resize.")
                    # Fallback: create a black image of target size
                    depth_colormap = np.zeros((target_height, target_width, 3), dtype=np.uint8)

                elif depth_colormap.shape[0] != target_height or depth_colormap.shape[1] != target_width:
                    depth_colormap_resized = cv2.resize(depth_colormap, (target_width, target_height))
                    print(f"[MainWindow] create_composite_view: Depth colormap resized. Shape: {depth_colormap_resized.shape}")
                else:
                    depth_colormap_resized = depth_colormap # No resize needed

                # Create a composite image (side by side)
                if composite.shape[0] == depth_colormap_resized.shape[0]: # Check height compatibility for hstack
                    composite = np.hstack((composite, depth_colormap_resized))
                    print(f"[MainWindow] create_composite_view: Composite after hstack with depth. Shape: {composite.shape}")
                else:
                    print(f"[MainWindow] Error: Height mismatch for hstack. Color: {composite.shape[0]}, Depth: {depth_colormap_resized.shape[0]}")
                    # Fallback: don't stack, just use original composite (color only)
            except Exception as e:
                print(f"[MainWindow] Error creating depth colormap or hstacking: {e}")
                # Fallback to just color image if depth processing fails
                composite = color_image.copy()
      
        # If masks are available and should be shown
        if masks is not None and self.show_masks:
            try:
                mask_images = []
                
                for mask_name, mask in masks.items():
                    if mask is None:
                        print(f"Warning: Mask '{mask_name}' is None")
                        continue
                        
                    # Convert mask to BGR for visualization
                    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                    
                    # Add the mask name
                    cv2.putText(mask_bgr, mask_name, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Resize mask to a smaller size
                    mask_small = cv2.resize(mask_bgr, (320, 240))
                    
                    mask_images.append(mask_small)
                
                # Combine masks horizontally
                if mask_images:
                    masks_row = np.hstack(mask_images)
                    
                    # Add padding to match the width of the composite image
                    if masks_row.shape[1] < composite.shape[1]:
                        padding = np.zeros((masks_row.shape[0], composite.shape[1] - masks_row.shape[1], 3), dtype=np.uint8)
                        masks_row = np.hstack((masks_row, padding))
                    
                    # Combine with the composite image
                    composite = np.vstack((composite, masks_row))
            except Exception as e:
                print(f"[MainWindow] Error processing masks: {e}")
                # Continue with just the color/depth composite
        
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
        self.show_depth = settings.value("show_depth", False, type=bool)
        self.show_masks = settings.value("show_masks", False, type=bool)
        self.debug_mode = settings.value("debug_mode", False, type=bool)
        self.show_fps = settings.value("show_fps", True, type=bool)
        self.show_extension_results = settings.value("show_extension_results", True, type=bool)
        
        # Update actions to match settings
        self.toggle_depth_action.setChecked(self.show_depth)
        self.toggle_masks_action.setChecked(self.show_masks)
        self.toggle_debug_action.setChecked(self.debug_mode)
        self.toggle_fps_action.setChecked(self.show_fps)
        self.toggle_extensions_action.setChecked(self.show_extension_results)
        
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
        settings.setValue("show_depth", self.show_depth)
        settings.setValue("show_masks", self.show_masks)
        settings.setValue("debug_mode", self.debug_mode)
        settings.setValue("show_fps", self.show_fps)
        settings.setValue("show_extension_results", self.show_extension_results)
    
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
        self.show_depth = False
        self.show_masks = False
        self.debug_mode = False
        self.show_fps = True
        self.show_extension_results = True
        
        # Update actions
        self.toggle_depth_action.setChecked(self.show_depth)
        self.toggle_masks_action.setChecked(self.show_masks)
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