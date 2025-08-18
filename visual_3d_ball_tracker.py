#!/usr/bin/env python3
"""
Visual 3D Ball Tracker for JugVid2cpp

This script creates a graphical interface that shows balls as colored circles
with 3D visualization:
- Left/right movement (X-axis)
- Up/down movement (Y-axis) 
- Close/far movement (Z-axis) represented by circle size
"""

import sys
import time
import signal
import math
from datetime import datetime
from typing import Dict, List, Tuple

# Add the project root to the path
sys.path.append('.')

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

from apps.juggling_tracker.modules.jugvid2cpp_interface import JugVid2cppInterface

class Ball3DWidget(QWidget):
    """Widget to display 3D ball positions as colored circles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.balls = []
        self.setStyleSheet("background-color: black;")
        
        # 3D space bounds for normalization
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
        self.min_radius = 10
        self.max_radius = 80
        
    def update_balls(self, identified_balls: List[Dict]):
        """Update the ball positions."""
        self.balls = identified_balls
        print(f"🎨 Ball3DWidget received {len(identified_balls)} balls for rendering")
        if identified_balls:
            for i, ball in enumerate(identified_balls):
                original_3d = ball.get('original_3d', (0, 0, 0))
                profile_id = ball.get('profile_id', 'unknown')
                print(f"   Ball {i+1}: {profile_id} at {original_3d}")
        self.update()  # Trigger repaint
        
    def normalize_position(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """Convert 3D world coordinates to 2D screen coordinates with size."""
        # Normalize X to screen width (left/right) - REVERSED
        screen_x = int(((self.x_range[1] - x) / (self.x_range[1] - self.x_range[0])) * self.width())
        screen_x = max(0, min(self.width(), screen_x))
        
        # Normalize Y to screen height (up/down) - REVERSED (no additional flip needed)
        screen_y = int(((y - self.y_range[0]) / (self.y_range[1] - self.y_range[0])) * self.height())
        screen_y = max(0, min(self.height(), screen_y))
        
        # Normalize Z to circle radius (close/far)
        z_normalized = (z - self.z_range[0]) / (self.z_range[1] - self.z_range[0])
        z_normalized = max(0.0, min(1.0, z_normalized))
        # Invert so closer objects are bigger
        radius = int(self.max_radius - (z_normalized * (self.max_radius - self.min_radius)))
        
        return screen_x, screen_y, radius
        
    def paintEvent(self, event):
        """Paint the balls on the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw coordinate system guides
        self.draw_guides(painter)
        
        print(f"🎨 paintEvent called with {len(self.balls)} balls to draw")
        
        # Draw each ball
        for i, ball in enumerate(self.balls):
            original_3d = ball.get('original_3d', (0, 0, 0))
            profile_id = ball.get('profile_id', 'unknown')
            timestamp_str = ball.get('timestamp_str', '')
            
            x, y, z = original_3d
            screen_x, screen_y, radius = self.normalize_position(x, y, z)
            
            print(f"   Ball {i+1}: {profile_id} 3D({x:.3f}, {y:.3f}, {z:.3f}) -> Screen({screen_x}, {screen_y}) radius={radius}")
            
            # Get ball color
            color = self.ball_colors.get(profile_id, self.ball_colors['unknown'])
            
            # Draw ball shadow (slightly offset and darker)
            shadow_color = QColor(color.red() // 3, color.green() // 3, color.blue() // 3, 100)
            painter.setBrush(QBrush(shadow_color))
            painter.setPen(QPen(shadow_color, 1))
            painter.drawEllipse(screen_x - radius + 3, screen_y - radius + 3, radius * 2, radius * 2)
            
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
            
            # Draw ball info text
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setFont(QFont("Arial", 10))
            info_text = f"{profile_id.replace('_ball', '').upper()}"
            painter.drawText(screen_x - radius, screen_y + radius + 15, info_text)
            
            # Draw 3D coordinates
            painter.setFont(QFont("Arial", 8))
            coord_text = f"({x:.2f}, {y:.2f}, {z:.2f})"
            painter.drawText(screen_x - radius, screen_y + radius + 30, coord_text)
        
        # If no balls, draw a message
        if not self.balls:
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.setFont(QFont("Arial", 16))
            painter.drawText(self.width()//2 - 100, self.height()//2, "No balls detected")
            
    def draw_guides(self, painter):
        """Draw coordinate system guides."""
        painter.setPen(QPen(QColor(64, 64, 64), 1))
        
        # Draw center lines
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Vertical center line (X=0)
        painter.drawLine(center_x, 0, center_x, self.height())
        
        # Horizontal center line (Y=0)
        painter.drawLine(0, center_y, self.width(), center_y)
        
        # Draw axis labels
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.setFont(QFont("Arial", 12))
        
        # X-axis labels
        painter.drawText(10, center_y - 10, "LEFT")
        painter.drawText(self.width() - 50, center_y - 10, "RIGHT")
        
        # Y-axis labels  
        painter.drawText(center_x + 10, 20, "UP")
        painter.drawText(center_x + 10, self.height() - 10, "DOWN")
        
        # Z-axis info (size legend)
        painter.drawText(10, 30, "CLOSE = BIG")
        painter.drawText(10, 50, "FAR = SMALL")

class Visual3DBallTracker(QMainWindow):
    """Main window for the visual 3D ball tracker."""
    
    def __init__(self):
        super().__init__()
        self.interface = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.running = False
        self.start_time = None
        self.frame_count = 0
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Visual 3D Ball Tracker - JugVid2cpp")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("🎯 Visual 3D Ball Tracker")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: #2c3e50; padding: 10px;")
        layout.addWidget(title_label)
        
        # Control panel
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: #34495e; padding: 10px;")
        control_layout = QHBoxLayout(control_frame)
        
        # Start/Stop button
        self.start_stop_btn = QPushButton("🚀 Start Tracking")
        self.start_stop_btn.clicked.connect(self.toggle_tracking)
        self.start_stop_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.start_stop_btn)
        
        # Status label
        self.status_label = QLabel("Ready to start tracking")
        self.status_label.setStyleSheet("color: white; font-weight: bold;")
        control_layout.addWidget(self.status_label)
        
        # Stats label
        self.stats_label = QLabel("Frames: 0 | Balls: 0")
        self.stats_label.setStyleSheet("color: #bdc3c7;")
        control_layout.addWidget(self.stats_label)
        
        control_layout.addStretch()
        layout.addWidget(control_frame)
        
        # 3D visualization widget
        self.ball_widget = Ball3DWidget()
        layout.addWidget(self.ball_widget)
        
        # Info panel
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #2c3e50; color: white; padding: 5px;")
        info_layout = QHBoxLayout(info_frame)
        
        info_text = QLabel("🎨 Ball Colors: PINK | ORANGE | YELLOW | GREEN  •  📏 3D Axes: LEFT↔RIGHT (X) | UP↔DOWN (Y) | BIG=CLOSE↔SMALL=FAR (Z)")
        info_text.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_frame)
        
    def toggle_tracking(self):
        """Start or stop the ball tracking."""
        if not self.running:
            self.start_tracking()
        else:
            self.stop_tracking()
            
    def start_tracking(self):
        """Start the ball tracking."""
        try:
            print("🎯 Starting Visual 3D Ball Tracker...")
            
            # Initialize JugVid2cpp interface
            self.interface = JugVid2cppInterface()
            
            if not self.interface.start():
                self.status_label.setText("❌ Failed to start JugVid2cpp")
                return
                
            self.running = True
            self.start_time = time.time()
            self.frame_count = 0
            
            # Update UI
            self.start_stop_btn.setText("🛑 Stop Tracking")
            self.start_stop_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; }")
            self.status_label.setText("🎥 Tracking active - Move balls in front of camera!")
            
            # Start update timer (30 FPS)
            self.timer.start(33)
            
            print("✅ Visual 3D Ball Tracker started successfully")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            print(f"❌ Error starting tracker: {e}")
            
    def stop_tracking(self):
        """Stop the ball tracking."""
        self.running = False
        self.timer.stop()
        
        if self.interface:
            self.interface.stop()
            self.interface = None
            
        # Update UI
        self.start_stop_btn.setText("🚀 Start Tracking")
        self.start_stop_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; }")
        self.status_label.setText("⏹️ Tracking stopped")
        
        # Show final stats
        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"\n📊 TRACKING SESSION COMPLETE:")
            print(f"   ⏱️  Duration: {total_time:.1f} seconds")
            print(f"   🎞️  Frames processed: {self.frame_count}")
            print(f"   📈 Average FPS: {self.frame_count / total_time:.1f}")
            
        print("✅ Visual 3D Ball Tracker stopped")
        
    def update_display(self):
        """Update the display with latest ball data."""
        if not self.running or not self.interface:
            return
            
        try:
            # Get the latest frame and ball data (same as working console test)
            _, _, _, video_frame = self.interface.get_frames()
            identified_balls = self.interface.get_identified_balls()
            
            # Update the 3D visualization
            self.ball_widget.update_balls(identified_balls)
            
            # Update stats
            self.frame_count += 1
            ball_count = len(identified_balls)
            
            if self.start_time:
                elapsed = time.time() - self.start_time
                fps = self.frame_count / elapsed if elapsed > 0 else 0
                self.stats_label.setText(f"Frames: {self.frame_count} | Balls: {ball_count} | FPS: {fps:.1f}")
                
            # Print ball info to console (less frequent)
            if self.frame_count % 30 == 0 and identified_balls:  # Every ~1 second at 30 FPS
                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp_str}] 🏀 {ball_count} balls detected:")
                for i, ball in enumerate(identified_balls):
                    profile_id = ball.get('profile_id', 'unknown')
                    original_3d = ball.get('original_3d', (0, 0, 0))
                    x, y, z = original_3d
                    print(f"  └─ {profile_id.replace('_ball', '').upper()}: ({x:.3f}, {y:.3f}, {z:.3f}) m")
                    
        except Exception as e:
            print(f"❌ Error updating display: {e}")
            
    def closeEvent(self, event):
        """Handle window close event."""
        if self.running:
            self.stop_tracking()
        event.accept()

def main():
    """Main function to run the visual 3D ball tracker."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2c3e50;
        }
        QWidget {
            background-color: #34495e;
            color: white;
        }
        QPushButton {
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3498db;
        }
        QLabel {
            color: white;
        }
    """)
    
    tracker = Visual3DBallTracker()
    tracker.show()
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, closing application...")
        tracker.close()
        app.quit()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🎯 Visual 3D Ball Tracker GUI started")
    print("   Click 'Start Tracking' to begin")
    print("   Move balls in front of the RealSense camera to see them visualized")
    print("   Press Ctrl+C or close window to exit")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()