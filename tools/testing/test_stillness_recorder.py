#!/usr/bin/env python3
"""
Test script for the Stillness Recorder application.

This script tests the main components without requiring a RealSense camera.
"""

import sys
import os
import numpy as np
import cv2
import time

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from motion_detector import MotionDetector
        print("✓ MotionDetector imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import MotionDetector: {e}")
        return False
    
    try:
        from core.motion.circular_frame_buffer import CircularFrameBuffer, FrameBufferRecorder
        print("✓ CircularFrameBuffer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import CircularFrameBuffer: {e}")
        return False
    
    try:
        from color_only_frame_acquisition import ColorOnlyFrameAcquisition
        print("✓ ColorOnlyFrameAcquisition imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ColorOnlyFrameAcquisition: {e}")
        return False
    
    try:
        from stillness_recorder import StillnessRecorder
        print("✓ StillnessRecorder imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import StillnessRecorder: {e}")
        return False
    
    return True

def test_motion_detector():
    """Test the motion detector with synthetic frames."""
    print("\nTesting MotionDetector...")
    
    from motion_detector import MotionDetector
    
    detector = MotionDetector(motion_threshold=1000, stillness_duration=1.0)
    
    # Create test frames
    frame_still = np.zeros((240, 320, 3), dtype=np.uint8)
    frame_motion = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.rectangle(frame_motion, (100, 100), (200, 200), (255, 255, 255), -1)
    
    # Test motion detection
    motion1, is_motion1, _ = detector.detect_motion(frame_still)
    motion2, is_motion2, _ = detector.detect_motion(frame_motion)
    
    print(f"  Still frame motion: {motion1:.0f}, detected: {is_motion1}")
    print(f"  Motion frame motion: {motion2:.0f}, detected: {is_motion2}")
    
    # Test stillness detection
    for i in range(15):  # Simulate 1.5 seconds at 10fps
        motion, _, _ = detector.detect_motion(frame_still)
        stillness_triggered = detector.check_stillness(motion)
        if stillness_triggered:
            print(f"  ✓ Stillness triggered after {i+1} frames")
            break
        time.sleep(0.1)
    else:
        print("  ✗ Stillness not triggered")
        return False
    
    print("✓ MotionDetector test passed")
    return True

def test_circular_buffer():
    """Test the circular frame buffer."""
    print("\nTesting CircularFrameBuffer...")
    
    from core.motion.circular_frame_buffer import CircularFrameBuffer
    
    buffer = CircularFrameBuffer(max_duration_seconds=2.0, fps=10)
    
    # Add test frames
    start_time = time.time()
    for i in range(30):  # 3 seconds worth of frames
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        buffer.add_frame(frame, start_time + i * 0.1)
    
    # Check buffer stats
    stats = buffer.get_buffer_stats()
    print(f"  Buffer has {stats['frame_count']} frames")
    print(f"  Duration: {stats['buffer_duration']:.2f}s")
    print(f"  Utilization: {stats['buffer_utilization']:.1%}")
    
    # Test frame retrieval
    recent_frames = buffer.get_frames_in_duration(1.0)
    print(f"  Retrieved {len(recent_frames)} frames from last 1 second")
    
    if stats['frame_count'] > 0 and len(recent_frames) > 0:
        print("✓ CircularFrameBuffer test passed")
        return True
    else:
        print("✗ CircularFrameBuffer test failed")
        return False

def test_configuration():
    """Test the configuration and runner script."""
    print("\nTesting configuration...")
    
    try:
        from run_stillness_recorder import main as runner_main
        print("✓ Runner script imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import runner script: {e}")
        return False
    
    # Test that we can create a StillnessRecorder instance
    try:
        from stillness_recorder import StillnessRecorder
        recorder = StillnessRecorder(
            record_duration=5.0,
            motion_threshold=500,
            stillness_duration=2.0,
            output_dir="test_recordings"
        )
        print("✓ StillnessRecorder instance created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create StillnessRecorder: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Stillness Recorder - Component Tests")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Motion Detector Test", test_motion_detector),
        ("Circular Buffer Test", test_circular_buffer),
        ("Configuration Test", test_configuration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_name} failed")
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Stillness Recorder is ready to use.")
        print("\nTo run the application:")
        print("  python3 run_stillness_recorder.py")
        print("  python3 stillness_recorder.py --help")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)