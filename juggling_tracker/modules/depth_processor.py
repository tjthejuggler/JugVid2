import numpy as np
import cv2

class DepthProcessor:
    """
    Handles the processing of depth data from the RealSense camera.
    
    This module is responsible for:
    - Converting raw depth data to meters
    - Creating proximity masks to identify the closest objects
    - Applying morphological operations to clean up the masks
    """
    
    def __init__(self, min_depth=0.3, max_depth=3.0, proximity_delta=0.15):
        """
        Initialize the DepthProcessor module.
        
        Args:
            min_depth (float): Minimum depth in meters to consider (objects closer than this will be ignored)
            max_depth (float): Maximum depth in meters to consider (objects farther than this will be ignored)
            proximity_delta (float): Margin in meters to include objects near the closest one
        """
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.proximity_delta = proximity_delta
        
    def process_depth_frame(self, depth_frame, depth_image, depth_scale):
        """
        Process a depth frame to convert it to meters.
        
        Args:
            depth_frame: RealSense depth frame
            depth_image: Numpy array containing the depth image
            depth_scale: Depth scale in meters
            
        Returns:
            numpy.ndarray: Depth image in meters
        """
        # Convert depth from raw units to meters
        depth_in_meters = depth_image * depth_scale
        
        # Apply depth limits
        depth_in_meters[depth_in_meters < self.min_depth] = 0
        depth_in_meters[depth_in_meters > self.max_depth] = 0
        
        return depth_in_meters
    
    def create_proximity_mask(self, depth_in_meters, delta=None):
        """
        Create a proximity mask based on the closest objects.
        
        Args:
            depth_in_meters: Depth image in meters
            delta: Optional override for proximity_delta
            
        Returns:
            numpy.ndarray: Binary mask where the closest objects are white (255)
        """
        if delta is None:
            delta = self.proximity_delta
            
        # Find the minimum non-zero depth (ignore zero values)
        valid_depths = depth_in_meters[depth_in_meters > 0]
        if valid_depths.size == 0:
            # No valid depths found, return an empty mask
            return np.zeros_like(depth_in_meters, dtype=np.uint8)
            
        min_depth_val = np.min(valid_depths)
        
        # Create a mask for objects within a certain range of the minimum depth
        proximity_mask = cv2.inRange(depth_in_meters, min_depth_val, min_depth_val + delta)
        
        return proximity_mask
    
    def cleanup_mask(self, mask, open_kernel_size=5, close_kernel_size=5):
        """
        Clean up a mask with morphological operations.
        
        Args:
            mask: Binary mask to clean up
            open_kernel_size: Size of the kernel for the opening operation
            close_kernel_size: Size of the kernel for the closing operation
            
        Returns:
            numpy.ndarray: Cleaned up binary mask
        """
        # Create kernels for morphological operations
        open_kernel = np.ones((open_kernel_size, open_kernel_size), np.uint8)
        close_kernel = np.ones((close_kernel_size, close_kernel_size), np.uint8)
        
        # Apply opening to remove small noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
        
        # Apply closing to fill small holes
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
        
        return mask
    
    def get_depth_at_point(self, depth_frame, x, y, window_size=5):
        """
        Get the average depth at a specific point with a small window.
        
        Args:
            depth_frame: RealSense depth frame
            x: X coordinate
            y: Y coordinate
            window_size: Size of the window to average over
            
        Returns:
            float: Average depth in meters
        """
        half_size = window_size // 2
        depths = []
        
        for dy in range(-half_size, half_size + 1):
            for dx in range(-half_size, half_size + 1):
                px, py = x + dx, y + dy
                # Check if the pixel is within the frame
                if 0 <= px < depth_frame.get_width() and 0 <= py < depth_frame.get_height():
                    depth = depth_frame.get_distance(px, py)
                    if depth > 0:  # Ignore invalid depth values
                        depths.append(depth)
        
        if not depths:
            return 0.0
            
        return np.mean(depths)