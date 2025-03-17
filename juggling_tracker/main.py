#!/usr/bin/env python3
import os
import sys
import time
import cv2
import numpy as np
import argparse

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juggling_tracker.modules.frame_acquisition import FrameAcquisition
from juggling_tracker.modules.depth_processor import DepthProcessor
from juggling_tracker.modules.skeleton_detector import SkeletonDetector
from juggling_tracker.modules.blob_detector import BlobDetector
from juggling_tracker.modules.color_calibration import ColorCalibration
from juggling_tracker.modules.ball_identifier import BallIdentifier
from juggling_tracker.modules.multi_ball_tracker import MultiBallTracker
from juggling_tracker.ui.visualizer import Visualizer
from juggling_tracker.ui.ui_manager import UIManager
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
    
    def __init__(self, width=640, height=480, fps=30, num_balls=3):
        """
        Initialize the SimulationFrameAcquisition module.
        
        Args:
            width (int): Width of the simulated frames
            height (int): Height of the simulated frames
            fps (int): Frames per second
            num_balls (int): Number of balls to simulate
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.num_balls = num_balls
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
                
                # Draw ball on depth image
                for y in range(max(0, int(ball['y']) - ball['radius']), min(self.height, int(ball['y']) + ball['radius'])):
                    for x in range(max(0, int(ball['x']) - ball['radius']), min(self.width, int(ball['x']) + ball['radius'])):
                        if (x - ball['x']) ** 2 + (y - ball['y']) ** 2 <= ball['radius'] ** 2:
                            depth_image[y, x] = ball['z']
            
            # Simulate hands
            hand_y = self.height - 50
            left_hand_x = int(self.width / 4)
            right_hand_x = int(3 * self.width / 4)
            
            # Draw hands on color image
            cv2.circle(color_image, (left_hand_x, hand_y), 20, (0, 0, 255), -1)
            cv2.circle(color_image, (right_hand_x, hand_y), 20, (0, 255, 0), -1)
            
            # Draw hands on depth image
            for y in range(max(0, hand_y - 20), min(self.height, hand_y + 20)):
                for x in range(max(0, left_hand_x - 20), min(self.width, left_hand_x + 20)):
                    if (x - left_hand_x) ** 2 + (y - hand_y) ** 2 <= 20 ** 2:
                        depth_image[y, x] = 800  # Hands are closer than balls
                
                for x in range(max(0, right_hand_x - 20), min(self.width, right_hand_x + 20)):
                    if (x - right_hand_x) ** 2 + (y - hand_y) ** 2 <= 20 ** 2:
                        depth_image[y, x] = 800  # Hands are closer than balls
            
            # Add frame count
            self.frame_count += 1
            cv2.putText(color_image, f"Frame: {self.frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add a small delay to simulate real-time
            time.sleep(1 / self.fps)
            
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
    
    def __init__(self, config_dir=None, use_realsense=True, use_webcam=False, use_simulation=False, camera_index=0):
        """
        Initialize the JugglingTracker application.
        
        Args:
            config_dir (str): Directory to save configuration files (default: None)
            use_realsense (bool): Whether to use the RealSense camera (default: True)
            use_webcam (bool): Whether to use a webcam as fallback (default: False)
            use_simulation (bool): Whether to use simulation mode (default: False)
            camera_index (int): Index of the webcam to use (default: 0)
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
            print("Using simulation mode as specified.")
            self.frame_acquisition = SimulationFrameAcquisition()
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
        self.visualizer = Visualizer()
        self.ui_manager = UIManager(self.visualizer.window_name, self.config_dir)
        
        # Set the reference to this application in the UI manager
        self.ui_manager.set_app(self)
        
        self.extension_manager = ExtensionManager()
        
        # Initialize state
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.start_time = 0
        self.fps = 0
        
        # Load default extensions (but don't enable them)
        self.load_default_extensions()
    
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
        self.ui_manager.update_extensions_menu(self.extension_manager)
    
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
            while self.running:
                # Process a frame
                self.process_frame()
                
                # Handle user input
                key = cv2.waitKey(1)
                self.handle_key(key)
                
                # Check if the window was closed
                if cv2.getWindowProperty(self.visualizer.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    print("Window closed by user.")
                    self.running = False
                    break
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
        if self.paused:
            return
        
        # Get frames from the camera
        depth_frame, color_frame, depth_image, color_image = self.frame_acquisition.get_frames()
        
        if depth_image is None or color_image is None:
            return
        
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
        if self.ui_manager.is_calibrating() and filtered_blobs:
            # Use the largest blob for calibration
            largest_blob = max(filtered_blobs, key=lambda b: b['radius'])
            self.ui_manager.update_calibration(largest_blob, color_image)
        
        # Prepare masks for visualization
        masks = {
            'Proximity': proximity_mask,
            'Hands': hand_mask,
            'Combined': combined_mask
        }
        
        # Draw the UI
        color_image = self.ui_manager.draw_ui(color_image)
        
        # Show the frame
        self.visualizer.show_frame(
            color_image=color_image,
            depth_image=depth_image,
            masks=masks if self.visualizer.show_masks else None,
            identified_balls=identified_balls,
            hand_positions=hand_positions,
            extension_results=extension_results,
            debug_info={
                'Num Blobs': len(blobs),
                'Num Filtered Blobs': len(filtered_blobs),
                'Num Identified Balls': len(identified_balls),
                'Num Tracked Balls': len(self.ball_tracker.get_tracked_balls()),
                'Mode': 'RealSense' if isinstance(self.frame_acquisition, FrameAcquisition) else 
                       ('Webcam' if isinstance(self.frame_acquisition, WebcamFrameAcquisition) else 'Simulation')
            }
        )
        
        # Update frame count and FPS
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.fps = self.frame_count / elapsed_time
    
    def handle_key(self, key):
        """
        Handle a key press.
        
        Args:
            key (int): Key code
        """
        if key == -1:
            return
        
        key = key & 0xFF
        
        if key == ord('q') or key == 27:  # q or ESC
            self.running = False
        elif key == ord('p'):  # p
            self.paused = not self.paused
        elif key == ord('d'):  # d
            self.visualizer.toggle_debug_mode()
        elif key == ord('m'):  # m
            self.visualizer.toggle_masks_view()
        elif key == ord('v'):  # v
            self.visualizer.toggle_depth_view()
        elif key == ord('f'):  # f
            self.visualizer.toggle_fps_display()
        elif key == ord('e'):  # e
            self.visualizer.toggle_extension_results()
        elif key == ord('r'):  # r
            # Reset the application
            self.ball_tracker.reset()
            self.frame_count = 0
            self.start_time = time.time()
    
    def cleanup(self):
        """
        Clean up resources.
        """
        try:
            # Stop the camera
            if self.frame_acquisition:
                self.frame_acquisition.stop()
            
            # Clean up the visualizer
            if self.visualizer:
                self.visualizer.cleanup()
            
            # Clean up the UI manager
            if self.ui_manager:
                self.ui_manager.cleanup()
            
            # Clean up the extension manager
            if self.extension_manager:
                self.extension_manager.cleanup()
            
            # Close all OpenCV windows
            cv2.destroyAllWindows()
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
        camera_index=args.camera_index
    )
    app.run()


if __name__ == '__main__':
    main()