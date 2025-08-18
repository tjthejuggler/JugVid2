import subprocess
import time
import numpy as np
import cv2
import base64
import threading
import queue
from typing import Dict, List, Optional, Tuple

class JugVid2cppInterface:
    """
    Interface for the JugVid2cpp ball tracker with video streaming support.
    
    This module handles:
    - Starting and managing the JugVid2cpp subprocess in streaming mode
    - Reading and parsing both video frames and 3D position data from JugVid2cpp
    - Converting the data to the format expected by juggling_tracker
    - Providing both video frames and identified balls to juggling_tracker
    """
    
    def __init__(self, 
                 executable_path: str = "/home/twain/Projects/JugVid2cpp/build/bin/ball_tracker",
                 color_to_profile_mapping: Optional[Dict[str, Dict]] = None,
                 default_radius_px: int = 15,
                 synthetic_intrinsics: Optional[Dict] = None):
        """
        Initialize the JugVid2cpp interface.
        
        Args:
            executable_path: Path to the JugVid2cpp executable
            color_to_profile_mapping: Mapping of JugVid2cpp color names to juggling_tracker profiles
            default_radius_px: Default radius in pixels for synthetic blobs
            synthetic_intrinsics: Synthetic camera intrinsics for coordinate conversion
        """
        self.executable_path = executable_path
        self.process = None
        self.is_running = False
        self.last_frame_data = []
        self.last_identified_balls = []
        self.last_video_frame = None
        self.mode = 'jugvid2cpp'  # Add mode attribute for compatibility
        
        # Threading for non-blocking reads
        self.read_thread = None
        self.frame_queue = queue.Queue(maxsize=10)  # Buffer up to 10 frames
        self.stop_thread = False
        
        # Default color to profile mapping if none provided
        self.color_to_profile_mapping = color_to_profile_mapping or {
            "pink": {"profile_id": "pink_ball", "name": "Pink Ball"},
            "orange": {"profile_id": "orange_ball", "name": "Orange Ball"},
            "green": {"profile_id": "green_ball", "name": "Green Ball"},
            "yellow": {"profile_id": "yellow_ball", "name": "Yellow Ball"}
        }
        
        self.default_radius_px = default_radius_px
        
        # Synthetic camera intrinsics for coordinate conversion if needed
        self.synthetic_intrinsics = synthetic_intrinsics or {
            "fx": 600.0,  # Focal length x
            "fy": 600.0,  # Focal length y
            "ppx": 320.0, # Principal point x
            "ppy": 240.0  # Principal point y
        }
        
        # Create a class that mimics the RealSense intrinsics structure
        class SyntheticIntrinsics:
            def __init__(self, fx, fy, ppx, ppy):
                self.fx = fx
                self.fy = fy
                self.ppx = ppx
                self.ppy = ppy
        
        self.intrinsics_obj = SyntheticIntrinsics(
            self.synthetic_intrinsics["fx"],
            self.synthetic_intrinsics["fy"],
            self.synthetic_intrinsics["ppx"],
            self.synthetic_intrinsics["ppy"]
        )
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.error_state = False
        self.error_message = ""
    
    def _decode_base64_image(self, base64_string: str) -> Optional[np.ndarray]:
        """Decode base64 string to OpenCV image."""
        try:
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_string)
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            # Decode image
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"Error decoding base64 image: {e}")
            return None
    
    def _parse_tracking_data(self, tracking_string: str) -> List[Dict]:
        """Parse tracking data string into ball data list."""
        ball_data_list = []
        if not tracking_string.strip():
            return ball_data_list
            
        ball_entries = tracking_string.split(';')
        for ball_entry in ball_entries:
            parts = ball_entry.split(',')
            if len(parts) == 4:
                color_name = parts[0]
                try:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    ball_data_list.append({
                        "color_name": color_name,
                        "position_3d": (x, y, z)
                    })
                except ValueError:
                    continue  # Skip malformed data
        return ball_data_list
    
    def _read_stream_thread(self):
        """Thread function to continuously read from JugVid2cpp stream."""
        while not self.stop_thread and self.process and self.is_running:
            try:
                if self.process.poll() is not None:
                    print("JugVid2cpp process has exited")
                    self.error_state = True
                    self.error_message = "JugVid2cpp process exited unexpectedly"
                    break
                
                line = self.process.stdout.readline()
                if not line:
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse the streaming format: FRAME:<base64_image>|TRACK:<tracking_data>
                if line.startswith("FRAME:") and "|TRACK:" in line:
                    parts = line.split("|TRACK:", 1)
                    if len(parts) == 2:
                        frame_part = parts[0][6:]  # Remove "FRAME:" prefix
                        track_part = parts[1]
                        
                        # Decode video frame
                        video_frame = self._decode_base64_image(frame_part)
                        
                        # Parse tracking data
                        ball_data = self._parse_tracking_data(track_part)
                        
                        # Put frame data in queue (non-blocking)
                        frame_data = {
                            'video_frame': video_frame,
                            'ball_data': ball_data,
                            'timestamp': time.time()
                        }
                        
                        try:
                            self.frame_queue.put_nowait(frame_data)
                            self.consecutive_errors = 0  # Reset error counter on success
                        except queue.Full:
                            # Remove oldest frame and add new one
                            try:
                                self.frame_queue.get_nowait()
                                self.frame_queue.put_nowait(frame_data)
                            except queue.Empty:
                                pass
                
            except Exception as e:
                self.consecutive_errors += 1
                print(f"Error in read thread: {e}")
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.error_state = True
                    self.error_message = f"Too many consecutive read errors: {str(e)}"
                    break
                time.sleep(0.1)  # Brief pause on error
    
    def initialize(self) -> bool:
        """
        Initialize the JugVid2cpp interface (alias for start method).
        
        Returns:
            bool: True if initialized successfully, False otherwise
        """
        return self.start()
    
    def start(self) -> bool:
        """
        Start the JugVid2cpp ball tracker process in streaming mode.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Start JugVid2cpp in streaming mode
            self.process = subprocess.Popen(
                [self.executable_path, "stream"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line-buffered
            )
            self.is_running = True
            self.error_state = False
            self.error_message = ""
            self.consecutive_errors = 0
            
            # Start the reading thread
            self.stop_thread = False
            self.read_thread = threading.Thread(target=self._read_stream_thread, daemon=True)
            self.read_thread.start()
            
            print(f"JugVid2cpp ball tracker started in streaming mode at {self.executable_path}")
            return True
            
        except FileNotFoundError:
            print(f"Error: JugVid2cpp executable not found at {self.executable_path}")
            self.error_state = True
            self.error_message = f"Executable not found: {self.executable_path}"
            return False
        except Exception as e:
            print(f"Error starting JugVid2cpp ball tracker: {e}")
            self.error_state = True
            self.error_message = f"Start error: {str(e)}"
            return False
    
    def stop(self):
        """Stop the JugVid2cpp ball tracker process."""
        self.stop_thread = True
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        
        if self.process and self.is_running:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1)
            except Exception as e:
                print(f"Error stopping JugVid2cpp process: {e}")
            finally:
                self.is_running = False
                print("JugVid2cpp ball tracker stopped")
    
    def get_frames(self) -> Tuple[None, None, None, Optional[np.ndarray]]:
        """
        Get the latest video frame from JugVid2cpp.
        
        Returns:
            Tuple: (None, None, None, color_image) - compatible with juggling_tracker interface
        """
        try:
            # Get the latest frame from queue
            frame_data = self.frame_queue.get_nowait()
            self.last_video_frame = frame_data['video_frame']
            self.last_frame_data = frame_data['ball_data']
            return None, None, None, frame_data['video_frame']
        except queue.Empty:
            # Return last known frame if no new frame available
            return None, None, None, self.last_video_frame
    
    def convert_to_identified_balls(self, ball_data_list: List[Dict]) -> List[Dict]:
        """
        Convert JugVid2cpp ball data to the format expected by juggling_tracker.
        
        Args:
            ball_data_list: List of ball data dictionaries from JugVid2cpp
            
        Returns:
            List[Dict]: List of identified ball dictionaries for MultiBallTracker
        """
        identified_balls = []
        
        for ball_data in ball_data_list:
            color_name = ball_data["color_name"]
            x, y, z = ball_data["position_3d"]
            
            # Skip if color not in mapping
            if color_name not in self.color_to_profile_mapping:
                continue
            
            profile_info = self.color_to_profile_mapping[color_name]
            
            # Project 3D point to 2D using synthetic intrinsics
            if z > 0:  # Avoid division by zero
                pixel_x = int((x * self.intrinsics_obj.fx / z) + self.intrinsics_obj.ppx)
                pixel_y = int((y * self.intrinsics_obj.fy / z) + self.intrinsics_obj.ppy)
            else:
                continue
            
            # Create a synthetic identified ball
            identified_ball = {
                "profile_id": profile_info["profile_id"],
                "name": profile_info["name"],
                "position": (pixel_x, pixel_y),  # 2D pixel position
                "radius": self.default_radius_px,  # Default radius in pixels
                "depth_m": z,  # Depth in meters
                "color_bgr": (0, 255, 0),  # Default color (green)
                "contour": None,  # No contour available
                "original_3d": (x, y, z)  # Store original 3D coordinates
            }
            
            identified_balls.append(identified_ball)
        
        self.last_identified_balls = identified_balls
        return identified_balls
    
    def get_identified_balls(self) -> List[Dict]:
        """
        Get the latest identified balls from the most recent frame data.
        
        Returns:
            List[Dict]: List of identified ball dictionaries
        """
        return self.convert_to_identified_balls(self.last_frame_data)
    
    def get_intrinsics(self):
        """
        Get the synthetic camera intrinsics.
        
        Returns:
            object: Synthetic camera intrinsics object
        """
        return self.intrinsics_obj
    
    def get_depth_scale(self):
        """
        Get the depth scale for converting depth values to meters.
        
        Returns:
            float: A default depth scale
        """
        return 0.001  # Default depth scale for RealSense cameras
    
    def get_status(self) -> Dict:
        """Get the current status of the JugVid2cpp interface."""
        return {
            "is_running": self.is_running,
            "error_state": self.error_state,
            "error_message": self.error_message,
            "consecutive_errors": self.consecutive_errors,
            "queue_size": self.frame_queue.qsize(),
            "last_frame_ball_count": len(self.last_frame_data)
        }
    
    def get_error_output(self) -> str:
        """Get any error output from the JugVid2cpp process."""
        if self.process and self.process.stderr:
            try:
                return self.process.stderr.read()
            except:
                return ""
        return ""