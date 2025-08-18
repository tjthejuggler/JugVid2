#!/usr/bin/env python3
"""
Test script for the new video feed system in juggling_tracker.

This script tests the dynamic layout system and latency monitoring.
"""

import sys
import os
import time
import numpy as np
import cv2
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap, QImage

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apps.juggling_tracker.ui.video_feed_manager import VideoFeedManager

class TestWindow(QMainWindow):
    """Test window for the video feed system."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Feed System Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create video feed manager
        self.video_feed_manager = VideoFeedManager()
        self.video_feed_manager.feeds_changed.connect(self.on_feeds_changed)
        layout.addWidget(self.video_feed_manager)
        
        # Create control buttons
        controls_layout = QHBoxLayout()
        
        self.add_feed_btn = QPushButton("Add Feed")
        self.add_feed_btn.clicked.connect(self.add_test_feed)
        controls_layout.addWidget(self.add_feed_btn)
        
        self.remove_feed_btn = QPushButton("Remove Feed")
        self.remove_feed_btn.clicked.connect(self.remove_test_feed)
        controls_layout.addWidget(self.remove_feed_btn)
        
        self.clear_feeds_btn = QPushButton("Clear All")
        self.clear_feeds_btn.clicked.connect(self.clear_all_feeds)
        controls_layout.addWidget(self.clear_feeds_btn)
        
        self.demo_btn = QPushButton("Demo Configurations")
        self.demo_btn.clicked.connect(self.demo_configurations)
        controls_layout.addWidget(self.demo_btn)
        
        layout.addLayout(controls_layout)
        
        # Status label
        self.status_label = QLabel("Ready - No feeds active")
        layout.addWidget(self.status_label)
        
        # Timer for generating test frames
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.update_test_frames)
        self.frame_timer.start(33)  # ~30 FPS
        
        self.frame_counter = 0
        
    def add_test_feed(self):
        """Add a test feed with generated content."""
        feed_count = self.video_feed_manager.get_feed_count()
        feed_names = ["Main Camera", "Depth View", "Mask View", "Tracking View", "Debug View", "Analysis View"]
        
        if feed_count < 6:
            name = feed_names[feed_count] if feed_count < len(feed_names) else f"Feed {feed_count + 1}"
            feed_id = self.video_feed_manager.add_feed(name)
            print(f"Added feed: {feed_id}")
        else:
            print("Maximum of 6 feeds supported")
    
    def remove_test_feed(self):
        """Remove the last feed."""
        feed_ids = self.video_feed_manager.get_feed_ids()
        if feed_ids:
            removed = self.video_feed_manager.remove_feed(feed_ids[-1])
            if removed:
                print(f"Removed feed: {feed_ids[-1]}")
        else:
            print("No feeds to remove")
    
    def clear_all_feeds(self):
        """Clear all feeds."""
        self.video_feed_manager.clear_all_feeds()
        print("Cleared all feeds")
    
    def demo_configurations(self):
        """Demo different feed configurations."""
        print("Starting demo...")
        self.clear_all_feeds()
        
        # Test 1 feed
        QTimer.singleShot(500, lambda: self._demo_step(1))
        # Test 3 feeds (single row)
        QTimer.singleShot(2000, lambda: self._demo_step(3))
        # Test 6 feeds (two rows)
        QTimer.singleShot(4000, lambda: self._demo_step(6))
        # Test 4 feeds
        QTimer.singleShot(6000, lambda: self._demo_step(4))
        # Test 2 feeds
        QTimer.singleShot(8000, lambda: self._demo_step(2))
    
    def _demo_step(self, target_count):
        """Demo step to set specific number of feeds."""
        self.clear_all_feeds()
        for i in range(target_count):
            self.add_test_feed()
        print(f"Demo: {target_count} feeds")
    
    def update_test_frames(self):
        """Generate and update test frames for all feeds."""
        self.frame_counter += 1
        
        feed_ids = self.video_feed_manager.get_feed_ids()
        for i, feed_id in enumerate(feed_ids):
            # Generate a test image
            test_image = self.generate_test_image(i, self.frame_counter)
            
            # Convert to QPixmap
            pixmap = self.numpy_to_pixmap(test_image)
            
            # Update the feed
            self.video_feed_manager.update_feed(feed_id, pixmap)
    
    def generate_test_image(self, feed_index, frame_counter):
        """Generate a test image for a specific feed."""
        # Create a 320x240 test image
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # Different colors for different feeds
        colors = [
            (255, 100, 100),  # Red
            (100, 255, 100),  # Green
            (100, 100, 255),  # Blue
            (255, 255, 100),  # Yellow
            (255, 100, 255),  # Magenta
            (100, 255, 255),  # Cyan
        ]
        
        color = colors[feed_index % len(colors)]
        img[:] = color
        
        # Add some animation
        center_x = 160 + int(50 * np.sin(frame_counter * 0.1 + feed_index))
        center_y = 120 + int(30 * np.cos(frame_counter * 0.1 + feed_index))
        
        # Draw a moving circle
        cv2.circle(img, (center_x, center_y), 20, (255, 255, 255), -1)
        
        # Add text
        cv2.putText(img, f"Feed {feed_index + 1}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Frame {frame_counter}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return img
    
    def numpy_to_pixmap(self, img):
        """Convert numpy array to QPixmap."""
        height, width, channel = img.shape
        bytes_per_line = 3 * width
        q_image = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        return QPixmap.fromImage(q_image)
    
    def on_feeds_changed(self, feed_count):
        """Handle feed count changes."""
        latencies = self.video_feed_manager.get_feed_latencies()
        fps_data = self.video_feed_manager.get_feed_fps()
        
        status_parts = [f"Feeds: {feed_count}"]
        
        if latencies:
            avg_latency = sum(latencies.values()) / len(latencies)
            avg_fps = sum(fps_data.values()) / len(fps_data) if fps_data else 0
            status_parts.append(f"Avg Latency: {avg_latency:.1f}ms")
            status_parts.append(f"Avg FPS: {avg_fps:.1f}")
        
        self.status_label.setText(" | ".join(status_parts))
        
        # Adjust window size based on feed count
        if feed_count <= 3:
            # Single row layout
            min_width = max(800, feed_count * 320 + 100)
            min_height = 600
        else:
            # Two row layout
            min_width = max(800, 3 * 320 + 100)
            min_height = 700
            
        self.setMinimumSize(min_width, min_height)


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("Video Feed System Test")
    print("======================")
    print("Use the buttons to:")
    print("- Add Feed: Add a new video feed (max 6)")
    print("- Remove Feed: Remove the last feed")
    print("- Clear All: Remove all feeds")
    print("- Demo Configurations: Automatically test different layouts")
    print()
    print("Layout Rules:")
    print("- 1-3 feeds: Single row")
    print("- 4-6 feeds: Two rows (max 3 per row)")
    print("- Each feed shows latency and FPS information")
    print()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()