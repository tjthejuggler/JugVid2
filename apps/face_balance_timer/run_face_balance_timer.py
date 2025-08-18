#!/usr/bin/env python3
"""
Face Balance Timer Launcher

Simple launcher script for the Face Balance Timer application.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from face_balance_timer import FaceBalanceTimer
    
    def main():
        """Main entry point for the Face Balance Timer."""
        print("=" * 50)
        print("    FACE BALANCE TIMER")
        print("=" * 50)
        print()
        
        # Create and run the timer
        timer = FaceBalanceTimer(width=640, height=480, fps=30)
        timer.run()
        
        print()
        print("Thanks for using Face Balance Timer!")
        
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure all dependencies are installed:")
    print("- pyrealsense2")
    print("- mediapipe")
    print("- opencv-python")
    print("- numpy")
    sys.exit(1)
except Exception as e:
    print(f"Error running Face Balance Timer: {e}")
    sys.exit(1)