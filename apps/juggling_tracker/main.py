#!/usr/bin/env python3
import os
import sys
import time
import cv2
import numpy as np
import argparse
from PyQt6.QtWidgets import QApplication, QInputDialog
from PyQt6.QtCore import QTimer

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juggling_tracker.modules.frame_acquisition import FrameAcquisition
from juggling_tracker.modules.depth_processor import DepthProcessor
from juggling_tracker.modules.skeleton_detector import SkeletonDetector
from juggling_tracker.modules.blob_detector import BlobDetector
from juggling_tracker.modules.color_calibration import ColorCalibration
from juggling_tracker.modules.ball_identifier import BallIdentifier
from juggling_tracker.modules.multi_ball_tracker import MultiBallTracker
from juggling_tracker.modules.simple_tracker import SimpleTracker
from juggling_tracker.modules.jugvid2cpp_interface import JugVid2cppInterface
from juggling_tracker.ui.main_window import MainWindow
from juggling_tracker.extensions.extension_manager import ExtensionManager
from juggling_tracker.modules.ball_definer import BallDefiner
from juggling_tracker.modules.ball_profile_manager import BallProfileManager
# HIGH-PERFORMANCE IMU INTEGRATION (2025-08-18)
from smart_imu_manager import WatchIMUManager  # Automatically uses high-performance system


class WebcamFrameAcquisition:
    """
    Fallback frame acquisition class that uses a webcam instead of a RealSense camera.
    """
    
    def __init__(self, width=640, height=480, fps=30, camera_index=0):
        """
        Initialize the WebcamFrameAcquisition module.
        
        Args:
            width (int): Width of the camera frames
            height (int): Height of the camera frames
            fps (int): Frames per second
            camera_index (int): Index of the webcam to use
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.camera_index = camera_index
        self.cap = None
        self.frame_skip = 0  # Skip frames to improve performance
        self.current_frame = 0
        # Add mode attribute for consistency, though WebcamFrameAcquisition is always 'live' in a sense
        self.mode = 'live_webcam'
        
    def initialize(self):
        """
        Initialize the webcam.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            # Try to set a lower resolution for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self.cap.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS for better performance
            
            # Get the actual resolution and FPS
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            if not self.cap.isOpened():
                print("Failed to open webcam.")
                return False
            
            print(f"Using webcam at index {self.camera_index} as fallback.")
            print(f"Resolution: {self.width}x{self.height}, FPS: {actual_fps}")
            print("Note: Depth information will not be available in fallback mode.")
            
            return True
        except Exception as e:
            print(f"Error initializing webcam: {e}")
            return False
    
    def get_frames(self):
        """
        Get frames from the webcam.
        
        Returns:
            tuple: (None, None, simulated_depth_image, color_image) or (None, None, None, None) if frames could not be captured
        """
        if self.cap is None:
            print("Webcam not initialized. Call initialize() first.")
            return None, None, None, None
        
        try:
            # Skip frames to improve performance
            self.current_frame += 1
            if self.current_frame % (self.frame_skip + 1) != 0:
                # Return the previous frame
                if hasattr(self, 'last_color_image') and hasattr(self, 'last_depth_image'):
                    return None, None, self.last_depth_image, self.last_color_image
            
            ret, color_image = self.cap.read()
            
            if not ret:
                return None, None, None, None
            
            # Create a simulated depth image (all zeros, indicating no reliable depth)
            # Downstream processing will need to handle this.
            simulated_depth_image = np.zeros((self.height, self.width), dtype=np.uint16)
            
            # Store the frames for frame skipping
            self.last_color_image = color_image
            self.last_depth_image = simulated_depth_image
            
            # Webcam provides color_image, depth_image is simulated (and often ignored or handled as None/zeros)
            # depth_frame and color_frame (RealSense objects) are None.
            return None, None, simulated_depth_image, color_image
        except Exception as e:
            print(f"Error getting frames: {e}")
            return None, None, None, None
    
    def get_intrinsics(self):
        """
        Get the camera intrinsics for 3D calculations.
        
        Returns:
            None: Camera intrinsics are not available in fallback mode
        """
        return None
    
    def get_depth_scale(self):
        """
        Get the depth scale for converting depth values to meters.
        
        Returns:
            float: A default depth scale
        """
        return 0.001  # Default depth scale for RealSense cameras
    
    def stop(self):
        """
        Stop the webcam.
        """
        if self.cap:
            self.cap.release()
            self.cap = None

# SimulationFrameAcquisition class is removed as per the new requirement
# to use video playback for simulation.

