#!/usr/bin/env python3
"""
Test script to verify camera frame updates are working properly.
This will help diagnose if frames are freezing or updating correctly.
"""

import cv2
import time
import numpy as np
from color_only_frame_acquisition import ColorOnlyFrameAcquisition

def test_realsense_frames():
    """Test RealSense frame updates."""
    print("Testing RealSense frame updates...")
    
    acquisition = ColorOnlyFrameAcquisition(width=640, height=480, fps=30)
    
    if not acquisition.initialize():
        print("❌ RealSense initialization failed")
        return False
    
    print("✅ RealSense initialized, testing frame updates...")
    
    frame_count = 0
    last_frame_hash = None
    frozen_count = 0
    max_frozen = 5  # Allow some identical frames
    
    try:
        start_time = time.time()
        while frame_count < 100:  # Test 100 frames
            depth_frame, color_frame, depth_image, color_image = acquisition.get_frames()
            
            if color_image is not None:
                frame_count += 1
                
                # Calculate simple hash to detect if frame changed
                frame_hash = hash(color_image.tobytes())
                
                if frame_hash == last_frame_hash:
                    frozen_count += 1
                    if frozen_count > max_frozen:
                        print(f"❌ Frame frozen detected at frame {frame_count}")
                        print(f"   Same frame hash for {frozen_count} consecutive frames")
                        return False
                else:
                    frozen_count = 0  # Reset counter
                    last_frame_hash = frame_hash
                
                # Add frame counter to image
                cv2.putText(color_image, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(color_image, f"Time: {time.time() - start_time:.1f}s", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                cv2.imshow('RealSense Frame Update Test', color_image)
                
                if frame_count % 10 == 0:
                    print(f"✅ Frame {frame_count}: OK (frozen_count: {frozen_count})")
            else:
                print(f"⚠️  No frame at attempt {frame_count}")
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            time.sleep(0.033)  # ~30 FPS
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        acquisition.stop()
        cv2.destroyAllWindows()
    
    elapsed = time.time() - start_time
    fps = frame_count / elapsed if elapsed > 0 else 0
    print(f"✅ RealSense test completed: {frame_count} frames in {elapsed:.1f}s ({fps:.1f} FPS)")
    return True

def test_webcam_frames():
    """Test webcam frame updates."""
    print("Testing webcam frame updates...")
    
    webcam = cv2.VideoCapture(0)
    if not webcam.isOpened():
        print("❌ Webcam initialization failed")
        return False
    
    # Set properties
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    webcam.set(cv2.CAP_PROP_FPS, 30)
    
    print("✅ Webcam initialized, testing frame updates...")
    
    frame_count = 0
    last_frame_hash = None
    frozen_count = 0
    max_frozen = 5
    
    try:
        start_time = time.time()
        while frame_count < 100:  # Test 100 frames
            ret, color_image = webcam.read()
            
            if ret and color_image is not None:
                frame_count += 1
                
                # Calculate simple hash to detect if frame changed
                frame_hash = hash(color_image.tobytes())
                
                if frame_hash == last_frame_hash:
                    frozen_count += 1
                    if frozen_count > max_frozen:
                        print(f"❌ Frame frozen detected at frame {frame_count}")
                        print(f"   Same frame hash for {frozen_count} consecutive frames")
                        return False
                else:
                    frozen_count = 0
                    last_frame_hash = frame_hash
                
                # Add frame counter to image
                cv2.putText(color_image, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(color_image, f"Time: {time.time() - start_time:.1f}s", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                cv2.imshow('Webcam Frame Update Test', color_image)
                
                if frame_count % 10 == 0:
                    print(f"✅ Frame {frame_count}: OK (frozen_count: {frozen_count})")
            else:
                print(f"⚠️  No frame at attempt {frame_count}")
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            time.sleep(0.033)  # ~30 FPS
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        webcam.release()
        cv2.destroyAllWindows()
    
    elapsed = time.time() - start_time
    fps = frame_count / elapsed if elapsed > 0 else 0
    print(f"✅ Webcam test completed: {frame_count} frames in {elapsed:.1f}s ({fps:.1f} FPS)")
    return True

def main():
    """Run camera frame update tests."""
    print("🎥 Camera Frame Update Test")
    print("=" * 50)
    print("This test will check if camera frames are updating properly")
    print("Press 'q' to quit each test early")
    print()
    
    # Test RealSense first
    realsense_ok = test_realsense_frames()
    print()
    
    # Test webcam
    webcam_ok = test_webcam_frames()
    print()
    
    # Summary
    print("📊 TEST RESULTS:")
    print(f"RealSense: {'✅ PASS' if realsense_ok else '❌ FAIL'}")
    print(f"Webcam: {'✅ PASS' if webcam_ok else '❌ FAIL'}")
    
    if realsense_ok or webcam_ok:
        print("✅ At least one camera is working properly")
        return True
    else:
        print("❌ Both cameras have frame update issues")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)