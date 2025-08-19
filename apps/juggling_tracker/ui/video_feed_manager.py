#!/usr/bin/env python3
import time
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

# Import the IMU feed widget and 3D ball tracker widget
from .imu_feed_widget import IMUFeedWidget
from .ball_3d_feed_widget import Ball3DFeedWidget

class VideoFeedWidget(QFrame):
    """
    Individual video feed widget with latency monitoring.
    """
    
    def __init__(self, feed_id, feed_name="Feed", parent=None):
        super().__init__(parent)
        self.feed_id = feed_id
        self.feed_name = feed_name
        self.last_update_time = 0
        self.frame_count = 0
        self.fps = 0.0
        self.latency_ms = 0.0
        
        self.setup_ui()
        
        # Timer for FPS calculation
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the UI for this feed widget."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setStyleSheet("""
            VideoFeedWidget {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #000;
            }
            VideoFeedWidget:hover {
                border-color: #888;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Video display area
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(160, 120)  # Minimum size for readability
        self.video_label.setStyleSheet("background-color: #000000; border: none;")
        self.video_label.setScaledContents(True)
        layout.addWidget(self.video_label, 1)  # Give it most of the space
        
        # Info overlay
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setMaximumHeight(30)
        self.info_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            font-size: 10px;
            padding: 2px;
            border: none;
        """)
        layout.addWidget(self.info_label)
        
        self.update_info_display()
        
    def update_frame(self, pixmap):
        """Update the video frame and calculate latency."""
        current_time = time.time()
        
        if pixmap and not pixmap.isNull():
            self.video_label.setPixmap(pixmap)
            
            # Calculate latency (time since last frame)
            if self.last_update_time > 0:
                self.latency_ms = (current_time - self.last_update_time) * 1000
            
            self.last_update_time = current_time
            self.frame_count += 1
            
        self.update_info_display()
        
    def update_fps(self):
        """Update FPS calculation."""
        if self.frame_count > 0:
            elapsed = time.time() - (self.last_update_time - (self.frame_count - 1) * (self.latency_ms / 1000))
            if elapsed > 0:
                self.fps = self.frame_count / elapsed
        
        # Reset counters periodically to keep FPS current
        if self.frame_count > 30:
            self.frame_count = 0
            
        self.update_info_display()
        
    def update_info_display(self):
        """Update the information display."""
        info_text = f"{self.feed_name} | FPS: {self.fps:.1f} | Latency: {self.latency_ms:.1f}ms"
        self.info_label.setText(info_text)
        
    def set_feed_name(self, name):
        """Set the feed name."""
        self.feed_name = name
        self.update_info_display()
        
    def get_latency(self):
        """Get current latency in milliseconds."""
        return self.latency_ms
        
    def get_fps(self):
        """Get current FPS."""
        return self.fps


class VideoFeedManager(QWidget):
    """
    Manages multiple video and IMU feeds with dynamic layout.
    
    Layout rules:
    - 1-4 feeds: Single row
    - 5+ feeds: Two rows (automatically calculated)
    - Automatically pushes other UI elements down
    - Supports both video feeds (VideoFeedWidget) and IMU feeds (IMUFeedWidget)
    """
    
    feeds_changed = pyqtSignal(int)  # Signal emitted when number of feeds changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.feeds = {}  # feed_id -> VideoFeedWidget or IMUFeedWidget
        self.feed_types = {}  # feed_id -> 'video' or 'imu'
        self.feed_counter = 0
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI layout."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        
        # Container for video feeds
        self.feeds_container = QWidget()
        self.feeds_layout = QGridLayout(self.feeds_container)
        self.feeds_layout.setContentsMargins(5, 5, 5, 5)
        self.feeds_layout.setSpacing(5)
        
        self.main_layout.addWidget(self.feeds_container)
        
        # Initially hide the container
        self.feeds_container.setVisible(False)
        
    def add_feed(self, feed_name="Feed", feed_id=None, feed_type="video"):
        """
        Add a new video, IMU, or 3D ball tracker feed.
        
        Args:
            feed_name (str): Display name for the feed
            feed_id (str, optional): Unique ID for the feed. If None, auto-generated.
            feed_type (str): Type of feed - 'video', 'imu', or 'ball_3d'
            
        Returns:
            str: The feed ID
        """
        if feed_id is None:
            feed_id = f"feed_{self.feed_counter}"
            self.feed_counter += 1
            
        if feed_id in self.feeds:
            print(f"Warning: Feed {feed_id} already exists")
            return feed_id
            
        # Create appropriate feed widget based on type
        if feed_type == "imu":
            # Extract watch name from feed_name if possible
            watch_name = "unknown"
            if "left" in feed_name.lower():
                watch_name = "left"
            elif "right" in feed_name.lower():
                watch_name = "right"
            elif "watch" in feed_name.lower():
                # Try to extract watch identifier
                parts = feed_name.lower().split()
                for part in parts:
                    if "watch" in part:
                        watch_name = part.replace("watch", "").strip("_-")
                        break
            
            feed_widget = IMUFeedWidget(feed_id, feed_name, watch_name, self)
        elif feed_type == "ball_3d":
            feed_widget = Ball3DFeedWidget(feed_id, feed_name, self)
        else:
            feed_widget = VideoFeedWidget(feed_id, feed_name, self)
        
        self.feeds[feed_id] = feed_widget
        self.feed_types[feed_id] = feed_type
        
        # Update layout
        self._update_layout()
        
        # Show container if this is the first feed
        if len(self.feeds) == 1:
            self.feeds_container.setVisible(True)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Added {feed_type} feed: {feed_id} ({feed_name})")
        return feed_id
    
    def add_imu_feed(self, feed_name="IMU Feed", feed_id=None, watch_name="unknown"):
        """
        Convenience method to add an IMU feed.
        
        Args:
            feed_name (str): Display name for the feed
            feed_id (str, optional): Unique ID for the feed. If None, auto-generated.
            watch_name (str): Name of the watch (left, right, etc.)
            
        Returns:
            str: The feed ID
        """
        if feed_id is None:
            feed_id = f"imu_{watch_name}_{self.feed_counter}"
            self.feed_counter += 1
            
        if feed_id in self.feeds:
            print(f"Warning: IMU Feed {feed_id} already exists")
            return feed_id
            
        # Create IMU feed widget
        feed_widget = IMUFeedWidget(feed_id, feed_name, watch_name, self)
        self.feeds[feed_id] = feed_widget
        self.feed_types[feed_id] = "imu"
        
        # Update layout
        self._update_layout()
        
        # Show container if this is the first feed
        if len(self.feeds) == 1:
            self.feeds_container.setVisible(True)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Added IMU feed: {feed_id} ({feed_name}) for {watch_name} watch")
        return feed_id
        
    def remove_feed(self, feed_id):
        """
        Remove a video feed.
        
        Args:
            feed_id (str): ID of the feed to remove
            
        Returns:
            bool: True if feed was removed, False if not found
        """
        if feed_id not in self.feeds:
            print(f"Warning: Feed {feed_id} not found")
            return False
            
        # Remove widget
        widget = self.feeds[feed_id]
        widget.setParent(None)
        widget.deleteLater()
        del self.feeds[feed_id]
        del self.feed_types[feed_id]
        
        # Update layout
        self._update_layout()
        
        # Hide container if no feeds left
        if len(self.feeds) == 0:
            self.feeds_container.setVisible(False)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Removed feed: {feed_id}")
        return True
        
    def update_feed(self, feed_id, data):
        """
        Update a specific feed with new data.
        
        Args:
            feed_id (str): ID of the feed to update
            data: New data - QPixmap for video feeds, dict for IMU feeds, list for ball_3d feeds
        """
        if feed_id in self.feeds:
            feed_type = self.feed_types.get(feed_id, "video")
            if feed_type == "imu":
                # Update IMU feed with sensor data
                self.feeds[feed_id].update_imu_data(data)
            elif feed_type == "ball_3d":
                # Update 3D ball tracker feed with ball data
                self.feeds[feed_id].update_ball_data(data)
            else:
                # Update video feed with pixmap
                self.feeds[feed_id].update_frame(data)
        else:
            print(f"Warning: Attempted to update non-existent feed: {feed_id}")
    
    def update_imu_feed(self, feed_id, imu_data):
        """
        Convenience method to update an IMU feed with sensor data.
        
        Args:
            feed_id (str): ID of the IMU feed to update
            imu_data (dict): IMU sensor data
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "imu":
            self.feeds[feed_id].update_imu_data(imu_data)
        else:
            print(f"Warning: Attempted to update non-existent or non-IMU feed: {feed_id}")
            
    def set_feed_name(self, feed_id, name):
        """
        Set the display name for a feed.
        
        Args:
            feed_id (str): ID of the feed
            name (str): New display name
        """
        if feed_id in self.feeds:
            self.feeds[feed_id].set_feed_name(name)
            
    def get_feed_count(self):
        """Get the number of active feeds."""
        return len(self.feeds)
        
    def get_feed_ids(self):
        """Get list of all feed IDs."""
        return list(self.feeds.keys())
        
    def get_feed_latencies(self):
        """
        Get latency information for all feeds.
        
        Returns:
            dict: feed_id -> latency_ms
        """
        return {feed_id: widget.get_latency() for feed_id, widget in self.feeds.items()}
        
    def get_feed_fps(self):
        """
        Get FPS information for all feeds.
        
        Returns:
            dict: feed_id -> fps
        """
        return {feed_id: widget.get_fps() for feed_id, widget in self.feeds.items()}
        
    def _update_layout(self):
        """Update the grid layout based on number of feeds."""
        # Clear existing layout
        while self.feeds_layout.count():
            child = self.feeds_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                
        feed_count = len(self.feeds)
        if feed_count == 0:
            return
            
        # Calculate grid dimensions
        if feed_count <= 4:
            # Single row for 1-4 feeds
            rows = 1
            cols = feed_count
        else:
            # Two rows for 5+ feeds
            rows = 2
            # Calculate columns needed for the feeds
            cols = (feed_count + 1) // 2  # Ceiling division to distribute feeds across rows
            
        # Add feeds to grid
        feed_widgets = list(self.feeds.values())
        for i, widget in enumerate(feed_widgets):
            row = i // cols
            col = i % cols
            self.feeds_layout.addWidget(widget, row, col)
            
        # Set column stretch to make feeds equal width
        for col in range(cols):
            self.feeds_layout.setColumnStretch(col, 1)
            
        # Set row stretch
        for row in range(rows):
            self.feeds_layout.setRowStretch(row, 1)
            
        print(f"Updated layout: {feed_count} feeds in {rows}x{cols} grid")
        
    def clear_all_feeds(self):
        """Remove all feeds."""
        feed_ids = list(self.feeds.keys())
        for feed_id in feed_ids:
            self.remove_feed(feed_id)
    
    def get_feed_type(self, feed_id):
        """
        Get the type of a feed.
        
        Args:
            feed_id (str): ID of the feed
            
        Returns:
            str: 'video', 'imu', or None if feed doesn't exist
        """
        return self.feed_types.get(feed_id)
    
    def get_imu_feeds(self):
        """
        Get all IMU feed IDs.
        
        Returns:
            list: List of IMU feed IDs
        """
        return [feed_id for feed_id, feed_type in self.feed_types.items() if feed_type == "imu"]
    
    def get_video_feeds(self):
        """
        Get all video feed IDs.
        
        Returns:
            list: List of video feed IDs
        """
        return [feed_id for feed_id, feed_type in self.feed_types.items() if feed_type == "video"]
    
    def get_ball_3d_feeds(self):
        """
        Get all 3D ball tracker feed IDs.
        
        Returns:
            list: List of 3D ball tracker feed IDs
        """
        return [feed_id for feed_id, feed_type in self.feed_types.items() if feed_type == "ball_3d"]
    
    def clear_imu_feed_data(self, feed_id):
        """
        Clear data from an IMU feed.
        
        Args:
            feed_id (str): ID of the IMU feed to clear
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "imu":
            self.feeds[feed_id].clear_data()
        else:
            print(f"Warning: Attempted to clear non-existent or non-IMU feed: {feed_id}")
    
    def set_imu_feed_settings(self, feed_id, history_length=None, auto_scale=None, value_ranges=None):
        """
        Configure settings for an IMU feed.
        
        Args:
            feed_id (str): ID of the IMU feed
            history_length (int, optional): Number of data points to keep
            auto_scale (bool, optional): Enable/disable auto-scaling
            value_ranges (tuple, optional): (accel_range, gyro_range) for custom scaling
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "imu":
            imu_widget = self.feeds[feed_id]
            
            if history_length is not None:
                imu_widget.set_history_length(history_length)
            
            if auto_scale is not None:
                imu_widget.set_auto_scale(auto_scale)
            
            if value_ranges is not None:
                accel_range, gyro_range = value_ranges
                imu_widget.set_value_ranges(accel_range, gyro_range)
        else:
            print(f"Warning: Attempted to configure non-existent or non-IMU feed: {feed_id}")
    
    def add_ball_3d_feed(self, feed_name="3D Ball Tracker", feed_id=None):
        """
        Convenience method to add a 3D ball tracker feed.
        
        Args:
            feed_name (str): Display name for the feed
            feed_id (str, optional): Unique ID for the feed. If None, auto-generated.
            
        Returns:
            str: The feed ID
        """
        if feed_id is None:
            feed_id = f"ball_3d_{self.feed_counter}"
            self.feed_counter += 1
            
        if feed_id in self.feeds:
            print(f"Warning: 3D Ball Tracker Feed {feed_id} already exists")
            return feed_id
            
        # Create 3D ball tracker feed widget
        feed_widget = Ball3DFeedWidget(feed_id, feed_name, self)
        self.feeds[feed_id] = feed_widget
        self.feed_types[feed_id] = "ball_3d"
        
        # Update layout
        self._update_layout()
        
        # Show container if this is the first feed
        if len(self.feeds) == 1:
            self.feeds_container.setVisible(True)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Added 3D ball tracker feed: {feed_id} ({feed_name})")
        return feed_id
        
    def update_ball_3d_feed(self, feed_id, ball_data):
        """
        Convenience method to update a 3D ball tracker feed with ball data.
        
        Args:
            feed_id (str): ID of the 3D ball tracker feed to update
            ball_data (list): List of ball data dictionaries with 3D positions
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "ball_3d":
            self.feeds[feed_id].update_ball_data(ball_data)
        else:
            print(f"Warning: Attempted to update non-existent or non-3D ball tracker feed: {feed_id}")
            
    def clear_ball_3d_feed_data(self, feed_id):
        """
        Clear data from a 3D ball tracker feed.
        
        Args:
            feed_id (str): ID of the 3D ball tracker feed to clear
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "ball_3d":
            self.feeds[feed_id].clear_data()
        else:
            print(f"Warning: Attempted to clear non-existent or non-3D ball tracker feed: {feed_id}")
    
    def configure_ball_3d_feed_settings(self, feed_id, x_range=None, y_range=None, z_range=None,
                                       ball_colors=None, size_range=None):
        """
        Configure settings for a 3D ball tracker feed.
        
        Args:
            feed_id (str): ID of the 3D ball tracker feed
            x_range (tuple, optional): (min, max) for X-axis in meters
            y_range (tuple, optional): (min, max) for Y-axis in meters
            z_range (tuple, optional): (min, max) for Z-axis in meters
            ball_colors (dict, optional): Ball color mapping
            size_range (tuple, optional): (min_radius, max_radius) for depth visualization
        """
        if feed_id in self.feeds and self.feed_types.get(feed_id) == "ball_3d":
            ball_3d_widget = self.feeds[feed_id]
            
            if x_range or y_range or z_range:
                ball_3d_widget.set_3d_bounds(x_range, y_range, z_range)
            
            if ball_colors:
                ball_3d_widget.set_ball_colors(ball_colors)
            
            if size_range:
                min_radius, max_radius = size_range
                ball_3d_widget.set_size_range(min_radius, max_radius)
        else:
            print(f"Warning: Attempted to configure non-existent or non-3D ball tracker feed: {feed_id}")