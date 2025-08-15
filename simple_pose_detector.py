#!/usr/bin/env python3
"""
Simple Pose Detector

A basic pose detection system using OpenCV that can detect arm positions
for the face balance timer when MediaPipe is not available.
"""

import cv2
import numpy as np

class SimplePoseDetector:
    """
    Simple pose detector using OpenCV background subtraction and contour analysis.
    
    This detector looks for significant motion/changes in specific regions of the frame
    to determine if arms are down (at sides) or up (above head).
    """
    
    def __init__(self):
        """Initialize the simple pose detector."""
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=False)
        self.frame_count = 0
        self.calibration_frames = 30  # Frames to learn background
        self.is_calibrated = False
        
        # Motion detection parameters
        self.motion_threshold = 1000  # Minimum area for significant motion
        self.arms_down_region_ratio = 0.6  # Bottom 60% of frame for "arms down"
        self.arms_up_region_ratio = 0.3    # Top 30% of frame for "arms up"
        
    def detect_pose(self, frame):
        """
        Detect pose from frame using motion analysis.
        
        Args:
            frame: OpenCV frame (BGR)
            
        Returns:
            dict: Pose information with 'arms_down' and 'arms_up' boolean flags
        """
        self.frame_count += 1
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(gray)
        
        # Skip detection during calibration
        if self.frame_count < self.calibration_frames:
            return {'arms_down': False, 'arms_up': False, 'calibrating': True}
        
        if not self.is_calibrated:
            self.is_calibrated = True
            print("Simple pose detector calibrated!")
        
        # Define regions of interest
        height, width = frame.shape[:2]
        
        # Arms down region (bottom portion, sides)
        arms_down_y_start = int(height * self.arms_down_region_ratio)
        arms_down_region = fg_mask[arms_down_y_start:height, :]
        
        # Arms up region (top portion, center-ish)
        arms_up_y_end = int(height * self.arms_up_region_ratio)
        center_x_start = int(width * 0.2)
        center_x_end = int(width * 0.8)
        arms_up_region = fg_mask[0:arms_up_y_end, center_x_start:center_x_end]
        
        # Find contours in each region
        arms_down_contours, _ = cv2.findContours(arms_down_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        arms_up_contours, _ = cv2.findContours(arms_up_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate total motion area in each region
        arms_down_motion = sum(cv2.contourArea(c) for c in arms_down_contours)
        arms_up_motion = sum(cv2.contourArea(c) for c in arms_up_contours)
        
        # Determine pose based on motion
        arms_down = arms_down_motion > self.motion_threshold
        arms_up = arms_up_motion > self.motion_threshold
        
        return {
            'arms_down': arms_down,
            'arms_up': arms_up,
            'calibrating': False,
            'arms_down_motion': arms_down_motion,
            'arms_up_motion': arms_up_motion
        }
    
    def draw_debug_info(self, frame, pose_info):
        """
        Draw debug information on the frame.
        
        Args:
            frame: OpenCV frame to draw on
            pose_info: Pose information from detect_pose()
            
        Returns:
            frame: Frame with debug info drawn
        """
        height, width = frame.shape[:2]
        
        # Draw region boundaries
        arms_down_y = int(height * self.arms_down_region_ratio)
        arms_up_y = int(height * self.arms_up_region_ratio)
        center_x_start = int(width * 0.2)
        center_x_end = int(width * 0.8)
        
        # Arms down region (green)
        cv2.line(frame, (0, arms_down_y), (width, arms_down_y), (0, 255, 0), 2)
        cv2.putText(frame, "Arms Down Region", (10, arms_down_y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Arms up region (blue)
        cv2.line(frame, (center_x_start, arms_up_y), (center_x_end, arms_up_y), (255, 0, 0), 2)
        cv2.line(frame, (center_x_start, 0), (center_x_start, arms_up_y), (255, 0, 0), 2)
        cv2.line(frame, (center_x_end, 0), (center_x_end, arms_up_y), (255, 0, 0), 2)
        cv2.putText(frame, "Arms Up Region", (center_x_start, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # Status indicators
        if pose_info.get('calibrating', False):
            cv2.putText(frame, "CALIBRATING...", (width//2 - 80, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        else:
            # Arms down indicator
            if pose_info.get('arms_down', False):
                cv2.putText(frame, "ARMS DOWN", (10, height - 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Arms up indicator
            if pose_info.get('arms_up', False):
                cv2.putText(frame, "ARMS UP", (10, height - 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Motion values
        if 'arms_down_motion' in pose_info:
            cv2.putText(frame, f"Down Motion: {pose_info['arms_down_motion']:.0f}", 
                       (width - 200, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if 'arms_up_motion' in pose_info:
            cv2.putText(frame, f"Up Motion: {pose_info['arms_up_motion']:.0f}", 
                       (width - 200, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

def main():
    """Test the simple pose detector."""
    detector = SimplePoseDetector()
    cap = cv2.VideoCapture(0)
    
    print("Simple Pose Detector Test")
    print("Move your arms to test detection")
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
        cv2.imshow('Simple Pose Detector Test', debug_frame)
        
        # Print status
        if not pose_info.get('calibrating', False):
            status = []
            if pose_info.get('arms_down', False):
                status.append("ARMS_DOWN")
            if pose_info.get('arms_up', False):
                status.append("ARMS_UP")
            if status:
                print(f"Detected: {', '.join(status)}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()