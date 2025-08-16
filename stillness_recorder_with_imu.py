#!/usr/bin/env python3
"""
Stillness Recorder with IMU - Motion-triggered video recorder with Watch OS IMU integration

This application extends the original stillness recorder to include:
1. Synchronized IMU recording from dual Watch OS apps (left and right wrist)
2. Network-based start/stop commands to watches
3. Automatic IMU data retrieval and storage
4. Combined video + IMU data sessions

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
from watch_imu_manager import WatchIMUManager


class ControlsWindowWithIMU:
    """Enhanced Tkinter GUI window with IMU controls."""
    
    def __init__(self, recorder):
        self.recorder = recorder
        self.root = None
        self.record_duration_var = None
        self.motion_threshold_var = None
        self.stillness_threshold_var = None
        self.stillness_duration_var = None
        
        # IMU-specific variables
        self.left_watch_ip_var = None
        self.right_watch_ip_var = None
        self.watch_status_labels = {}
        
    def create_window(self):
        """Create the tkinter controls window with IMU controls."""
        try:
            self.root = tk.Tk()
            self.root.title("Stillness Recorder with IMU Controls")
            self.root.geometry("900x1100")
            self.root.resizable(True, True)
            self.root.minsize(800, 1000)
            
            # Configure the root window to expand properly
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            
            print("✓ Controls window root created successfully")
        except Exception as e:
            print(f"✗ Error creating controls window root: {e}")
            return
        
        # Main frame with scrollable content
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        
        current_row = 0
        
        # Title
        title_label = ttk.Label(main_frame, text="STILLNESS RECORDER WITH IMU",
                               font=("Arial", 14, "bold"))
        title_label.grid(row=current_row, column=0, columnspan=3, pady=(0, 15))
        current_row += 1
        
        # === VIDEO RECORDING CONTROLS ===
        ttk.Label(main_frame, text="VIDEO RECORDING",
                 font=("Arial", 12, "bold")).grid(row=current_row, column=0, columnspan=3, pady=(10, 8))
        current_row += 1
        
        # Record Duration
        ttk.Label(main_frame, text="Record Duration (seconds):",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.record_duration_var = tk.StringVar(value=str(int(self.recorder.record_duration)))
        record_entry = ttk.Entry(main_frame, textvariable=self.record_duration_var, width=12, font=("Arial", 10))
        record_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_record_duration).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Motion Threshold
        ttk.Label(main_frame, text="Motion Threshold (movement):",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.motion_threshold_var = tk.StringVar(value=str(int(self.recorder.motion_threshold)))
        motion_entry = ttk.Entry(main_frame, textvariable=self.motion_threshold_var, width=12, font=("Arial", 10))
        motion_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_motion_threshold).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Stillness Threshold
        ttk.Label(main_frame, text="Stillness Threshold (stop):",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.stillness_threshold_var = tk.StringVar(value=str(int(self.recorder.stillness_threshold)))
        stillness_thresh_entry = ttk.Entry(main_frame, textvariable=self.stillness_threshold_var, width=12, font=("Arial", 10))
        stillness_thresh_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_stillness_threshold).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Stillness Duration
        ttk.Label(main_frame, text="Stillness Trigger (1/10ths sec):",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.stillness_duration_var = tk.StringVar(value=str(int(self.recorder.stillness_duration * 10)))
        stillness_entry = ttk.Entry(main_frame, textvariable=self.stillness_duration_var, width=12, font=("Arial", 10))
        stillness_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Update",
                  command=self.update_stillness_duration).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=15)
        current_row += 1
        
        # === IMU CONTROLS ===
        ttk.Label(main_frame, text="WATCH IMU CONTROLS",
                 font=("Arial", 12, "bold")).grid(row=current_row, column=0, columnspan=3, pady=(0, 8))
        current_row += 1
        
        # Left Watch IP
        ttk.Label(main_frame, text="Left Watch IP:",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.left_watch_ip_var = tk.StringVar(value="192.168.1.101")
        left_ip_entry = ttk.Entry(main_frame, textvariable=self.left_watch_ip_var, width=15, font=("Arial", 10))
        left_ip_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Connect",
                  command=self.connect_left_watch).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Right Watch IP
        ttk.Label(main_frame, text="Right Watch IP:",
                 font=("Arial", 11)).grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.right_watch_ip_var = tk.StringVar(value="192.168.1.102")
        right_ip_entry = ttk.Entry(main_frame, textvariable=self.right_watch_ip_var, width=15, font=("Arial", 10))
        right_ip_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(main_frame, text="Connect",
                  command=self.connect_right_watch).grid(row=current_row, column=2, padx=(10, 0), pady=5)
        current_row += 1
        
        # Watch Discovery
        discovery_frame = ttk.Frame(main_frame)
        discovery_frame.grid(row=current_row, column=0, columnspan=3, pady=10)
        ttk.Button(discovery_frame, text="Discover Watches",
                  command=self.discover_watches).pack(side=tk.LEFT, padx=5)
        ttk.Button(discovery_frame, text="Test Connections",
                  command=self.test_watch_connections).pack(side=tk.LEFT, padx=5)
        current_row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=15)
        current_row += 1
        
        # === STATUS DISPLAYS ===
        ttk.Label(main_frame, text="CURRENT STATUS",
                 font=("Arial", 12, "bold")).grid(row=current_row, column=0, columnspan=3, pady=(0, 8))
        current_row += 1
        
        # Video Status
        self.current_record_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_record_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.current_motion_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_motion_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.current_stillness_thresh_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_stillness_thresh_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.current_stillness_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.current_stillness_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        # IMU Status
        self.imu_status_label = ttk.Label(main_frame, text="", font=("Arial", 10, "bold"))
        self.imu_status_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.watch_status_labels['left'] = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.watch_status_labels['left'].grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.watch_status_labels['right'] = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.watch_status_labels['right'].grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        # Session Info
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=15)
        current_row += 1
        
        ttk.Label(main_frame, text="SESSION INFO",
                 font=("Arial", 12, "bold")).grid(row=current_row, column=0, columnspan=3, pady=(0, 8))
        current_row += 1
        
        self.recordings_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.recordings_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.movement_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.movement_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        self.session_dir_label = ttk.Label(main_frame, text="", font=("Arial", 10))
        self.session_dir_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=3)
        current_row += 1
        
        # Control Buttons
        ttk.Separator(main_frame, orient='horizontal').grid(row=current_row, column=0, columnspan=3,
                                                           sticky=(tk.W, tk.E), pady=10)
        current_row += 1
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row, column=0, columnspan=3, pady=5)
        
        ttk.Button(button_frame, text="Manual Record",
                  command=self.manual_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset Movement",
                  command=self.reset_movement).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="IMU Status",
                  command=self.show_imu_status).pack(side=tk.LEFT, padx=5)
        
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
    
    # Video control methods (same as original)
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
    
    # IMU control methods
    def connect_left_watch(self):
        """Connect to left watch."""
        if not self.recorder.imu_manager:
            tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled")
            return
            
        ip = self.left_watch_ip_var.get().strip()
        if ip:
            success = self.recorder.imu_manager.add_watch("left", ip)
            if success:
                tk.messagebox.showinfo("Success", f"Connected to left watch at {ip}")
            else:
                tk.messagebox.showwarning("Warning", f"Added left watch at {ip} but connection failed")
        else:
            tk.messagebox.showerror("Error", "Please enter a valid IP address")
    
    def connect_right_watch(self):
        """Connect to right watch."""
        if not self.recorder.imu_manager:
            tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled")
            return
            
        ip = self.right_watch_ip_var.get().strip()
        if ip:
            success = self.recorder.imu_manager.add_watch("right", ip)
            if success:
                tk.messagebox.showinfo("Success", f"Connected to right watch at {ip}")
            else:
                tk.messagebox.showwarning("Warning", f"Added right watch at {ip} but connection failed")
        else:
            tk.messagebox.showerror("Error", "Please enter a valid IP address")
    
    def discover_watches(self):
        """Discover watches on the network."""
        if not self.recorder.imu_manager:
            tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled")
            return
            
        print("🔍 Starting watch discovery...")
        # Run discovery in a separate thread to avoid blocking UI
        discovery_thread = threading.Thread(target=self._discover_watches_thread)
        discovery_thread.daemon = True
        discovery_thread.start()
    
    def _discover_watches_thread(self):
        """Discovery thread function."""
        if not self.recorder.imu_manager:
            self.root.after(0, lambda: tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled"))
            return
            
        discovered = self.recorder.imu_manager.discover_watches()
        if discovered:
            # Update UI with discovered watches
            self.root.after(0, lambda: self._handle_discovered_watches(discovered))
        else:
            self.root.after(0, lambda: tk.messagebox.showinfo("Discovery", "No watches found on the network"))
    
    def _handle_discovered_watches(self, discovered):
        """Handle discovered watches in UI thread."""
        message = f"Found {len(discovered)} watches:\n\n"
        for ip, name in discovered:
            message += f"• {name} at {ip}\n"
        message += "\nWould you like to connect to them automatically?"
        
        if tk.messagebox.askyesno("Watches Discovered", message):
            for ip, name in discovered:
                if name.lower() in ['left', 'right']:
                    self.recorder.imu_manager.add_watch(name.lower(), ip)
                else:
                    # Auto-assign based on order
                    watch_name = "left" if len(self.recorder.imu_manager.watches) == 0 else "right"
                    self.recorder.imu_manager.add_watch(watch_name, ip)
    
    def test_watch_connections(self):
        """Test all watch connections with enhanced status."""
        if not self.recorder.imu_manager:
            tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled")
            return
            
        # Test connections using integration guide functionality
        if hasattr(self.recorder.imu_manager, 'controller') and self.recorder.imu_manager.controller.watch_ips:
            # Use controller for testing
            status_data = self.recorder.imu_manager.controller.get_status_all()
            message = f"Enhanced Watch Connection Status (Integration Guide):\n\n"
            message += f"Configured IPs: {len(self.recorder.imu_manager.controller.watch_ips)}\n"
            message += f"Active watches: {len([s for s in status_data.values() if s is not None])}\n\n"
            
            for ip, status in status_data.items():
                if status:
                    state = status.get('recording_state', 'UNKNOWN')
                    samples = status.get('sample_count', 0)
                    conn_icon = "✅" if status.get('server_running', False) else "❌"
                    message += f"{conn_icon} {ip} - State: {state}, Samples: {samples}\n"
                else:
                    message += f"❌ {ip} - No response\n"
        else:
            # Fallback to legacy status
            status = self.recorder.imu_manager.get_connection_status()
            message = f"Watch Connection Status:\n\n"
            message += f"Total watches: {status['total_watches']}\n"
            message += f"Connected: {status['connected_watches']}\n\n"
            
            for name, watch_status in status['watches'].items():
                conn_icon = "✅" if watch_status['connected'] else "❌"
                rec_icon = "🎬" if watch_status.get('recording', False) else "⏸️"
                message += f"{conn_icon} {rec_icon} {name.upper()} ({watch_status['ip']}:{watch_status.get('port', 8080)})\n"
                if watch_status['last_error']:
                    message += f"   Error: {watch_status['last_error'][:50]}...\n"
        
        tk.messagebox.showinfo("Enhanced Connection Test", message)
    
    def show_imu_status(self):
        """Show detailed IMU status."""
        if not self.recorder.imu_manager:
            tk.messagebox.showwarning("IMU Disabled", "IMU functionality is disabled")
            return
            
        self.recorder.imu_manager.print_status()
    
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
        """Update the display labels with enhanced IMU status."""
        if self.root and self.root.winfo_exists():
            # Video status
            self.current_record_label.config(text=f"Record Duration: {int(self.recorder.record_duration)} seconds")
            self.current_motion_label.config(text=f"Motion Threshold (movement): {int(self.recorder.motion_threshold)}")
            self.current_stillness_thresh_label.config(text=f"Stillness Threshold (stop): {int(self.recorder.stillness_threshold)}")
            stillness_tenths = int(self.recorder.stillness_duration * 10)
            self.current_stillness_label.config(text=f"Stillness Trigger: {stillness_tenths} (1/10ths sec) = {self.recorder.stillness_duration:.1f}s")
            
            # Enhanced IMU status
            if self.recorder.imu_manager:
                # Check if using integration guide functionality
                if hasattr(self.recorder.imu_manager, 'controller') and self.recorder.imu_manager.controller.watch_ips:
                    # Enhanced status with integration guide
                    configured_ips = len(self.recorder.imu_manager.controller.watch_ips)
                    active_ports = len(self.recorder.imu_manager.controller.watch_ports)
                    recording_status = "RECORDING" if self.recorder.imu_manager.is_recording else "IDLE"
                    
                    self.imu_status_label.config(
                        text=f"Enhanced IMU: {active_ports}/{configured_ips} watches active - {recording_status}",
                        foreground="green" if active_ports > 0 else "red"
                    )
                    
                    # Update individual watch status with enhanced info
                    watch_names = ["left", "right"]
                    for i, name in enumerate(watch_names):
                        if i < len(self.recorder.imu_manager.controller.watch_ips):
                            ip = self.recorder.imu_manager.controller.watch_ips[i]
                            port = self.recorder.imu_manager.controller.watch_ports.get(ip, "?")
                            
                            # Get detailed status if available
                            status_data = self.recorder.imu_manager.controller.get_status_all()
                            watch_status = status_data.get(ip)
                            
                            if watch_status:
                                state = watch_status.get('recording_state', 'UNKNOWN')
                                samples = watch_status.get('sample_count', 0)
                                conn_icon = "🟢" if watch_status.get('server_running', False) else "🔴"
                                rec_icon = "🎬" if state == "RECORDING" else "⏸️"
                                status_text = f"{conn_icon} {rec_icon} {name.upper()} ({ip}:{port}) - {state} ({samples} samples)"
                            else:
                                status_text = f"🔴 ⏸️ {name.upper()} ({ip}:{port}) - No response"
                        else:
                            status_text = f"🔴 ⏸️ {name.upper()} Watch (not configured)"
                        
                        self.watch_status_labels[name].config(text=status_text)
                else:
                    # Legacy status display
                    imu_status = self.recorder.imu_manager.get_connection_status()
                    self.imu_status_label.config(text=f"Legacy IMU: {imu_status['connected_watches']}/{imu_status['total_watches']} watches connected")
                    
                    for name in ['left', 'right']:
                        if name in imu_status['watches']:
                            watch_info = imu_status['watches'][name]
                            conn_icon = "🟢" if watch_info['connected'] else "🔴"
                            rec_icon = "🎬" if watch_info.get('recording', False) else "⏸️"
                            port = watch_info.get('port', 8080)
                            status_text = f"{conn_icon} {rec_icon} {name.upper()} ({watch_info['ip']}:{port})"
                            if watch_info['last_error']:
                                status_text += f" - Error: {watch_info['last_error'][:30]}..."
                        else:
                            status_text = f"🔴 ⏸️ {name.upper()} Watch (not configured)"
                        
                        self.watch_status_labels[name].config(text=status_text)
            else:
                self.imu_status_label.config(text="IMU: Disabled", foreground="gray")
                for name in ['left', 'right']:
                    self.watch_status_labels[name].config(text=f"🔴 ⏸️ {name.upper()} Watch (IMU disabled)")
            
            # Session info
            self.recordings_label.config(text=f"Session Recordings: {self.recorder.total_recordings}")
            movement_status = "Yes" if self.recorder.has_detected_movement else "No"
            self.movement_label.config(text=f"Movement Detected: {movement_status}")
            self.session_dir_label.config(text=f"Session Dir: {os.path.basename(self.recorder.session_dir)}")
    
    def schedule_update(self):
        """Schedule the next display update."""
        if self.root and self.root.winfo_exists():
            self.update_display()
            self.root.after(2000, self.schedule_update)  # Update every 2 seconds
    
    def process_events(self):
        """Process tkinter events (call this from main loop)."""
        try:
            if self.root and self.root.winfo_exists():
                self.root.update_idletasks()
                return True
        except tk.TclError:
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


class StillnessRecorderWithIMU:
    """
    Enhanced stillness recorder with Watch OS IMU integration.
    
    Uses the complete Python Integration Guide functionality for synchronized
    video and IMU recording with dual Watch OS apps.
    """
    
    def __init__(self,
                 record_duration=10.0,
                 motion_threshold=1000,
                 stillness_threshold=500,
                 stillness_duration=3.0,
                 output_dir="recordings",
                 camera_width=1280,
                 camera_height=720,
                 camera_fps=30,
                 enable_imu=True,
                 watch_ips=None,
                 manual_mode=False):
        """Initialize the enhanced stillness recorder with IMU support."""
        
        # Initialize base recorder properties (same as original)
        self.record_duration = record_duration
        self.motion_threshold = motion_threshold
        self.stillness_threshold = stillness_threshold
        self.stillness_duration = stillness_duration
        self.output_dir = output_dir
        self.manual_mode = manual_mode
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize camera components
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.camera_fps = camera_fps
        self.using_webcam = False
        self.using_color_only = False
        self.webcam = None
        
        self.color_frame_acquisition = ColorOnlyFrameAcquisition(camera_width, camera_height, camera_fps)
        self.motion_detector = MotionDetector(stillness_threshold, stillness_duration)
        
        buffer_duration = record_duration + stillness_duration + 2.0
        self.frame_buffer = CircularFrameBuffer(buffer_duration, camera_fps)
        self.recorder = FrameBufferRecorder(output_dir)
        
        # Application state
        self.running = False
        self.recording_in_progress = False
        self.total_recordings = 0
        self.last_recording_time = None
        
        # Session management
        self.session_start_time = datetime.now()
        self.session_dir = os.path.join(output_dir, f"session_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Movement tracking
        self.has_detected_movement = False
        
        # Manual recording state
        self.manual_recording_active = False
        self.manual_recording_start_time = None
        self.manual_recording_thread = None
        self.stop_manual_recording_flag = False
        
        # UI state
        self.show_motion_mask = False
        self.show_help = False
        self.show_controls = False
        self.controls_window = None
        
        # Display settings
        self.display_width = 2560
        self.display_height = 1440
        
        # Statistics
        self.frame_count = 0
        self.start_time = None
        
        # Enhanced IMU Manager with integration guide functionality
        self.enable_imu = enable_imu
        self.watch_ips = watch_ips or []
        if enable_imu:
            imu_output_dir = os.path.join(self.session_dir, "imu_data")
            self.imu_manager = WatchIMUManager(
                watch_ips=self.watch_ips,
                output_dir=imu_output_dir,
                default_port=8080,
                timeout=5
            )
            print("✅ Enhanced IMU Manager initialized with integration guide functionality")
        else:
            self.imu_manager = None
            print("⚠️  IMU functionality disabled")
    
    def initialize(self):
        """Initialize camera and IMU components."""
        print("Initializing Enhanced Stillness Recorder with IMU...")
        print(f"Record Duration: {self.record_duration}s")
        if self.manual_mode:
            print("Manual Mode: Motion detection DISABLED")
        else:
            print(f"Motion Threshold: {self.motion_threshold}")
            print(f"Stillness Duration: {self.stillness_duration}s")
        print(f"Session Directory: {self.session_dir}")
        print(f"IMU Enabled: {self.enable_imu}")
        
        # Initialize camera (same as original)
        if self.color_frame_acquisition.initialize():
            print("RealSense color-only initialized")
            self.using_color_only = True
            camera_success = True
        else:
            self.webcam = cv2.VideoCapture(0)
            if self.webcam.isOpened():
                self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
                self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
                self.webcam.set(cv2.CAP_PROP_FPS, self.camera_fps)
                self.using_webcam = True
                print("Webcam initialized")
                camera_success = True
            else:
                print("Failed to initialize any camera")
                camera_success = False
        
        # Initialize IMU monitoring and discovery
        if self.enable_imu and self.imu_manager:
            # Discover watches if IPs are provided
            if self.watch_ips:
                print("🔍 Discovering watches...")
                discovered = self.imu_manager.discover_watches()
                if discovered:
                    print(f"✅ Discovered {len(discovered)} watches")
                    # Auto-assign watches if not already configured
                    if not self.imu_manager.watches:
                        watch_names = ["left", "right"]
                        for i, (ip, port) in enumerate(discovered.items()):
                            if i < len(watch_names):
                                self.imu_manager.add_watch(watch_names[i], ip, port)
                else:
                    print("⚠️  No watches discovered, manual configuration required")
            
            self.imu_manager.start_monitoring()
            print("✅ Enhanced IMU monitoring started")
        
        return camera_success
    
    def get_frames(self):
        """Get frames from camera with improved error handling."""
        if self.using_webcam:
            ret, color_image = self.webcam.read()
            if ret:
                return None, None, None, color_image
            else:
                print("DEBUG: Webcam frame read failed")
                return None, None, None, None
        else:
            # Pass recording mode flag to optimize frame acquisition during recording
            recording_mode = self.recording_in_progress or self.manual_recording_active
            depth_frame, color_frame, depth_image, color_image = self.color_frame_acquisition.get_frames(recording_mode=recording_mode)
            
            # Track consecutive RealSense failures
            if color_image is None:
                if not hasattr(self, '_realsense_failure_count'):
                    self._realsense_failure_count = 0
                self._realsense_failure_count += 1
                
                # During recording, be more tolerant of failures - only fallback after 5 minutes
                failure_threshold = 9000 if (self.recording_in_progress or self.manual_recording_active) else 900
                
                # Only consider fallback after many consecutive failures
                if self._realsense_failure_count > failure_threshold and not self.using_webcam:
                    duration_text = "5+ minutes" if failure_threshold == 9000 else "30+ seconds"
                    print(f"⚠️  RealSense has failed for {duration_text}, attempting webcam fallback...")
                    # Stop RealSense first to avoid conflicts
                    self.color_frame_acquisition.stop()
                    
                    self.webcam = cv2.VideoCapture(0)
                    if self.webcam.isOpened():
                        # Set camera properties to match RealSense resolution to avoid size mismatch
                        actual_width = getattr(self.color_frame_acquisition, 'width', self.camera_width)
                        actual_height = getattr(self.color_frame_acquisition, 'height', self.camera_height)
                        
                        self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, actual_width)
                        self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, actual_height)
                        self.webcam.set(cv2.CAP_PROP_FPS, self.camera_fps)
                        
                        # Give camera time to initialize
                        time.sleep(0.1)
                        
                        self.using_webcam = True
                        self.using_color_only = False
                        print(f"✅ Successfully switched to webcam mode ({actual_width}x{actual_height})")
                        
                        # Try to get first frame
                        ret, color_image = self.webcam.read()
                        if ret:
                            # Resize webcam frame to match RealSense resolution if needed
                            if color_image.shape[:2] != (actual_height, actual_width):
                                color_image = cv2.resize(color_image, (actual_width, actual_height))
                            return None, None, None, color_image
                        else:
                            print("⚠️  Initial webcam frame read failed")
                    else:
                        print("❌ Failed to open webcam as fallback")
                
                # Return None to indicate no frame available, but don't switch cameras yet
                return None, None, None, None
            else:
                # Reset failure count on successful frame
                if hasattr(self, '_realsense_failure_count'):
                    if self._realsense_failure_count > 100:  # Only log recovery for significant failures
                        print(f"✅ RealSense recovered after {self._realsense_failure_count} failed attempts")
                    self._realsense_failure_count = 0
                        
            return depth_frame, color_frame, depth_image, color_image
    
    def create_controls_window(self):
        """Create enhanced controls window with IMU support."""
        if self.controls_window is None:
            self.controls_window = ControlsWindowWithIMU(self)
            self.controls_window.create_window()
            if self.controls_window.root:
                self.controls_window.root.lift()
                self.controls_window.root.attributes('-topmost', True)
                self.controls_window.root.after(100, lambda: self.controls_window.root.attributes('-topmost', False))
                self.controls_window.root.update()
    
    def process_frame(self, frame):
        """Process a single frame for motion detection and recording."""
        if frame is None:
            return None, None
            
        # Add frame to circular buffer
        self.frame_buffer.add_frame(frame)
        
        # Detect motion
        motion_value, is_motion, motion_mask = self.motion_detector.detect_motion(frame)
        
        # In manual mode, skip motion detection logic
        stillness_triggered = False
        if not self.manual_mode:
            # Track significant movement to ignore first stillness
            if motion_value > self.motion_threshold:
                self.has_detected_movement = True
            
            # Check for stillness trigger (only after movement has been detected)
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
        """Draw enhanced information overlay with IMU status."""
        h, w = frame.shape[:2]
        
        # Color scheme
        text_color = (255, 255, 255)  # White
        bg_color = (0, 0, 0)  # Black background
        
        # Motion status colors
        if self.manual_mode:
            if self.recording_in_progress or self.manual_recording_active:
                motion_color = (0, 0, 255)  # Red - recording
                status_text = "RECORDING - SPACEBAR TO STOP"
                status_color = (0, 0, 255)
            else:
                motion_color = (0, 255, 0)  # Green - ready
                status_text = "READY - SPACEBAR TO START"
                status_color = (0, 255, 0)
        elif not self.has_detected_movement:
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
        
        # Motion value bar (only show in automatic mode)
        if not self.manual_mode:
            bar_width = 300
            bar_height = 20
            bar_x = (w - bar_width) // 2
            bar_y = 70
            
            # Background bar
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
            
            # Motion level bar
            max_scale = max(self.motion_threshold * 2, 3000)
            motion_ratio = min(motion_value / max_scale, 1.0)
            fill_width = int(bar_width * motion_ratio)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), motion_color, -1)
            
            # Threshold markers
            stillness_x = bar_x + int(bar_width * (self.stillness_threshold / max_scale))
            cv2.line(frame, (stillness_x, bar_y), (stillness_x, bar_y + bar_height), (0, 0, 255), 2)
            
            motion_x = bar_x + int(bar_width * (self.motion_threshold / max_scale))
            cv2.line(frame, (motion_x, bar_y), (motion_x, bar_y + bar_height), (255, 255, 255), 2)
            
            # Motion value text
            cv2.putText(frame, f"Motion: {motion_value:.0f} | Still: {self.stillness_threshold:.0f} | Move: {self.motion_threshold:.0f}",
                       (bar_x, bar_y + bar_height + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        # IMU Status overlay
        if self.enable_imu and self.imu_manager:
            imu_status = self.imu_manager.get_connection_status()
            imu_y = 110
            
            # IMU connection status
            imu_text = f"IMU: {imu_status['connected_watches']}/{imu_status['total_watches']} watches"
            if imu_status['recording']:
                imu_text += " [RECORDING]"
                imu_color = (0, 255, 0)  # Green when recording
            else:
                imu_color = (255, 255, 255)  # White when not recording
            
            cv2.putText(frame, imu_text, (15, imu_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, imu_color, 1)
            
            # Individual watch status
            watch_y = imu_y + 25
            for name, watch_info in imu_status['watches'].items():
                conn_icon = "●" if watch_info['connected'] else "○"
                rec_icon = "REC" if watch_info['recording'] else "---"
                watch_color = (0, 255, 0) if watch_info['connected'] else (128, 128, 128)
                
                watch_text = f"{conn_icon} {name.upper()}: {rec_icon}"
                cv2.putText(frame, watch_text, (15, watch_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, watch_color, 1)
                watch_y += 20
        
        # Recording indicators
        if stillness_triggered:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 255), 10)
            cv2.putText(frame, "RECORDING TRIGGERED!", (w//2 - 200, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 4)
        
        if self.recording_in_progress:
            cv2.circle(frame, (w - 50, 50), 20, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 65, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Session info
        cv2.putText(frame, f"Session: {self.total_recordings} recordings",
                   (15, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
        cv2.putText(frame, f"Record Duration: {self.record_duration:.1f}s",
                   (15, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
        cv2.putText(frame, f"Session: {os.path.basename(self.session_dir)}",
                   (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 1)
    
    def trigger_recording(self, manual=False):
        """Trigger a recording with enhanced synchronized IMU data."""
        if self.recording_in_progress:
            print("Recording already in progress, skipping trigger")
            return
        
        if manual:
            print(f"Manual recording triggered! Starting synchronized recording...")
        else:
            print(f"Stillness detected! Triggering enhanced synchronized recording...")
        
        # Use synchronized recording session if IMU is enabled and configured
        if self.enable_imu and self.imu_manager and self.imu_manager.watch_ips:
            print("🎬 Using synchronized recording session with IMU integration guide functionality")
            
            # Start synchronized recording session in a separate thread
            recording_thread = threading.Thread(target=self._synchronized_recording_session, args=(manual,))
            recording_thread.daemon = True
            recording_thread.start()
        else:
            # Fallback to legacy recording method
            print("🎬 Using legacy recording method")
            
            # Start IMU recording first (legacy method)
            if self.enable_imu and self.imu_manager:
                imu_success = self.imu_manager.start_recording()
                if imu_success:
                    print("✅ IMU recording started (legacy)")
                else:
                    print("⚠️  IMU recording failed to start (legacy)")
            
            # Start video recording in a separate thread
            recording_thread = threading.Thread(target=self._save_recording)
            recording_thread.daemon = True
            recording_thread.start()
    
    def _synchronized_recording_session(self, manual=False):
        """Perform synchronized recording session using integration guide functionality."""
        self.recording_in_progress = True
        
        # Store reference to this thread for manual stopping
        if manual:
            self.manual_recording_thread = threading.current_thread()
            self.stop_manual_recording_flag = False
        
        try:
            if manual:
                # Manual mode: record from current time
                current_time = time.time()
                recording_start_time = current_time
                
                # Generate sync_id first for coordination
                session_timestamp = datetime.fromtimestamp(recording_start_time)
                sync_id = session_timestamp.strftime("%Y%m%d_%H%M%S")
                
                # Start IMU recording (no duration limit - will be stopped manually)
                if self.enable_imu and self.imu_manager:
                    print(f"🎬 Starting manual IMU recording with ID: {sync_id}")
                    # Start IMU recording without duration limit
                    if hasattr(self.imu_manager, 'controller'):
                        self.imu_manager.controller.start_recording_all()
                    else:
                        self.imu_manager.start_recording()
                
                # Record video until user stops (no duration limit in manual mode)
                recording_frames = []
                start_time = time.time()
                frame_errors = 0
                max_frame_errors = 300  # Allow many more frame errors during recording (10 seconds worth)
                
                print(f"🎬 Manual recording started - press SPACEBAR to stop")
                
                while True:
                    # Check if user requested stop
                    if self.stop_manual_recording_flag:
                        print("🛑 Manual recording stopped by user")
                        break
                        
                    # Get current frame
                    depth_frame, color_frame, depth_image, color_image = self.get_frames()
                    if color_image is not None:
                        timestamp = time.time()
                        recording_frames.append((timestamp, color_image))
                        frame_errors = 0  # Reset error count on successful frame
                    else:
                        frame_errors += 1
                        if frame_errors > max_frame_errors:
                            print("⚠️  Too many frame errors, stopping recording")
                            break
                    
                    time.sleep(1.0 / self.camera_fps)  # Maintain frame rate
                
                # Stop IMU recording when user stops
                if self.enable_imu and self.imu_manager:
                    print("🛑 Stopping IMU recording...")
                    # Send stop command to watches
                    if hasattr(self.imu_manager, 'controller'):
                        self.imu_manager.controller.stop_recording_all()
                    else:
                        self.imu_manager.stop_recording()
                    
                    # Wait a moment for IMU to stop
                    time.sleep(0.5)
                    
                    # Retrieve IMU data immediately with sync_id to same directory as video
                    print(f"📥 Retrieving IMU data with sync_id: {sync_id}")
                    self.imu_manager.current_sync_id = sync_id
                    self.imu_manager._retrieve_imu_data(target_dir=self.session_dir)
                
                if not recording_frames:
                    print("⚠️  No frames captured during manual recording (camera issues)")
                    print("🎬 IMU data will still be saved if available")
                    # Still try to save IMU data even if video failed
                    if self.enable_imu and self.imu_manager:
                        print(f"📥 Retrieving IMU data with sync_id: {sync_id}")
                        self.imu_manager.current_sync_id = sync_id
                        self.imu_manager._retrieve_imu_data(target_dir=self.session_dir)
                    return
                
                # Calculate actual recording duration
                actual_duration = recording_frames[-1][0] - recording_frames[0][0] if recording_frames else 0
                print(f"📊 Manual recording duration: {actual_duration:.2f} seconds")
                
                filename = f"manual_{sync_id}.mp4"
                
            else:
                # Automatic mode: use existing logic
                all_frames = self.frame_buffer.get_all_frames()
                
                if not all_frames:
                    print("No frames available for recording")
                    return
                
                # Calculate recording window (same logic as original)
                current_time = time.time()
                motion_stats = self.motion_detector.get_motion_stats()
                stillness_start_time = current_time - motion_stats['stillness_duration']
                recording_start_time = stillness_start_time - self.record_duration
                recording_end_time = stillness_start_time
                
                # Filter frames for the recording window
                recording_frames = []
                for timestamp, frame in all_frames:
                    if recording_start_time <= timestamp <= recording_end_time:
                        recording_frames.append((timestamp, frame))
                
                if not recording_frames:
                    print("No frames found in the recording window")
                    return
                
                # Generate synchronized filename
                clip_start_time = datetime.fromtimestamp(recording_frames[0][0])
                sync_id = clip_start_time.strftime("%Y%m%d_%H%M%S")
                filename = f"auto_{sync_id}.mp4"
            
            # Save video (IMU already handled above for manual mode)
            session_recorder = FrameBufferRecorder(self.session_dir)
            output_path = session_recorder.save_frames_to_video(recording_frames, filename, fps=30)
            
            # For automatic mode, start IMU recording with duration
            if not manual and self.enable_imu and self.imu_manager:
                print(f"🎬 Starting synchronized IMU recording session ({self.record_duration}s)")
                imu_success = self.imu_manager.synchronized_recording_session(duration=self.record_duration, sync_id=sync_id)
            else:
                imu_success = True  # Already handled for manual mode
            
            # Update recording count and report results
            if output_path or imu_success:
                self.total_recordings += 1
                self.last_recording_time = time.time()
                duration = recording_frames[-1][0] - recording_frames[0][0] if recording_frames else 0
                mode_text = "Manual" if manual else "Automatic"
                print(f"🎬 {mode_text} recording completed!")
                
                if output_path:
                    print(f"📹 Video saved: {output_path}")
                    print(f"📊 Recorded {len(recording_frames)} frames ({duration:.2f}s)")
                else:
                    print(f"⚠️  Video recording failed (camera issues)")
                
                if imu_success:
                    print(f"✅ IMU data synchronized and saved")
                else:
                    print(f"⚠️  IMU data had issues")
                    
                print(f"📊 Total recordings this session: {self.total_recordings}")
            else:
                print("❌ Both video and IMU recording failed")
                
        except Exception as e:
            print(f"❌ Error during synchronized recording: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.recording_in_progress = False
            self.manual_recording_active = False
            self.manual_recording_thread = None
            self.stop_manual_recording_flag = False
            
            # Reset for next recording
            print("✅ Ready for next recording")
    
    def _save_recording(self):
        """Save the recording with synchronized IMU data."""
        self.recording_in_progress = True
        
        try:
            # Get video frames
            all_frames = self.frame_buffer.get_all_frames()
            
            if not all_frames:
                print("No frames available for recording")
                return
            
            # Calculate recording window (same logic as original)
            current_time = time.time()
            motion_stats = self.motion_detector.get_motion_stats()
            stillness_start_time = current_time - motion_stats['stillness_duration']
            recording_start_time = stillness_start_time - self.record_duration
            recording_end_time = stillness_start_time
            
            # Filter frames
            recording_frames = []
            for timestamp, frame in all_frames:
                if recording_start_time <= timestamp <= recording_end_time:
                    recording_frames.append((timestamp, frame))
            
            if not recording_frames:
                print("No frames found in the recording window")
                return
            
            # Generate filename
            clip_start_time = datetime.fromtimestamp(recording_frames[0][0])
            clip_timestamp = clip_start_time.strftime("%H%M%S")
            filename = f"clip_{clip_timestamp}.mp4"
            
            # Save video
            session_recorder = FrameBufferRecorder(self.session_dir)
            output_path = session_recorder.save_frames_to_video(recording_frames, filename, fps=30)
            
            if output_path:
                self.total_recordings += 1
                self.last_recording_time = time.time()
                duration = recording_frames[-1][0] - recording_frames[0][0]
                print(f"🎬 Video saved: {output_path}")
                print(f"📊 Recorded {len(recording_frames)} frames ({duration:.2f}s)")
                
                # Stop IMU recording after video is saved
                if self.enable_imu and self.imu_manager:
                    # Give IMU a moment to record the full duration
                    time.sleep(1.0)
                    imu_success = self.imu_manager.stop_recording()
                    if imu_success:
                        print("✅ IMU recording stopped and data retrieved")
                    else:
                        print("⚠️  IMU recording stop failed")
                
                print(f"📊 Total recordings this session: {self.total_recordings}")
            else:
                print("❌ Failed to save video recording")
                
        except Exception as e:
            print(f"❌ Error during recording: {e}")
        finally:
            self.recording_in_progress = False
    
    def handle_key_press(self, key):
        """Handle keyboard input with manual mode support."""
        if key == ord('q'):
            return False
        elif key == ord('h'):
            self.show_help = not self.show_help
        elif key == ord('m') and not self.manual_mode:
            self.show_motion_mask = not self.show_motion_mask
        elif key == ord('r') or key == 32:  # 'r' or spacebar
            if self.manual_mode:
                if not self.recording_in_progress and not self.manual_recording_active:
                    print("🎬 Starting manual recording...")
                    self.manual_recording_active = True
                    self.manual_recording_start_time = time.time()
                    self.trigger_recording(manual=True)
                elif self.recording_in_progress or self.manual_recording_active:
                    print("🛑 Stopping manual recording...")
                    self.stop_manual_recording()
            else:
                print("🎬 Manual recording trigger")
                self.trigger_recording()
        elif key == ord('c') and not self.manual_mode:
            print("🔄 Resetting movement detection")
            self.motion_detector.reset_stillness()
            self.has_detected_movement = False
        elif key == ord('i'):
            # IMU status toggle
            if self.enable_imu and self.imu_manager:
                self.imu_manager.print_status()
        
        return True
    
    def stop_manual_recording(self):
        """Stop manual recording."""
        if not self.manual_recording_active and not self.recording_in_progress:
            print("⚠️  No manual recording in progress to stop")
            return
        
        print("🛑 Stopping manual recording...")
        self.stop_manual_recording_flag = True
        
        # Reset manual recording state immediately for UI responsiveness
        self.manual_recording_active = False
        
        # If there's an active recording thread, let it know to stop
        if hasattr(self, 'manual_recording_thread') and self.manual_recording_thread:
            # The recording thread will check the flag and stop
            pass
    
    def run(self):
        """Main application loop with IMU integration."""
        if not self.initialize():
            return False
        
        print("\nEnhanced Stillness Recorder with IMU Started!")
        if self.manual_mode:
            print("MANUAL MODE: Press SPACEBAR to start/stop recordings")
            print("Video and IMU data will be recorded with synchronized filenames")
        else:
            print("The application will automatically record video and IMU data when stillness is detected.")
        print("Press 'h' for help, 'i' for IMU status, 'q' to quit")
        print("-" * 60)
        
        # Create main video window
        cv2.namedWindow('Stillness Recorder with IMU', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Stillness Recorder with IMU', self.display_width, self.display_height)
        
        # Create controls window
        self.create_controls_window()
        
        self.running = True
        self.start_time = time.time()
        
        try:
            frame_counter = 0
            while self.running:
                # Get frames from camera
                depth_frame, color_frame, depth_image, color_image = self.get_frames()
                
                if color_image is not None:
                    self.frame_count += 1
                    frame_counter += 1
                    
                    # Process frame
                    display_frame, motion_info = self.process_frame(color_image)
                    
                    if display_frame is not None:
                        # Resize if needed
                        current_height, current_width = display_frame.shape[:2]
                        if abs(current_width - self.display_width) > 50 or abs(current_height - self.display_height) > 50:
                            display_frame = cv2.resize(display_frame, (self.display_width, self.display_height))
                        
                        # Show main display
                        cv2.imshow('Stillness Recorder with IMU', display_frame)
                        
                        # Show motion mask if enabled
                        if self.show_motion_mask and motion_info and motion_info['motion_mask'] is not None:
                            cv2.imshow('Motion Mask', motion_info['motion_mask'])
                        elif not self.show_motion_mask:
                            try:
                                cv2.destroyWindow('Motion Mask')
                            except cv2.error:
                                pass
                
                # Process tkinter events
                if self.controls_window:
                    try:
                        if self.controls_window.root and self.controls_window.root.winfo_exists():
                            if frame_counter % 5 == 0:
                                self.controls_window.root.update_idletasks()
                            if frame_counter % 30 == 0:
                                self.controls_window.root.update()
                        else:
                            self.controls_window = None
                    except tk.TclError:
                        self.controls_window = None
                    except Exception as e:
                        print(f"Warning: Tkinter error: {e}")
                        self.controls_window = None
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key != 255:
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
        """Clean up resources including IMU manager."""
        print("Cleaning up Enhanced Stillness Recorder...")
        self.running = False
        
        # Clean up IMU manager
        if self.enable_imu and self.imu_manager:
            self.imu_manager.cleanup()
        
        # Clean up tkinter controls window
        if self.controls_window:
            try:
                self.controls_window.destroy()
            except:
                pass
            self.controls_window = None
        
        # Clean up other resources (same as original)
        if hasattr(self, 'frame_buffer'):
            self.frame_buffer.clear()
        
        if hasattr(self, 'motion_detector'):
            self.motion_detector.reset_stillness()
        
        # Clean up camera resources
        if self.using_webcam and self.webcam:
            self.webcam.release()
            self.webcam = None
        elif self.using_color_only:
            self.color_frame_acquisition.stop()
        else:
            self.color_frame_acquisition.stop()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        # Print final statistics
        if self.start_time:
            runtime = time.time() - self.start_time
            fps = self.frame_count / runtime if runtime > 0 else 0
            print(f"\nSession Statistics:")
            print(f"Runtime: {runtime:.1f} seconds")
            print(f"Frames processed: {self.frame_count}")
            print(f"Average FPS: {fps:.1f}")
            print(f"Total recordings: {self.total_recordings}")
            print(f"Output directory: {self.session_dir}")


def main():
    """Main entry point with enhanced command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Stillness Recorder with Watch OS IMU integration")
    
    # Video recording arguments
    parser.add_argument('--record-duration', type=float, default=10.0,
                       help='Duration in seconds to record when stillness is detected (default: 10.0)')
    parser.add_argument('--motion-threshold', type=float, default=1000,
                       help='Motion threshold for detecting significant movement (default: 1000)')
    parser.add_argument('--stillness-threshold', type=float, default=500,
                       help='Stillness threshold for detecting when motion stops (default: 500)')
    parser.add_argument('--stillness-duration', type=float, default=3.0,
                       help='Duration of stillness required to trigger recording (default: 3.0)')
    parser.add_argument('--output-dir', type=str, default='recordings',
                       help='Directory to save recorded videos and IMU data (default: recordings)')
    parser.add_argument('--camera-width', type=int, default=640,
                       help='Camera frame width (default: 640)')
    parser.add_argument('--camera-height', type=int, default=480,
                       help='Camera frame height (default: 480)')
    parser.add_argument('--camera-fps', type=int, default=30,
                       help='Camera frames per second (default: 30)')
    
    # IMU arguments
    parser.add_argument('--disable-imu', action='store_true',
                       help='Disable IMU functionality')
    parser.add_argument('--left-watch-ip', type=str, default=None,
                       help='IP address of left watch (e.g., 192.168.1.101)')
    parser.add_argument('--right-watch-ip', type=str, default=None,
                       help='IP address of right watch (e.g., 192.168.1.102)')
    parser.add_argument('--discover-watches', action='store_true',
                       help='Automatically discover watches on network')
    
    args = parser.parse_args()
    
    # Create and configure the recorder
    recorder = StillnessRecorderWithIMU(
        record_duration=args.record_duration,
        motion_threshold=args.motion_threshold,
        stillness_threshold=args.stillness_threshold,
        stillness_duration=args.stillness_duration,
        output_dir=args.output_dir,
        camera_width=args.camera_width,
        camera_height=args.camera_height,
        camera_fps=args.camera_fps,
        enable_imu=not args.disable_imu
    )
    
    # Configure watches if specified
    if not args.disable_imu and recorder.imu_manager:
        if args.discover_watches:
            print("🔍 Discovering watches on network...")
            discovered = recorder.imu_manager.discover_watches()
            for ip, name in discovered:
                if name.lower() in ['left', 'right']:
                    recorder.imu_manager.add_watch(name.lower(), ip)
                else:
                    # Auto-assign based on order
                    watch_name = "left" if len(recorder.imu_manager.watches) == 0 else "right"
                    recorder.imu_manager.add_watch(watch_name, ip)
        else:
            if args.left_watch_ip:
                recorder.imu_manager.add_watch("left", args.left_watch_ip)
            if args.right_watch_ip:
                recorder.imu_manager.add_watch("right", args.right_watch_ip)
    
    success = recorder.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())