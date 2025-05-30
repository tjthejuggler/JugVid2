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
from juggling_tracker.ui.main_window import MainWindow
from juggling_tracker.extensions.extension_manager import ExtensionManager
from juggling_tracker.modules.ball_definer import BallDefiner
from juggling_tracker.modules.ball_profile_manager import BallProfileManager


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
            
            # Create a simulated depth image (just a gradient)
            simulated_depth_image = np.zeros((self.height, self.width), dtype=np.uint16)
            for y in range(0, self.height, 4):  # Skip pixels for better performance
                for x in range(0, self.width, 4):
                    # Create a gradient based on the distance from the center
                    center_x, center_y = self.width // 2, self.height // 2
                    distance = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                    # Normalize to 0-65535 (16-bit depth)
                    depth_value = int(65535 * (1 - distance / np.sqrt(center_x ** 2 + center_y ** 2)))
                    
                    # Fill a 4x4 block with the same value for better performance
                    for dy in range(4):
                        for dx in range(4):
                            if y + dy < self.height and x + dx < self.width:
                                simulated_depth_image[y + dy, x + dx] = depth_value
            
            # Store the frames for frame skipping
            self.last_color_image = color_image
            self.last_depth_image = simulated_depth_image
            
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


class SimulationFrameAcquisition:
    """
    Simulation frame acquisition class that generates random ball positions for testing.
    """
    
    def __init__(self, width=320, height=240, fps=30, num_balls=3, simulation_speed=2.0):
        """
        Initialize the SimulationFrameAcquisition module.
        
        Args:
            width (int): Width of the simulated frames
            height (int): Height of the simulated frames
            fps (int): Frames per second
            num_balls (int): Number of balls to simulate
            simulation_speed (float): Speed multiplier for simulation (higher = faster)
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.num_balls = num_balls
        self.simulation_speed = simulation_speed
        self.balls = []
        self.frame_count = 0
        
    def initialize(self):
        """
        Initialize the simulation.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Create random balls
            for i in range(self.num_balls):
                self.balls.append({
                    'x': np.random.randint(50, self.width - 50),
                    'y': np.random.randint(50, self.height - 50),
                    'z': np.random.randint(500, 1500),  # Depth in mm
                    'vx': np.random.randint(-5, 5),
                    'vy': np.random.randint(-5, 5),
                    'vz': np.random.randint(-5, 5),
                    'color': (
                        np.random.randint(0, 255),
                        np.random.randint(0, 255),
                        np.random.randint(0, 255)
                    ),
                    'radius': np.random.randint(10, 20)
                })
            
            print("Using simulation mode.")
            print("Note: This is a simulation for testing purposes only.")
            
            return True
        except Exception as e:
            print(f"Error initializing simulation: {e}")
            return False
    
    def get_frames(self):
        """
        Get simulated frames.
        
        Returns:
            tuple: (None, None, depth_image, color_image)
        """
        try:
            # Create empty images
            color_image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            depth_image = np.ones((self.height, self.width), dtype=np.uint16) * 65535  # Far background
            
            # Update ball positions
            for ball in self.balls:
                # Update position
                ball['x'] += ball['vx']
                ball['y'] += ball['vy']
                ball['z'] += ball['vz']
                
                # Bounce off walls
                if ball['x'] < ball['radius'] or ball['x'] > self.width - ball['radius']:
                    ball['vx'] = -ball['vx']
                if ball['y'] < ball['radius'] or ball['y'] > self.height - ball['radius']:
                    ball['vy'] = -ball['vy']
                if ball['z'] < 500 or ball['z'] > 1500:
                    ball['vz'] = -ball['vz']
                
                # Draw ball on color image
                cv2.circle(color_image, (int(ball['x']), int(ball['y'])), ball['radius'], ball['color'], -1)
                
                # Create a mask for the ball and use it to set depth values efficiently
                ball_mask = np.zeros((self.height, self.width), dtype=np.uint8)
                cv2.circle(ball_mask, (int(ball['x']), int(ball['y'])), ball['radius'], 255, -1)
                depth_image[ball_mask > 0] = ball['z']
            
            # Simulate hands
            hand_y = self.height - 50
            left_hand_x = int(self.width / 4)
            right_hand_x = int(3 * self.width / 4)
            
            # Draw hands on color image
            cv2.circle(color_image, (left_hand_x, hand_y), 20, (0, 0, 255), -1)
            cv2.circle(color_image, (right_hand_x, hand_y), 20, (0, 255, 0), -1)
            
            # Create masks for hands and use them to set depth values efficiently
            hand_mask = np.zeros((self.height, self.width), dtype=np.uint8)
            cv2.circle(hand_mask, (left_hand_x, hand_y), 20, 255, -1)
            cv2.circle(hand_mask, (right_hand_x, hand_y), 20, 255, -1)
            depth_image[hand_mask > 0] = 800  # Hands are closer than balls
            
            # Add frame count
            self.frame_count += 1
            cv2.putText(color_image, f"Frame: {self.frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add a small delay to simulate real-time, adjusted by simulation speed
            if self.simulation_speed > 0:
                time.sleep((1 / self.fps) / self.simulation_speed)
            
            return None, None, depth_image, color_image
        except Exception as e:
            print(f"Error getting simulated frames: {e}")
            return None, None, None, None
    
    def get_intrinsics(self):
        """
        Get the camera intrinsics for 3D calculations.
        
        Returns:
            None: Camera intrinsics are not available in simulation mode
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
        Stop the simulation.
        """
        pass

class JugglingTracker:
    """
    Main application class for the Juggling Tracker.
    
    This class ties all the modules together and provides the main entry point for the application.
    """
    
    def __init__(self, config_dir=None, use_realsense=True, use_webcam=False, use_simulation=False, camera_index=0, simulation_speed=2.0):
        """
        Initialize the JugglingTracker application.
        
        Args:
            config_dir (str): Directory to save configuration files (default: None)
            use_realsense (bool): Whether to use the RealSense camera (default: True)
            use_webcam (bool): Whether to use a webcam as fallback (default: False)
            use_simulation (bool): Whether to use simulation mode (default: False)
            camera_index (int): Index of the webcam to use (default: 0)
            simulation_speed (float): Speed multiplier for simulation (higher = faster)
        """
        # Set up configuration directory
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize frame acquisition based on mode
        self.use_realsense = use_realsense
        self.use_webcam = use_webcam
        self.use_simulation = use_simulation
        self.camera_index = camera_index
        
        # Set the frame acquisition module based on the specified mode
        if use_simulation:
            print("Using optimized simulation mode as specified.")
            self.frame_acquisition = SimulationFrameAcquisition(
                width=320,  # Lower resolution for better performance
                height=240,
                simulation_speed=simulation_speed
            )
        elif use_webcam:
            print("Using webcam mode as specified.")
            self.frame_acquisition = WebcamFrameAcquisition(camera_index=camera_index)
        elif use_realsense:
            print("Using RealSense mode as specified.")
            self.frame_acquisition = FrameAcquisition()
        else:
            # Default to RealSense with fallback
            print("Using RealSense mode with fallback.")
            self.frame_acquisition = FrameAcquisition()
        
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
        
        # Set up frame processing timer with faster rate for simulation mode
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.process_frame)
        
        # Use a faster timer interval for simulation mode
        if use_simulation:
            self.frame_timer_interval = 16  # ~60 FPS target for simulation
        else:
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
            print("Failed to initialize primary camera mode.")
            
            # If the specified mode failed, try fallback modes
            if self.use_realsense and not self.use_webcam and not self.use_simulation:
                print("Trying webcam fallback...")
                self.frame_acquisition = WebcamFrameAcquisition(camera_index=self.camera_index)
                if not self.frame_acquisition.initialize():
                    print("Webcam fallback failed. Trying simulation mode...")
                    self.frame_acquisition = SimulationFrameAcquisition()
                    if not self.frame_acquisition.initialize():
                        print("Simulation mode failed. Exiting.")
                        return False
        
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
            
            # Start the frame processing timer with the appropriate interval
            self.frame_timer.start(self.frame_timer_interval)
            
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

        if depth_image is None or color_image is None:
            print("Warning: Invalid frames received from frame_acquisition, skipping frame processing.") # Enhanced message
            return
        
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
        
        # Check if we're in simulation mode for optimized processing
        is_simulation_mode = isinstance(self.frame_acquisition, SimulationFrameAcquisition)
        
        if is_simulation_mode:
            # Simplified processing path for simulation mode
            # Get simulated hand positions
            hand_y = self.frame_acquisition.height - 50
            left_hand_x = int(self.frame_acquisition.width / 4)
            right_hand_x = int(3 * self.frame_acquisition.width / 4)
            hand_positions = ((left_hand_x, hand_y), (right_hand_x, hand_y))
            
            # Get current time for tracking
            current_time = time.time()
            
            # Get current intrinsics (might be None in simulation mode)
            current_intrinsics = self.frame_acquisition.get_intrinsics()
            
            # Create simplified identified balls directly from simulation data
            identified_balls = []
            for i, ball in enumerate(self.frame_acquisition.balls):
                # Create a ball structure that matches what BallIdentifier.identify_balls would return
                identified_balls.append({
                    'profile_id': f"sim_ball_{i+1}",  # Simulated profile ID
                    'name': f"Ball {i+1}",
                    'position': (int(ball['x']), int(ball['y'])),
                    'radius': ball['radius'],
                    'color_bgr': ball['color'],
                    'depth_m': ball['z'] * self.frame_acquisition.get_depth_scale(),
                    'contour': None  # Not needed for visualization
                })
            
            # Update ball trackers with new signature
            if hasattr(self, 'ball_tracker') and self.ball_tracker is not None:
                tracked_balls_display_info = self.ball_tracker.update_trackers(
                    identified_balls,
                    current_intrinsics,
                    current_time=current_time
                )
            else:
                tracked_balls_display_info = []
            
            # Prepare simplified frame data for simulation mode
            frame_data = {
                'timestamp': current_time,
                'color_image': color_image,
                'depth_image': depth_image,
                'intrinsics': current_intrinsics,
                'identified_balls_raw': identified_balls,
                'tracked_balls': self.ball_tracker.get_tracked_balls() if hasattr(self, 'ball_tracker') else [],
                'hand_positions': hand_positions
            }
            
            # Update the main window with the simulated data
            try:
                # Create a simple tracking result for simulation mode
                if len(identified_balls) > 0:
                    avg_x = sum(ball['position'][0] for ball in identified_balls) / len(identified_balls)
                    avg_y = sum(ball['position'][1] for ball in identified_balls) / len(identified_balls)
                    sim_tracking_result = {
                        'stable_position': (int(avg_x), int(avg_y)),
                        'confidence': 0.8,
                        'stability_score': 0.9,
                        'object_count': len(identified_balls)
                    }
                else:
                    sim_tracking_result = {
                        'stable_position': None,
                        'confidence': 0.0,
                        'stability_score': 0.0,
                        'object_count': 0
                    }
                
                self.main_window.update_frame(
                    color_image=color_image,
                    depth_image=depth_image,
                    masks=None,  # Skip mask visualization in simulation mode
                    tracked_balls_for_display=tracked_balls_display_info,
                    hand_positions=hand_positions,
                    extension_results=None,  # Skip extension processing in simulation mode
                    simple_tracking=sim_tracking_result,
                    debug_info={
                        'Num Identified Balls': len(identified_balls),
                        'Num Tracked Balls': len(self.ball_tracker.get_tracked_balls()) if hasattr(self, 'ball_tracker') else 0,
                        'Mode': 'Simulation (Optimized)',
                        'Simulation Speed': self.frame_acquisition.simulation_speed,
                        'Frame Size': f"{color_image.shape[1]}x{color_image.shape[0]}"
                    }
                )
                
                # Update the tracking position display
                self.main_window.update_tracking_position_display(sim_tracking_result)
            except Exception as e:
                print(f"Error updating frame in simulation mode: {e}")
        else:
            # Original processing path for real camera or webcam
            # Process the depth frame
            depth_in_meters = self.depth_processor.process_depth_frame(depth_frame, depth_image, self.frame_acquisition.get_depth_scale())
            
            # Create a proximity mask
            proximity_mask = self.depth_processor.create_proximity_mask(depth_in_meters)
            proximity_mask = self.depth_processor.cleanup_mask(proximity_mask)
            
            # Detect the skeleton
            pose_landmarks = self.skeleton_detector.detect_skeleton(color_image)
            
            # Get hand positions
            hand_positions = self.skeleton_detector.get_hand_positions(pose_landmarks, color_image.shape)
            
            # Create a hand mask
            hand_mask = self.skeleton_detector.create_hand_mask(hand_positions, color_image.shape)
            
            # Combine the proximity mask and hand mask
            combined_mask = cv2.bitwise_and(proximity_mask, cv2.bitwise_not(hand_mask))
            
            # Perform simple tracking on the combined mask
            min_size, max_size = self.depth_processor.get_object_size_range()
            simple_tracking_result = self.simple_tracker.track_objects(combined_mask, min_size, max_size)
            
            # Detect blobs in the combined mask
            blobs = self.blob_detector.detect_blobs(combined_mask)
            
            # Filter blobs by depth variance
            filtered_blobs = self.blob_detector.filter_blobs_by_depth_variance(blobs, depth_in_meters)
            
            # Get current time for tracking
            current_time = time.time()
            
            # Get current intrinsics
            current_intrinsics = self.frame_acquisition.get_intrinsics()
            
            # Identify balls with depth and intrinsics
            if hasattr(self, 'ball_identifier') and self.ball_identifier is not None:
                identified_balls = self.ball_identifier.identify_balls(
                    filtered_blobs,
                    color_image,
                    depth_in_meters,
                    current_intrinsics
                )
            else:
                identified_balls = []
                # print_once("WARN: BallIdentifier not available in process_frame.")
            
            # Update ball trackers with new signature
            if hasattr(self, 'ball_tracker') and self.ball_tracker is not None:
                tracked_balls_display_info = self.ball_tracker.update_trackers(
                    identified_balls,
                    current_intrinsics,
                    current_time=current_time
                )
            else:
                tracked_balls_display_info = []
                # print_once("WARN: MultiBallTracker not available in process_frame.")
            
            # Get ball velocities (still available through the tracker)
            ball_velocities = self.ball_tracker.get_ball_velocities()
            
            # Prepare frame data for extensions with updated structure
            frame_data = {
                'timestamp': current_time,
                'color_image': color_image,
                'depth_image': depth_image,
                'depth_in_meters': depth_in_meters,
                'intrinsics': current_intrinsics,
                'raw_blobs': filtered_blobs,
                'identified_balls_raw': identified_balls,
                'tracked_balls': self.ball_tracker.get_tracked_balls(),
                'ball_velocities': ball_velocities,
                'hand_positions': hand_positions,
                'simple_tracking': simple_tracking_result
            }
            
            # Process the frame with extensions
            extension_results = self.extension_manager.process_frame(frame_data)
            
            # Update calibration if in calibration mode
            if self.main_window.is_calibrating() and filtered_blobs:
                # Use the largest blob for calibration
                largest_blob = max(filtered_blobs, key=lambda b: b['radius'])
                self.main_window.update_calibration(largest_blob, color_image)
            
            # Prepare masks for visualization
            masks = {
                'Proximity': proximity_mask,
                'Hands': hand_mask,
                'Combined': combined_mask
            }
            
            # Update the main window with the frame, now using tracked_balls_display_info
            try:
                self.main_window.update_frame(
                    color_image=color_image,
                    depth_image=depth_image,
                    masks=masks if self.main_window.show_masks else None,
                    tracked_balls_for_display=tracked_balls_display_info,
                    hand_positions=hand_positions,
                    extension_results=extension_results,
                    simple_tracking=simple_tracking_result,
                    debug_info={
                        'Num Blobs': len(blobs),
                        'Num Filtered Blobs': len(filtered_blobs),
                        'Num Identified Balls': len(identified_balls),
                        'Num Tracked Balls': len(self.ball_tracker.get_tracked_balls()),
                        'Simple Tracking Objects': simple_tracking_result.get('object_count', 0),
                        'Mode': 'RealSense' if isinstance(self.frame_acquisition, FrameAcquisition) else 'Webcam',
                        'Frame Size': f"{color_image.shape[1]}x{color_image.shape[0]}"
                    }
                )
                
                # Update the tracking position display
                self.main_window.update_tracking_position_display(simple_tracking_result)
            except Exception as e:
                print(f"Error updating frame in camera mode: {e}")
        
        # Update frame count and FPS
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.fps = self.frame_count / elapsed_time
    
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
    parser.add_argument('--simulation', action='store_true', help='Use simulation mode')
    parser.add_argument('--camera-index', type=int, default=0, help='Index of the webcam to use')
    parser.add_argument('--simulation-speed', type=float, default=2.0,
                        help='Speed multiplier for simulation (higher = faster)')
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
        use_realsense=not args.no_realsense and not args.webcam and not args.simulation,
        use_webcam=args.webcam,
        use_simulation=args.simulation,
        camera_index=args.camera_index,
        simulation_speed=args.simulation_speed
    )
    app.run()


if __name__ == '__main__':
    main()