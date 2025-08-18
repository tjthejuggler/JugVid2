#!/usr/bin/env python3
"""
Simple test for the controls window to verify it displays properly.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_controls_window():
    """Test the controls window independently."""
    print("Testing Controls Window...")
    
    try:
        from stillness_recorder import StillnessRecorder, ControlsWindow
        
        # Create a mock recorder with basic settings
        class MockRecorder:
            def __init__(self):
                self.record_duration = 10.0
                self.motion_threshold = 1000
                self.stillness_threshold = 500
                self.stillness_duration = 3.0
                self.total_recordings = 0
                self.has_detected_movement = False
                
        mock_recorder = MockRecorder()
        
        # Create the controls window
        controls = ControlsWindow(mock_recorder)
        controls.create_window()
        
        print("✓ Controls window created successfully")
        print("✓ Window should be visible with all controls")
        print("Press Ctrl+C or close the window to exit")
        
        # Run the tkinter main loop
        controls.root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating controls window: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_controls_window()
    sys.exit(0 if success else 1)