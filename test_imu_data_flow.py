#!/usr/bin/env python3
"""
Test script to verify IMU data flow in the high-performance system.
"""

import time
import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smart_imu_manager import WatchIMUManager

def test_imu_data_flow():
    """Test if IMU data is flowing through the system."""
    print("🔍 Testing IMU data flow...")
    
    # Create manager with the same IP as the main application
    watch_ips = ["10.200.169.205"]
    manager = WatchIMUManager(watch_ips=watch_ips)
    
    print(f"📡 Connecting to watches: {watch_ips}")
    
    # Discover watches
    discovered = manager.discover_watches()
    print(f"🔍 Discovered watches: {discovered}")
    
    if not discovered:
        print("❌ No watches discovered. Check IP address and watch connectivity.")
        return False
    
    # Start streaming
    print("🚀 Starting IMU streaming...")
    manager.start_streaming()
    
    # Wait for data
    print("⏳ Waiting for IMU data (10 seconds)...")
    data_received = False
    
    for i in range(10):
        time.sleep(1)
        
        # Check for data
        imu_data = manager.get_latest_imu_data()
        
        if imu_data:
            data_received = True
            print(f"✅ IMU data received! ({len(imu_data)} data points)")
            
            for data_point in imu_data:
                watch_name = data_point.get('watch_name', 'unknown')
                accel_mag = data_point.get('accel_magnitude', 0)
                gyro_mag = data_point.get('gyro_magnitude', 0)
                data_age = data_point.get('data_age', 0) * 1000
                
                print(f"   {watch_name}: Accel={accel_mag:.3f}m/s², Gyro={gyro_mag:.3f}rad/s, Age={data_age:.1f}ms")
            break
        else:
            print(f"   Waiting... ({i+1}/10)")
    
    if not data_received:
        print("❌ No IMU data received after 10 seconds")
        print("   Possible issues:")
        print("   - Watch is not running the IMU streaming app")
        print("   - Watch is not connected to the same network")
        print("   - Watch app is not sending sensor data")
        print("   - Firewall blocking connections")
    
    # Cleanup
    manager.cleanup()
    
    return data_received

if __name__ == "__main__":
    success = test_imu_data_flow()
    sys.exit(0 if success else 1)