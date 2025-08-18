#!/usr/bin/env python3
"""
Test script for JugVid2cpp integration with juggling_tracker.
 
This script tests the basic functionality of the JugVid2cpp integration
without requiring the full GUI application.
"""
 
import sys
import os
import time
import logging
import cv2
 
# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from juggling_tracker.modules.jugvid2cpp_interface import JugVid2cppInterface

def test_jugvid2cpp_interface():
    """Test the JugVid2cppInterface module."""
    print("=" * 60)
    print("Testing JugVid2cpp Integration")
    print("=" * 60)
 
    # Set up logging
    logging.basicConfig(level=logging.INFO)
 
    # Create the interface
    print("\n1. Creating JugVid2cppInterface...")
    interface = JugVid2cppInterface()
    
    print(f"   Executable path: {interface.executable_path}")
    print(f"   Mode: {interface.mode}")
    
    # Check if the executable exists
    if not os.path.exists(interface.executable_path):
        print(f"\n❌ ERROR: JugVid2cpp executable not found at {interface.executable_path}")
        print("\nTo build JugVid2cpp:")
        print("   cd /home/twain/Projects/JugVid2cpp")
        print("   ./build.sh")
        return False
    
    print("   ✅ Executable found.")
    
    # Test initialization
    print("\n2. Testing initialization...")
    success = interface.initialize()
    
    if not success:
        print(f"   ❌ Failed to initialize JugVid2cpp. Error: {interface.get_status().get('error_message')}")
        error_output = interface.get_error_output()
        if error_output:
            print("\n--- JugVid2cpp stderr ---")
            print(error_output)
            print("-------------------------\n")
        return False
    
    print("   ✅ JugVid2cpp initialized successfully.")
    
    # Test data retrieval for 5 seconds
    print("\n3. Testing data retrieval (5 seconds)...")
    start_time = time.time()
    frame_count = 0
    ball_detections = 0
    last_print_time = 0
    
    try:
        while time.time() - start_time < 5:
            # Get frames and ball data
            _, _, _, color_image = interface.get_frames()
            identified_balls = interface.get_identified_balls()
            
            if color_image is not None:
                frame_count += 1
                if identified_balls:
                    ball_detections += 1
                
                # Print status once per second
                if time.time() - last_print_time > 1:
                    print(f"   Time: {time.time() - start_time:.1f}s | Frames received: {frame_count} | Detections: {len(identified_balls)}")
                    for ball in identified_balls:
                        pos3d = ball.get('original_3d', (0,0,0))
                        print(f"     - {ball['name']}: X={pos3d[0]:.2f}, Y={pos3d[1]:.2f}, Z={pos3d[2]:.2f}")
                    last_print_time = time.time()
            
            time.sleep(0.01) # Small sleep to avoid a tight loop
            
    except KeyboardInterrupt:
        print("\n   Test interrupted by user")
    
    # Final status
    print(f"\n4. Test Results:")
    print(f"   Total frames processed: {frame_count}")
    print(f"   Frames with ball detections: {ball_detections}")
    
    # Clean up
    print("\n5. Cleaning up...")
    interface.stop()
    print("   ✅ Interface stopped")
    
    print("\n" + "=" * 60)
    print("JugVid2cpp Integration Test Complete")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    print("JugVid2cpp Integration Test Suite")
    print("This script tests the integration between JugVid2cpp and juggling_tracker")
    
    # Test basic interface
    interface_success = test_jugvid2cpp_interface()
    
    if interface_success:
        print("\n🎉 Basic interface test passed! The Python side is ready.")
        print("You can now run the main application:")
        print("   python -m juggling_tracker.main --jugvid2cpp")
    else:
        print("\n❌ Basic interface test failed. Please check JugVid2cpp installation.")
        print("   Ensure the C++ application runs and prints to stdout in 'stream' mode.")
    
    print("\nTest complete.")