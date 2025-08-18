#!/usr/bin/env python3
"""
Test script for IMU Feed System

This script tests the IMU feed visualization system by creating mock IMU data
and displaying it in the video feed manager. It tests:

1. IMU feed creation and display
2. Real-time data updates
3. Multiple IMU feeds (left and right watch)
4. >4 feeds layout system
5. Latency monitoring
6. FPS calculation

Usage:
    python test_imu_feeds.py
"""

import sys
import os
import time
import math
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from juggling_tracker.ui.video_feed_manager import VideoFeedManager


class IMUFeedTestWindow(QMainWindow):
    """Test window for IMU feed system."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMU Feed System Test")
        self.setMinimumSize(1400, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create control buttons
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start IMU Simulation")
        self.start_button.clicked.connect(self.start_simulation)
        controls_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.clicked.connect(self.stop_simulation)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        self.add_video_button = QPushButton("Add Video Feeds")
        self.add_video_button.clicked.connect(self.add_video_feeds)
        controls_layout.addWidget(self.add_video_button)
        
        self.clear_button = QPushButton("Clear All Feeds")
        self.clear_button.clicked.connect(self.clear_feeds)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Create video feed manager
        self.video_feed_manager = VideoFeedManager()
        self.video_feed_manager.feeds_changed.connect(self.on_feeds_changed)
        layout.addWidget(self.video_feed_manager)
        
        # Simulation state
        self.simulation_running = False
        self.simulation_time = 0.0
        
        # Create timer for IMU data updates
        self.imu_timer = QTimer()
        self.imu_timer.timeout.connect(self.update_imu_data)
        
        print("IMU Feed Test Window initialized")
        print("Click 'Start IMU Simulation' to begin testing")
    
    def start_simulation(self):
        """Start the IMU data simulation."""
        print("Starting IMU simulation...")
        
        # Create IMU feeds for left and right watches
        self.left_feed_id = self.video_feed_manager.add_imu_feed("Left Watch IMU", "imu_left", "left")
        self.right_feed_id = self.video_feed_manager.add_imu_feed("Right Watch IMU", "imu_right", "right")
        
        print(f"Created IMU feeds: {self.left_feed_id}, {self.right_feed_id}")
        
        # Start simulation
        self.simulation_running = True
        self.simulation_time = 0.0
        self.imu_timer.start(33)  # ~30 FPS
        
        # Update button states
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        print("IMU simulation started")
    
    def stop_simulation(self):
        """Stop the IMU data simulation."""
        print("Stopping IMU simulation...")
        
        self.simulation_running = False
        self.imu_timer.stop()
        
        # Update button states
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        print("IMU simulation stopped")
    
    def update_imu_data(self):
        """Update IMU feeds with simulated data."""
        if not self.simulation_running:
            return
        
        current_time = time.time()
        self.simulation_time += 0.033  # 33ms increment
        
        # Generate realistic IMU data patterns
        # Left watch - simulate juggling motion
        left_accel_x = 2.0 * math.sin(self.simulation_time * 2.0) + np.random.normal(0, 0.1)
        left_accel_y = 9.81 + 3.0 * math.cos(self.simulation_time * 1.5) + np.random.normal(0, 0.2)
        left_accel_z = 1.0 * math.sin(self.simulation_time * 3.0) + np.random.normal(0, 0.1)
        
        left_gyro_x = 0.5 * math.cos(self.simulation_time * 2.5) + np.random.normal(0, 0.05)
        left_gyro_y = 0.8 * math.sin(self.simulation_time * 1.8) + np.random.normal(0, 0.05)
        left_gyro_z = 0.3 * math.cos(self.simulation_time * 3.2) + np.random.normal(0, 0.03)
        
        # Right watch - different pattern
        right_accel_x = 1.5 * math.cos(self.simulation_time * 1.8 + 0.5) + np.random.normal(0, 0.1)
        right_accel_y = 9.81 + 2.5 * math.sin(self.simulation_time * 1.3 + 0.3) + np.random.normal(0, 0.2)
        right_accel_z = 0.8 * math.cos(self.simulation_time * 2.8 + 0.7) + np.random.normal(0, 0.1)
        
        right_gyro_x = 0.4 * math.sin(self.simulation_time * 2.2 + 0.4) + np.random.normal(0, 0.05)
        right_gyro_y = 0.6 * math.cos(self.simulation_time * 1.6 + 0.6) + np.random.normal(0, 0.05)
        right_gyro_z = 0.2 * math.sin(self.simulation_time * 3.5 + 0.8) + np.random.normal(0, 0.03)
        
        # Create IMU data dictionaries
        left_imu_data = {
            'timestamp': current_time,
            'accel_x': left_accel_x,
            'accel_y': left_accel_y,
            'accel_z': left_accel_z,
            'gyro_x': left_gyro_x,
            'gyro_y': left_gyro_y,
            'gyro_z': left_gyro_z,
            'watch_name': 'left'
        }
        
        right_imu_data = {
            'timestamp': current_time,
            'accel_x': right_accel_x,
            'accel_y': right_accel_y,
            'accel_z': right_accel_z,
            'gyro_x': right_gyro_x,
            'gyro_y': right_gyro_y,
            'gyro_z': right_gyro_z,
            'watch_name': 'right'
        }
        
        # Update the feeds
        self.video_feed_manager.update_imu_feed(self.left_feed_id, left_imu_data)
        self.video_feed_manager.update_imu_feed(self.right_feed_id, right_imu_data)
    
    def add_video_feeds(self):
        """Add some video feeds to test >4 feeds layout."""
        print("Adding video feeds to test >4 feeds layout...")
        
        # Add several video feeds to test the layout system
        video_feeds = [
            ("Main Camera", "main_cam"),
            ("Depth View", "depth"),
            ("Mask View", "mask"),
            ("Tracking View", "tracking")
        ]
        
        for name, feed_id in video_feeds:
            self.video_feed_manager.add_feed(name, feed_id, "video")
            print(f"Added video feed: {name}")
        
        print(f"Total feeds: {self.video_feed_manager.get_feed_count()}")
    
    def clear_feeds(self):
        """Clear all feeds."""
        print("Clearing all feeds...")
        self.video_feed_manager.clear_all_feeds()
        
        # Stop simulation if running
        if self.simulation_running:
            self.stop_simulation()
    
    def on_feeds_changed(self, feed_count):
        """Handle feed count changes."""
        print(f"Feed count changed to: {feed_count}")
        
        # Get feed type breakdown
        imu_feeds = self.video_feed_manager.get_imu_feeds()
        video_feeds = self.video_feed_manager.get_video_feeds()
        
        print(f"  IMU feeds: {len(imu_feeds)}")
        print(f"  Video feeds: {len(video_feeds)}")
        
        # Test latency monitoring
        if imu_feeds:
            latencies = {}
            fps_data = {}
            
            for feed_id in imu_feeds:
                if feed_id in self.video_feed_manager.feeds:
                    latencies[feed_id] = self.video_feed_manager.feeds[feed_id].get_latency()
                    fps_data[feed_id] = self.video_feed_manager.feeds[feed_id].get_fps()
            
            print(f"  IMU feed latencies: {latencies}")
            print(f"  IMU feed FPS: {fps_data}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.simulation_running:
            self.stop_simulation()
        event.accept()


def main():
    """Main function to run the test."""
    print("Starting IMU Feed System Test")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    # Create and show the test window
    window = IMUFeedTestWindow()
    window.show()
    
    print("\nTest Instructions:")
    print("1. Click 'Start IMU Simulation' to create IMU feeds with live data")
    print("2. Click 'Add Video Feeds' to test >4 feeds layout")
    print("3. Observe the real-time graphs and layout changes")
    print("4. Check FPS and latency monitoring in console output")
    print("5. Use 'Clear All Feeds' to reset")
    print("\nFeatures to test:")
    print("- Real-time IMU data visualization")
    print("- Color-coded axes (X=red, Y=green, Z=blue)")
    print("- Automatic scaling")
    print("- Multiple watch support")
    print("- Dynamic layout (1-4 feeds single row, 5+ feeds two rows)")
    print("- FPS and latency monitoring")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()