class JugglingTracker:
    """
    Main application class for the Juggling Tracker.
    
    This class ties all the modules together and provides the main entry point for the application.
    """
    
    def __init__(self, config_dir=None, use_realsense=True, use_webcam=False, use_simulation=False, use_jugvid2cpp=False, camera_index=0, video_path=None, simulation_speed=2.0, watch_ips=None): # simulation_speed is legacy
        """
        Initialize the JugglingTracker application.
        
        Args:
            config_dir (str): Directory to save configuration files (default: None)
            use_realsense (bool): Whether to use the RealSense camera (default: True)
            use_webcam (bool): Whether to use a webcam as fallback (default: False)
            use_simulation (bool): Whether to use video playback mode (replaces old simulation)
            use_jugvid2cpp (bool): Whether to use JugVid2cpp for 3D ball tracking (default: False)
            camera_index (int): Index of the webcam to use (default: 0)
            video_path (str, optional): Path to video file for playback mode.
            simulation_speed (float): Legacy, no longer used directly for FrameAcquisition speed.
            watch_ips (list, optional): List of TicWatch IP addresses for IMU streaming.
        """
        # Set up configuration directory
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize frame acquisition based on mode
        # Store initial preferences from args for later use when switching modes
        self._initial_use_realsense = use_realsense
        self._initial_use_webcam = use_webcam
        self._initial_use_simulation = use_simulation # Though this directly sets current mode
        self._initial_use_jugvid2cpp = use_jugvid2cpp # Store for JugVid2cpp mode
        self._initial_camera_index = camera_index   # Store for webcam mode
        self._initial_video_path = video_path       # Store for playback mode

        self.use_realsense = use_realsense
        self.use_webcam = use_webcam
        self.use_simulation = use_simulation # This now means video playback
        self.use_jugvid2cpp = use_jugvid2cpp # JugVid2cpp 3D tracking mode
        self.watch_ips = watch_ips or []
        self.camera_index = camera_index
        self.video_path = video_path
        
        # Default frame dimensions - can be overridden by specific camera modes
        default_width, default_height = 640, 480

        # Set the frame acquisition module based on the specified mode
        if self.use_jugvid2cpp: # JugVid2cpp 3D Tracking Mode
            print("Using JugVid2cpp 3D tracking mode.")
            self.frame_acquisition = JugVid2cppInterface()
        elif self.use_simulation: # Video Playback Mode
            if self.video_path:
                print(f"Using video playback mode with video: {self.video_path}")
                self.frame_acquisition = FrameAcquisition(
                    width=default_width,
                    height=default_height,
                    mode='playback',
                    video_path=self.video_path
                )
            else:
                print("Error: Video playback mode selected but no --video-path provided.")
                print("Falling back to RealSense (if available) or exiting.")
                # Fallback logic will be handled in self.initialize()
                self.frame_acquisition = FrameAcquisition(width=default_width, height=default_height, mode='live')
                self.use_simulation = False # Revert flag as playback init will fail
        elif self.use_webcam:
            print("Using webcam mode as specified.")
            self.frame_acquisition = WebcamFrameAcquisition(
                width=default_width, # Webcam class might override this with its capabilities
                height=default_height,
                camera_index=self.camera_index
            )
        elif self.use_realsense:
            print("Using RealSense mode as specified.")
            self.frame_acquisition = FrameAcquisition(width=default_width, height=default_height, mode='live')
        else:
            # Default to RealSense if no other mode is explicitly chosen by args
            print("Defaulting to RealSense mode.")
            self.frame_acquisition = FrameAcquisition(width=default_width, height=default_height, mode='live')
        
        # Initialize other modules
        self.depth_processor = DepthProcessor()
        self.skeleton_detector = SkeletonDetector()
        self.blob_detector = BlobDetector()
        self.color_calibration = ColorCalibration(config_dir=self.config_dir)
        
        self.ball_profile_manager = BallProfileManager(self.config_dir)
        # Assuming self.depth_processor is initialized before this line
        if hasattr(self, 'depth_processor'):
            self.ball_definer = BallDefiner(self.depth_processor)
        else:
            print("ERROR: self.depth_processor not initialized before BallDefiner. BallDefiner might not work.")
            self.ball_definer = None # Or handle error appropriately
        
        # Store last frames for definition process
        self.last_color_image_for_def = None
        self.last_depth_image_for_def = None # This should be the raw depth (e.g. uint16 mm)
        self.last_intrinsics_for_def = None
        self.last_depth_scale_for_def = None

        # Initialize BallIdentifier with ColorCalibration
        # Note: The current BallIdentifier implementation expects ColorCalibration, not BallProfileManager
        # In a future update, BallIdentifier could be modified to use BallProfileManager directly
        self.ball_identifier = BallIdentifier(self.ball_profile_manager, self.color_calibration)
        self.ball_tracker = MultiBallTracker()
        self.simple_tracker = SimpleTracker()
        
        # Initialize Watch IMU Manager for real-time data streaming
        if self.watch_ips:
            self.watch_imu_manager = WatchIMUManager(watch_ips=self.watch_ips)
            print(f"Watch IMU Manager initialized for IPs: {self.watch_ips}")
            # Start real-time streaming immediately
            self.watch_imu_manager.start_streaming()
            print("🚀 Real-time IMU streaming started")
        else:
            self.watch_imu_manager = None

        # Create Qt application
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        
        # Load QSS stylesheet
        self.load_stylesheet()
        
        # Create main window
        self.main_window = MainWindow(self, self.config_dir)
        
        # In __init__, after main_window is created and ball_profile_manager is initialized:
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'update_defined_balls_list'):
            self.main_window.update_defined_balls_list()
        
        # Connect save/load buttons from MainWindow to JugglingTracker methods
        if hasattr(self, 'main_window'):
            if hasattr(self.main_window, 'save_balls_button'):
                self.main_window.save_balls_button.clicked.connect(self.save_ball_profiles)
            if hasattr(self.main_window, 'load_balls_button'):
                self.main_window.load_balls_button.clicked.connect(self.load_ball_profiles)
        
        self.extension_manager = ExtensionManager()
        
        # Initialize state
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.start_time = 0
        self.fps = 0
        self.is_currently_recording = False # New state for recording
        
        # Set up frame processing timer with faster rate for simulation mode
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.process_frame)
        
        # Use a faster timer interval for simulation mode
        if self.use_simulation: # Video playback
            # For video playback, timer interval could be based on video's FPS,
            # but for simplicity and consistency with UI responsiveness, let's use a fixed reasonable rate.
            # The FrameAcquisition's get_frames for playback will handle its own pacing if needed (currently it doesn't).
            self.frame_timer_interval = 33 # ~30 FPS target for UI updates
        else: # Live camera (RealSense or Webcam)
            self.frame_timer_interval = 33  # ~30 FPS for real camera
        
        # Load default extensions (but don't enable them)
        self.load_default_extensions()
    
    def load_stylesheet(self):
        """
        Load the QSS stylesheet.
        """
        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'default.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                self.qt_app.setStyleSheet(f.read())
    
    def load_default_extensions(self):
        """
        Load default extensions but don't enable them by default.
        """
        # Discover available extensions
        extension_names = self.extension_manager.discover_extensions()
        
        # Register extensions but don't enable them
        for name in extension_names:
            self.extension_manager.register_extension_by_name(name)
            # Note: We're not enabling extensions by default anymore
        
        # Update the UI
        self.main_window.update_extensions_menu(self.extension_manager)
    
    def initialize(self):
        """
        Initialize the application.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        # Initialize the camera
        if not self.frame_acquisition.initialize():
            print("Failed to initialize primary camera/video mode.")
            original_intended_mode = self.frame_acquisition.mode

            if original_intended_mode == 'jugvid2cpp': # JugVid2cpp failed
                print("JugVid2cpp initialization failed. Attempting fallback to live mode.")
                # Attempt to fall back to default live mode (RealSense then Webcam)
                self.use_jugvid2cpp = False
                self.use_realsense = self._initial_use_realsense if not self._initial_use_webcam else True
                self.use_webcam = self._initial_use_webcam if self.use_realsense else True
                
                if self.use_realsense:
                    print("Falling back to RealSense mode.")
                    self.frame_acquisition = FrameAcquisition(width=640, height=480, mode='live')
                    if not self.frame_acquisition.initialize():
                        print("RealSense fallback failed. Trying Webcam.")
                        self.use_realsense = False; self.use_webcam = True
                        self.frame_acquisition = WebcamFrameAcquisition(width=640, height=480, camera_index=self._initial_camera_index)
                        if not self.frame_acquisition.initialize():
                            print("FATAL: All fallback modes failed after JugVid2cpp failure.")
                            return False
                    else:
                         self.use_webcam = False
                elif self.use_webcam:
                    print("Falling back to Webcam mode.")
                    self.frame_acquisition = WebcamFrameAcquisition(width=640, height=480, camera_index=self._initial_camera_index)
                    if not self.frame_acquisition.initialize():
                        print("FATAL: Webcam fallback failed.")
                        return False
                else:
                    print("FATAL: JugVid2cpp failed and no live mode to fall back to.")
                    return False
            elif original_intended_mode == 'playback': # Playback failed
                print(f"Video playback failed for: {self.video_path}. Attempting live mode.")
                # Attempt to fall back to default live mode (RealSense then Webcam)
                self.use_simulation = False
                self.video_path = None
                self.use_realsense = self._initial_use_realsense if not self._initial_use_webcam else True # Prioritize RealSense for fallback
                self.use_webcam = self._initial_use_webcam if self.use_realsense else True
                
                if self.use_realsense:
                    print("Falling back to RealSense mode.")
                    self.frame_acquisition = FrameAcquisition(width=640, height=480, mode='live')
                    if not self.frame_acquisition.initialize():
                        print("RealSense fallback failed. Trying Webcam.")
                        self.use_realsense = False; self.use_webcam = True
                        self.frame_acquisition = WebcamFrameAcquisition(width=640, height=480, camera_index=self._initial_camera_index)
                        if not self.frame_acquisition.initialize():
                            print("FATAL: All fallback modes failed after playback failure.")
                            return False
                    else: # RealSense fallback succeeded
                         self.use_webcam = False # Ensure webcam flag is false
                elif self.use_webcam: # Only webcam was an option initially or RealSense failed
                    print("Falling back to Webcam mode (or primary was webcam).")
                    self.frame_acquisition = WebcamFrameAcquisition(width=640, height=480, camera_index=self._initial_camera_index)
                    if not self.frame_acquisition.initialize():
                        print("FATAL: Webcam fallback failed.")
                        return False
                else: # No live mode specified as fallback
                    print("FATAL: Playback failed and no live mode to fall back to.")
                    return False

            elif original_intended_mode == 'live': # Live RealSense mode failed
                print("RealSense initialization failed. Trying webcam fallback...")
                self.use_realsense = False
                self.use_webcam = True # Attempt webcam
                self.frame_acquisition = WebcamFrameAcquisition(camera_index=self._initial_camera_index)
                if not self.frame_acquisition.initialize():
                    print("Webcam fallback also failed. No camera sources available.")
                    # Potentially could fall back to an error state or a "no camera" mode
                    # For now, we'll return False, indicating initialization failure.
                    self.use_webcam = False # Ensure it's false if it failed
                    return False
            # If it was WebcamFrameAcquisition that failed init, self.use_webcam would already be true
            # and self.use_realsense false. The outer `if not self.frame_acquisition.initialize()` catches this.
            # If it was a specific webcam that failed, there isn't a further fallback implemented here.
            else: # An unknown mode or already failed webcam
                 print(f"Initialization failed for mode '{original_intended_mode}'. No further fallbacks.")
                 return False
        
        # Update current mode flags based on the successfully initialized frame_acquisition
        if isinstance(self.frame_acquisition, JugVid2cppInterface):
            self.use_realsense = False
            self.use_webcam = False
            self.use_simulation = False
            self.use_jugvid2cpp = True
        elif isinstance(self.frame_acquisition, FrameAcquisition) and self.frame_acquisition.mode == 'live':
            self.use_realsense = True
            self.use_webcam = False
            self.use_simulation = False
            self.use_jugvid2cpp = False
        elif isinstance(self.frame_acquisition, WebcamFrameAcquisition):
            self.use_realsense = False
            self.use_webcam = True
            self.use_simulation = False
            self.use_jugvid2cpp = False
        elif isinstance(self.frame_acquisition, FrameAcquisition) and self.frame_acquisition.mode == 'playback':
            self.use_realsense = False
            self.use_webcam = False
            self.use_simulation = True # This means video playback
            self.use_jugvid2cpp = False

        print(f"JugglingTracker initialized. Active mode: {self.frame_acquisition.mode}")
        print(f"[DEBUG Roo] JugglingTracker.initialize: Final frame_acquisition type: {type(self.frame_acquisition)}, mode: {self.frame_acquisition.mode if hasattr(self.frame_acquisition, 'mode') else 'N/A'}") # Roo log
        # Set the start time
        self.start_time = time.time()
        
        return True
    
    def run(self):
        """
        Run the main application loop.
        """
        if not self.initialize():
            return
        
        self.running = True
        
        try:
            # Show the main window
            self.main_window.show()

            # Synchronize UI to the actual app state after initialization
            if hasattr(self.main_window, 'sync_ui_to_app_state'):
                self.main_window.sync_ui_to_app_state()
            
            # Start the frame processing timer with the appropriate interval
            self.frame_timer.start(self.frame_timer_interval)
            print(f"Frame timer started with interval {self.frame_timer_interval}ms.")
            
            # Run the Qt event loop
            self.qt_app.exec()
            
        except KeyboardInterrupt:
            print("Application interrupted by user.")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def process_frame(self):
        """
        Process a single frame.
        """
        # Skip processing if paused
        if self.paused or not self.running:
            return
        
        # Get frames from the camera
        depth_frame, color_frame, depth_image, color_image = self.frame_acquisition.get_frames()
        
        # Get latest IMU data from watches
        if self.watch_imu_manager:
            imu_data_points = self.watch_imu_manager.get_latest_imu_data()
            if imu_data_points:
                # Process and synchronize IMU data with vision data
                self._process_imu_data(imu_data_points, time.time())

        # ------------ TEMPORARY DEBUG START ------------
        if color_image is not None:
            print(f"[Tracker Loop] Color image received: shape={color_image.shape}, dtype={color_image.dtype}")
        else:
            print("[Tracker Loop] Color image is NONE")
        
        if depth_image is not None:
            print(f"[Tracker Loop] Depth image received: shape={depth_image.shape}, dtype={depth_image.dtype}")
        else:
            print("[Tracker Loop] Depth image is NONE")
        # ------------ TEMPORARY DEBUG END ------------

        # Get current mode from the frame acquisition
        current_mode = self.frame_acquisition.mode if hasattr(self.frame_acquisition, 'mode') else 'unknown'
        
        # Special handling for JugVid2cpp mode - it may not have camera frames but should still process
        if current_mode != 'jugvid2cpp' and (depth_image is None or color_image is None):
            print("Warning: Invalid frames received from frame_acquisition, skipping frame processing.") # Enhanced message
            return
        
        # For JugVid2cpp mode, create status image if no camera feed
        if current_mode == 'jugvid2cpp' and color_image is None:
            color_image = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(color_image, "JugVid2cpp 3D Tracking Active", (50, 200),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.putText(color_image, "Camera feed unavailable", (50, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Show JugVid2cpp status
            if isinstance(self.frame_acquisition, JugVid2cppInterface):
                identified_balls = self.frame_acquisition.get_identified_balls()
                if identified_balls:
                    cv2.putText(color_image, f"Tracking {len(identified_balls)} balls", (50, 300),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_offset = 330
                    for ball in identified_balls:
                        if 'original_3d' in ball:
                            x, y, z = ball['original_3d']
                            text = f"{ball['name']}: X={x:.2f}, Y={y:.2f}, Z={z:.2f}"
                            cv2.putText(color_image, text, (50, y_offset),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                            y_offset += 25
                else:
                    cv2.putText(color_image, "No balls detected", (50, 300),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if current_mode == 'jugvid2cpp' and depth_image is None:
            depth_image = np.zeros((480, 640), dtype=np.uint16)
        
        # Store frames for ball definition
        self.last_color_image_for_def = color_image.copy()
        self.last_depth_image_for_def = depth_image.copy() # Assuming depth_image is raw depth (e.g. mm)
        
        # Get intrinsics and depth scale
        if hasattr(self, 'frame_acquisition'):
            if hasattr(self.frame_acquisition, 'get_intrinsics'):
                self.last_intrinsics_for_def = self.frame_acquisition.get_intrinsics()
            else:
                print("WARN: frame_acquisition does not have get_intrinsics method.")
            if hasattr(self.frame_acquisition, 'get_depth_scale'):
                self.last_depth_scale_for_def = self.frame_acquisition.get_depth_scale()
            else:
                print("WARN: frame_acquisition does not have get_depth_scale method.")
        else:
            print("WARN: self.frame_acquisition not available for intrinsics/depth_scale.")
        
        # Determine current operating mode from frame_acquisition object
        # self.frame_acquisition.mode can be 'live' (RealSense), 'playback', 'live_webcam', or 'jugvid2cpp'
        current_mode = self.frame_acquisition.mode
        
        # Handle JugVid2cpp mode differently - it provides 3D positions directly but also has camera feed
        if current_mode == 'jugvid2cpp':
            # JugVid2cpp provides 3D ball positions directly, use those instead of normal pipeline
            if isinstance(self.frame_acquisition, JugVid2cppInterface):
                # Get 3D ball positions from JugVid2cpp
                identified_balls = self.frame_acquisition.get_identified_balls()
                
                # In JugVid2cpp mode, the C++ side is the tracker. We bypass the Python
                # MultiBallTracker and format the data directly for display. The 'identified_balls'
                # from the interface are already structured with the necessary info.
                tracked_balls_display_info = identified_balls

                # Create dummy values for compatibility with existing pipeline
                depth_in_meters = None
                proximity_mask = np.ones((color_image.shape[0] if color_image is not None else 480,
                                        color_image.shape[1] if color_image is not None else 640), dtype=np.uint8) * 255
                hand_positions = ((0, 0), (0, 0))  # Dummy hand positions since JugVid2cpp handles this
                hand_mask = np.zeros((color_image.shape[0] if color_image is not None else 480,
                                    color_image.shape[1] if color_image is not None else 640), dtype=np.uint8)
                combined_mask = proximity_mask
                simple_tracking_result = {'object_count': len(identified_balls), 'total_area': 0, 'average_position': None, 'individual_positions': []}
                blobs = []
                filtered_blobs = []
                
                current_time = time.time()
                current_intrinsics = self.frame_acquisition.get_intrinsics()
                
            else:
                print("Error: JugVid2cpp mode but frame_acquisition is not JugVid2cppInterface")
                return
        else:
            # Normal processing path for all other modes
            # Depth-related data (depth_frame, depth_image, depth_in_meters, intrinsics)
            # might be None or default values if not available (e.g., in playback or webcam mode).
            # Downstream modules must handle this gracefully.

            depth_in_meters = None
            proximity_mask = None # Initialize to None
            # Get depth_scale from frame_acquisition; it will be None if not applicable (e.g. playback)
            current_depth_scale = self.frame_acquisition.get_depth_scale()

            if current_mode == 'live' and depth_frame is not None and depth_image is not None and current_depth_scale is not None:
                # This is RealSense with valid depth data
                depth_in_meters = self.depth_processor.process_depth_frame(depth_frame, depth_image, current_depth_scale)
                if depth_in_meters is not None:
                    proximity_mask = self.depth_processor.create_proximity_mask(depth_in_meters)
                    proximity_mask = self.depth_processor.cleanup_mask(proximity_mask)
            
            # If proximity_mask is still None (e.g. playback, webcam, or failed depth processing),
            # create a default "pass-through" mask.
            if proximity_mask is None and color_image is not None:
                proximity_mask = np.ones((color_image.shape[0], color_image.shape[1]), dtype=np.uint8) * 255
            elif color_image is None: # Should not happen if frame acquisition is working
                print("Error: color_image is None in process_frame, cannot create default proximity_mask.")
                return

            # Skeleton detection (works on color_image, so applicable to all modes)
            pose_landmarks = self.skeleton_detector.detect_skeleton(color_image)
            hand_positions = self.skeleton_detector.get_hand_positions(pose_landmarks, color_image.shape)
            hand_mask = self.skeleton_detector.create_hand_mask(hand_positions, color_image.shape)
            
            # Combine proximity mask and hand mask
            combined_mask = cv2.bitwise_and(proximity_mask, cv2.bitwise_not(hand_mask))
                
            # Simple tracking on the combined mask
            min_size, max_size = self.depth_processor.get_object_size_range()
            simple_tracking_result = self.simple_tracker.track_objects(combined_mask, min_size, max_size)
            
            # Blob detection in the combined mask
            blobs = self.blob_detector.detect_blobs(combined_mask)
            
            # Filter blobs by depth variance (only if depth_in_meters is available)
            if depth_in_meters is not None:
                filtered_blobs = self.blob_detector.filter_blobs_by_depth_variance(blobs, depth_in_meters)
            else:
                filtered_blobs = blobs # No depth variance filtering if depth_in_meters is None
                
            current_time = time.time()
            # Get intrinsics; will be None if not available (playback, webcam)
            current_intrinsics = self.frame_acquisition.get_intrinsics()
            
            # Identify balls
            if hasattr(self, 'ball_identifier') and self.ball_identifier is not None:
                identified_balls = self.ball_identifier.identify_balls(
                    filtered_blobs,
                    color_image,
                    depth_in_meters,    # Can be None
                    current_intrinsics  # Can be None
                )
            else:
                identified_balls = []
            
            # Update ball trackers
            if hasattr(self, 'ball_tracker') and self.ball_tracker is not None:
                tracked_balls_display_info = self.ball_tracker.update_trackers(
                    identified_balls,
                    current_intrinsics, # Can be None
                    current_time=current_time
                )
            else:
                tracked_balls_display_info = []
            
        ball_velocities = self.ball_tracker.get_ball_velocities() if hasattr(self, 'ball_tracker') else []
        
        # Prepare frame data for extensions
        frame_data = {
            'timestamp': current_time,
            'color_image': color_image,
            'depth_image': depth_image,         # Raw depth image from source (can be None/zeros)
            'depth_in_meters': depth_in_meters, # Processed depth in meters (can be None)
            'intrinsics': current_intrinsics,   # Camera intrinsics (can be None)
            'raw_blobs': filtered_blobs,        # Blobs after (optional) depth filtering
            'identified_balls_raw': identified_balls, # This is now the tracked data in jugvid2cpp mode
            'tracked_balls': self.ball_tracker.get_tracked_balls() if hasattr(self, 'ball_tracker') else [],
            'ball_velocities': ball_velocities,
            'hand_positions': hand_positions,
            'simple_tracking': simple_tracking_result,
            'imu_data': getattr(self, 'latest_imu_data', {})  # Real-time IMU data from watches
        }
        
        extension_results = self.extension_manager.process_frame(frame_data)
        
        # Update calibration if in calibration mode and blobs are available
        if self.main_window.is_calibrating() and filtered_blobs:
            largest_blob = max(filtered_blobs, key=lambda b: b.get('radius', 0)) # Added .get for safety
            self.main_window.update_calibration(largest_blob, color_image)
        
        # Prepare masks for visualization
        masks_for_display = {
            'Proximity': proximity_mask, # Already handled to be a valid mask or default
            'Hands': hand_mask,
            'Combined': combined_mask
        }

        # Determine mode string for debug info
        mode_str = "Unknown"
        if current_mode == 'jugvid2cpp':
            mode_str = 'JugVid2cpp 3D Tracking'
        elif current_mode == 'live':
            mode_str = 'RealSense'
        elif current_mode == 'playback':
            mode_str = f'Playback ({os.path.basename(self.video_path or "No File")})'
        elif current_mode == 'live_webcam':
            mode_str = 'Webcam'
            
        # Update the main window
        try:
            self.main_window.update_frame(
                color_image=color_image,
                depth_image=depth_image, # Pass original depth for display
                masks=masks_for_display if self.main_window.show_masks else None,
                tracked_balls_for_display=tracked_balls_display_info,
                hand_positions=hand_positions,
                extension_results=extension_results,
                simple_tracking=simple_tracking_result,
                debug_info={
                    'Num Blobs': len(blobs),
                    'Num Filtered Blobs': len(filtered_blobs),
                    'Num Identified Balls': len(identified_balls),
                    'Num Tracked Balls': len(tracked_balls_display_info), # Use display info for consistency
                    'Simple Tracking Objects': simple_tracking_result.get('object_count', 0),
                    'Mode': mode_str,
                    'Frame Size': f"{color_image.shape[1]}x{color_image.shape[0]}" if color_image is not None else "N/A"
                }
            )
            self.main_window.update_tracking_position_display(simple_tracking_result)
        except Exception as e:
            print(f"Error updating main window frame: {e}")
            import traceback
            traceback.print_exc()
        
        # Update frame count and FPS
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.fps = self.frame_count / elapsed_time
    
    def _process_imu_data(self, imu_data_points: list, current_time: float):
        """
        Process and synchronize IMU data with vision data.
        
        Args:
            imu_data_points: List of IMU data dictionaries from watches
            current_time: Current timestamp for synchronization
        """
        if not imu_data_points:
            return
        
        # Group data by watch
        watch_data = {}
        for data_point in imu_data_points:
            watch_name = data_point.get('watch_name', 'unknown')
            if watch_name not in watch_data:
                watch_data[watch_name] = []
            watch_data[watch_name].append(data_point)
        
        # Process data for each watch
        for watch_name, data_list in watch_data.items():
            latest_data = data_list[-1]  # Get most recent data point
            
            # Calculate data freshness
            data_age = current_time - latest_data.get('received_at', current_time)
            
            # Only process recent data (within last 100ms for real-time feel)
            if data_age < 0.1:
                # Extract IMU values
                accel = (
                    latest_data.get('accel_x', 0.0),
                    latest_data.get('accel_y', 0.0),
                    latest_data.get('accel_z', 0.0)
                )
                gyro = (
                    latest_data.get('gyro_x', 0.0),
                    latest_data.get('gyro_y', 0.0),
                    latest_data.get('gyro_z', 0.0)
                )
                
                # Calculate motion intensity for basic motion detection
                accel_magnitude = (accel[0]**2 + accel[1]**2 + accel[2]**2)**0.5
                gyro_magnitude = (gyro[0]**2 + gyro[1]**2 + gyro[2]**2)**0.5
                
                # Store in frame data for extensions to use
                if not hasattr(self, 'latest_imu_data'):
                    self.latest_imu_data = {}
                
                self.latest_imu_data[watch_name] = {
                    'timestamp': latest_data.get('timestamp', current_time),
                    'accel': accel,
                    'gyro': gyro,
                    'accel_magnitude': accel_magnitude,
                    'gyro_magnitude': gyro_magnitude,
                    'data_age': data_age,
                    'watch_ip': latest_data.get('watch_ip', 'unknown')
                }
                
                # Print periodic status (every 30 frames to avoid spam)
                if self.frame_count % 30 == 0:
                    print(f"IMU {watch_name}: accel={accel_magnitude:.2f}m/s², gyro={gyro_magnitude:.2f}rad/s, age={data_age*1000:.1f}ms")
    
    def define_new_ball(self, roi_rect_display_coords):
        if self.last_color_image_for_def is None or \
           self.last_depth_image_for_def is None or \
           self.last_intrinsics_for_def is None or \
           self.last_depth_scale_for_def is None:
            print("Error: Frame data not available for ball definition.")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Error: Frame data not ready. Try again.")
            return

        if not self.ball_definer:
            print("Error: BallDefiner not initialized.")
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Error: BallDefiner service not available.")
            return

        # IMPORTANT: Map ROI from display coordinates to original image coordinates
        # This is crucial if your display scales the image.
        # The plan suggests MainWindow handles this scaling. If roi_rect_display_coords
        # are from a scaled display, they MUST be converted to original image coordinates here or in MainWindow.
        # For this example, assuming roi_rect_display_coords are already scaled to original image dimensions
        # or that no scaling is applied in the display.
        # If scaling is needed:
        # current_display_width = self.main_window.video_label.pixmap().width()
        # current_display_height = self.main_window.video_label.pixmap().height()
        # original_image_width = self.last_color_image_for_def.shape[1]
        # original_image_height = self.last_color_image_for_def.shape[0]
        #
        # if current_display_width == 0 or current_display_height == 0: # Avoid division by zero
        #     print("Error: Display pixmap has zero dimensions. Cannot scale ROI.")
        #     return
        #
        # scale_x = original_image_width / current_display_width
        # scale_y = original_image_height / current_display_height
        #
        # roi_rect_image_coords = (
        #     int(roi_rect_display_coords[0] * scale_x),
        #     int(roi_rect_display_coords[1] * scale_y),
        #     int(roi_rect_display_coords[2] * scale_x),
        #     int(roi_rect_display_coords[3] * scale_y)
        # )
        # For now, let's assume no scaling or it's handled by MainWindow:
        roi_rect_image_coords = roi_rect_display_coords


        name_suggestion = f"Ball {len(self.ball_profile_manager.get_all_profiles()) + 1}"
        ball_name, ok = QInputDialog.getText(self.main_window if hasattr(self, 'main_window') else None,
                                             "Define New Ball",
                                             "Enter ball name:", text=name_suggestion)
        if not ok or not ball_name:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Ball definition cancelled.")
            return

        new_profile = self.ball_definer.define_ball_from_roi(
            roi_rect_image_coords,
            self.last_color_image_for_def,
            self.last_depth_image_for_def, # Pass the raw depth image (e.g. uint16 in mm)
            self.last_intrinsics_for_def,
            self.last_depth_scale_for_def
        )

        if new_profile:
            new_profile.name = ball_name # Set user-defined name
            self.ball_profile_manager.add_profile(new_profile)
            if hasattr(self, 'main_window'):
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(f"Ball '{new_profile.name}' defined successfully.")
                if hasattr(self.main_window, 'update_defined_balls_list'):
                    self.main_window.update_defined_balls_list() # Update UI
        else:
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Failed to define ball. Check console for errors.")
    
    def save_ball_profiles(self):
        self.ball_profile_manager.save_profiles()
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar().showMessage("Ball profiles saved.")

    def load_ball_profiles(self):
        self.ball_profile_manager.load_profiles()
        if hasattr(self, 'main_window'):
            if hasattr(self.main_window, 'update_defined_balls_list'):
                self.main_window.update_defined_balls_list()
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(f"Loaded {len(self.ball_profile_manager.get_all_profiles())} ball profiles.")
    
    def untrack_ball(self, ball_id):
        """
        Remove a specific ball from tracking.
        
        Args:
            ball_id: ID of the ball to untrack
        """
        if hasattr(self, 'ball_tracker') and self.ball_tracker:
            if hasattr(self.ball_tracker, 'remove_ball'):
                success = self.ball_tracker.remove_ball(ball_id)
                if success and hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(f"Ball with ID {ball_id} removed from tracking", 3000)
                elif hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(f"Failed to remove ball with ID {ball_id}", 3000)
            else:
                print("Error: ball_tracker does not have remove_ball method.")
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage("Error: Ball tracking system does not support removing balls", 3000)

    def switch_to_playback_mode(self, video_path):
        """Switch the frame acquisition to video playback mode."""
        print(f"[DEBUG Roo] JugglingTracker.switch_to_playback_mode: Called with video_path='{video_path}'") # Roo log
        print(f"Attempting to switch to playback mode with video: {video_path}")
        if self.frame_timer:
            self.frame_timer.stop()

        if self.frame_acquisition:
            self.frame_acquisition.stop()

        self.video_path = video_path
        self.use_simulation = True # This flag now indicates video playback
        self.use_realsense = False
        self.use_webcam = False
        
        # Use default dimensions from __init__ or define them here
        default_width, default_height = 640, 480

        self.frame_acquisition = FrameAcquisition(
            width=default_width,
            height=default_height,
            mode='playback',
            video_path=self.video_path
        )
        init_success = self.frame_acquisition.initialize() # Roo log
        print(f"[DEBUG Roo] JugglingTracker.switch_to_playback_mode: frame_acquisition.initialize() result: {init_success}") # Roo log
        if not init_success:
            print(f"Failed to initialize playback for video: {video_path}. Reverting to live mode if possible.")
            print(f"[DEBUG Roo] JugglingTracker.switch_to_playback_mode: Playback init failed, attempting fallback to live mode.") # Roo log
            # Attempt to revert to a default live mode
            self.main_window.feed_mode_combo.setCurrentIndex(0) # Visually switch back UI
            self.switch_to_live_mode(fallback=True) # Internal switch
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(f"Error: Could not play {os.path.basename(video_path)}. Reverted to live.", 5000)
            return False
        
        self.frame_count = 0
        self.start_time = time.time()
        if self.frame_timer:
            self.frame_timer.start(self.frame_timer_interval)
        print(f"Switched to playback mode. Video: {self.video_path}")
        print(f"[DEBUG Roo] JugglingTracker.switch_to_playback_mode: Successfully switched. FA mode: {self.frame_acquisition.mode}, type: {type(self.frame_acquisition)}") # Roo log
        return True

    def switch_to_live_mode(self, fallback=False):
        """Switch the frame acquisition to live camera mode (RealSense or Webcam)."""
        print(f"[DEBUG Roo] JugglingTracker.switch_to_live_mode: Called. fallback={fallback}") # Roo log
        print("Attempting to switch to live mode.")
        if self.frame_timer:
            self.frame_timer.stop()

        if self.frame_acquisition:
            self.frame_acquisition.stop()

        self.use_simulation = False
        self.video_path = None
        
        # Determine original intended live mode (RealSense or Webcam from initial args)
        # These flags (self._initial_use_realsense, self._initial_use_webcam)
        # should be stored in __init__ from args to remember user's preference.
        # For now, we'll use current self.use_realsense/webcam, but this might be
        # tricky if they were changed by a failed playback switch.
        # A cleaner way is to store initial args. Let's assume they are stored.
        # If not stored, we might default to RealSense then Webcam.

        # Use stored initial preferences
        initial_use_realsense = self._initial_use_realsense
        initial_use_webcam = self._initial_use_webcam
        
        default_width, default_height = 640, 480

        # Logic for selecting live mode based on initial preferences
        # The 'fallback' parameter indicates if this call is a result of a failed playback attempt
        if not fallback and initial_use_webcam:
            print("Switching to Webcam (based on initial preference or direct switch).")
            self.frame_acquisition = WebcamFrameAcquisition(
                width=default_width, height=default_height, camera_index=self._initial_camera_index
            )
            current_primary_mode_is_webcam = True
        elif not fallback and initial_use_realsense:
            print("Switching to RealSense (based on initial preference or direct switch).")
            self.frame_acquisition = FrameAcquisition(
                width=default_width, height=default_height, mode='live'
            )
            current_primary_mode_is_webcam = False
        else: # Default or fallback scenario: Try RealSense first, then Webcam
            print("Attempting RealSense as primary live mode (default or fallback).")
            self.frame_acquisition = FrameAcquisition(
                width=default_width, height=default_height, mode='live'
            )
            current_primary_mode_is_webcam = False # Tentatively

        live_init_success = self.frame_acquisition.initialize() # Roo log
        print(f"[DEBUG Roo] JugglingTracker.switch_to_live_mode: Initial live init attempt ({'Webcam' if current_primary_mode_is_webcam else 'RealSense'}) result: {live_init_success}") # Roo log
        if not live_init_success:
            print(f"Failed to initialize {'Webcam' if current_primary_mode_is_webcam else 'RealSense'}.")
            # If the primary attempt (RealSense or explicit Webcam) failed, try the other if not already tried.
            if not current_primary_mode_is_webcam and (initial_use_webcam or fallback): # If RealSense failed, and Webcam is an option
                print("[DEBUG Roo] JugglingTracker.switch_to_live_mode: RealSense failed, trying Webcam fallback.") # Roo log
                print("RealSense failed. Trying Webcam as fallback.")
                self.frame_acquisition = WebcamFrameAcquisition(
                    width=default_width, height=default_height, camera_index=self._initial_camera_index
                )
                webcam_fallback_init_success = self.frame_acquisition.initialize() # Roo log
                print(f"[DEBUG Roo] JugglingTracker.switch_to_live_mode: Webcam fallback initialize() result: {webcam_fallback_init_success}") # Roo log
                if not webcam_fallback_init_success:
                    print("FATAL: All live camera modes failed.")
                    if hasattr(self.main_window, 'statusBar'):
                         self.main_window.statusBar().showMessage("Error: All camera modes failed!", 5000)
                    return False
                print("Successfully switched to Webcam as fallback.")
                self.use_webcam = True
                self.use_realsense = False
            elif current_primary_mode_is_webcam and (initial_use_realsense or fallback): # If explicit Webcam failed, and RealSense is an option
                 print("[DEBUG Roo] JugglingTracker.switch_to_live_mode: Webcam failed, trying RealSense fallback.") # Roo log
                 print("Webcam failed. Trying RealSense as fallback.")
                 self.frame_acquisition = FrameAcquisition(width=default_width, height=default_height, mode='live')
                 realsense_fallback_init_success = self.frame_acquisition.initialize() # Roo log
                 print(f"[DEBUG Roo] JugglingTracker.switch_to_live_mode: RealSense fallback initialize() result: {realsense_fallback_init_success}") # Roo log
                 if not realsense_fallback_init_success:
                    print("FATAL: All live camera modes failed.")
                    if hasattr(self.main_window, 'statusBar'):
                        self.main_window.statusBar().showMessage("Error: All camera modes failed!", 5000)
                    return False
                 print("Successfully switched to RealSense as fallback.")
                 self.use_realsense = True
                 self.use_webcam = False
            else: # The first attempt failed and no other viable fallback based on initial args
                if hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage("Error: Failed to initialize chosen live camera!", 5000)
                return False
        else: # Initial acquisition successful
            if isinstance(self.frame_acquisition, WebcamFrameAcquisition):
                self.use_webcam = True
                self.use_realsense = False
            else: # FrameAcquisition in 'live' mode
                self.use_realsense = True
                self.use_webcam = False
            print(f"Successfully initialized {self.frame_acquisition.mode} mode.")
        
        self.frame_count = 0
        self.start_time = time.time()
        if self.frame_timer:
            self.frame_timer.start(self.frame_timer_interval)
        print("Switched to live mode.")
        print(f"[DEBUG Roo] JugglingTracker.switch_to_live_mode: Successfully switched. FA mode: {self.frame_acquisition.mode}, type: {type(self.frame_acquisition)}") # Roo log
        return True

    def switch_to_jugvid2cpp_mode(self):
        """Switch the frame acquisition to JugVid2cpp 3D tracking mode."""
        print(f"[DEBUG Roo] JugglingTracker.switch_to_jugvid2cpp_mode: Called") # Roo log
        print("Attempting to switch to JugVid2cpp 3D tracking mode.")
        if self.frame_timer:
            self.frame_timer.stop()

        if self.frame_acquisition:
            self.frame_acquisition.stop()

        self.use_simulation = False
        self.use_realsense = False
        self.use_webcam = False
        self.use_jugvid2cpp = True
        self.video_path = None
        
        self.frame_acquisition = JugVid2cppInterface()
        jugvid2cpp_init_success = self.frame_acquisition.initialize()
        print(f"[DEBUG Roo] JugglingTracker.switch_to_jugvid2cpp_mode: JugVid2cpp initialize() result: {jugvid2cpp_init_success}") # Roo log
        
        if not jugvid2cpp_init_success:
            print("Failed to initialize JugVid2cpp. Reverting to live mode if possible.")
            print(f"[DEBUG Roo] JugglingTracker.switch_to_jugvid2cpp_mode: JugVid2cpp init failed, attempting fallback to live mode.") # Roo log
            # Attempt to revert to a default live mode
            self.main_window.feed_mode_combo.setCurrentIndex(0) # Visually switch back UI
            self.switch_to_live_mode(fallback=True) # Internal switch
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Error: Could not start JugVid2cpp. Reverted to live.", 5000)
            return False
        
        self.frame_count = 0
        self.start_time = time.time()
        if self.frame_timer:
            self.frame_timer.start(self.frame_timer_interval)
        print("Switched to JugVid2cpp 3D tracking mode.")
        print(f"[DEBUG Roo] JugglingTracker.switch_to_jugvid2cpp_mode: Successfully switched. FA mode: {self.frame_acquisition.mode}, type: {type(self.frame_acquisition)}") # Roo log
        return True

    @property
    def is_realsense_live_active(self):
        """Checks if the current frame_acquisition is RealSense in live mode."""
        if not self.frame_acquisition:
            print(f"[DEBUG Roo] JugglingTracker.is_realsense_live_active: self.frame_acquisition is None. Returning False.") # Roo log
            return False
        
        is_fa_instance = isinstance(self.frame_acquisition, FrameAcquisition) # Roo log
        not_webcam_instance = not isinstance(self.frame_acquisition, WebcamFrameAcquisition) # Roo log
        is_live_mode = self.frame_acquisition.mode == 'live' # Roo log
        result = is_fa_instance and not_webcam_instance and is_live_mode # Roo log
        print(f"[DEBUG Roo] JugglingTracker.is_realsense_live_active: is_FrameAcquisition={is_fa_instance}, not_WebcamFrameAcquisition={not_webcam_instance}, mode_is_live={is_live_mode}. Result: {result}") # Roo log
        return result

    def start_video_recording(self, filepath):
        """
        Starts recording the current RealSense feed to a .bag file.
        """
        if not (self.frame_acquisition and self.frame_acquisition.mode == 'live' and not self.frame_acquisition.is_recording):
            message = "Recording is only available for live RealSense feed and not already recording."
            print(f"Error: {message}")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(message, 3000)
            return False

        # Pause processing during re-initialization for recording (optional, but safer)
        # original_paused_state = self.paused
        # self.paused = True
        # if self.frame_timer:
        #     self.frame_timer.stop()

        success = self.frame_acquisition.start_recording(filepath)

        # self.paused = original_paused_state # Restore pause state
        # if self.frame_timer and self.running and not self.paused:
        #     self.frame_timer.start(self.frame_timer_interval)

        if success:
            self.is_currently_recording = True
            print(f"JugglingTracker: Recording started to {filepath}")
            if hasattr(self.main_window, 'update_recording_status'): # UI update callback
                self.main_window.update_recording_status(True, filepath)
            return True
        else:
            self.is_currently_recording = False
            print(f"JugglingTracker: Failed to start recording.")
            if hasattr(self.main_window, 'update_recording_status'): # UI update callback
                self.main_window.update_recording_status(False)
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Failed to start recording. Check console.", 3000)
            return False

    def stop_video_recording(self):
        """
        Stops the current video recording.
        """
        if not self.is_currently_recording:
            message = "Not currently recording."
            print(message)
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(message, 3000)
            return False

        if not (self.frame_acquisition and self.frame_acquisition.mode == 'live'):
            message = "Recording can only be stopped if in live RealSense mode."
            print(f"Error: {message}")
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage(message, 3000)
            # Still attempt to ensure recording flag is false
            self.is_currently_recording = False
            if hasattr(self.main_window, 'update_recording_status'):
                self.main_window.update_recording_status(False)
            return False

        # original_paused_state = self.paused
        # self.paused = True
        # if self.frame_timer:
        #     self.frame_timer.stop()
            
        success = self.frame_acquisition.stop_recording()
        
        # self.paused = original_paused_state
        # if self.frame_timer and self.running and not self.paused:
        #     self.frame_timer.start(self.frame_timer_interval)

        if success:
            recorded_filepath = self.frame_acquisition.recording_filepath # Path might be cleared in stop_recording
            self.is_currently_recording = False
            print(f"JugglingTracker: Recording stopped. File likely at {recorded_filepath if recorded_filepath else 'previous path'}") # Path might be cleared
            if hasattr(self.main_window, 'update_recording_status'): # UI update callback
                self.main_window.update_recording_status(False, recorded_filepath) # Pass path for msg
            return True
        else:
            # Even if frame_acquisition.stop_recording reports an issue with re-initializing live stream,
            # the recording itself might have stopped. We reflect that the app is no longer *trying* to record.
            self.is_currently_recording = False
            print(f"JugglingTracker: Issues reported while stopping recording or restarting live stream.")
            if hasattr(self.main_window, 'update_recording_status'): # UI update callback
                self.main_window.update_recording_status(False)
            if hasattr(self.main_window, 'statusBar'):
                self.main_window.statusBar().showMessage("Recording stopped, but there might have been issues. Check console.", 3000)
            return False

    def cleanup(self):
        """
        Clean up resources.
        """
        try:
            # Stop the frame timer
            self.frame_timer.stop()
            
            # Stop the camera
            if self.frame_acquisition:
                self.frame_acquisition.stop()
            
            # Clean up the extension manager
            if self.extension_manager:
                self.extension_manager.cleanup()

            # Clean up the watch manager
            if self.watch_imu_manager:
                self.watch_imu_manager.cleanup()
            
            # Close the main window
            self.main_window.close()
            
            # Exit the Qt application
            self.qt_app.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")


def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Juggling Tracker')
    parser.add_argument('--config-dir', type=str, help='Directory to save configuration files')
    parser.add_argument('--no-realsense', action='store_true', help='Disable RealSense camera')
    parser.add_argument('--webcam', action='store_true', help='Use webcam instead of RealSense')
    parser.add_argument('--simulation', action='store_true', help='Use video playback mode (replaces old simulation)')
    parser.add_argument('--jugvid2cpp', action='store_true', help='Use JugVid2cpp for high-performance 3D ball tracking')
    parser.add_argument('--video-path', type=str, help='Path to video file for playback mode')
    parser.add_argument('--camera-index', type=int, default=0, help='Index of the webcam to use')
    parser.add_argument('--watch-ips', nargs='+', help='Space-separated IP addresses of TicWatches for IMU streaming')
    # --simulation-speed is now legacy, but kept for arg parsing compatibility if scripts use it.
    parser.add_argument('--simulation-speed', type=float, default=1.0,
                        help='Legacy. Speed of video playback is determined by video FPS and processing.')
    return parser.parse_args()


def main():
    """
    Main entry point.
    """
    # Parse command line arguments
    args = parse_args()
    
    # Create and run the application
    app = JugglingTracker(
        config_dir=args.config_dir,
        use_realsense=not args.no_realsense and not args.webcam and not args.simulation and not args.jugvid2cpp,
        use_webcam=args.webcam,
        use_simulation=args.simulation,
        use_jugvid2cpp=args.jugvid2cpp,
        camera_index=args.camera_index,
        simulation_speed=args.simulation_speed, # Pass along, though its direct effect is diminished
        video_path=args.video_path,
        watch_ips=args.watch_ips
    )
    app.run()


if __name__ == '__main__':
    main()