#!/usr/bin/env python3
"""
Debug script to test IMU data flow in GUI context
"""

import time
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smart_imu_manager import WatchIMUManager

def test_gui_imu_flow(watch_ip):
    """Test IMU data flow as it would work in the GUI."""
    print("🔍 Testing GUI IMU Data Flow")
    print("=" * 50)
    
    # Create manager exactly like in main.py
    watch_ips = [watch_ip]
    watch_imu_manager = WatchIMUManager(watch_ips=watch_ips)
    print(f"✅ Manager created for IPs: {watch_ips}")
    
    # Start streaming exactly like in main.py
    watch_imu_manager.start_streaming()
    print("✅ Streaming started")
    
    # Wait for connection
    time.sleep(2)
    
    # Test data retrieval like in main.py process_frame()
    for i in range(5):
        print(f"\n🔄 Test iteration {i+1}:")
        
        # This is exactly what main.py does
        imu_data_points = watch_imu_manager.get_latest_imu_data()
        print(f"   get_latest_imu_data() returned: {len(imu_data_points)} data points")
        
        if imu_data_points:
            for data_point in imu_data_points:
                watch_name = data_point.get('watch_name', 'unknown')
                accel_x = data_point.get('accel_x', 0.0)
                accel_y = data_point.get('accel_y', 0.0)
                accel_z = data_point.get('accel_z', 0.0)
                gyro_x = data_point.get('gyro_x', 0.0)
                gyro_y = data_point.get('gyro_y', 0.0)
                gyro_z = data_point.get('gyro_z', 0.0)
                data_age = data_point.get('data_age', 0.0)
                
                accel_magnitude = (accel_x**2 + accel_y**2 + accel_z**2)**0.5
                gyro_magnitude = (gyro_x**2 + gyro_y**2 + gyro_z**2)**0.5
                
                print(f"   {watch_name}: A({accel_x:.3f},{accel_y:.3f},{accel_z:.3f}) G({gyro_x:.3f},{gyro_y:.3f},{gyro_z:.3f})")
                print(f"   Magnitudes: accel={accel_magnitude:.3f}, gyro={gyro_magnitude:.3f}, age={data_age*1000:.1f}ms")
                
                # This is what the periodic print in main.py would show
                print(f"   Periodic print format: IMU {watch_name}: accel={accel_magnitude:.2f}m/s², gyro={gyro_magnitude:.2f}rad/s, age={data_age*1000:.1f}ms")
        else:
            print("   No data points returned")
        
        time.sleep(1)
    
    # Cleanup
    watch_imu_manager.cleanup()
    print("\n✅ Cleanup completed")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_gui_imu_debug.py <watch_ip>")
        sys.exit(1)
    
    watch_ip = sys.argv[1]
    test_gui_imu_flow(watch_ip)