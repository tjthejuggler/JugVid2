import numpy as np
import cv2

class SkeletonDetector:
    """
    Fallback SkeletonDetector that doesn't require MediaPipe.
    
    This is a simplified version that provides the same interface
    but doesn't actually detect skeletons. It's used when MediaPipe
    is not available (e.g., Python 3.13).
    """
    
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """
        Initialize the fallback SkeletonDetector module.
        
        Args:
            min_detection_confidence (float): Minimum confidence value (ignored in fallback)
            min_tracking_confidence (float): Minimum confidence value (ignored in fallback)
        """
        print("Warning: Using fallback SkeletonDetector - hand tracking disabled")
        
    def detect_skeleton(self, color_image):
        """
        Fallback skeleton detection - always returns None.
        
        Args:
            color_image: Color image in BGR format
            
        Returns:
            None: No skeleton detection in fallback mode
        """
        return None
    
    def get_hand_positions(self, pose_landmarks, image_shape):
        """
        Fallback hand position extraction - always returns None.
        
        Args:
            pose_landmarks: Pose landmarks (ignored in fallback)
            image_shape: Shape of the image (ignored in fallback)
            
        Returns:
            tuple: (None, None) - no hands detected in fallback mode
        """
        return None, None
    
    def create_hand_mask(self, hand_positions, image_shape, hand_radius=30):
        """
        Create an empty hand mask since no hands are detected.
        
        Args:
            hand_positions: Tuple of hand positions (ignored)
            image_shape: Shape of the image (height, width, channels)
            hand_radius: Radius of the hand mask (ignored)
            
        Returns:
            numpy.ndarray: Empty mask (all zeros)
        """
        # Return an empty mask
        return np.zeros((image_shape[0], image_shape[1]), dtype=np.uint8)
    
    def draw_skeleton(self, color_image, pose_landmarks):
        """
        Fallback skeleton drawing - returns original image.
        
        Args:
            color_image: Color image in BGR format
            pose_landmarks: Pose landmarks (ignored)
            
        Returns:
            numpy.ndarray: Original color image unchanged
        """
        return color_image
    
    def draw_hands(self, color_image, hand_positions, left_color=(0, 0, 255), right_color=(0, 255, 0), radius=10):
        """
        Fallback hand drawing - returns original image.
        
        Args:
            color_image: Color image in BGR format
            hand_positions: Tuple of hand positions (ignored)
            left_color: Color for the left hand (ignored)
            right_color: Color for the right hand (ignored)
            radius: Radius of the circles (ignored)
            
        Returns:
            numpy.ndarray: Original color image unchanged
        """
        return color_image