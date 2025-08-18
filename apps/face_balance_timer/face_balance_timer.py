#!/usr/bin/env python3
"""
Face Balance Timer

A simple program that uses skeletal tracking to automatically time face balancing exercises.
The timer starts when both arms go down to the sides and stops when one hand goes back over the head.

Uses RealSense camera and MediaPipe for pose detection.
"""

import cv2
import numpy as np
import time
import os
import subprocess
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from apps.juggling_tracker.modules.frame_acquisition import FrameAcquisition
from core.camera.color_only_frame_acquisition import ColorOnlyFrameAcquisition
from apps.juggling_tracker.modules.skeleton_detector import SkeletonDetector
from apps.pose_detection.simple_pose_detector import SimplePoseDetector
from apps.pose_detection.improved_pose_detector import ImprovedPoseDetector
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

class FaceBalanceTimer:
    """
    Face Balance Timer using skeletal tracking.
    
    Timer logic:
    - START: When both arms are down at sides (wrists below shoulders)
    - STOP: When either hand goes above head level (wrist above nose)
    - State machine prevents immediate restart after stopping
    """
    
    def __init__(self, width=1280, height=720, fps=30, use_webcam_fallback=True):
        """
        Initialize the Face Balance Timer.
        
        Args:
            width (int): Camera frame width (increased for larger display)
            height (int): Camera frame height (increased for larger display)
            fps (int): Camera frames per second
            use_webcam_fallback (bool): Use regular webcam if RealSense fails
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.use_webcam_fallback = use_webcam_fallback
        self.using_webcam = False
        self.webcam = None
        
        # Initialize camera and skeleton detector
        self.color_frame_acquisition = ColorOnlyFrameAcquisition(width=width, height=height, fps=fps)
        self.frame_acquisition = FrameAcquisition(width=width, height=height, fps=fps, mode='live')  # Fallback
        self.skeleton_detector = SkeletonDetector(min_detection_confidence=0.7, min_tracking_confidence=0.5)
        self.using_color_only = False
        
        # Initialize pose detectors
        self.improved_pose_detector = ImprovedPoseDetector()
        if not MEDIAPIPE_AVAILABLE:
            self.simple_pose_detector = SimplePoseDetector()
        else:
            self.simple_pose_detector = None
        
        # Use improved pose detector as primary method
        self.use_improved_detector = True
        
        # Timer state
        self.timer_running = False
        self.start_time = None
        self.current_time = 0.0
        self.best_time = 0.0
        self.session_times = []
        self.last_completed_time = 0.0
        
        # State machine for preventing immediate restart
        self.state = "WAITING"  # WAITING, READY_TO_START, TIMING, COOLDOWN
        self.cooldown_start = None
        self.cooldown_duration = 2.0  # 2 seconds cooldown after stopping
        
        # Pose detection state
        self.arms_down_frames = 0
        self.arms_down_threshold = 15  # More frames to confirm arms are down (reduce false triggers)
        self.hand_up_frames = 0
        self.hand_up_threshold = 8     # More frames to confirm hand is up
        
        # Database setup
        self.db_path = "face_balance_sessions.db"
        self.init_database()
        
        # MediaPipe pose landmarks for reference (if available)
        if MEDIAPIPE_AVAILABLE:
            self.mp_pose = mp.solutions.pose
        else:
            self.mp_pose = None
            print("MediaPipe not available. Using improved OpenCV-based pose detection.")
    
    def init_database(self):
        """Initialize SQLite database for storing session data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_start TIMESTAMP,
                    session_end TIMESTAMP,
                    total_attempts INTEGER,
                    best_time REAL,
                    average_time REAL
                )
            ''')
            
            # Create attempts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    attempt_time REAL,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def save_session_to_db(self):
        """Save current session data to database."""
        if not self.session_times:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert session record
            session_start = datetime.now() - timedelta(minutes=len(self.session_times))  # Approximate
            session_end = datetime.now()
            
            cursor.execute('''
                INSERT INTO sessions (session_start, session_end, total_attempts, best_time, average_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_start, session_end, len(self.session_times), self.best_time, np.mean(self.session_times)))
            
            session_id = cursor.lastrowid
            
            # Insert individual attempts
            for i, attempt_time in enumerate(self.session_times):
                timestamp = session_start + timedelta(minutes=i)  # Approximate timestamps
                cursor.execute('''
                    INSERT INTO attempts (session_id, attempt_time, timestamp)
                    VALUES (?, ?, ?)
                ''', (session_id, attempt_time, timestamp))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database save error: {e}")

    def initialize(self):
        """Initialize the camera and detection systems."""
        # Try RealSense COLOR ONLY first (avoids bandwidth issues)
        if self.color_frame_acquisition.initialize():
            self.using_color_only = True
            return True
        # Try regular RealSense (depth+color) as fallback
        elif self.frame_acquisition.initialize():
            return True
        elif self.use_webcam_fallback:
            self.webcam = cv2.VideoCapture(0)
            if self.webcam.isOpened():
                self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.webcam.set(cv2.CAP_PROP_FPS, self.fps)
                self.using_webcam = True
                return True
            else:
                return False
        else:
            return False
    
    def play_sound(self, sound_type):
        """
        Play a sound effect using system beep or different tones.
        
        Args:
            sound_type (str): 'start' or 'stop'
        """
        try:
            if sound_type == 'start':
                # High pitch beep for start (short beep)
                os.system('(speaker-test -t sine -f 800 -l 1 & sleep 0.2 && kill $!) 2>/dev/null || echo -e "\a"')
            elif sound_type == 'stop':
                # Lower pitch beep for stop (longer, lower beep)
                os.system('(speaker-test -t sine -f 400 -l 1 & sleep 0.5 && kill $!) 2>/dev/null || echo -e "\a\a"')
        except:
            # Fallback to simple beeps
            try:
                if sound_type == 'start':
                    os.system('echo -e "\a"')  # Single beep
                elif sound_type == 'stop':
                    os.system('echo -e "\a\a"')  # Double beep
            except:
                pass  # Silent fallback
    
    def get_frames(self):
        """Get frames from camera (RealSense color-only, RealSense depth+color, or webcam)."""
        if self.using_webcam:
            ret, color_image = self.webcam.read()
            if ret:
                return None, None, None, color_image
            else:
                return None, None, None, None
        elif self.using_color_only:
            # Use color-only RealSense
            depth_frame, color_frame, depth_image, color_image = self.color_frame_acquisition.get_frames()
            
            # If color-only fails, try fallback to webcam
            if color_image is None and self.use_webcam_fallback and not self.using_webcam:
                self.webcam = cv2.VideoCapture(0)
                if self.webcam.isOpened():
                    self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.webcam.set(cv2.CAP_PROP_FPS, self.fps)
                    self.using_webcam = True
                    self.using_color_only = False
                    # Try to get a frame from webcam
                    ret, color_image = self.webcam.read()
                    if ret:
                        return None, None, None, color_image
                    
            return depth_frame, color_frame, depth_image, color_image
        else:
            # Try regular RealSense (depth+color)
            depth_frame, color_frame, depth_image, color_image = self.frame_acquisition.get_frames()
            
            # If RealSense fails and we have webcam fallback enabled, switch to webcam
            if color_image is None and self.use_webcam_fallback and not self.using_webcam:
                self.webcam = cv2.VideoCapture(0)
                if self.webcam.isOpened():
                    self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.webcam.set(cv2.CAP_PROP_FPS, self.fps)
                    self.using_webcam = True
                    # Try to get a frame from webcam
                    ret, color_image = self.webcam.read()
                    if ret:
                        return None, None, None, color_image
                    
            return depth_frame, color_frame, depth_image, color_image
    
    def are_arms_down(self, pose_landmarks, image_shape, color_image=None):
        """
        Check if both arms are down at the sides.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks (or None if using simple detector)
            image_shape: Shape of the image (height, width, channels)
            color_image: Color image for simple pose detection
            
        Returns:
            bool: True if both arms are down at sides
        """
        # Use improved pose detector as primary method
        if self.use_improved_detector and color_image is not None:
            pose_info = self.improved_pose_detector.detect_pose(color_image)
            return pose_info.get('arms_down', False) and not pose_info.get('calibrating', True)
        elif MEDIAPIPE_AVAILABLE and pose_landmarks:
            img_height, img_width = image_shape[:2]
            
            # Get relevant landmarks
            left_shoulder = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            left_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            
            # Convert to pixel coordinates
            left_shoulder_y = left_shoulder.y * img_height
            right_shoulder_y = right_shoulder.y * img_height
            left_wrist_y = left_wrist.y * img_height
            right_wrist_y = right_wrist.y * img_height
            
            # Check if both wrists are well below shoulders (arms down)
            left_arm_down = left_wrist_y > left_shoulder_y + 80  # Increased buffer to reduce false triggers
            right_arm_down = right_wrist_y > right_shoulder_y + 80
            
            return left_arm_down and right_arm_down
        elif not MEDIAPIPE_AVAILABLE and self.simple_pose_detector and color_image is not None:
            # Use simple pose detector as fallback
            pose_info = self.simple_pose_detector.detect_pose(color_image)
            return pose_info.get('arms_down', False) and not pose_info.get('calibrating', True)
        else:
            return False
    
    def is_hand_above_head(self, pose_landmarks, image_shape, color_image=None):
        """
        Check if either hand is above head level.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks (or None if using simple detector)
            image_shape: Shape of the image (height, width, channels)
            color_image: Color image for simple pose detection
            
        Returns:
            bool: True if either hand is above head level
        """
        # Use improved pose detector as primary method
        if self.use_improved_detector and color_image is not None:
            pose_info = self.improved_pose_detector.detect_pose(color_image)
            return pose_info.get('arms_up', False) and not pose_info.get('calibrating', True)
        elif MEDIAPIPE_AVAILABLE and pose_landmarks:
            img_height, img_width = image_shape[:2]
            
            # Get relevant landmarks
            nose = pose_landmarks.landmark[self.mp_pose.PoseLandmark.NOSE]
            left_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            
            # Convert to pixel coordinates
            nose_y = nose.y * img_height
            left_wrist_y = left_wrist.y * img_height
            right_wrist_y = right_wrist.y * img_height
            
            # Check if either wrist is well above nose level
            left_hand_up = left_wrist_y < nose_y - 50  # Increased buffer
            right_hand_up = right_wrist_y < nose_y - 50
            
            return left_hand_up or right_hand_up
        elif not MEDIAPIPE_AVAILABLE and self.simple_pose_detector and color_image is not None:
            # Use simple pose detector as fallback
            pose_info = self.simple_pose_detector.detect_pose(color_image)
            return pose_info.get('arms_up', False) and not pose_info.get('calibrating', True)
        else:
            return False
    
    def update_timer_state(self, pose_landmarks, image_shape, color_image=None):
        """
        Update the timer state based on pose detection using state machine.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks (or None if using simple detector)
            image_shape: Shape of the image (height, width, channels)
            color_image: Color image for simple pose detection
        """
        current_time = time.time()
        
        # State machine logic
        if self.state == "WAITING":
            # Wait for arms to go down
            if self.are_arms_down(pose_landmarks, image_shape, color_image):
                self.arms_down_frames += 1
                if self.arms_down_frames >= self.arms_down_threshold:
                    self.state = "READY_TO_START"
                    self.arms_down_frames = 0
            else:
                self.arms_down_frames = 0
                
        elif self.state == "READY_TO_START":
            # Arms are down, ready to start timing
            if not self.are_arms_down(pose_landmarks, image_shape, color_image):
                # Arms went back up, go back to waiting
                self.state = "WAITING"
                self.arms_down_frames = 0
            else:
                # Start timing immediately when in ready state
                self.start_timer()
                self.state = "TIMING"
                
        elif self.state == "TIMING":
            # Timer is running, check if we should stop it
            if self.is_hand_above_head(pose_landmarks, image_shape, color_image):
                self.hand_up_frames += 1
                if self.hand_up_frames >= self.hand_up_threshold:
                    self.stop_timer()
                    self.state = "COOLDOWN"
                    self.cooldown_start = current_time
                    self.hand_up_frames = 0
            else:
                self.hand_up_frames = 0
                
        elif self.state == "COOLDOWN":
            # Cooldown period after stopping timer
            if current_time - self.cooldown_start >= self.cooldown_duration:
                # Check if hands are still up
                if not self.is_hand_above_head(pose_landmarks, image_shape, color_image):
                    self.state = "WAITING"
        
        # Update current time if timer is running
        if self.timer_running and self.start_time:
            self.current_time = time.time() - self.start_time
    
    def start_timer(self):
        """Start the face balance timer."""
        self.timer_running = True
        self.start_time = time.time()
        self.current_time = 0.0
        self.arms_down_frames = 0
        self.hand_up_frames = 0
        print("🟢 TIMER STARTED!")
        self.play_sound('start')
    
    def stop_timer(self):
        """Stop the face balance timer and record the time."""
        if self.timer_running and self.start_time:
            final_time = time.time() - self.start_time
            self.current_time = final_time
            self.last_completed_time = final_time
            self.session_times.append(final_time)
            
            # Update best time
            if final_time > self.best_time:
                self.best_time = final_time
                print(f"🔴 STOPPED! ⏱️ {final_time:.2f}s 🏆 NEW BEST!")
            else:
                print(f"🔴 STOPPED! ⏱️ {final_time:.2f}s")
            
            self.timer_running = False
            self.start_time = None
            self.hand_up_frames = 0
            self.arms_down_frames = 0
            self.play_sound('stop')
    
    def reset_session(self):
        """Reset all session data."""
        self.timer_running = False
        self.start_time = None
        self.current_time = 0.0
        self.best_time = 0.0
        self.session_times = []
        self.last_completed_time = 0.0
        self.arms_down_frames = 0
        self.hand_up_frames = 0
        self.state = "WAITING"
        print("Session reset!")
    
    def get_status_text(self):
        """Get current status text for display."""
        if self.state == "WAITING":
            if self.arms_down_frames > 0:
                return f"Getting ready... ({self.arms_down_frames}/{self.arms_down_threshold})"
            else:
                return "Put arms down to start"
        elif self.state == "READY_TO_START":
            return "READY - Keep arms down to start!"
        elif self.state == "TIMING":
            if self.hand_up_frames > 0:
                return f"Stopping... ({self.hand_up_frames}/{self.hand_up_threshold})"
            else:
                return f"TIMING: {self.current_time:.2f}s"
        elif self.state == "COOLDOWN":
            remaining = self.cooldown_duration - (time.time() - self.cooldown_start)
            return f"Cooldown: {remaining:.1f}s"
        else:
            return "Unknown state"
    
    def draw_overlay(self, image, pose_landmarks):
        """
        Draw timer overlay and pose information on the image.
        
        Args:
            image: OpenCV image to draw on
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            numpy.ndarray: Image with overlay drawn
        """
        overlay_image = image.copy()
        
        # Draw skeleton if detected
        if pose_landmarks:
            overlay_image = self.skeleton_detector.draw_skeleton(overlay_image, pose_landmarks)
            
            # Get hand positions and draw them
            hand_positions = self.skeleton_detector.get_hand_positions(pose_landmarks, image.shape)
            overlay_image = self.skeleton_detector.draw_hands(overlay_image, hand_positions)
        
        # Draw timer information with larger fonts
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Large timer display
        if self.state == "TIMING":
            timer_text = f"{self.current_time:.2f}s"
            font_scale = 4.0
            thickness = 8
        elif self.last_completed_time > 0 and self.state != "TIMING":
            timer_text = f"Last: {self.last_completed_time:.2f}s"
            font_scale = 2.0
            thickness = 4
        else:
            timer_text = ""
            font_scale = 0
            thickness = 0
            
        if timer_text:
            text_size = cv2.getTextSize(timer_text, font, font_scale, thickness)[0]
            text_x = (image.shape[1] - text_size[0]) // 2
            text_y = image.shape[0] // 2
            
            # Background rectangle for timer
            cv2.rectangle(overlay_image, (text_x - 20, text_y - text_size[1] - 20), 
                         (text_x + text_size[0] + 20, text_y + 20), (0, 0, 0), -1)
            
            # Timer text in bright green when running, white when showing last time
            color = (0, 255, 0) if self.state == "TIMING" else (255, 255, 255)
            cv2.putText(overlay_image, timer_text, (text_x, text_y), 
                       font, font_scale, color, thickness)
        
        # Status text
        status_text = self.get_status_text()
        font_scale = 1.2
        thickness = 3
        text_size = cv2.getTextSize(status_text, font, font_scale, thickness)[0]
        text_x = (image.shape[1] - text_size[0]) // 2
        text_y = 80
        
        # Background rectangle for status
        cv2.rectangle(overlay_image, (text_x - 15, text_y - 40), 
                     (text_x + text_size[0] + 15, text_y + 15), (0, 0, 0), -1)
        
        # Status text color based on state
        if self.state == "TIMING":
            color = (0, 255, 0)  # Green when running
        elif self.state == "READY_TO_START":
            color = (0, 255, 255)  # Yellow when ready
        elif self.state == "COOLDOWN":
            color = (0, 165, 255)  # Orange during cooldown
        else:
            color = (255, 255, 255)  # White when waiting
            
        cv2.putText(overlay_image, status_text, (text_x, text_y), 
                   font, font_scale, color, thickness)
        
        # Session stats
        if self.best_time > 0:
            best_text = f"Best: {self.best_time:.2f}s"
            cv2.putText(overlay_image, best_text, (20, image.shape[0] - 100), 
                       font, 0.8, (0, 255, 255), 2)
        
        if len(self.session_times) > 0:
            attempts_text = f"Attempts: {len(self.session_times)}"
            cv2.putText(overlay_image, attempts_text, (20, image.shape[0] - 60), 
                       font, 0.8, (255, 255, 255), 2)
            
            avg_text = f"Avg: {np.mean(self.session_times):.2f}s"
            cv2.putText(overlay_image, avg_text, (20, image.shape[0] - 20), 
                       font, 0.8, (255, 255, 255), 2)
        
        # Instructions (smaller, in corner)
        instructions = [
            "Arms down to START",
            "Hand up to STOP", 
            "'r' reset, 'q' quit"
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(overlay_image, instruction, (image.shape[1] - 250, 30 + i * 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return overlay_image
    
    def show_session_graph(self):
        """Show a graph of session times when program closes."""
        if not self.session_times:
            return
            
        try:
            plt.figure(figsize=(12, 8))
            
            # Plot individual times
            plt.subplot(2, 1, 1)
            plt.plot(range(1, len(self.session_times) + 1), self.session_times, 'bo-', linewidth=2, markersize=8)
            plt.axhline(y=self.best_time, color='r', linestyle='--', label=f'Best: {self.best_time:.2f}s')
            plt.axhline(y=np.mean(self.session_times), color='g', linestyle='--', label=f'Average: {np.mean(self.session_times):.2f}s')
            plt.xlabel('Attempt Number')
            plt.ylabel('Time (seconds)')
            plt.title('Face Balance Timer - Session Performance')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Histogram of times
            plt.subplot(2, 1, 2)
            plt.hist(self.session_times, bins=min(10, len(self.session_times)), alpha=0.7, color='skyblue', edgecolor='black')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Frequency')
            plt.title('Distribution of Balance Times')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Could not display graph: {e}")
    
    def run(self):
        """Main application loop."""
        print("Face Balance Timer Starting...")
        print("Instructions:")
        print("- Put both arms down at your sides to start the timer")
        print("- Raise one hand above your head to stop the timer")
        print("- After stopping, wait for cooldown before next attempt")
        if not MEDIAPIPE_AVAILABLE:
            print("- Using motion-based detection")
        print("- Press 'r' to reset session")
        print("- Press 'q' to quit")
        
        if not self.initialize():
            print("Failed to initialize camera!")
            return
        
        try:
            while True:
                # Get frames from camera
                depth_frame, color_frame, depth_image, color_image = self.get_frames()
                
                if color_image is None:
                    continue
                
                # Detect skeleton
                pose_landmarks = self.skeleton_detector.detect_skeleton(color_image)
                
                # Update timer state based on pose
                self.update_timer_state(pose_landmarks, color_image.shape, color_image)
                
                # Draw overlay
                display_image = self.draw_overlay(color_image, pose_landmarks)
                
                # Add pose detector debug info
                if self.use_improved_detector:
                    pose_info = self.improved_pose_detector.detect_pose(color_image)
                    display_image = self.improved_pose_detector.draw_debug_info(display_image, pose_info)
                elif not MEDIAPIPE_AVAILABLE and self.simple_pose_detector:
                    pose_info = self.simple_pose_detector.detect_pose(color_image)
                    display_image = self.simple_pose_detector.draw_debug_info(display_image, pose_info)
                
                # Show the image (larger window)
                cv2.imshow('Face Balance Timer', display_image)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.reset_session()
                        
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            if self.using_webcam and self.webcam:
                self.webcam.release()
            elif self.using_color_only:
                self.color_frame_acquisition.stop()
            else:
                self.frame_acquisition.stop()
            cv2.destroyAllWindows()
            
            # Save session to database
            self.save_session_to_db()
            
            # Print session summary
            if self.session_times:
                print(f"\n📊 Session Summary:")
                print(f"Total attempts: {len(self.session_times)}")
                print(f"Best time: {self.best_time:.2f} seconds")
                print(f"Average time: {np.mean(self.session_times):.2f} seconds")
                print(f"All times: {[f'{t:.2f}s' for t in self.session_times]}")
                
                # Show graph
                self.show_session_graph()

def main():
    """Main entry point."""
    timer = FaceBalanceTimer(width=1280, height=720, fps=30)
    timer.run()

if __name__ == "__main__":
    main()