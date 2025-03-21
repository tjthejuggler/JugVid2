#!/usr/bin/env python3
import os
import sys
import time
import cv2
import numpy as np
import argparse
from PyQt6.QtWidgets import QApplication
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
from juggling_tracker.ui.main_window import MainWindow
from juggling_tracker.extensions.extension_manager import ExtensionManager


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
        self.ball_identifier = BallIdentifier(self.color_calibration)
        self.ball_tracker = MultiBallTracker()
        
        # Create Qt application
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        
        # Load QSS stylesheet
        self.load_stylesheet()
        
        # Create main window
        self.main_window = MainWindow(self, self.config_dir)
        
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
        
        if depth_image is None or color_image is None:
            return
        
        # Check if we're in simulation mode for optimized processing
        is_simulation_mode = isinstance(self.frame_acquisition, SimulationFrameAcquisition)
        
        if is_simulation_mode:
            # Simplified processing path for simulation mode
            # Get simulated hand positions
            hand_y = self.frame_acquisition.height - 50
            left_hand_x = int(self.frame_acquisition.width / 4)
            right_hand_x = int(3 * self.frame_acquisition.width / 4)
            hand_positions = ((left_hand_x, hand_y), (right_hand_x, hand_y))
            
            # Create simplified identified balls directly from simulation data
            identified_balls = []
            for i, ball in enumerate(self.frame_acquisition.balls):
                identified_balls.append({
                    'name': f"Ball {i+1}",
                    'position': (int(ball['x']), int(ball['y'])),
                    'radius': ball['radius'],
                    'color': ball['color'],
                    'depth': ball['z'] * self.frame_acquisition.get_depth_scale(),
                    'contour': None  # Not needed for visualization
                })
            
            # Update the main window with the simulated data
            self.main_window.update_frame(
                color_image=color_image,
                depth_image=depth_image,
                masks=None,  # Skip mask visualization in simulation mode
                identified_balls=identified_balls,
                hand_positions=hand_positions,
                extension_results=None,  # Skip extension processing in simulation mode
                debug_info={
                    'Num Identified Balls': len(identified_balls),
                    'Mode': 'Simulation (Optimized)',
                    'Simulation Speed': self.frame_acquisition.simulation_speed
                }
            )
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
            
            # Detect blobs in the combined mask
            blobs = self.blob_detector.detect_blobs(combined_mask)
            
            # Filter blobs by depth variance
            filtered_blobs = self.blob_detector.filter_blobs_by_depth_variance(blobs, depth_in_meters)
            
            # Identify balls
            identified_balls = self.ball_identifier.identify_balls(filtered_blobs, color_image)
            
            # Get ball positions and depths
            ball_positions = self.ball_identifier.get_ball_positions(identified_balls)
            ball_depths = self.ball_identifier.get_ball_depths(identified_balls)
            
            # Update ball trackers
            ball_3d_positions = self.ball_tracker.update_trackers(
                identified_balls,
                ball_positions,
                ball_depths,
                self.frame_acquisition.get_intrinsics()
            )
            
            # Get ball velocities
            ball_velocities = self.ball_tracker.get_ball_velocities()
            
            # Prepare frame data for extensions
            frame_data = {
                'color_image': color_image,
                'depth_image': depth_image,
                'depth_in_meters': depth_in_meters,
                'tracked_balls': self.ball_tracker.get_tracked_balls(),
                'ball_positions': ball_3d_positions,
                'ball_velocities': ball_velocities,
                'hand_positions': hand_positions,
                'timestamp': time.time()
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
            
            # Update the main window with the frame
            self.main_window.update_frame(
                color_image=color_image,
                depth_image=depth_image,
                masks=masks if self.main_window.show_masks else None,
                identified_balls=identified_balls,
                hand_positions=hand_positions,
                extension_results=extension_results,
                debug_info={
                    'Num Blobs': len(blobs),
                    'Num Filtered Blobs': len(filtered_blobs),
                    'Num Identified Balls': len(identified_balls),
                    'Num Tracked Balls': len(self.ball_tracker.get_tracked_balls()),
                    'Mode': 'RealSense' if isinstance(self.frame_acquisition, FrameAcquisition) else 'Webcam'
                }
            )
        
        # Update frame count and FPS
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.fps = self.frame_count / elapsed_time
    
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