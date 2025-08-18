#!/usr/bin/env python3
"""
Test script for Enhanced IMU Integration with Watch OS apps

This script tests the complete Python Integration Guide functionality
integrated into the stillness recorder.

Author: Generated for JugVid2 project
Date: 2025-08-15
"""

import sys
import time
import logging
from core.imu.watch_imu_manager import WatchIMUManager, WatchController, debug_watch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_watch_controller():
    """Test the WatchController functionality from integration guide."""
    print("\n=== Testing WatchController (Integration Guide) ===")
    
    # Test with example IPs (replace with actual watch IPs)
    WATCH_IPS = ["192.168.1.101", "192.168.1.102"]
    
    controller = WatchController(WATCH_IPS)
    
    # Test discovery
    print("1. Testing watch discovery...")
    discovered = controller.discover_watches()
    print(f"Discovered watches: {discovered}")
    
    if not discovered:
        print("⚠️  No watches discovered. Make sure watches are on the network and running the IMU app.")
        return False
    
    # Test status
    print("2. Testing status retrieval...")
    status_data = controller.get_status_all()
    for ip, status in status_data.items():
        if status:
            print(f"✅ {ip}: {status}")
        else:
            print(f"❌ {ip}: No response")
    
    # Test synchronized recording session
    print("3. Testing synchronized recording session...")
    success = controller.synchronized_recording_session(duration=5.0)
    print(f"Synchronized recording session: {'✅ Success' if success else '❌ Failed'}")
    
    return success


def test_enhanced_imu_manager():
    """Test the enhanced WatchIMUManager."""
    print("\n=== Testing Enhanced WatchIMUManager ===")
    
    # Test with example IPs (replace with actual watch IPs)
    WATCH_IPS = ["192.168.1.101", "192.168.1.102"]
    
    manager = WatchIMUManager(WATCH_IPS, output_dir="test_imu_data")
    
    # Test discovery
    print("1. Testing enhanced discovery...")
    discovered = manager.discover_watches()
    print(f"Discovered watches: {discovered}")
    
    if not discovered:
        print("⚠️  No watches discovered. Testing with manual configuration...")
        # Add watches manually for testing
        manager.add_watch("left", "192.168.1.101")
        manager.add_watch("right", "192.168.1.102")
    else:
        # Auto-assign discovered watches
        watch_names = ["left", "right"]
        for i, (ip, port) in enumerate(discovered.items()):
            if i < len(watch_names):
                manager.add_watch(watch_names[i], ip, port)
    
    # Test status
    print("2. Testing enhanced status...")
    manager.print_status()
    
    # Test synchronized recording
    print("3. Testing synchronized recording session...")
    success = manager.synchronized_recording_session(duration=3.0)
    print(f"Enhanced synchronized recording: {'✅ Success' if success else '❌ Failed'}")
    
    # Cleanup
    manager.cleanup()
    
    return success


def test_debug_functionality():
    """Test debug functionality."""
    print("\n=== Testing Debug Functionality ===")
    
    # Test debug function with example IP
    test_ip = "192.168.1.101"
    print(f"Testing debug connectivity to {test_ip}...")
    debug_watch(test_ip)


def test_stillness_recorder_integration():
    """Test the integration with stillness recorder."""
    print("\n=== Testing Stillness Recorder Integration ===")
    
    try:
        from stillness_recorder_with_imu import StillnessRecorderWithIMU
        
        # Test with example IPs
        WATCH_IPS = ["192.168.1.101", "192.168.1.102"]
        
        # Create recorder with IMU integration
        recorder = StillnessRecorderWithIMU(
            record_duration=5.0,
            enable_imu=True,
            watch_ips=WATCH_IPS
        )
        
        print("✅ StillnessRecorderWithIMU created successfully")
        
        # Test IMU manager initialization
        if recorder.imu_manager:
            print("✅ Enhanced IMU Manager initialized")
            
            # Test discovery
            if recorder.imu_manager.watch_ips:
                discovered = recorder.imu_manager.discover_watches()
                print(f"Discovered watches: {discovered}")
            
            # Test status
            recorder.imu_manager.print_status()
            
            # Cleanup
            recorder.imu_manager.cleanup()
        else:
            print("❌ IMU Manager not initialized")
            return False
        
        print("✅ Stillness recorder integration test completed")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import stillness recorder: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing stillness recorder integration: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Enhanced IMU Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("WatchController", test_watch_controller),
        ("Enhanced WatchIMUManager", test_enhanced_imu_manager),
        ("Debug Functionality", test_debug_functionality),
        ("Stillness Recorder Integration", test_stillness_recorder_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name} test...")
        try:
            result = test_func()
            results[test_name] = result
            print(f"{'✅' if result else '⚠️'} {test_name} test {'passed' if result else 'completed with warnings'}")
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🧪 Test Results Summary:")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced IMU integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check watch connectivity and configuration.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)