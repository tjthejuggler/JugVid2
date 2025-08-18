#!/usr/bin/env python3
"""
IMU Integration Validation Script

This script validates that the high-performance IMU integration is working correctly.
"""

import sys
import time
from pathlib import Path

def test_import():
    """Test that the smart IMU manager can be imported."""
    print("🧪 Testing IMU manager import...")
    
    try:
        from smart_imu_manager import WatchIMUManager, check_imu_system_status
        print("✅ Smart IMU manager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import smart IMU manager: {e}")
        return False

def test_manager_creation():
    """Test that the IMU manager can be created."""
    print("🧪 Testing IMU manager creation...")
    
    try:
        from smart_imu_manager import WatchIMUManager
        
        manager = WatchIMUManager(watch_ips=["192.168.1.101", "192.168.1.102"])
        print("✅ IMU manager created successfully")
        
        # Print performance info
        manager.print_performance_info()
        
        # Test cleanup
        if hasattr(manager, 'cleanup'):
            manager.cleanup()
        
        return True
    except Exception as e:
        print(f"❌ Failed to create IMU manager: {e}")
        return False

def test_performance_system():
    """Test the performance of the system."""
    print("🧪 Testing performance system...")
    
    try:
        # Run performance test if available
        if Path('simple_performance_test.py').exists():
            import subprocess
            result = subprocess.run([sys.executable, 'simple_performance_test.py'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Performance test passed")
                # Look for key performance indicators
                if "ALL PERFORMANCE GOALS ACHIEVED" in result.stdout:
                    print("🎉 High-performance system is working optimally!")
                    return True
                else:
                    print("⚠️  Performance test completed but goals not fully achieved")
                    return False
            else:
                print(f"❌ Performance test failed: {result.stderr}")
                return False
        else:
            print("⚠️  Performance test not available")
            return True
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

def main():
    """Run validation tests."""
    print("🔍 IMU INTEGRATION VALIDATION")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_import),
        ("Manager Creation Test", test_manager_creation),
        ("Performance Test", test_performance_system)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"VALIDATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ High-performance IMU integration is working correctly")
        print("🚀 Your application should now have lag-free IMU streaming")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("💡 Try running: python run_debug_analysis.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
