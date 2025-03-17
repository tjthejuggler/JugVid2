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
    
    def __init__(self, width=640, height=480, fps=30):
        """
        Initialize the FrameAcquisition module.
        
        Args:
            width (int): Width of the camera frames
            height (int): Height of the camera frames
            fps (int): Frames per second
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.pipeline = None
        self.align = None
        self.intrinsics = None
        self.depth_scale = None
        
    def initialize(self):
        """
        Initialize the RealSense pipeline and configure the streams.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Create a pipeline
            self.pipeline = rs.pipeline()
            
            # Create a config and enable the depth and color streams
            config = rs.config()
            config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            
            # Start streaming
            profile = self.pipeline.start(config)
            
            # Get the depth sensor's depth scale
            depth_sensor = profile.get_device().first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()
            print(f"Depth Scale is: {self.depth_scale:.3f} meters")
            
            # Align depth frame to color frame
            self.align = rs.align(rs.stream.color)
            
            # Get camera intrinsics for 3D deprojection
            color_profile = profile.get_stream(rs.stream.color)
            self.intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
            
            return True
        except Exception as e:
            print(f"Error initializing RealSense camera: {e}")
            return False
    
    def get_frames(self):
        """
        Get aligned depth and color frames from the RealSense camera.
        
        Returns:
            tuple: (depth_frame, color_frame, depth_image, color_image) or (None, None, None, None) if frames could not be captured
        """
        if self.pipeline is None:
            print("Pipeline not initialized. Call initialize() first.")
            return None, None, None, None
        
        try:
            # Wait for a coherent pair of frames: depth and color
            frames = self.pipeline.wait_for_frames()
            aligned_frames = self.align.process(frames)
            
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return None, None, None, None
            
            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            return depth_frame, color_frame, depth_image, color_image
        except Exception as e:
            print(f"Error getting frames: {e}")
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
    
    def stop(self):
        """
        Stop the RealSense pipeline.
        """
        if self.pipeline:
            self.pipeline.stop()
            self.pipeline = None
            self.align = None
            self.intrinsics = None
            self.depth_scale = None