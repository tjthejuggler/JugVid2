#!/usr/bin/env python3
"""
Juggling Tracker - A robust juggling ball tracking system

This script is the entry point for the Juggling Tracker application.
It imports and runs the main application from the juggling_tracker package.
"""

import os
import sys
import platform
import argparse

# Add the librealsense build directory to PYTHONPATH if it exists
librealsense_path = os.path.expanduser("~/Projects/librealsense/build/Release")
if os.path.exists(librealsense_path):
    # Add to PYTHONPATH
    if "PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = f"{librealsense_path}:{os.environ['PYTHONPATH']}"
    else:
        os.environ["PYTHONPATH"] = librealsense_path
    
    # Also add to sys.path for the current process
    sys.path.insert(0, librealsense_path)

# Add the current directory to the path so we can import the juggling_tracker package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Check if pyrealsense2 is available
realsense_available = False
try:
    import pyrealsense2 as rs
    print(f"Successfully imported pyrealsense2 version: {rs.__version__}")
    
    # Try to create a pipeline to check if the camera is accessible
    try:
        pipeline = rs.pipeline()
        config = rs.config()
        # Try to get a list of devices
        ctx = rs.context()
        devices = ctx.query_devices()
        if devices.size() > 0:
            print(f"Found {devices.size()} RealSense device(s)")
            realsense_available = True
        else:
            print("No RealSense devices found")
    except Exception as e:
        print(f"Error checking RealSense devices: {e}")
except ImportError as e:
    print(f"Error importing pyrealsense2: {e}")
    print("\nPossible solutions:")
    print("1. Make sure the Intel RealSense SDK is installed")
    print("2. Set the PYTHONPATH environment variable to point to the librealsense build directory:")
    print("   export PYTHONPATH=~/Projects/librealsense/build/Release:$PYTHONPATH")
    print("3. Install the pyrealsense2 package using pip:")
    print("   pip install pyrealsense2")
except AttributeError as e:
    print(f"Error with pyrealsense2: {e}")
    print("\nIt seems the pyrealsense2 module is found but not properly configured.")
    print("This might be due to a mismatch between the Python bindings and the installed SDK.")
    print("\nPossible solutions:")
    print("1. Make sure the Intel RealSense SDK is installed correctly")
    print("2. Try reinstalling the pyrealsense2 package:")
    print("   pip uninstall pyrealsense2")
    print("   pip install pyrealsense2")

def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Juggling Tracker')
    parser.add_argument('--config-dir', type=str, help='Directory to save configuration files')
    parser.add_argument('--no-realsense', action='store_true', help='Disable RealSense camera')
    parser.add_argument('--webcam', action='store_true', help='Use webcam instead of RealSense')
    parser.add_argument('--simulation', action='store_true', help='Use simulation mode')
    parser.add_argument('--camera-index', type=int, default=0, help='Index of the webcam to use')
    return parser.parse_args()

def main():
    """
    Main entry point.
    """
    # Parse command line arguments
    args = parse_args()
    
    # Check if we should use RealSense
    use_realsense = not args.no_realsense and not args.webcam and not args.simulation
    
    # If RealSense is requested but not available, show a message and exit
    if use_realsense and not realsense_available:
        print("\nERROR: RealSense camera is not available, but no alternative mode was specified.")
        print("\nPlease use one of the following options:")
        print("  --webcam         Use a webcam instead of RealSense")
        print("  --simulation     Use simulation mode (no camera required)")
        print("  --no-realsense   Disable RealSense and use fallback modes automatically")
        print("\nExample:")
        print("  python run_juggling_tracker.py --simulation")
        print("  python run_juggling_tracker.py --webcam --camera-index 0")
        sys.exit(1)
    
    # Import the main module
    from juggling_tracker.main import main as juggling_main
    
    # Run the application
    juggling_main()

if __name__ == '__main__':
    main()