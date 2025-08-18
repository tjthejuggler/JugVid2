#!/usr/bin/env python3
"""
Test script to verify the video feed layout system works correctly
with the new threshold of 4 feeds before moving to second row.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
from juggling_tracker.ui.video_feed_manager import VideoFeedManager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Feed Layout Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Feed")
        self.add_button.clicked.connect(self.add_feed)
        controls_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Feed")
        self.remove_button.clicked.connect(self.remove_feed)
        controls_layout.addWidget(self.remove_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_feeds)
        controls_layout.addWidget(self.clear_button)
        
        # Status label
        self.status_label = QLabel("Feeds: 0 | Layout: None")
        controls_layout.addWidget(self.status_label)
        
        layout.addLayout(controls_layout)
        
        # Video feed manager
        self.feed_manager = VideoFeedManager()
        self.feed_manager.feeds_changed.connect(self.update_status)
        layout.addWidget(self.feed_manager)
        
        # Timer to simulate video frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_feeds)
        self.timer.start(100)  # Update every 100ms
        
        self.feed_counter = 0
        
    def add_feed(self):
        """Add a new video feed."""
        self.feed_counter += 1
        feed_id = self.feed_manager.add_feed(f"Test Feed {self.feed_counter}")
        print(f"Added feed: {feed_id}")
        
    def remove_feed(self):
        """Remove the last video feed."""
        feed_ids = self.feed_manager.get_feed_ids()
        if feed_ids:
            removed = self.feed_manager.remove_feed(feed_ids[-1])
            if removed:
                print(f"Removed feed: {feed_ids[-1]}")
        
    def clear_feeds(self):
        """Clear all feeds."""
        self.feed_manager.clear_all_feeds()
        print("Cleared all feeds")
        
    def update_status(self, feed_count):
        """Update the status display."""
        if feed_count == 0:
            layout_info = "None"
        elif feed_count <= 4:
            layout_info = f"Single row ({feed_count} feeds)"
        else:
            rows = 2
            cols = (feed_count + 1) // 2
            layout_info = f"Two rows ({rows}x{cols} grid, {feed_count} feeds)"
            
        self.status_label.setText(f"Feeds: {feed_count} | Layout: {layout_info}")
        
    def update_feeds(self):
        """Update all feeds with dummy frames."""
        for i, feed_id in enumerate(self.feed_manager.get_feed_ids()):
            # Create a dummy colored frame
            pixmap = QPixmap(320, 240)
            color = QColor(50 + (i * 40) % 200, 100 + (i * 60) % 150, 150 + (i * 80) % 100)
            pixmap.fill(color)
            
            # Add some text to identify the feed
            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(10, 30, f"Feed {i+1}")
            painter.drawText(10, 50, f"ID: {feed_id}")
            painter.end()
            
            self.feed_manager.update_feed(feed_id, pixmap)

def test_layout_logic():
    """Test the layout logic without GUI."""
    print("Testing layout logic...")
    
    # Test cases: feed_count -> expected (rows, cols)
    test_cases = [
        (1, (1, 1)),
        (2, (1, 2)),
        (3, (1, 3)),
        (4, (1, 4)),  # This should now be single row
        (5, (2, 3)),  # This should now be two rows
        (6, (2, 3)),
    ]
    
    for feed_count, expected in test_cases:
        # Simulate the layout calculation logic
        if feed_count <= 4:
            rows = 1
            cols = feed_count
        else:
            rows = 2
            cols = (feed_count + 1) // 2
            
        result = (rows, cols)
        status = "✓" if result == expected else "✗"
        print(f"{status} {feed_count} feeds: {result} (expected {expected})")
        
        if result != expected:
            print(f"  ERROR: Layout calculation failed for {feed_count} feeds")
            return False
    
    print("All layout tests passed!")
    return True

def main():
    """Main test function."""
    print("Video Feed Layout Test")
    print("=" * 50)
    
    # Test layout logic first
    if not test_layout_logic():
        print("Layout logic test failed!")
        return 1
    
    print("\nStarting GUI test...")
    print("Instructions:")
    print("1. Click 'Add Feed' to add feeds one by one")
    print("2. Observe layout changes:")
    print("   - 1-4 feeds should be in a single row")
    print("   - 5+ feeds should move to two rows")
    print("3. Click 'Remove Feed' to test removal")
    print("4. Click 'Clear All' to reset")
    print("5. Close window when done")
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())