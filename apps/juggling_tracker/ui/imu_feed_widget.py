#!/usr/bin/env python3
"""
IMU Feed Widget - Real-time IMU Data Visualization

This module provides a specialized widget for displaying IMU data (accelerometer and gyroscope)
as real-time graphs within the video feed system. It integrates seamlessly with the existing
VideoFeedManager to provide IMU feeds alongside video feeds.

Features:
- Real-time line graphs for accelerometer X, Y, Z values
- Real-time line graphs for gyroscope X, Y, Z values  
- Color-coded axes (X=red, Y=green, Z=blue)
- Time-based scrolling display with configurable history
- FPS and latency monitoring like video feeds
- Support for multiple IMU feeds (left watch, right watch)
- Automatic scaling and data buffering
- Clear labeling and identification

Author: Generated for JugVid2 project
Date: 2025-08-18
"""

import time
import numpy as np
from collections import deque
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QTimer


class IMUFeedWidget(QFrame):
    """
    Individual IMU feed widget with real-time graph visualization and latency monitoring.
    
    This widget displays IMU data as real-time line graphs, similar to how VideoFeedWidget
    displays video frames. It maintains the same interface for consistency with the 
    video feed system.
    """
    
    def __init__(self, feed_id, feed_name="IMU Feed", watch_name="unknown", parent=None):
        super().__init__(parent)
        self.feed_id = feed_id
        self.feed_name = feed_name
        self.watch_name = watch_name
        self.last_update_time = 0
        self.frame_count = 0
        self.fps = 0.0
        self.latency_ms = 0.0
        
        # IMU data buffers - store recent history for graphing
        self.history_length = 100  # Number of data points to keep
        self.time_buffer = deque(maxlen=self.history_length)
        self.accel_x_buffer = deque(maxlen=self.history_length)
        self.accel_y_buffer = deque(maxlen=self.history_length)
        self.accel_z_buffer = deque(maxlen=self.history_length)
        self.gyro_x_buffer = deque(maxlen=self.history_length)
        self.gyro_y_buffer = deque(maxlen=self.history_length)
        self.gyro_z_buffer = deque(maxlen=self.history_length)
        
        # Graph settings
        self.graph_width = 300
        self.graph_height = 200
        self.margin = 20
        self.line_width = 2
        
        # Color scheme for axes (X=red, Y=green, Z=blue)
        self.colors = {
            'x': QColor(255, 0, 0),      # Red
            'y': QColor(0, 255, 0),      # Green  
            'z': QColor(0, 0, 255),      # Blue
            'background': QColor(0, 0, 0),
            'grid': QColor(64, 64, 64),
            'text': QColor(255, 255, 255)
        }
        
        # Auto-scaling parameters
        self.accel_range = [-20.0, 20.0]  # m/s² range
        self.gyro_range = [-10.0, 10.0]   # rad/s range
        self.auto_scale = True
        
        self.setup_ui()
        
        # Timer for FPS calculation
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the UI for this IMU feed widget."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setStyleSheet("""
            IMUFeedWidget {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #000;
            }
            IMUFeedWidget:hover {
                border-color: #888;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # IMU graph display area
        self.graph_label = QLabel()
        self.graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graph_label.setMinimumSize(320, 240)  # Minimum size for readability
        self.graph_label.setStyleSheet("background-color: #000000; border: none;")
        self.graph_label.setScaledContents(False)  # Don't scale, we'll draw at exact size
        layout.addWidget(self.graph_label, 1)  # Give it most of the space
        
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
        
    def update_imu_data(self, imu_data):
        """
        Update the IMU feed with new data and generate visualization.
        
        Args:
            imu_data (dict): IMU data containing accelerometer and gyroscope values
                Expected format: {
                    'timestamp': float,
                    'accel_x': float, 'accel_y': float, 'accel_z': float,
                    'gyro_x': float, 'gyro_y': float, 'gyro_z': float,
                    'watch_name': str
                }
        """
        current_time = time.time()
        
        if imu_data:
            # Extract data
            timestamp = imu_data.get('timestamp', current_time)
            accel_x = imu_data.get('accel_x', 0.0)
            accel_y = imu_data.get('accel_y', 0.0) 
            accel_z = imu_data.get('accel_z', 0.0)
            gyro_x = imu_data.get('gyro_x', 0.0)
            gyro_y = imu_data.get('gyro_y', 0.0)
            gyro_z = imu_data.get('gyro_z', 0.0)
            
            # Add to buffers
            self.time_buffer.append(timestamp)
            self.accel_x_buffer.append(accel_x)
            self.accel_y_buffer.append(accel_y)
            self.accel_z_buffer.append(accel_z)
            self.gyro_x_buffer.append(gyro_x)
            self.gyro_y_buffer.append(gyro_y)
            self.gyro_z_buffer.append(gyro_z)
            
            # Update auto-scaling if enabled
            if self.auto_scale and len(self.accel_x_buffer) > 10:
                self._update_auto_scaling()
            
            # Generate and display the graph
            pixmap = self._create_graph_pixmap()
            if pixmap and not pixmap.isNull():
                self.graph_label.setPixmap(pixmap)
            
            # Calculate latency (time since data was generated)
            if timestamp > 0:
                self.latency_ms = (current_time - timestamp) * 1000
            
            self.last_update_time = current_time
            self.frame_count += 1
            
        self.update_info_display()
        
    def _update_auto_scaling(self):
        """Update the scaling ranges based on recent data."""
        if len(self.accel_x_buffer) < 10:
            return
            
        # Get recent data for scaling
        recent_data = list(self.accel_x_buffer)[-50:] + list(self.accel_y_buffer)[-50:] + list(self.accel_z_buffer)[-50:]
        if recent_data:
            accel_min = min(recent_data)
            accel_max = max(recent_data)
            accel_range = accel_max - accel_min
            if accel_range > 0:
                margin = accel_range * 0.1  # 10% margin
                self.accel_range = [accel_min - margin, accel_max + margin]
        
        recent_gyro = list(self.gyro_x_buffer)[-50:] + list(self.gyro_y_buffer)[-50:] + list(self.gyro_z_buffer)[-50:]
        if recent_gyro:
            gyro_min = min(recent_gyro)
            gyro_max = max(recent_gyro)
            gyro_range = gyro_max - gyro_min
            if gyro_range > 0:
                margin = gyro_range * 0.1  # 10% margin
                self.gyro_range = [gyro_min - margin, gyro_max + margin]
    
    def _create_graph_pixmap(self):
        """Create a QPixmap with the IMU data graphs."""
        if len(self.time_buffer) < 2:
            return self._create_no_data_pixmap()
        
        # Create pixmap
        pixmap = QPixmap(self.graph_width, self.graph_height)
        pixmap.fill(self.colors['background'])
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background and grid
        self._draw_background(painter)
        
        # Calculate graph area
        graph_x = self.margin
        graph_y = self.margin
        graph_w = self.graph_width - 2 * self.margin
        graph_h = (self.graph_height - 3 * self.margin) // 2  # Split into two graphs
        
        # Draw accelerometer graph (top half)
        accel_rect = (graph_x, graph_y, graph_w, graph_h)
        self._draw_sensor_graph(painter, accel_rect, "Accelerometer (m/s²)", 
                               self.accel_x_buffer, self.accel_y_buffer, self.accel_z_buffer,
                               self.accel_range)
        
        # Draw gyroscope graph (bottom half)
        gyro_y = graph_y + graph_h + self.margin
        gyro_rect = (graph_x, gyro_y, graph_w, graph_h)
        self._draw_sensor_graph(painter, gyro_rect, "Gyroscope (rad/s)",
                               self.gyro_x_buffer, self.gyro_y_buffer, self.gyro_z_buffer,
                               self.gyro_range)
        
        painter.end()
        return pixmap
    
    def _draw_background(self, painter):
        """Draw the background and grid."""
        # Set up font
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # Draw title
        painter.setPen(QPen(self.colors['text'], 1))
        title = f"{self.feed_name} ({self.watch_name.upper()})"
        painter.drawText(5, 15, title)
    
    def _draw_sensor_graph(self, painter, rect, title, x_data, y_data, z_data, value_range):
        """Draw a sensor graph (accelerometer or gyroscope)."""
        x, y, w, h = rect
        
        # Draw graph border
        painter.setPen(QPen(self.colors['grid'], 1))
        painter.drawRect(x, y, w, h)
        
        # Draw title
        painter.setPen(QPen(self.colors['text'], 1))
        painter.drawText(x + 5, y - 5, title)
        
        if len(x_data) < 2:
            painter.drawText(x + w//2 - 30, y + h//2, "No Data")
            return
        
        # Draw grid lines
        painter.setPen(QPen(self.colors['grid'], 1))
        for i in range(1, 4):  # 3 horizontal grid lines
            grid_y = y + (h * i) // 4
            painter.drawLine(x, grid_y, x + w, grid_y)
        
        # Convert data to screen coordinates
        time_data = list(self.time_buffer)
        if len(time_data) < 2:
            return
            
        time_min = min(time_data)
        time_max = max(time_data)
        time_range = time_max - time_min
        
        if time_range == 0:
            time_range = 1  # Avoid division by zero
        
        val_min, val_max = value_range
        val_range = val_max - val_min
        if val_range == 0:
            val_range = 1  # Avoid division by zero
        
        # Draw data lines
        datasets = [
            (list(x_data), self.colors['x'], 'X'),
            (list(y_data), self.colors['y'], 'Y'), 
            (list(z_data), self.colors['z'], 'Z')
        ]
        
        for data, color, label in datasets:
            if len(data) < 2:
                continue
                
            painter.setPen(QPen(color, self.line_width))
            
            # Draw the line
            points = []
            for i, (t, val) in enumerate(zip(time_data, data)):
                screen_x = x + int((t - time_min) / time_range * w)
                screen_y = y + h - int((val - val_min) / val_range * h)
                points.append((screen_x, screen_y))
            
            # Draw line segments
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                painter.drawLine(x1, y1, x2, y2)
        
        # Draw legend
        legend_x = x + w - 60
        legend_y = y + 15
        for i, (_, color, label) in enumerate(datasets):
            painter.setPen(QPen(color, 2))
            painter.drawLine(legend_x, legend_y + i * 12, legend_x + 15, legend_y + i * 12)
            painter.setPen(QPen(self.colors['text'], 1))
            painter.drawText(legend_x + 20, legend_y + i * 12 + 4, label)
        
        # Draw value range labels
        painter.setPen(QPen(self.colors['text'], 1))
        painter.drawText(x - 15, y + 5, f"{val_max:.1f}")
        painter.drawText(x - 15, y + h, f"{val_min:.1f}")
    
    def _create_no_data_pixmap(self):
        """Create a pixmap showing 'No Data' message."""
        pixmap = QPixmap(self.graph_width, self.graph_height)
        pixmap.fill(self.colors['background'])
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(self.colors['text'], 1))
        
        font = QFont("Arial", 12)
        painter.setFont(font)
        
        # Draw "No Data" message
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "No IMU Data\nWaiting for sensor data...")
        
        # Draw watch name
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(10, 20, f"{self.feed_name} ({self.watch_name.upper()})")
        
        painter.end()
        return pixmap
    
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
        data_points = len(self.time_buffer)
        info_text = f"{self.feed_name} | FPS: {self.fps:.1f} | Latency: {self.latency_ms:.1f}ms | Points: {data_points}"
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
    
    def clear_data(self):
        """Clear all buffered data."""
        self.time_buffer.clear()
        self.accel_x_buffer.clear()
        self.accel_y_buffer.clear()
        self.accel_z_buffer.clear()
        self.gyro_x_buffer.clear()
        self.gyro_y_buffer.clear()
        self.gyro_z_buffer.clear()
        
        # Update display
        pixmap = self._create_no_data_pixmap()
        self.graph_label.setPixmap(pixmap)
        self.update_info_display()
    
    def set_history_length(self, length):
        """Set the number of data points to keep in history."""
        self.history_length = max(10, min(1000, length))  # Clamp between 10 and 1000
        
        # Recreate buffers with new length
        old_time = list(self.time_buffer)
        old_ax = list(self.accel_x_buffer)
        old_ay = list(self.accel_y_buffer)
        old_az = list(self.accel_z_buffer)
        old_gx = list(self.gyro_x_buffer)
        old_gy = list(self.gyro_y_buffer)
        old_gz = list(self.gyro_z_buffer)
        
        self.time_buffer = deque(old_time[-self.history_length:], maxlen=self.history_length)
        self.accel_x_buffer = deque(old_ax[-self.history_length:], maxlen=self.history_length)
        self.accel_y_buffer = deque(old_ay[-self.history_length:], maxlen=self.history_length)
        self.accel_z_buffer = deque(old_az[-self.history_length:], maxlen=self.history_length)
        self.gyro_x_buffer = deque(old_gx[-self.history_length:], maxlen=self.history_length)
        self.gyro_y_buffer = deque(old_gy[-self.history_length:], maxlen=self.history_length)
        self.gyro_z_buffer = deque(old_gz[-self.history_length:], maxlen=self.history_length)
    
    def set_auto_scale(self, enabled):
        """Enable or disable auto-scaling."""
        self.auto_scale = enabled
        if not enabled:
            # Reset to default ranges
            self.accel_range = [-20.0, 20.0]
            self.gyro_range = [-10.0, 10.0]
    
    def set_value_ranges(self, accel_range, gyro_range):
        """Set custom value ranges for the graphs."""
        self.accel_range = accel_range
        self.gyro_range = gyro_range
        self.auto_scale = False  # Disable auto-scale when setting custom ranges