import pyrealsense2 as rs
import numpy as np
import cv2

class FrameAcquisition:
    """
    Handles the RealSense camera setup and frame capture.
    
    This module is responsible for:
    - Setting up the RealSense pipeline
    - Configuring the depth and color streams
    - Aligning the depth and color frames
    - Providing access to camera intrinsics for 3D calculations
    """
    
    def __init__(self, width=640, height=480, fps=30, mode='live', video_path=None, depth_only=False):
        """
        Initialize the FrameAcquisition module.
        
        Args:
            width (int): Width of the camera frames or desired output width for video.
            height (int): Height of the camera frames or desired output height for video.
            fps (int): Frames per second for camera configuration.
            mode (str): 'live' for RealSense camera, 'playback' for video file.
            video_path (str, optional): Path to the video file if mode is 'playback'.
            depth_only (bool): If True, only enable depth stream (for cable compatibility).
        """
        self.width = width
        self.height = height
        self.fps = fps  # Target FPS for camera, video FPS is intrinsic to file
        self.mode = mode
        self.video_path = video_path
        self.depth_only = depth_only
        
        self.pipeline = None
        self.align = None
        self.intrinsics = None
        self.depth_scale = None
        self.video_capture = None
        self.video_frame_count = 0
        self.video_fps = 0
        self.is_recording = False
        self.recording_filepath = None
        
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
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if self.mode == 'live':
            return self._initialize_live_stream()
        elif self.mode == 'playback':
            if not self.video_path:
                print("Error: Video path not provided for playback mode.")
                return False
            try:
                self.video_capture = cv2.VideoCapture(self.video_path)
                if not self.video_capture.isOpened():
                    print(f"Error: Could not open video file: {self.video_path}")
                    self.video_capture = None
                    return False
                
                # Get video properties
                self.video_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                self.video_frame_count = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                native_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                native_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Playback Mode: Video '{self.video_path}' opened.")
                print(f"Native resolution: {native_width}x{native_height}, FPS: {self.video_fps:.2f}")
                print(f"Outputting at: {self.width}x{self.height}")

                # In playback mode, RealSense specific attributes are not available from generic video
                self.intrinsics = None
                self.depth_scale = None
                self.align = None
                return True
            except Exception as e:
                print(f"Error initializing video playback: {e}")
                return False
        else:
            print(f"Error: Unknown mode '{self.mode}'")
            return False
    
    def get_frames(self):
        """
        Get frames based on the current mode (live camera or video playback).
        
        Returns:
            tuple: (depth_frame, color_frame, depth_image, color_image) or (None, None, None, None)
                   In playback mode, depth_frame, color_frame (rs object), and depth_image will be None.
        """
        if self.mode == 'live':
            if self.pipeline is None:
                print("Live pipeline not initialized. Call initialize() first.")
                return None, None, None, None
            
            try:
                # print("[DEBUG Roo FA] get_frames (live): Attempting to wait_for_frames().") # Roo log - too noisy for every frame
                frames = self.pipeline.wait_for_frames(5000) # Keep timeout explicit
                # print("[DEBUG Roo FA] get_frames (live): wait_for_frames() returned.") # Roo log
                
                if self.depth_only:
                    # Depth-only mode: no alignment needed, no color frame
                    depth_frame = frames.get_depth_frame()
                    if not depth_frame:
                        print("[DEBUG Roo FA] get_frames (live): Depth frame is None in depth-only mode.") # Roo log
                        return None, None, None, None
                    
                    depth_image = np.asanyarray(depth_frame.get_data())
                    # Create a grayscale "color" image from depth for visualization
                    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
                    
                    return depth_frame, None, depth_image, depth_colormap
                else:
                    # Normal mode: both depth and color with alignment
                    aligned_frames = self.align.process(frames)
                    # print("[DEBUG Roo FA] get_frames (live): Frames aligned.") # Roo log
                    
                    depth_frame = aligned_frames.get_depth_frame()
                    color_frame = aligned_frames.get_color_frame()
                    
                    if not depth_frame or not color_frame:
                        print("[DEBUG Roo FA] get_frames (live): Depth or Color frame is None after alignment.") # Roo log
                        return None, None, None, None
                    
                    depth_image = np.asanyarray(depth_frame.get_data())
                    color_image = np.asanyarray(color_frame.get_data())
                    # print("[DEBUG Roo FA] get_frames (live): Frame data converted to numpy arrays.") # Roo log
                    
                    return depth_frame, color_frame, depth_image, color_image
            except RuntimeError as e: # Catch specific RealSense errors
                print(f"[DEBUG Roo FA] get_frames (live): RuntimeError: {e}") # Roo log
                print(f"Error getting live frames: {e}")
                return None, None, None, None
            except Exception as e: # Catch any other errors
                print(f"[DEBUG Roo FA] get_frames (live): Unexpected Exception: {e}") # Roo log
                print(f"Error getting live frames: {e}")
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
        Also stops recording if active.
        """
        if self.is_recording:
            print("Recording was active, stopping recording as part of general stop.")
            # self.stop_recording() will call pipeline.stop() and then try to restart live.
            # For a general stop, we just want to stop the pipeline.
            if self.pipeline:
                try:
                    self.pipeline.stop()
                    print(f"Recording stopped. File saved: {self.recording_filepath}")
                except RuntimeError as e:
                    print(f"Error stopping recording pipeline during general stop: {e}")
                self.pipeline = None
            self.is_recording = False
            self.recording_filepath = None
            # After stopping a recording pipeline, it's fully stopped. No need to re-init here.

        if self.mode == 'live':
            if self.pipeline: # Check if pipeline object exists
                try:
                    # Check if the pipeline was actually started.
                    # Calling stop() on a pipeline that was never started can raise an error.
                    # A simple way to check is if a profile exists (pipeline.start() returns a profile)
                    # However, checking internal state of pipeline_profile is tricky.
                    # For now, rely on the try-except, but note that a pipeline object can exist
                    # without having been successfully started.
                    active_profile = self.pipeline.get_active_profile() # This will error if not started
                    if active_profile: # Check if a profile is active
                         self.pipeline.stop()
                         print("RealSense pipeline stopped.")
                except RuntimeError as e:
                    # This error ("stop() cannot be called before start()") is common if initialize() failed.
                    print(f"Info: Error stopping live pipeline (may not have been started or already stopped): {e}")
                finally: # Ensure pipeline is reset regardless of stop success/failure
                    self.pipeline = None
            else:
                print("Info: Live pipeline was None, nothing to stop.")
            # self.align = None # These are re-acquired on init
        elif self.mode == 'playback':
            if self.video_capture: # Check if video_capture object exists
                if self.video_capture.isOpened():
                    self.video_capture.release()
                    print("Video capture released.")
                self.video_capture = None # Ensure reset
            else:
                print("Info: Video capture was None, nothing to stop.")
        
        # General cleanup of state flags related to active streaming/recording
        self.is_recording = False
        # self.recording_filepath = None # Keep last path for potential UI display? Or clear? Let's clear.
        self.recording_filepath = None

        # self.intrinsics = None # Keep these as they might be from a valid previous session
        # self.depth_scale = None
        # self.align = None