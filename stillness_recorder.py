#!/usr/bin/env python3
"""
Stillness Recorder - Motion-triggered video recorder using RealSense camera

This application:
1. Shows a live video feed from RealSense camera
2. Continuously monitors for motion in the video
3. When stillness is detected (low motion for specified duration), 
   it saves the preceding X seconds of video to a file
4. Provides configurable parameters for recording duration and motion sensitivity

Author: Generated for JugVid2 project
Date: 2025-08-15
"""

import cv2
import numpy as np
import time
import threading
import argparse
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# Import our custom modules
try:
    from color_only_frame_acquisition import ColorOnlyFrameAcquisition
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    print("Warning: RealSense modules not available")

from motion_detector import MotionDetector
from circular_frame_buffer import CircularFrameBuffer, FrameBufferRecorder

class ControlsWindow:
    """Tkinter GUI window for controls with text input fields and submit buttons."""
    
    def __init__(self, recorder):
        self.recorder = recorder
        self.root = None
        self.record_duration_var = None
        self.motion_threshold_var = None
        self.stillness_threshold_var = None
        self.stillness_duration_var = None
        
    def create_window(self):
        """Create the tkinter controls window."""
        try:
            self.root = tk.Tk()
            self.root.title("Stillness Recorder Controls")
            self.root.geometry("800x900")
            self.root.resizable(True, True)
            self.root.minsize(700, 800)
            
            # Configure the root window to expand properly
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            
            print("✓ Controls window root created successfully")
        except Exception as e:
            print(f"✗ Error creating controls window root: {e}")
            return
        
        # Main frame with smaller padding
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame to expand
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Title with smaller font and padding
        title_label = ttk.Label(main_frame, text="STILLNESS RECORDER CONTROLS",
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Record Duration with smaller font and padding
        ttk.Label(main_frame, text="Record Duration (seconds):",
                 font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.record_duration_var = tk.StringVar(value=str(int(self.recorder.record_duration)))
        record_entry = ttk.Entry(main_frame, textvariable=self.record_duration_var, width=12, font=("Arial", 10))
        record_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_record_duration).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Motion Threshold with smaller font and padding
        ttk.Label(main_frame, text="Motion Threshold (movement):",
                 font=("Arial", 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.motion_threshold_var = tk.StringVar(value=str(int(self.recorder.motion_threshold)))
        motion_entry = ttk.Entry(main_frame, textvariable=self.motion_threshold_var, width=12, font=("Arial", 10))
        motion_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_motion_threshold).grid(row=2, column=2, padx=(10, 0), pady=5)
        
        # Stillness Threshold with smaller font and padding
        ttk.Label(main_frame, text="Stillness Threshold (stop):",
                 font=("Arial", 11)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.stillness_threshold_var = tk.StringVar(value=str(int(self.recorder.stillness_threshold)))
        stillness_thresh_entry = ttk.Entry(main_frame, textvariable=self.stillness_threshold_var, width=12, font=("Arial", 10))
        stillness_thresh_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_stillness_threshold).grid(row=3, column=2, padx=(10, 0), pady=5)
        
        # Stillness Duration with smaller font and padding
        ttk.Label(main_frame, text="Stillness Trigger (1/10ths sec):",
                 font=("Arial", 11)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.stillness_duration_var = tk.StringVar(value=str(int(self.recorder.stillness_duration * 10)))
        stillness_entry = ttk.Entry(main_frame, textvariable=self.stillness_duration_var, width=12, font=("Arial", 10))
        stillness_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_stillness_duration).grid(row=4, column=2, padx=(10, 0), pady=5)
        
        # Separator with smaller padding
        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=10)
        
        # Current Values Display with smaller font and padding
        ttk.Label(main_frame, text="CURRENT VALUES",
                 font=("Arial", 12, "bold")).grid(row=6, column=0, columnspan=3, pady=(10, 8))
        
        self.current_record_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_record_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        self.current_motion_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_motion_label.grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        self.current_stillness_thresh_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_stillness_thresh_label.grid(row=9, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        self.current_stillness_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_stillness_label.grid(row=10, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        # Session Info with smaller font and padding
        ttk.Separator(main_frame, orient='horizontal').grid(row=11, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=15)
        
        ttk.Label(main_frame, text="SESSION INFO",
                 font=("Arial", 12, "bold")).grid(row=12, column=0, columnspan=3, pady=(0, 8))
        
        self.recordings_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.recordings_label.grid(row=13, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        self.movement_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.movement_label.grid(row=14, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        # Control Buttons with smaller padding
        ttk.Separator(main_frame, orient='horizontal').grid(row=15, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=10)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=16, column=0, columnspan=3, pady=5)
        
        ttk.Button(button_frame, text="Manual Record",
                  command=self.manual_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset Movement",
                  command=self.reset_movement).pack(side=tk.LEFT, padx=5)
        
        try:
            # Update display
            self.update_display()
            
            # Start the update loop
            self.schedule_update()
            
            # Force initial window update to ensure it displays
            self.root.update()
            print("✓ Controls window initialized and updated successfully")
        except Exception as e:
            print(f"✗ Error initializing controls window: {e}")
            import traceback
            traceback.print_exc()
        
    def update_record_duration(self):
        """Update record duration from text input."""
        try:
            value = float(self.record_duration_var.get())
            if 1 <= value <= 60:
                self.recorder.record_duration = value
                buffer_duration = value + self.recorder.stillness_duration + 2.0
                self.recorder.frame_buffer.update_max_duration(buffer_duration)
                print(f"📹 Record duration set to: {int(value)} seconds")
                self.update_display()
            else:
                tk.messagebox.showerror("Invalid Input", "Record duration must be between 1 and 60 seconds")
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def update_motion_threshold(self):
        """Update motion threshold from text input."""
        try:
            value = float(self.motion_threshold_var.get())
            if 100 <= value <= 10000:
                self.recorder.motion_threshold = int(value)
                print(f"🎯 Motion threshold (movement detection) set to: {int(value)}")
                self.update_display()
            else:
                tk.messagebox.showerror("Invalid Input", "Motion threshold must be between 100 and 10000")
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def update_stillness_threshold(self):
        """Update stillness threshold from text input."""
        try:
            value = float(self.stillness_threshold_var.get())
            if 50 <= value <= 5000:
                self.recorder.stillness_threshold = int(value)
                self.recorder.motion_detector.update_threshold(int(value))
                print(f"🎯 Stillness threshold (stop detection) set to: {int(value)}")
                self.update_display()
            else:
                tk.messagebox.showerror("Invalid Input", "Stillness threshold must be between 50 and 5000")
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def update_stillness_duration(self):
        """Update stillness duration from text input."""
        try:
            value = float(self.stillness_duration_var.get())
            if 5 <= value <= 100:  # 0.5 to 10.0 seconds
                seconds = value / 10.0
                self.recorder.stillness_duration = seconds
                self.recorder.motion_detector.update_stillness_duration(seconds)
                buffer_duration = self.recorder.record_duration + seconds + 2.0
                self.recorder.frame_buffer.update_max_duration(buffer_duration)
                print(f"⏱️ Stillness trigger set to: {int(value)} (1/10ths sec) = {seconds:.1f}s")
                self.update_display()
            else:
                tk.messagebox.showerror("Invalid Input", "Stillness trigger must be between 5 and 100 (1/10ths of seconds)")
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def manual_record(self):
        """Trigger manual recording."""
        print("🎬 Manual recording trigger")
        self.recorder.trigger_recording()
    
    def reset_movement(self):
        """Reset movement detection."""
        print("🔄 Resetting movement detection")
        self.recorder.motion_detector.reset_stillness()
        self.recorder.has_detected_movement = False
    
    def update_display(self):
        """Update the display labels with current values."""
        if self.root and self.root.winfo_exists():
            # Current values
            self.current_record_label.config(text=f"Record Duration: {int(self.recorder.record_duration)} seconds")
            self.current_motion_label.config(text=f"Motion Threshold (movement): {int(self.recorder.motion_threshold)}")
            self.current_stillness_thresh_label.config(text=f"Stillness Threshold (stop): {int(self.recorder.stillness_threshold)}")
            stillness_tenths = int(self.recorder.stillness_duration * 10)
            self.current_stillness_label.config(text=f"Stillness Trigger: {stillness_tenths} (1/10ths sec) = {self.recorder.stillness_duration:.1f}s")
            
            # Session info
            self.recordings_label.config(text=f"Session Recordings: {self.recorder.total_recordings}")
            movement_status = "Yes" if self.recorder.has_detected_movement else "No"
            self.movement_label.config(text=f"Movement Detected: {movement_status}")
    
    def schedule_update(self):
        """Schedule the next display update."""
        if self.root and self.root.winfo_exists():
            self.update_display()
            self.root.after(2000, self.schedule_update)  # Update every 2 seconds to reduce load
    
    def process_events(self):
        """Process tkinter events (call this from main loop)."""
        try:
            if self.root and self.root.winfo_exists():
                self.root.update_idletasks()  # Lightweight update to avoid blocking
                return True
        except tk.TclError:
            # Window was closed, clean up
            self.root = None
            return False
        except Exception as e:
            print(f"Warning: Tkinter process_events error: {e}")
            self.root = None
            return False
        return False
    
    def destroy(self):
        """Destroy the tkinter window."""
        if self.root:
            self.root.destroy()

class StillnessRecorder:
    """
    Main application class for the stillness-triggered recorder.
    """
    
    def __init__(self,
                 record_duration=10.0,
                 motion_threshold=1000,
                 stillness_threshold=500,
                 stillness_duration=3.0,
                 output_dir="recordings",
                 camera_width=1280,
                 camera_height=720,
                 camera_fps=30):
        """
        Initialize the stillness recorder.
        
        Args:
            record_duration (float): Seconds of video to save when stillness is detected
            motion_threshold (float): Motion threshold for detecting significant movement
            stillness_threshold (float): Stillness threshold for detecting when motion stops
            stillness_duration (float): Duration of stillness required to trigger recording
            output_dir (str): Directory to save recorded videos
            camera_width (int): Camera frame width
            camera_height (int): Camera frame height
            camera_fps (int): Camera frames per second
        """
        self.record_duration = record_duration
        self.motion_threshold = motion_threshold
        self.stillness_threshold = stillness_threshold
        self.stillness_duration = stillness_duration
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize camera components (same pattern as face balance timer)
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.camera_fps = camera_fps
        self.using_webcam = False
        self.using_color_only = False
        self.webcam = None
        
        # Initialize camera exactly like face balance timer
        self.color_frame_acquisition = ColorOnlyFrameAcquisition(camera_width, camera_height, camera_fps)
        
        self.motion_detector = MotionDetector(stillness_threshold, stillness_duration)
        # Buffer needs to hold record_duration + stillness_duration + extra buffer
        # This ensures we always have enough frames to get the period BEFORE stillness
        buffer_duration = record_duration + stillness_duration + 2.0
        self.frame_buffer = CircularFrameBuffer(buffer_duration, camera_fps)
        self.recorder = FrameBufferRecorder(output_dir)
        
        # Application state
        self.running = False
        self.recording_in_progress = False
        self.total_recordings = 0
        self.last_recording_time = None
        
        # Session management for organized recordings
        self.session_start_time = datetime.now()
        self.session_dir = os.path.join(output_dir, f"session_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Movement tracking to ignore first stillness
        self.has_detected_movement = False
        # Use the motion_threshold for detecting significant movement
        
        # UI state
        self.show_motion_mask = False
        self.show_help = False  # Start with help hidden for cleaner display
        self.show_controls = False  # Controls panel in main window
        self.controls_window_created = False
        
        # Controls window
        self.controls_window = None
        
        # Display settings - doubled dimensions for better visibility
        self.display_width = 2560
        self.display_height = 1440
        
        # Input mode tracking
        self.input_mode = None  # None, 'record_duration', 'motion_threshold', 'stillness_duration'
        self.input_buffer = ""
        
        # Statistics
        self.frame_count = 0
        self.start_time = None
        
    def initialize(self):
        """Initialize camera exactly like face balance timer and test."""
        print("Initializing Stillness Recorder...")
        print(f"Record Duration: {self.record_duration}s")
        print(f"Motion Threshold: {self.motion_threshold}")
        print(f"Stillness Duration: {self.stillness_duration}s")
        print(f"Session Directory: {self.session_dir}")
        
        # Try RealSense COLOR ONLY first (same as face balance timer)
        if self.color_frame_acquisition.initialize():
            print("RealSense color-only initialized")
            self.using_color_only = True
            return True
        else:
            # Fallback to webcam (same as face balance timer)
            self.webcam = cv2.VideoCapture(0)
            if self.webcam.isOpened():
                self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
                self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
                self.webcam.set(cv2.CAP_PROP_FPS, self.camera_fps)
                self.using_webcam = True
                print("Webcam initialized")
                return True
            else:
                print("Failed to initialize any camera")
                return False
    
    def get_frames(self):
        """Get frames from camera (same pattern as face balance timer)."""
        if self.using_webcam:
            ret, color_image = self.webcam.read()
            if ret:
                return None, None, None, color_image
            else:
                return None, None, None, None
        else:
            # Use color-only RealSense
            depth_frame, color_frame, depth_image, color_image = self.color_frame_acquisition.get_frames()
            
            # If color-only fails, try fallback to webcam
            if color_image is None and not self.using_webcam:
                self.webcam = cv2.VideoCapture(0)
                if self.webcam.isOpened():
                    self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
                    self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
                    self.webcam.set(cv2.CAP_PROP_FPS, self.camera_fps)
                    self.using_webcam = True
                    self.using_color_only = False
                    # Try to get a frame from webcam
                    ret, color_image = self.webcam.read()
                    if ret:
                        return None, None, None, color_image
                        
            return depth_frame, color_frame, depth_image, color_image
    
    def create_controls_window(self):
        """Create a tkinter GUI controls window."""
        if self.controls_window is None:
            self.controls_window = ControlsWindow(self)
            self.controls_window.create_window()
            # Force the window to appear and update
            if self.controls_window.root:
                self.controls_window.root.lift()
                self.controls_window.root.attributes('-topmost', True)
                self.controls_window.root.after(100, lambda: self.controls_window.root.attributes('-topmost', False))
                self.controls_window.root.update()
    
    def process_frame(self, frame):
        """
        Process a single frame for motion detection and recording.
        
        Args:
            frame (numpy.ndarray): Input frame from camera
            
        Returns:
            tuple: (processed_frame, motion_info)
        """
        if frame is None:
            return None, None
            
        # Add frame to circular buffer
        self.frame_buffer.add_frame(frame)
        
        # Detect motion
        motion_value, is_motion, motion_mask = self.motion_detector.detect_motion(frame)
        
        # Track significant movement to ignore first stillness
        if motion_value > self.motion_threshold:
            self.has_detected_movement = True
        
        # Check for stillness trigger (only after movement has been detected)
        stillness_triggered = False
        if self.has_detected_movement:
            stillness_triggered = self.motion_detector.check_stillness(motion_value)
            
            # Handle recording trigger
            if stillness_triggered and not self.recording_in_progress:
                self.trigger_recording()
        
        # Get motion statistics
        motion_stats = self.motion_detector.get_motion_stats()
        
        # Create display frame with enhanced overlay
        display_frame = frame.copy()
        self.draw_enhanced_overlay(display_frame, motion_stats, stillness_triggered, motion_value)
        
        motion_info = {
            'motion_value': motion_value,
            'is_motion': is_motion,
            'motion_mask': motion_mask,
            'motion_stats': motion_stats,
            'stillness_triggered': stillness_triggered,
            'has_detected_movement': self.has_detected_movement
        }
        
        return display_frame, motion_info
    
    def draw_enhanced_overlay(self, frame, motion_stats, stillness_triggered, motion_value):
        """
        Draw enhanced information overlay with visual indicators and controls.
        
        Args:
            frame (numpy.ndarray): Frame to draw on
            motion_stats (dict): Motion statistics
            stillness_triggered (bool): Whether stillness was just triggered
            motion_value (float): Current motion value
        """
        h, w = frame.shape[:2]
        
        # Color scheme
        text_color = (255, 255, 255)  # White
        bg_color = (0, 0, 0)  # Black background
        
        # Motion status colors
        if not self.has_detected_movement:
            motion_color = (128, 128, 128)  # Gray - waiting for movement
            status_text = "WAITING FOR MOVEMENT"
            status_color = (128, 128, 128)
        elif motion_stats['is_still']:
            motion_color = (0, 255, 255)  # Cyan - still
            status_text = f"STILL ({motion_stats['stillness_duration']:.1f}s)"
            status_color = (0, 255, 255)
        elif motion_value > self.motion_threshold:
            motion_color = (0, 255, 0)  # Green - moving
            status_text = "MOVING"
            status_color = (0, 255, 0)
        elif motion_value > self.stillness_threshold:
            motion_color = (0, 165, 255)  # Orange - low motion
            status_text = "LOW MOTION"
            status_color = (0, 165, 255)
        else:
            motion_color = (0, 100, 200)  # Dark orange - very low motion
            status_text = "VERY LOW MOTION"
            status_color = (0, 100, 200)
        
        # Main status display (large, centered)
        font_scale = 1.2
        thickness = 3
        text_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (w - text_size[0]) // 2
        text_y = 50
        
        # Background for status
        cv2.rectangle(frame, (text_x - 20, text_y - 35), (text_x + text_size[0] + 20, text_y + 10), bg_color, -1)
        cv2.putText(frame, status_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, status_color, thickness)
        
        # Motion value bar (visual indicator)
        bar_width = 300
        bar_height = 20
        bar_x = (w - bar_width) // 2
        bar_y = 70
        
        # Background bar
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Motion level bar - scale to show both thresholds clearly
        max_scale = max(self.motion_threshold * 2, 3000)  # Scale to show both thresholds
        motion_ratio = min(motion_value / max_scale, 1.0)
        fill_width = int(bar_width * motion_ratio)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), motion_color, -1)
        
        # Stillness threshold marker (red line)
        stillness_x = bar_x + int(bar_width * (self.stillness_threshold / max_scale))
        cv2.line(frame, (stillness_x, bar_y), (stillness_x, bar_y + bar_height), (0, 0, 255), 2)
        
        # Motion threshold marker (white line)
        motion_x = bar_x + int(bar_width * (self.motion_threshold / max_scale))
        cv2.line(frame, (motion_x, bar_y), (motion_x, bar_y + bar_height), (255, 255, 255), 2)
        
        # Motion value text with both thresholds
        cv2.putText(frame, f"Motion: {motion_value:.0f} | Still: {self.stillness_threshold:.0f} | Move: {self.motion_threshold:.0f}",
                   (bar_x, bar_y + bar_height + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        # Controls panel
        if self.show_controls:
            self.draw_controls_panel(frame)
        
        # Recording indicators
        if stillness_triggered:
            # Flash effect for recording trigger
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 255), 10)
            cv2.putText(frame, "RECORDING TRIGGERED!", (w//2 - 200, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
        
        if self.recording_in_progress:
            # Pulsing red indicator
            cv2.circle(frame, (w - 50, 50), 20, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 65, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Session info
        cv2.putText(frame, f"Session: {self.total_recordings} recordings",
                   (15, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
        cv2.putText(frame, f"Record Duration: {self.record_duration:.1f}s",
                   (15, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
        cv2.putText(frame, f"Stillness Required: {self.stillness_duration:.1f}s",
                   (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
        
        # Help toggle
        if not self.show_help:
            cv2.putText(frame, "Press 'h' for help", (w - 150, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        else:
            self.draw_help_overlay(frame)
    
    def draw_controls_panel(self, frame):
        """Draw the controls panel with current settings."""
        h, w = frame.shape[:2]
        
        # Controls background
        panel_x = w - 350
        panel_y = 100
        panel_w = 340
        panel_h = 200
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Title
        cv2.putText(frame, "CONTROLS", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Control instructions
        controls = [
            f"Record Duration: {self.record_duration:.1f}s  [/]",
            f"Stillness Time: {self.stillness_duration:.1f}s  </> ",
            f"Motion Threshold: {self.motion_threshold:.0f}  +/-",
            "",
            "r - Manual record",
            "c - Reset movement detection",
            "m - Toggle motion mask",
            "h - Toggle help",
            "q - Quit"
        ]
        
        y_start = panel_y + 50
        for i, control in enumerate(controls):
            color = (255, 255, 255) if control else (100, 100, 100)
            cv2.putText(frame, control, (panel_x + 15, y_start + i * 18),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    def draw_help_overlay(self, frame):
        """Draw help overlay with keyboard shortcuts."""
        help_text = [
            "KEYBOARD SHORTCUTS:",
            "q - Quit application",
            "h - Toggle this help",
            "m - Toggle motion mask view",
            "r - Manual recording trigger",
            "c - Clear motion detector state",
            "+ - Increase motion threshold",
            "- - Decrease motion threshold",
            "[ - Decrease record duration",
            "] - Increase record duration"
        ]
        
        # Draw help background
        overlay = frame.copy()
        cv2.rectangle(overlay, (frame.shape[1] - 300, 50), (frame.shape[1] - 10, 300), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Draw help text
        y_start = 75
        for i, text in enumerate(help_text):
            color = (0, 255, 255) if i == 0 else (255, 255, 255)
            weight = 2 if i == 0 else 1
            cv2.putText(frame, text, (frame.shape[1] - 290, y_start + i * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, weight)
    
    def trigger_recording(self):
        """Trigger a recording of the last X seconds."""
        if self.recording_in_progress:
            print("Recording already in progress, skipping trigger")
            return
        
        print(f"Stillness detected! Triggering recording of last {self.record_duration} seconds...")
        
        # Start recording in a separate thread to avoid blocking
        recording_thread = threading.Thread(target=self._save_recording)
        recording_thread.daemon = True
        recording_thread.start()
    
    def _save_recording(self):
        """Save the recording (runs in separate thread)."""
        self.recording_in_progress = True
        
        try:
            # Get all frames from buffer to find the right time window
            all_frames = self.frame_buffer.get_all_frames()
            
            if not all_frames:
                print("No frames available for recording")
                return
            
            # Find the end of the recording period (start of stillness detection)
            # We want to record the X seconds BEFORE stillness was detected
            current_time = time.time()
            
            # The recording should end when stillness started being detected
            # Get motion stats to find when stillness started
            motion_stats = self.motion_detector.get_motion_stats()
            stillness_start_time = current_time - motion_stats['stillness_duration']
            
            # Calculate the recording window: [stillness_start - record_duration, stillness_start]
            recording_start_time = stillness_start_time - self.record_duration
            recording_end_time = stillness_start_time
            
            # Filter frames to get only the period BEFORE stillness detection
            recording_frames = []
            for timestamp, frame in all_frames:
                if recording_start_time <= timestamp <= recording_end_time:
                    recording_frames.append((timestamp, frame))
            
            if not recording_frames:
                print("No frames found in the recording window (before stillness)")
                return
            
            # Generate filename with clip start timestamp
            clip_start_time = datetime.fromtimestamp(recording_frames[0][0])
            clip_timestamp = clip_start_time.strftime("%H%M%S")
            filename = f"clip_{clip_timestamp}.mp4"
            
            # Create temporary recorder for this session directory
            session_recorder = FrameBufferRecorder(self.session_dir)
            
            # Save the video
            output_path = session_recorder.save_frames_to_video(recording_frames, filename, fps=30)
            
            if output_path:
                self.total_recordings += 1
                self.last_recording_time = time.time()
                duration = recording_frames[-1][0] - recording_frames[0][0]
                print(f"🎬 Recording saved: {output_path}")
                print(f"📊 Recorded {len(recording_frames)} frames ({duration:.2f}s) from BEFORE stillness detection")
                print(f"📊 Total recordings this session: {self.total_recordings}")
            else:
                print("❌ Failed to save recording")
                
        except Exception as e:
            print(f"❌ Error during recording: {e}")
        finally:
            self.recording_in_progress = False
    
    def handle_key_press(self, key):
        """
        Handle keyboard input with text input system.
        
        Args:
            key (int): Key code from cv2.waitKey()
            
        Returns:
            bool: True to continue running, False to quit
        """
        # Handle input mode
        if self.input_mode:
            if key == 13 or key == 10:  # Enter key
                self._process_input()
            elif key == 27:  # Escape key
                self._cancel_input()
            elif key == 8:  # Backspace
                if self.input_buffer:
                    self.input_buffer = self.input_buffer[:-1]
            elif key >= ord('0') and key <= ord('9'):  # Numeric input
                self.input_buffer += chr(key)
            elif key == ord('.') and '.' not in self.input_buffer:  # Decimal point (only one allowed)
                self.input_buffer += '.'
            return True
        
        # Normal mode key handling
        if key == ord('q'):
            return False
        elif key == ord('1'):
            self._start_input('record_duration', "Enter record duration in seconds:")
        elif key == ord('2'):
            self._start_input('motion_threshold', "Enter motion threshold:")
        elif key == ord('3'):
            self._start_input('stillness_duration', "Enter stillness trigger in 1/10ths of seconds:")
        elif key == ord('h'):
            self.show_help = not self.show_help
        elif key == ord('m'):
            self.show_motion_mask = not self.show_motion_mask
        elif key == ord('r'):
            print("🎬 Manual recording trigger")
            self.trigger_recording()
        elif key == ord('c'):
            print("🔄 Resetting movement detection")
            self.motion_detector.reset_stillness()
            self.has_detected_movement = False
        
        return True
    
    def _start_input(self, input_type, prompt):
        """Start text input mode."""
        self.input_mode = input_type
        self.input_buffer = ""
        print(f"\n{prompt}")
        print("Type the value and press Enter to confirm, or Escape to cancel.")
    
    def _cancel_input(self):
        """Cancel current input mode."""
        print("Input cancelled.")
        self.input_mode = None
        self.input_buffer = ""
    
    def _process_input(self):
        """Process the entered input value."""
        if not self.input_buffer:
            self._cancel_input()
            return
        
        try:
            value = float(self.input_buffer)
            
            if self.input_mode == 'record_duration':
                if 1 <= value <= 60:
                    self.record_duration = value
                    buffer_duration = value + self.stillness_duration + 2.0
                    self.frame_buffer.update_max_duration(buffer_duration)
                    print(f"📹 Record duration set to: {int(value)} seconds")
                else:
                    print("❌ Record duration must be between 1 and 60 seconds")
                    
            elif self.input_mode == 'motion_threshold':
                if 100 <= value <= 10000:
                    self.motion_threshold = int(value)
                    self.movement_threshold = int(value) * 2
                    self.motion_detector.update_threshold(int(value))
                    print(f"🎯 Motion threshold set to: {int(value)}")
                else:
                    print("❌ Motion threshold must be between 100 and 10000")
                    
            elif self.input_mode == 'stillness_duration':
                # Convert from 1/10ths of seconds to seconds
                if 5 <= value <= 100:  # 0.5 to 10.0 seconds
                    seconds = value / 10.0
                    self.stillness_duration = seconds
                    self.motion_detector.update_stillness_duration(seconds)
                    buffer_duration = self.record_duration + seconds + 2.0
                    self.frame_buffer.update_max_duration(buffer_duration)
                    print(f"⏱️ Stillness trigger set to: {int(value)} (1/10ths sec) = {seconds:.1f}s")
                else:
                    print("❌ Stillness trigger must be between 5 and 100 (1/10ths of seconds)")
                    
        except ValueError:
            print("❌ Invalid number format")
        
        # Reset input mode
        self.input_mode = None
        self.input_buffer = ""
    
    def run(self):
        """Main application loop."""
        if not self.initialize():
            return False
        
        print("\nStillness Recorder Started!")
        print("The application will automatically record video when stillness is detected.")
        print("Press 'h' for help, 'q' to quit")
        print("-" * 60)
        
        # Create main video window with larger size
        cv2.namedWindow('Stillness Recorder', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Stillness Recorder', self.display_width, self.display_height)
        
        # Create controls window
        self.create_controls_window()
        
        self.running = True
        self.start_time = time.time()
        
        try:
            frame_counter = 0
            while self.running:
                # Get frames from camera (exact same pattern as face balance timer)
                depth_frame, color_frame, depth_image, color_image = self.get_frames()
                
                if color_image is not None:
                    self.frame_count += 1
                    frame_counter += 1
                    
                    # Process frame
                    display_frame, motion_info = self.process_frame(color_image)
                    
                    if display_frame is not None:
                        # Only resize if significantly different to prevent unnecessary processing
                        current_height, current_width = display_frame.shape[:2]
                        if abs(current_width - self.display_width) > 50 or abs(current_height - self.display_height) > 50:
                            display_frame = cv2.resize(display_frame, (self.display_width, self.display_height))
                        
                        # Show main display (same as face balance timer)
                        cv2.imshow('Stillness Recorder', display_frame)
                        
                        # Show motion mask if enabled
                        if self.show_motion_mask and motion_info and motion_info['motion_mask'] is not None:
                            cv2.imshow('Motion Mask', motion_info['motion_mask'])
                        elif not self.show_motion_mask:
                            # Close motion mask window if it exists
                            try:
                                cv2.destroyWindow('Motion Mask')
                            except cv2.error:
                                pass
                
                # Process tkinter events to keep controls window responsive
                if self.controls_window:
                    try:
                        if self.controls_window.root and self.controls_window.root.winfo_exists():
                            # Process events more frequently for better responsiveness
                            if frame_counter % 5 == 0:
                                self.controls_window.root.update_idletasks()
                            # Full update less frequently
                            if frame_counter % 30 == 0:
                                self.controls_window.root.update()
                        else:
                            self.controls_window = None
                    except tk.TclError:
                        # Window was closed, clean up
                        self.controls_window = None
                    except Exception as e:
                        print(f"Warning: Tkinter error: {e}")
                        self.controls_window = None
                
                # Handle keyboard input (same as face balance timer)
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # Key was pressed
                    if not self.handle_key_press(key):
                        break
                        
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Clean up resources."""
        print("Cleaning up...")
        self.running = False
        
        # Clean up tkinter controls window
        if self.controls_window:
            try:
                self.controls_window.destroy()
            except:
                pass
            self.controls_window = None
        
        # Clean up circular buffer to free memory
        if hasattr(self, 'frame_buffer'):
            self.frame_buffer.clear()
        
        # Clean up motion detector
        if hasattr(self, 'motion_detector'):
            self.motion_detector.reset_stillness()
        
        # Clean up camera resources (same pattern as face balance timer)
        if self.using_webcam and self.webcam:
            self.webcam.release()
            self.webcam = None
        elif self.using_color_only:
            self.color_frame_acquisition.stop()
        else:
            self.color_frame_acquisition.stop()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Print final statistics
        if self.start_time:
            runtime = time.time() - self.start_time
            fps = self.frame_count / runtime if runtime > 0 else 0
            print(f"\nSession Statistics:")
            print(f"Runtime: {runtime:.1f} seconds")
            print(f"Frames processed: {self.frame_count}")
            print(f"Average FPS: {fps:.1f}")
            print(f"Total recordings: {self.total_recordings}")
            print(f"Output directory: {self.output_dir}")

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Stillness Recorder - Motion-triggered video recorder")
    
    parser.add_argument('--record-duration', type=float, default=10.0,
                       help='Duration in seconds to record when stillness is detected (default: 10.0)')
    parser.add_argument('--motion-threshold', type=float, default=1000,
                       help='Motion threshold for detecting significant movement (default: 1000)')
    parser.add_argument('--stillness-threshold', type=float, default=500,
                       help='Stillness threshold for detecting when motion stops (default: 500)')
    parser.add_argument('--stillness-duration', type=float, default=3.0,
                       help='Duration of stillness required to trigger recording (default: 3.0)')
    parser.add_argument('--output-dir', type=str, default='recordings',
                       help='Directory to save recorded videos (default: recordings)')
    parser.add_argument('--camera-width', type=int, default=640,
                       help='Camera frame width (default: 640)')
    parser.add_argument('--camera-height', type=int, default=480,
                       help='Camera frame height (default: 480)')
    parser.add_argument('--camera-fps', type=int, default=30,
                       help='Camera frames per second (default: 30)')
    
    args = parser.parse_args()
    
    # Create and run the recorder
    recorder = StillnessRecorder(
        record_duration=args.record_duration,
        motion_threshold=args.motion_threshold,
        stillness_threshold=getattr(args, 'stillness_threshold', 500),
        stillness_duration=args.stillness_duration,
        output_dir=args.output_dir,
        camera_width=args.camera_width,
        camera_height=args.camera_height,
        camera_fps=args.camera_fps
    )
    
    success = recorder.run()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())