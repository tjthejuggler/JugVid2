#!/usr/bin/env python3
import time
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

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
    Manages multiple video feeds with dynamic layout.
    
    Layout rules:
    - 1-3 feeds: Single row
    - 4-6 feeds: Two rows (max 3 per row)
    - Automatically pushes other UI elements down
    """
    
    feeds_changed = pyqtSignal(int)  # Signal emitted when number of feeds changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.feeds = {}  # feed_id -> VideoFeedWidget
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
        
    def add_feed(self, feed_name="Feed", feed_id=None):
        """
        Add a new video feed.
        
        Args:
            feed_name (str): Display name for the feed
            feed_id (str, optional): Unique ID for the feed. If None, auto-generated.
            
        Returns:
            str: The feed ID
        """
        if feed_id is None:
            feed_id = f"feed_{self.feed_counter}"
            self.feed_counter += 1
            
        if feed_id in self.feeds:
            print(f"Warning: Feed {feed_id} already exists")
            return feed_id
            
        # Create new feed widget
        feed_widget = VideoFeedWidget(feed_id, feed_name, self)
        self.feeds[feed_id] = feed_widget
        
        # Update layout
        self._update_layout()
        
        # Show container if this is the first feed
        if len(self.feeds) == 1:
            self.feeds_container.setVisible(True)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Added feed: {feed_id} ({feed_name})")
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
        
        # Update layout
        self._update_layout()
        
        # Hide container if no feeds left
        if len(self.feeds) == 0:
            self.feeds_container.setVisible(False)
            
        self.feeds_changed.emit(len(self.feeds))
        print(f"Removed feed: {feed_id}")
        return True
        
    def update_feed(self, feed_id, pixmap):
        """
        Update a specific feed with new frame data.
        
        Args:
            feed_id (str): ID of the feed to update
            pixmap (QPixmap): New frame data
        """
        if feed_id in self.feeds:
            self.feeds[feed_id].update_frame(pixmap)
        else:
            print(f"Warning: Attempted to update non-existent feed: {feed_id}")
            
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
        if feed_count <= 3:
            # Single row
            rows = 1
            cols = feed_count
        else:
            # Two rows, max 3 per row
            rows = 2
            cols = 3
            
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