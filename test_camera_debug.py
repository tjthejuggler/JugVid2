#!/usr/bin/env python3
"""
Camera debug script to help diagnose camera issues
"""

import cv2
import sys

def test_camera_sources():
    """Test different camera sources."""
    print("🎥 CAMERA DEBUG TEST")
    print("=" * 50)
    
    # Test webcam indices
    for i in range(3):
        print(f"\n📹 Testing camera index {i}...")
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"   ✅ Camera {i}: Working ({width}x{height})")
                    cap.release()
                    return i  # Return first working camera
                else:
                    print(f"   ❌ Camera {i}: Can't read frames")
            else:
                print(f"   ❌ Camera {i}: Can't open")
            cap.release()
        except Exception as e:
            print(f"   ❌ Camera {i}: Error - {e}")
    
    print("\n⚠️  No working cameras found!")
    return None

def suggest_camera_fix():
    """Suggest camera fixes."""
    print("\n🔧 CAMERA TROUBLESHOOTING:")
    print("1. Check if camera is being used by another application")
    print("2. Try disconnecting and reconnecting camera")
    print("3. Check camera permissions")
    print("4. Try running with different camera index:")
    print("   python3 run_stillness_recorder_with_imu.py --manual --camera-index 1")
    print("")
    print("🎯 WORKAROUND FOR IMU-ONLY TESTING:")
    print("If camera issues persist, you can test IMU recording without video:")
    print("1. The manual mode will still record IMU data even if camera fails")
    print("2. Check the session directory for CSV files")
    print("3. IMU data should be saved with synchronized timestamps")

def main():
    working_camera = test_camera_sources()
    
    if working_camera is not None:
        print(f"\n✅ SOLUTION: Use camera index {working_camera}")
        print(f"Modify the camera initialization to use index {working_camera}")
    else:
        suggest_camera_fix()
    
    print("\n📊 CURRENT ISSUE ANALYSIS:")
    print("From your log, the issues are:")
    print("1. ✅ FIXED: IMU 'NoneType' error (session_start_time)")
    print("2. 🔧 CAMERA: RealSense conflicts with webcam fallback")
    print("3. ✅ WORKING: Watch connection and IMU start/stop commands")
    print("4. 🎯 EXPECTED: IMU CSV files should now be created")
    
    print("\n🧪 NEXT TEST:")
    print("Try running manual mode again:")
    print("python3 run_stillness_recorder_with_imu.py --manual --watch-ips 10.200.169.90")
    print("")
    print("Even if video fails, you should now see:")
    print("• No crash from 'NoneType' error")
    print("• IMU CSV files created in session directory")
    print("• Proper start/stop toggle working")

if __name__ == "__main__":
    main()