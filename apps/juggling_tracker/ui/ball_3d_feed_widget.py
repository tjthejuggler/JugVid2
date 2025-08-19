#!/usr/bin/env python3
"""
3D Ball Tracker Feed Widget for JugVid2cpp Integration

This widget provides a 3D visualization of juggling balls as a feed in the
juggling tracker application, integrating the visual_3d_ball_tracker functionality.
"""

import time
import math
from typing import Dict, List, Tuple
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class Ball3DFeedWidget(QFrame):
    """
    3D Ball Tracker feed widget that displays juggling balls in 3D space.
    
    This widget integrates the visual_3d_ball_tracker functionality into the
    juggling tracker's video feed system, showing balls as colored circles
    with 3D visualization:
    - Left/right movement (X-axis)
    - Up/down movement (Y-axis) 
    - Close/far movement (Z-axis) represented by circle size
    """
    
    def __init__(self, feed_id, feed_name="3D Ball Tracker", parent=None):
        super().__init__(parent)
        self.feed_id = feed_id
        self.feed_name = feed_name
        self.last_update_time = 0
        self.frame_count = 0
        self.fps = 0.0
        self.latency_ms = 0.0
        
        # Ball tracking data
        self.balls = []
        self.last_ball_update = 0
        
        # 3D space bounds for normalization (same as visual_3d_ball_tracker)
        self.x_range = (-0.5, 0.5)  # meters
        self.y_range = (-0.3, 0.3)  # meters  
        self.z_range = (0.2, 1.5)   # meters (depth)
        
        # Color mapping for different ball types
        self.ball_colors = {
            'pink_ball': QColor(255, 20, 147),      # Deep pink
            'orange_ball': QColor(255, 165, 0),     # Orange
            'yellow_ball': QColor(255, 255, 0),     # Yellow
            'green_ball': QColor(0, 255, 0),        # Green
            'unknown': QColor(128, 128, 128)        # Gray for unknown
        }
        
        # Size mapping for depth (Z-axis)
        self.min_radius = 8
        self.max_radius = 60
        
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
            Ball3DFeedWidget {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #000;
            }
            Ball3DFeedWidget:hover {
                border-color: #888;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # 3D visualization area (main content)
        self.viz_area = QFrame()
        self.viz_area.setMinimumSize(160, 120)
        self.viz_area.setStyleSheet("background-color: #000000; border: none;")
        layout.addWidget(self.viz_area, 1)  # Give it most of the space
        
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
        
    def update_ball_data(self, identified_balls: List[Dict]):
        """
        Update the ball positions with data from JugVid2cpp.
        
        Args:
            identified_balls: List of ball data dictionaries with 3D positions
        """
        current_time = time.time()
        
        # Update ball data
        self.balls = identified_balls
        self.last_ball_update = current_time
        
        # Calculate latency (time since last update)
        if self.last_update_time > 0:
            self.latency_ms = (current_time - self.last_update_time) * 1000
        
        self.last_update_time = current_time
        self.frame_count += 1
        
        # Trigger repaint
        self.viz_area.update()
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
        ball_count = len(self.balls)
        info_text = f"{self.feed_name} | Balls: {ball_count} | FPS: {self.fps:.1f} | Latency: {self.latency_ms:.1f}ms"
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
        
    def normalize_position(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """Convert 3D world coordinates to 2D screen coordinates with size."""
        # Get widget dimensions
        width = self.viz_area.width()
        height = self.viz_area.height()
        
        # Normalize X to screen width (left/right) - REVERSED
        screen_x = int(((self.x_range[1] - x) / (self.x_range[1] - self.x_range[0])) * width)
        screen_x = max(0, min(width, screen_x))
        
        # Normalize Y to screen height (up/down) - REVERSED (no additional flip needed)
        screen_y = int(((y - self.y_range[0]) / (self.y_range[1] - self.y_range[0])) * height)
        screen_y = max(0, min(height, screen_y))
        
        # Normalize Z to circle radius (close/far)
        z_normalized = (z - self.z_range[0]) / (self.z_range[1] - self.z_range[0])
        z_normalized = max(0.0, min(1.0, z_normalized))
        # Invert so closer objects are bigger
        radius = int(self.max_radius - (z_normalized * (self.max_radius - self.min_radius)))
        
        return screen_x, screen_y, radius
        
    def paintEvent(self, event):
        """Paint the 3D ball visualization."""
        super().paintEvent(event)
        
        # Paint on the visualization area
        painter = QPainter(self.viz_area)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clear the background
        painter.fillRect(self.viz_area.rect(), QColor(0, 0, 0))
        
        # Draw coordinate system guides
        self.draw_guides(painter)
        
        # Draw each ball
        for i, ball in enumerate(self.balls):
            original_3d = ball.get('original_3d', (0, 0, 0))
            profile_id = ball.get('profile_id', 'unknown')
            
            x, y, z = original_3d
            screen_x, screen_y, radius = self.normalize_position(x, y, z)
            
            # Get ball color
            color = self.ball_colors.get(profile_id, self.ball_colors['unknown'])
            
            # Draw ball shadow (slightly offset and darker)
            shadow_color = QColor(color.red() // 3, color.green() // 3, color.blue() // 3, 100)
            painter.setBrush(QBrush(shadow_color))
            painter.setPen(QPen(shadow_color, 1))
            painter.drawEllipse(screen_x - radius + 2, screen_y - radius + 2, radius * 2, radius * 2)
            
            # Draw main ball
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.lighter(150), 2))
            painter.drawEllipse(screen_x - radius, screen_y - radius, radius * 2, radius * 2)
            
            # Draw ball highlight (3D effect)
            highlight_color = color.lighter(200)
            highlight_radius = radius // 3
            painter.setBrush(QBrush(highlight_color))
            painter.setPen(QPen(highlight_color, 1))
            painter.drawEllipse(screen_x - highlight_radius - radius//3,
                              screen_y - highlight_radius - radius//3,
                              highlight_radius * 2, highlight_radius * 2)
            
            # Draw ball info text (smaller for feed widget)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setFont(QFont("Arial", 8))
            info_text = f"{profile_id.replace('_ball', '').upper()}"
            painter.drawText(screen_x - radius, screen_y + radius + 12, info_text)
            
            # Draw 3D coordinates (smaller font)
            painter.setFont(QFont("Arial", 7))
            coord_text = f"({x:.2f}, {y:.2f}, {z:.2f})"
            painter.drawText(screen_x - radius, screen_y + radius + 24, coord_text)
        
        # If no balls, draw a message
        if not self.balls:
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.viz_area.width()//2 - 60, self.viz_area.height()//2, "No balls detected")
            
        painter.end()
            
    def draw_guides(self, painter):
        """Draw coordinate system guides."""
        painter.setPen(QPen(QColor(64, 64, 64), 1))
        
        # Draw center lines
        center_x = self.viz_area.width() // 2
        center_y = self.viz_area.height() // 2
        
        # Vertical center line (X=0)
        painter.drawLine(center_x, 0, center_x, self.viz_area.height())
        
        # Horizontal center line (Y=0)
        painter.drawLine(0, center_y, self.viz_area.width(), center_y)
        
        # Draw axis labels (smaller for feed widget)
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.setFont(QFont("Arial", 9))
        
        # X-axis labels
        painter.drawText(5, center_y - 5, "L")
        painter.drawText(self.viz_area.width() - 15, center_y - 5, "R")
        
        # Y-axis labels  
        painter.drawText(center_x + 5, 15, "UP")
        painter.drawText(center_x + 5, self.viz_area.height() - 5, "DN")
        
        # Z-axis info (size legend) - smaller
        painter.setFont(QFont("Arial", 7))
        painter.drawText(5, 20, "CLOSE=BIG")
        painter.drawText(5, 32, "FAR=SMALL")
        
    def clear_data(self):
        """Clear all ball data."""
        self.balls = []
        self.viz_area.update()
        self.update_info_display()
        
    def set_3d_bounds(self, x_range=None, y_range=None, z_range=None):
        """
        Set the 3D space bounds for normalization.
        
        Args:
            x_range: Tuple of (min, max) for X-axis in meters
            y_range: Tuple of (min, max) for Y-axis in meters
            z_range: Tuple of (min, max) for Z-axis in meters
        """
        if x_range:
            self.x_range = x_range
        if y_range:
            self.y_range = y_range
        if z_range:
            self.z_range = z_range
            
    def set_ball_colors(self, color_mapping: Dict[str, QColor]):
        """
        Set custom ball colors.
        
        Args:
            color_mapping: Dictionary mapping ball profile IDs to QColor objects
        """
        self.ball_colors.update(color_mapping)
        
    def set_size_range(self, min_radius: int, max_radius: int):
        """
        Set the size range for depth visualization.
        
        Args:
            min_radius: Minimum circle radius for far objects
            max_radius: Maximum circle radius for close objects
        """
        self.min_radius = min_radius
        self.max_radius = max_radius