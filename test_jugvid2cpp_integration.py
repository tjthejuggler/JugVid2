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
    
    # Check if executable exists
    if not os.path.exists(interface.executable_path):
        print(f"\n❌ ERROR: JugVid2cpp executable not found at {interface.executable_path}")
        print("\nTo build JugVid2cpp:")
        print("   cd /home/twain/Projects/JugVid2cpp")
        print("   ./build.sh")
        return False
    
    print("   ✅ Executable found")
    
    # Test initialization
    print("\n2. Testing initialization...")
    success = interface.initialize()
    
    if not success:
        print("   ❌ Failed to initialize JugVid2cpp")
        return False
    
    print("   ✅ JugVid2cpp initialized successfully")
    
    # Test status info
    print("\n3. Getting status info...")
    status = interface.get_status_info()
    print(f"   Running: {status['is_running']}")
    print(f"   Healthy: {status['is_healthy']}")
    print(f"   Process running: {status['process_running']}")
    
    # Test data retrieval for a few seconds
    print("\n4. Testing data retrieval (10 seconds)...")
    start_time = time.time()
    frame_count = 0
    ball_detections = 0
    
    try:
        while time.time() - start_time < 10:
            # Get frames (compatibility method)
            interface.get_frames()
            
            # Get ball positions
            positions = interface.get_ball_positions()
            if positions:
                ball_detections += 1
                print(f"   Frame {frame_count}: {len(positions)} balls detected")
                for ball_name, pos in positions.items():
                    print(f"     {ball_name}: X={pos['x']:.3f}, Y={pos['y']:.3f}, Z={pos['z']:.3f}")
            
            # Test conversion to juggling_tracker format
            converted = interface.convert_to_juggling_tracker_format()
            if converted:
                print(f"   Converted format: {len(converted)} balls")
            
            frame_count += 1
            time.sleep(0.1)  # 10 FPS for testing
    
    except KeyboardInterrupt:
        print("\n   Test interrupted by user")
    
    # Final status
    print(f"\n5. Test Results:")
    print(f"   Total frames processed: {frame_count}")
    print(f"   Frames with ball detections: {ball_detections}")
    print(f"   Detection rate: {ball_detections/frame_count*100:.1f}%" if frame_count > 0 else "   No frames processed")
    
    final_status = interface.get_status_info()
    print(f"   Final health status: {final_status['is_healthy']}")
    print(f"   Total balls detected: {final_status['ball_count']}")
    
    # Clean up
    print("\n6. Cleaning up...")
    interface.stop()
    print("   ✅ Interface stopped")
    
    print("\n" + "=" * 60)
    print("JugVid2cpp Integration Test Complete")
    print("=" * 60)
    
    return True

def test_full_integration():
    """Test the full integration with juggling_tracker."""
    print("\n" + "=" * 60)
    print("Testing Full Integration")
    print("=" * 60)
    
    try:
        from juggling_tracker.main import JugglingTracker
        
        print("\n1. Creating JugglingTracker with JugVid2cpp mode...")
        app = JugglingTracker(use_jugvid2cpp=True)
        
        print("\n2. Testing initialization...")
        success = app.initialize()
        
        if success:
            print("   ✅ Full integration initialized successfully")
            print(f"   Frame acquisition type: {type(app.frame_acquisition)}")
            print(f"   Frame acquisition mode: {app.frame_acquisition.mode}")
            
            # Test a few frames
            print("\n3. Testing frame processing...")
            for i in range(5):
                app.process_frame()
                time.sleep(0.2)
            
            print("   ✅ Frame processing test complete")
        else:
            print("   ❌ Failed to initialize full integration")
            return False
        
        # Clean up
        print("\n4. Cleaning up...")
        app.cleanup()
        print("   ✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error in full integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("JugVid2cpp Integration Test Suite")
    print("This script tests the integration between JugVid2cpp and juggling_tracker")
    
    # Test basic interface
    interface_success = test_jugvid2cpp_interface()
    
    if interface_success:
        # Test full integration (without GUI)
        print("\nProceed with full integration test? (y/n): ", end="")
        response = input().lower().strip()
        
        if response in ['y', 'yes']:
            full_success = test_full_integration()
            
            if full_success:
                print("\n🎉 All tests passed! Integration is working correctly.")
                print("\nTo use JugVid2cpp with juggling_tracker:")
                print("   python -m juggling_tracker.main --jugvid2cpp")
            else:
                print("\n❌ Full integration test failed.")
        else:
            print("\nSkipping full integration test.")
    else:
        print("\n❌ Basic interface test failed. Please check JugVid2cpp installation.")
    
    print("\nTest complete.")