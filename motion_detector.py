import cv2
import numpy as np
from collections import deque
import time

class MotionDetector:
    """
    Detects motion in video frames using background subtraction and frame differencing.
    
    This module provides:
    - Motion detection using background subtraction
    - Configurable motion threshold
    - Stillness detection (when motion falls below threshold for specified duration)
    """
    
    def __init__(self, motion_threshold=1000, stillness_duration=3.0, history_length=500):
        """
        Initialize the motion detector.
        
        Args:
            motion_threshold (float): Minimum motion value to consider as "motion"
            stillness_duration (float): Duration in seconds of low motion to trigger stillness
            history_length (int): Number of frames to keep in background subtractor history
        """
        self.motion_threshold = motion_threshold
        self.stillness_duration = stillness_duration
        self.history_length = history_length
        
        # Background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history_length,
            varThreshold=50,
            detectShadows=True
        )
        
        # Motion history tracking
        self.motion_history = deque(maxlen=100)  # Keep last 100 motion values
        self.stillness_start_time = None
        self.is_still = False
        
        # Previous frame for frame differencing (backup method)
        self.prev_frame = None
        
    def detect_motion(self, frame):
        """
        Detect motion in the current frame.
        
        Args:
            frame (numpy.ndarray): Current video frame (BGR format)
            
        Returns:
            tuple: (motion_value, is_motion_detected, motion_mask)
        """
        if frame is None:
            return 0.0, False, None
            
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Method 1: Background subtraction (primary method)
        fg_mask = self.bg_subtractor.apply(blurred)
        
        # Remove shadows (they are marked as 127 in MOG2)
        fg_mask[fg_mask == 127] = 0
        
        # Apply morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Calculate motion value as the number of non-zero pixels
        motion_value = cv2.countNonZero(fg_mask)
        
        # Method 2: Frame differencing (backup/validation method)
        if self.prev_frame is not None:
            frame_diff = cv2.absdiff(self.prev_frame, blurred)
            _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
            
            # Apply morphological operations
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            diff_motion_value = cv2.countNonZero(thresh)
            
            # Use the maximum of both methods for more robust detection
            motion_value = max(motion_value, diff_motion_value * 0.5)  # Weight frame diff less
        
        self.prev_frame = blurred.copy()
        
        # Add to motion history
        self.motion_history.append(motion_value)
        
        # Determine if motion is detected
        is_motion_detected = motion_value > self.motion_threshold
        
        return motion_value, is_motion_detected, fg_mask
    
    def check_stillness(self, motion_value):
        """
        Check if the scene has been still for the specified duration.
        
        Args:
            motion_value (float): Current motion value
            
        Returns:
            bool: True if stillness condition is met (triggers recording)
        """
        current_time = time.time()
        
        # Check if current motion is below threshold
        if motion_value <= self.motion_threshold:
            # Start tracking stillness if not already tracking
            if self.stillness_start_time is None:
                self.stillness_start_time = current_time
            
            # Check if we've been still long enough
            stillness_duration = current_time - self.stillness_start_time
            if stillness_duration >= self.stillness_duration and not self.is_still:
                self.is_still = True
                return True  # Trigger recording
                
        else:
            # Motion detected, reset stillness tracking
            self.stillness_start_time = None
            self.is_still = False
            
        return False
    
    def get_motion_stats(self):
        """
        Get current motion statistics.
        
        Returns:
            dict: Motion statistics including current value, average, and stillness info
        """
        if not self.motion_history:
            return {
                'current_motion': 0.0,
                'avg_motion': 0.0,
                'is_still': False,
                'stillness_duration': 0.0,
                'motion_threshold': self.motion_threshold
            }
        
        current_time = time.time()
        stillness_duration = 0.0
        
        if self.stillness_start_time is not None:
            stillness_duration = current_time - self.stillness_start_time
        
        return {
            'current_motion': self.motion_history[-1] if self.motion_history else 0.0,
            'avg_motion': np.mean(self.motion_history),
            'is_still': self.is_still,
            'stillness_duration': stillness_duration,
            'motion_threshold': self.motion_threshold
        }
    
    def reset_stillness(self):
        """Reset the stillness detection state."""
        self.stillness_start_time = None
        self.is_still = False
    
    def update_threshold(self, new_threshold):
        """
        Update the motion threshold.
        
        Args:
            new_threshold (float): New motion threshold value
        """
        self.motion_threshold = new_threshold
        # Reset stillness state when threshold changes
        self.reset_stillness()
    
    def update_stillness_duration(self, new_duration):
        """
        Update the stillness duration requirement.
        
        Args:
            new_duration (float): New stillness duration in seconds
        """
        self.stillness_duration = new_duration
        # Reset stillness state when duration changes
        self.reset_stillness()

def test_motion_detector():
    """Test the motion detector with webcam or RealSense camera."""
    import sys
    
    # Try to use RealSense first, fallback to webcam
    try:
        from color_only_frame_acquisition import ColorOnlyFrameAcquisition
        print("Using RealSense camera...")
        camera = ColorOnlyFrameAcquisition(width=640, height=480, fps=30)
        if not camera.initialize():
            raise Exception("Failed to initialize RealSense")
        use_realsense = True
    except Exception as e:
        print(f"RealSense not available ({e}), using webcam...")
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Error: Could not open webcam")
            return
        use_realsense = False
    
    # Initialize motion detector
    detector = MotionDetector(motion_threshold=1000, stillness_duration=2.0)
    
    print("Motion Detection Test")
    print("Press 'q' to quit, 's' to adjust sensitivity")
    
    try:
        while True:
            # Get frame
            if use_realsense:
                _, _, _, frame = camera.get_frames()
            else:
                ret, frame = camera.read()
                if not ret:
                    break
                    
            if frame is None:
                continue
            
            # Detect motion
            motion_value, is_motion, motion_mask = detector.detect_motion(frame)
            stillness_triggered = detector.check_stillness(motion_value)
            
            # Get motion stats
            stats = detector.get_motion_stats()
            
            # Draw motion information on frame
            cv2.putText(frame, f"Motion: {motion_value:.0f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Threshold: {stats['motion_threshold']:.0f}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            cv2.putText(frame, f"Still: {stats['is_still']}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f"Still Duration: {stats['stillness_duration']:.1f}s", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if stillness_triggered:
                cv2.putText(frame, "RECORDING TRIGGERED!", (10, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
            
            # Show frames
            cv2.imshow('Motion Detection Test', frame)
            
            if motion_mask is not None:
                cv2.imshow('Motion Mask', motion_mask)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                print(f"Current threshold: {detector.motion_threshold}")
                try:
                    new_threshold = float(input("Enter new threshold: "))
                    detector.update_threshold(new_threshold)
                    print(f"Threshold updated to: {new_threshold}")
                except ValueError:
                    print("Invalid threshold value")
                    
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if use_realsense:
            camera.stop()
        else:
            camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test_motion_detector()