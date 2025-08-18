import pyrealsense2 as rs
import numpy as np
import cv2
import os
import sys
import time
import atexit
from pathlib import Path

# Add core camera module to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from core.camera.camera_resource_manager import CameraResourceManager, CameraResourceError

class FrameAcquisition:
    """
    Handles the RealSense camera setup and frame capture.
    
    This module is responsible for:
    - Setting up the RealSense pipeline
    - Configuring the depth and color streams
    - Aligning the depth and color frames
    - Providing access to camera intrinsics for 3D calculations
    """
    
    def __init__(self, width=640, height=480, fps=30, mode='live', video_path=None, depth_only=False, debug_camera=False):
        """
        Initialize the FrameAcquisition module.
        
        Args:
            width (int): Width of the camera frames or desired output width for video.
            height (int): Height of the camera frames or desired output height for video.
            fps (int): Frames per second for camera configuration.
            mode (str): 'live' for RealSense camera, 'playback' for video file.
            video_path (str, optional): Path to the video file if mode is 'playback'.
            depth_only (bool): If True, only enable depth stream (for cable compatibility).
            debug_camera (bool): Enable camera debugging output.
        """
        self.width = width
        self.height = height
        self.fps = fps  # Target FPS for camera, video FPS is intrinsic to file
        self.mode = mode
        self.video_path = video_path
        self.depth_only = depth_only
        self.debug_camera = debug_camera
        
        self.pipeline = None
        self.align = None
        self.intrinsics = None
        self.depth_scale = None
        self.video_capture = None
        self.video_frame_count = 0
        self.video_fps = 0
        self.is_recording = False
        self.recording_filepath = None
        
        # Camera resource management
        self.camera_resource_manager = None
        self.resource_lock_acquired = False
        self.initialization_attempts = 0
        self.max_initialization_attempts = 3
        
        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
        
        if self.debug_camera:
            print(f"🎥 [DEBUG] FrameAcquisition initialized in {mode} mode")
        
    def _initialize_live_stream(self, recording_config=None):
        """
        Helper method to initialize or re-initialize the RealSense live stream.
        Can take an optional config (e.g., for recording).
        """
        if self.pipeline: # Stop existing pipeline if any
            try:
                print("[DEBUG Roo FA] _initialize_live_stream: Stopping existing pipeline.") # Roo log
                self.pipeline.stop()
            except RuntimeError as e:
                print(f"Runtime error stopping existing pipeline (may be normal if not started): {e}")
            self.pipeline = None # Ensure it's reset
 
        try:
            print("[DEBUG Roo FA] _initialize_live_stream: Creating new pipeline and config.") # Roo log
            self.pipeline = rs.pipeline()
            config_to_use = recording_config if recording_config else rs.config()

            # Enable streams if not already enabled in a provided recording_config
            if recording_config is None or not recording_config.can_resolve(self.pipeline):
                 # Check if streams are already configured (e.g. from enable_device_from_file in future)
                is_playback_from_file_config = False
                if recording_config:
                    try:
                        # This is a bit of a hack to see if it's a file playback config
                        # A better way would be to pass a flag or check config type
                        if len(config_to_use.get_streams()) > 0 and hasattr(config_to_use, 'enable_device_from_file'):
                           is_playback_from_file_config = True # Crude check
                    except: # rs.config might not have get_streams before resolve
                        pass
                
                if not is_playback_from_file_config: # Don't re-enable if playing from file
                    config_to_use.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
                    if not self.depth_only:
                        config_to_use.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
                        print("[DEBUG Roo FA] _initialize_live_stream: Enabled both depth and color streams.")
                    else:
                        print("[DEBUG Roo FA] _initialize_live_stream: Enabled depth-only stream for cable compatibility.")

            print("[DEBUG Roo FA] _initialize_live_stream: Starting pipeline...") # Roo log
            profile = self.pipeline.start(config_to_use)
            print("[DEBUG Roo FA] _initialize_live_stream: Pipeline started.") # Roo log
            
            depth_sensor = profile.get_device().first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()
            print(f"Live Mode: Depth Scale is: {self.depth_scale:.3f} meters")
            print(f"[DEBUG Roo FA] _initialize_live_stream: Depth scale set to {self.depth_scale}") # Roo log
            
            if not self.depth_only:
                self.align = rs.align(rs.stream.color)
                print("[DEBUG Roo FA] _initialize_live_stream: Align object created.") # Roo log
                
                color_profile = profile.get_stream(rs.stream.color) # Ensure it's color stream for intrinsics
                if not color_profile: # Try depth if color not found (e.g. bag file only has depth)
                     depth_stream_profile = profile.get_stream(rs.stream.depth)
                     if depth_stream_profile:
                          self.intrinsics = depth_stream_profile.as_video_stream_profile().get_intrinsics()
                else:
                     self.intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
            else:
                # In depth-only mode, use depth stream for intrinsics and no alignment
                self.align = None
                depth_stream_profile = profile.get_stream(rs.stream.depth)
                if depth_stream_profile:
                    self.intrinsics = depth_stream_profile.as_video_stream_profile().get_intrinsics()
                print("[DEBUG Roo FA] _initialize_live_stream: Depth-only mode, no alignment needed.") # Roo log

            print("[DEBUG Roo FA] _initialize_live_stream: Initialization successful.") # Roo log
            return True
        except Exception as e:
            print(f"[DEBUG Roo FA] _initialize_live_stream: Exception during initialization: {e}") # Roo log
            print(f"Error initializing RealSense stream: {e}")
            self.pipeline = None # Ensure pipeline is None on failure
            return False

    def initialize(self):
        """
        Initialize the RealSense pipeline or video capture based on the mode.
        Includes camera resource conflict detection and resolution.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.initialization_attempts += 1
        
        if self.debug_camera:
            print(f"🎥 [DEBUG] Initializing FrameAcquisition (attempt {self.initialization_attempts}/{self.max_initialization_attempts})")
        
        if self.mode == 'live':
            return self._initialize_live_with_resource_management()
        elif self.mode == 'playback':
            if not self.video_path:
                print("❌ Error: Video path not provided for playback mode.")
                return False
            try:
                self.video_capture = cv2.VideoCapture(self.video_path)
                if not self.video_capture.isOpened():
                    print(f"❌ Error: Could not open video file: {self.video_path}")
                    self.video_capture = None
                    return False
                
                # Get video properties
                self.video_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                self.video_frame_count = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                native_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                native_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"✅ Playback Mode: Video '{self.video_path}' opened.")
                print(f"   Native resolution: {native_width}x{native_height}, FPS: {self.video_fps:.2f}")
                print(f"   Outputting at: {self.width}x{self.height}")

                # In playback mode, RealSense specific attributes are not available from generic video
                self.intrinsics = None
                self.depth_scale = None
                self.align = None
                return True
            except Exception as e:
                print(f"❌ Error initializing video playback: {e}")
                return False
        else:
            print(f"❌ Error: Unknown mode '{self.mode}'")
            return False
    
    def _initialize_live_with_resource_management(self):
        """
        Initialize live RealSense stream with comprehensive resource management.
        
        Returns:
            bool: True if initialization successful
        """
        if self.debug_camera:
            print("🎥 [DEBUG] Starting live stream initialization with resource management")
        
        # Initialize camera resource manager
        if not self.camera_resource_manager:
            self.camera_resource_manager = CameraResourceManager(debug=self.debug_camera)
        
        # Check camera availability first
        available, status_message = self.camera_resource_manager.check_camera_availability()
        if self.debug_camera:
            print(f"🎥 [DEBUG] Camera availability check: {available} - {status_message}")
        
        if not available:
            print(f"🎥 Camera Resource Conflict Detected: {status_message}")
            
            # Try to resolve conflicts automatically on first attempt
            if self.initialization_attempts == 1:
                print("🔄 Attempting automatic conflict resolution...")
                
                # Try to acquire lock with cleanup
                if self.camera_resource_manager.acquire_camera_lock(force_cleanup=False):
                    self.resource_lock_acquired = True
                    print("✅ Camera resource conflicts resolved automatically")
                else:
                    print("❌ Failed to resolve camera resource conflicts")
                    return False
            else:
                print("❌ Camera resource conflicts persist after multiple attempts")
                return False
        else:
            # Camera appears available, try to acquire lock
            if not self.resource_lock_acquired:
                if self.camera_resource_manager.acquire_camera_lock():
                    self.resource_lock_acquired = True
                    if self.debug_camera:
                        print("🎥 [DEBUG] Camera resource lock acquired")
                else:
                    print("❌ Failed to acquire camera resource lock")
                    return False
        
        # Now attempt RealSense initialization with enhanced error handling
        try:
            success = self._initialize_live_stream()
            
            if success:
                print("✅ RealSense camera initialized successfully")
                return True
            else:
                # If initialization failed, check if it's a resource issue
                if self._is_resource_busy_error():
                    print("🔄 RealSense initialization failed due to resource busy - attempting recovery...")
                    
                    # Force camera reset and retry
                    if self.camera_resource_manager.force_camera_reset():
                        print("🔄 Camera resources reset, retrying initialization...")
                        time.sleep(2)  # Give camera time to reset
                        
                        success = self._initialize_live_stream()
                        if success:
                            print("✅ RealSense camera initialized after resource reset")
                            return True
                
                print("❌ RealSense camera initialization failed")
                return False
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'device or resource busy' in error_msg or 'errno=16' in error_msg:
                print(f"🎥 Resource Busy Error Detected: {e}")
                
                # This is the specific error we're trying to fix
                if self.initialization_attempts < self.max_initialization_attempts:
                    print(f"🔄 Attempting recovery (attempt {self.initialization_attempts + 1}/{self.max_initialization_attempts})...")
                    
                    # Force cleanup and retry
                    if self.camera_resource_manager.force_camera_reset():
                        time.sleep(3)  # Give more time for resource cleanup
                        return self.initialize()  # Recursive retry
                
                print("❌ Failed to resolve 'Device or resource busy' error after multiple attempts")
                return False
            else:
                print(f"❌ RealSense initialization error: {e}")
                return False
    
    def _is_resource_busy_error(self):
        """
        Check if the last error was related to resource busy issues.
        
        Returns:
            bool: True if resource busy error detected
        """
        # This is a simple heuristic - in a more advanced implementation,
        # we could capture and analyze the specific RealSense error
        return True  # Assume resource issues for now when initialization fails
    
    def get_frames(self):
        """
        Get frames based on the current mode (live camera or video playback).
        Includes enhanced error handling for resource conflicts.
        
        Returns:
            tuple: (depth_frame, color_frame, depth_image, color_image) or (None, None, None, None)
                   In playback mode, depth_frame, color_frame (rs object), and depth_image will be None.
        """
        if self.mode == 'live':
            if self.pipeline is None:
                if self.debug_camera:
                    print("🎥 [DEBUG] Live pipeline not initialized. Call initialize() first.")
                return None, None, None, None
            
            try:
                frames = self.pipeline.wait_for_frames(5000)  # Keep timeout explicit
                
                if self.depth_only:
                    # Depth-only mode: no alignment needed, no color frame
                    depth_frame = frames.get_depth_frame()
                    if not depth_frame:
                        if self.debug_camera:
                            print("🎥 [DEBUG] Depth frame is None in depth-only mode.")
                        return None, None, None, None
                    
                    depth_image = np.asanyarray(depth_frame.get_data())
                    # Create a grayscale "color" image from depth for visualization
                    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
                    
                    return depth_frame, None, depth_image, depth_colormap
                else:
                    # Normal mode: both depth and color with alignment
                    aligned_frames = self.align.process(frames)
                    
                    depth_frame = aligned_frames.get_depth_frame()
                    color_frame = aligned_frames.get_color_frame()
                    
                    if not depth_frame or not color_frame:
                        if self.debug_camera:
                            print("🎥 [DEBUG] Depth or Color frame is None after alignment.")
                        return None, None, None, None
                    
                    depth_image = np.asanyarray(depth_frame.get_data())
                    color_image = np.asanyarray(color_frame.get_data())
                    
                    return depth_frame, color_frame, depth_image, color_image
                    
            except RuntimeError as e:
                error_msg = str(e).lower()
                if self.debug_camera:
                    print(f"🎥 [DEBUG] get_frames RuntimeError: {e}")
                
                # Check for specific resource busy errors
                if 'device or resource busy' in error_msg or 'errno=16' in error_msg:
                    print(f"🎥 Resource Busy Error in get_frames: {e}")
                    # Don't attempt recovery here as it would be too frequent
                    # Let the main application handle reinitialization
                elif 'no device connected' in error_msg or 'device disconnected' in error_msg:
                    print(f"🎥 Camera Disconnected: {e}")
                else:
                    print(f"🎥 RealSense Runtime Error: {e}")
                
                return None, None, None, None
                
            except Exception as e:
                if self.debug_camera:
                    print(f"🎥 [DEBUG] get_frames Unexpected Exception: {e}")
                print(f"🎥 Unexpected error getting frames: {e}")
                return None, None, None, None
        
        elif self.mode == 'playback':
            if self.video_capture is None or not self.video_capture.isOpened():
                print("Video capture not initialized or not open. Call initialize() first.")
                return None, None, None, None
            
            try:
                ret, color_image = self.video_capture.read()
                
                if not ret: # If end of video or error
                    # Loop the video
                    self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, color_image = self.video_capture.read()
                    if not ret:
                        print("Error: Could not read frame even after looping.")
                        return None, None, None, None
                
                # Resize to desired output dimensions
                if color_image.shape[1] != self.width or color_image.shape[0] != self.height:
                    color_image = cv2.resize(color_image, (self.width, self.height))
                
                # For playback of generic video, depth data and RealSense frame objects are not available
                return None, None, None, color_image
            except Exception as e:
                print(f"Error getting playback frame: {e}")
                return None, None, None, None
        
        else: # Should not happen if initialize worked
            return None, None, None, None

    def get_intrinsics(self):
        """
        Get the camera intrinsics for 3D calculations.
        
        Returns:
            rs.intrinsics: Camera intrinsics
        """
        return self.intrinsics
    
    def get_depth_scale(self):
        """
        Get the depth scale for converting depth values to meters.
        
        Returns:
            float: Depth scale in meters
        """
        return self.depth_scale
    
    def start_recording(self, filepath):
        """
        Starts recording the RealSense stream to a .bag file.
        This will stop the current live stream and restart it with recording enabled.
        """
        if self.mode != 'live':
            print("Error: Recording is only supported in 'live' (RealSense) mode.")
            return False
        
        if self.is_recording:
            print(f"Already recording to {self.recording_filepath}. Stop current recording first.")
            return False

        print(f"Starting recording to: {filepath}")
        
        # Stop current pipeline before reconfiguring for recording
        if self.pipeline:
            try:
                self.pipeline.stop()
            except RuntimeError as e:
                print(f"Error stopping pipeline before recording (may be normal if not started): {e}")
            self.pipeline = None

        record_config = rs.config()
        # Important: Configure the streams BEFORE enabling record to file.
        record_config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
        if not self.depth_only:
            record_config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        record_config.enable_record_to_file(filepath)
        
        if self._initialize_live_stream(recording_config=record_config):
            self.is_recording = True
            self.recording_filepath = filepath
            print(f"Recording started successfully to {filepath}")
            return True
        else:
            print(f"Failed to start recording to {filepath}.")
            # Attempt to revert to non-recording live mode
            self.is_recording = False
            self.recording_filepath = None
            if not self._initialize_live_stream(): # Try to restart without recording
                 print("Critical: Failed to re-initialize live stream after failed recording attempt.")
            return False

    def stop_recording(self):
        """
        Stops the current RealSense recording and finalizes the .bag file.
        The live stream will continue without recording.
        """
        if not self.is_recording:
            print("Not currently recording.")
            return False

        print(f"Stopping recording from: {self.recording_filepath}")
        
        if self.pipeline:
            try:
                self.pipeline.stop() # This finalizes the bag file
                print(f"Recording stopped. File saved: {self.recording_filepath}")
            except RuntimeError as e:
                print(f"Error stopping recording pipeline: {e}")
                # Continue to attempt re-initialization of live stream
            self.pipeline = None
        
        self.is_recording = False
        self.recording_filepath = None
        
        # Re-initialize live stream without recording
        print("Restarting live stream without recording...")
        if not self._initialize_live_stream():
            print("Error: Failed to re-initialize live stream after stopping recording.")
            return False
        print("Live stream restarted.")
        return True

    def stop(self):
        """
        Stop the RealSense pipeline or release video capture based on mode.
        Also stops recording if active and releases camera resources.
        """
        if self.debug_camera:
            print("🎥 [DEBUG] Stopping FrameAcquisition...")
        
        try:
            if self.is_recording:
                if self.debug_camera:
                    print("🎥 [DEBUG] Recording was active, stopping recording as part of general stop.")
                # For a general stop, we just want to stop the pipeline.
                if self.pipeline:
                    try:
                        self.pipeline.stop()
                        print(f"✅ Recording stopped. File saved: {self.recording_filepath}")
                    except RuntimeError as e:
                        print(f"⚠️ Error stopping recording pipeline during general stop: {e}")
                    self.pipeline = None
                self.is_recording = False
                self.recording_filepath = None

            if self.mode == 'live':
                self._stop_live_pipeline()
            elif self.mode == 'playback':
                self._stop_video_capture()
            
            # Release camera resource lock
            self._release_camera_resources()
            
            # General cleanup of state flags
            self.is_recording = False
            self.recording_filepath = None
            
            if self.debug_camera:
                print("✅ FrameAcquisition stopped successfully")
                
        except Exception as e:
            print(f"❌ Error during FrameAcquisition stop: {e}")
    
    def _stop_live_pipeline(self):
        """Stop the RealSense live pipeline safely."""
        if self.pipeline:
            try:
                # Check if the pipeline was actually started
                active_profile = self.pipeline.get_active_profile()
                if active_profile:
                    self.pipeline.stop()
                    if self.debug_camera:
                        print("🎥 [DEBUG] RealSense pipeline stopped.")
                    else:
                        print("✅ RealSense pipeline stopped.")
            except RuntimeError as e:
                # This error is common if initialize() failed or pipeline wasn't started
                if self.debug_camera:
                    print(f"🎥 [DEBUG] Info: Error stopping live pipeline (may not have been started): {e}")
            finally:
                self.pipeline = None
        else:
            if self.debug_camera:
                print("🎥 [DEBUG] Live pipeline was None, nothing to stop.")
    
    def _stop_video_capture(self):
        """Stop video capture safely."""
        if self.video_capture:
            if self.video_capture.isOpened():
                self.video_capture.release()
                print("✅ Video capture released.")
            self.video_capture = None
        else:
            if self.debug_camera:
                print("🎥 [DEBUG] Video capture was None, nothing to stop.")
    
    def _release_camera_resources(self):
        """Release camera resource lock and cleanup."""
        if self.camera_resource_manager and self.resource_lock_acquired:
            try:
                self.camera_resource_manager.release_camera_lock()
                self.resource_lock_acquired = False
                if self.debug_camera:
                    print("🎥 [DEBUG] Camera resource lock released")
            except Exception as e:
                print(f"⚠️ Error releasing camera resource lock: {e}")
    
    def _cleanup_on_exit(self):
        """Cleanup method called on application exit."""
        if self.debug_camera:
            print("🎥 [DEBUG] FrameAcquisition cleanup on exit")
        
        try:
            self.stop()
        except Exception as e:
            print(f"⚠️ Error during exit cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self._cleanup_on_exit()
        except:
            pass  # Ignore errors during destruction