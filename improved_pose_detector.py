#!/usr/bin/env python3
"""
Improved Pose Detector

A robust pose detection system using OpenCV that can reliably detect arm positions
for the face balance timer without requiring MediaPipe.
"""

import cv2
import numpy as np
from collections import deque

class ImprovedPoseDetector:
    """
    Improved pose detector using OpenCV with multiple detection methods.
    
    This detector combines:
    1. Background subtraction for motion detection
    2. Contour analysis for body part identification
    3. Temporal smoothing to reduce false positives
    4. Region-based analysis for arm position detection
    """
    
    def __init__(self):
        """Initialize the improved pose detector."""
        # Background subtraction
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False, 
            varThreshold=50,
            history=500
        )
        
        # Calibration
        self.frame_count = 0
        self.calibration_frames = 60  # More frames for better background learning
        self.is_calibrated = False
        
        # Detection parameters
        self.min_contour_area = 500
        self.max_contour_area = 50000
        
        # Region definitions (as ratios of frame dimensions)
        self.regions = {
            'head': {'y_start': 0.0, 'y_end': 0.25, 'x_start': 0.3, 'x_end': 0.7},
            'torso': {'y_start': 0.25, 'y_end': 0.65, 'x_start': 0.25, 'x_end': 0.75},
            'arms_up': {'y_start': 0.0, 'y_end': 0.4, 'x_start': 0.1, 'x_end': 0.9},
            'arms_down': {'y_start': 0.4, 'y_end': 1.0, 'x_start': 0.0, 'x_end': 1.0},
            'left_side': {'y_start': 0.3, 'y_end': 0.8, 'x_start': 0.0, 'x_end': 0.3},
            'right_side': {'y_start': 0.3, 'y_end': 0.8, 'x_start': 0.7, 'x_end': 1.0}
        }
        
        # Temporal smoothing
        self.history_length = 10
        self.arms_down_history = deque(maxlen=self.history_length)
        self.arms_up_history = deque(maxlen=self.history_length)
        
        # Thresholds
        self.motion_threshold = 800
        self.confidence_threshold = 0.6  # 60% of recent frames must agree
        
    def get_region_mask(self, frame_shape, region_name):
        """
        Get a mask for a specific region of the frame.
        
        Args:
            frame_shape: Shape of the frame (height, width)
            region_name: Name of the region
            
        Returns:
            numpy.ndarray: Binary mask for the region
        """
        height, width = frame_shape[:2]
        region = self.regions[region_name]
        
        mask = np.zeros((height, width), dtype=np.uint8)
        
        y_start = int(height * region['y_start'])
        y_end = int(height * region['y_end'])
        x_start = int(width * region['x_start'])
        x_end = int(width * region['x_end'])
        
        mask[y_start:y_end, x_start:x_end] = 255
        
        return mask
    
    def analyze_motion_in_region(self, fg_mask, region_mask):
        """
        Analyze motion within a specific region.
        
        Args:
            fg_mask: Foreground mask from background subtraction
            region_mask: Mask defining the region of interest
            
        Returns:
            dict: Motion analysis results
        """
        # Apply region mask to foreground
        region_motion = cv2.bitwise_and(fg_mask, region_mask)
        
        # Find contours
        contours, _ = cv2.findContours(region_motion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size
        valid_contours = [c for c in contours 
                         if self.min_contour_area < cv2.contourArea(c) < self.max_contour_area]
        
        # Calculate metrics
        total_area = sum(cv2.contourArea(c) for c in valid_contours)
        contour_count = len(valid_contours)
        
        return {
            'total_area': total_area,
            'contour_count': contour_count,
            'contours': valid_contours,
            'has_significant_motion': total_area > self.motion_threshold
        }
    
    def detect_pose(self, frame):
        """
        Detect pose from frame using improved analysis.
        
        Args:
            frame: OpenCV frame (BGR)
            
        Returns:
            dict: Pose information with confidence scores
        """
        self.frame_count += 1
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(gray)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Skip detection during calibration
        if self.frame_count < self.calibration_frames:
            return {
                'arms_down': False, 
                'arms_up': False, 
                'calibrating': True,
                'confidence': 0.0
            }
        
        if not self.is_calibrated:
            self.is_calibrated = True
            print("Improved pose detector calibrated!")
        
        # Analyze motion in different regions
        frame_shape = frame.shape
        
        # Get region masks
        arms_up_mask = self.get_region_mask(frame_shape, 'arms_up')
        arms_down_mask = self.get_region_mask(frame_shape, 'arms_down')
        left_side_mask = self.get_region_mask(frame_shape, 'left_side')
        right_side_mask = self.get_region_mask(frame_shape, 'right_side')
        torso_mask = self.get_region_mask(frame_shape, 'torso')
        
        # Analyze motion in each region
        arms_up_motion = self.analyze_motion_in_region(fg_mask, arms_up_mask)
        arms_down_motion = self.analyze_motion_in_region(fg_mask, arms_down_mask)
        left_side_motion = self.analyze_motion_in_region(fg_mask, left_side_mask)
        right_side_motion = self.analyze_motion_in_region(fg_mask, right_side_mask)
        torso_motion = self.analyze_motion_in_region(fg_mask, torso_mask)
        
        # Determine arm positions based on motion analysis
        # Arms are considered "down" if there's significant motion in the lower regions
        # and minimal motion in the upper regions
        arms_down_score = 0.0
        arms_up_score = 0.0
        
        # Arms down indicators
        if arms_down_motion['has_significant_motion']:
            arms_down_score += 0.4
        if left_side_motion['has_significant_motion'] or right_side_motion['has_significant_motion']:
            arms_down_score += 0.3
        if torso_motion['has_significant_motion']:
            arms_down_score += 0.2
        if not arms_up_motion['has_significant_motion']:
            arms_down_score += 0.1
            
        # Arms up indicators
        if arms_up_motion['has_significant_motion']:
            arms_up_score += 0.5
        if torso_motion['has_significant_motion']:
            arms_up_score += 0.2
        if not (left_side_motion['has_significant_motion'] and right_side_motion['has_significant_motion']):
            arms_up_score += 0.3
        
        # Convert scores to boolean decisions
        arms_down_detected = arms_down_score > 0.5
        arms_up_detected = arms_up_score > 0.5
        
        # Add to history for temporal smoothing
        self.arms_down_history.append(arms_down_detected)
        self.arms_up_history.append(arms_up_detected)
        
        # Calculate confidence based on recent history
        arms_down_confidence = sum(self.arms_down_history) / len(self.arms_down_history)
        arms_up_confidence = sum(self.arms_up_history) / len(self.arms_up_history)
        
        # Final decisions based on confidence threshold
        arms_down_final = arms_down_confidence >= self.confidence_threshold
        arms_up_final = arms_up_confidence >= self.confidence_threshold
        
        return {
            'arms_down': arms_down_final,
            'arms_up': arms_up_final,
            'calibrating': False,
            'arms_down_confidence': arms_down_confidence,
            'arms_up_confidence': arms_up_confidence,
            'arms_down_score': arms_down_score,
            'arms_up_score': arms_up_score,
            'motion_data': {
                'arms_up': arms_up_motion,
                'arms_down': arms_down_motion,
                'left_side': left_side_motion,
                'right_side': right_side_motion,
                'torso': torso_motion
            }
        }
    
    def draw_debug_info(self, frame, pose_info):
        """
        Draw comprehensive debug information on the frame.
        
        Args:
            frame: OpenCV frame to draw on
            pose_info: Pose information from detect_pose()
            
        Returns:
            frame: Frame with debug info drawn
        """
        height, width = frame.shape[:2]
        
        # Draw region boundaries
        for region_name, region in self.regions.items():
            y_start = int(height * region['y_start'])
            y_end = int(height * region['y_end'])
            x_start = int(width * region['x_start'])
            x_end = int(width * region['x_end'])
            
            # Choose color based on region
            if region_name == 'arms_up':
                color = (255, 0, 0)  # Blue
            elif region_name == 'arms_down':
                color = (0, 255, 0)  # Green
            elif region_name in ['left_side', 'right_side']:
                color = (0, 255, 255)  # Yellow
            else:
                color = (128, 128, 128)  # Gray
            
            # Draw rectangle
            cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), color, 1)
            
            # Label
            cv2.putText(frame, region_name, (x_start + 5, y_start + 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Status indicators
        if pose_info.get('calibrating', False):
            cv2.putText(frame, "CALIBRATING...", (width//2 - 80, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        else:
            # Arms down indicator
            if pose_info.get('arms_down', False):
                cv2.putText(frame, "ARMS DOWN", (10, height - 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Arms up indicator
            if pose_info.get('arms_up', False):
                cv2.putText(frame, "ARMS UP", (10, height - 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Confidence scores
            arms_down_conf = pose_info.get('arms_down_confidence', 0)
            arms_up_conf = pose_info.get('arms_up_confidence', 0)
            
            cv2.putText(frame, f"Down Conf: {arms_down_conf:.2f}", 
                       (10, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"Up Conf: {arms_up_conf:.2f}", 
                       (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Scores
            arms_down_score = pose_info.get('arms_down_score', 0)
            arms_up_score = pose_info.get('arms_up_score', 0)
            
            cv2.putText(frame, f"Down Score: {arms_down_score:.2f}", 
                       (width - 200, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"Up Score: {arms_up_score:.2f}", 
                       (width - 200, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

def main():
    """Test the improved pose detector."""
    detector = ImprovedPoseDetector()
    cap = cv2.VideoCapture(0)
    
    print("Improved Pose Detector Test")
    print("Move your arms to test detection")
    print("- Put arms down at sides to trigger 'arms down'")
    print("- Raise arms above head to trigger 'arms up'")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Detect pose
        pose_info = detector.detect_pose(frame)
        
        # Draw debug info
        debug_frame = detector.draw_debug_info(frame, pose_info)
        
        # Show frame
        cv2.imshow('Improved Pose Detector Test', debug_frame)
        
        # Print status
        if not pose_info.get('calibrating', False):
            status = []
            if pose_info.get('arms_down', False):
                status.append(f"ARMS_DOWN (conf: {pose_info.get('arms_down_confidence', 0):.2f})")
            if pose_info.get('arms_up', False):
                status.append(f"ARMS_UP (conf: {pose_info.get('arms_up_confidence', 0):.2f})")
            if status:
                print(f"Detected: {', '.join(status)}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()