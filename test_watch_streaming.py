#!/usr/bin/env python3
"""
Real-time Watch IMU Streaming Test

This script connects to a watch at a specified IP address and displays
real-time IMU data streaming in the console.

Usage:
    python test_watch_streaming.py <watch_ip>
    python test_watch_streaming.py 192.168.1.101

Press Ctrl+C to stop streaming.
"""

import sys
import os
import time
import signal
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('\n\n🛑 Stopping streaming...')
    sys.exit(0)

def test_watch_streaming(watch_ip):
    """Test real-time streaming from a specific watch IP."""
    
    print(f"🔍 Testing Watch IMU Streaming")
    print(f"📱 Watch IP: {watch_ip}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        from watch_imu_manager import WatchIMUManager
        print("✅ WatchIMUManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import WatchIMUManager: {e}")
        print("💡 Make sure all dependencies are installed (websockets, requests, etc.)")
        return False
    
    # Initialize the manager
    try:
        manager = WatchIMUManager(watch_ips=[watch_ip])
        print(f"✅ WatchIMUManager initialized for {watch_ip}")
    except Exception as e:
        print(f"❌ Failed to initialize WatchIMUManager: {e}")
        return False
    
    # Test basic connectivity
    print(f"\n🔍 Testing connectivity to {watch_ip}...")
    try:
        discovered = manager.discover_watches()
        if discovered:
            print(f"✅ Watch discovered at {watch_ip}:{discovered[watch_ip]}")
        else:
            print(f"❌ No watch found at {watch_ip}")
            print("💡 Make sure:")
            print("   - Watch is on the same Wi-Fi network")
            print("   - Watch IMU app is running")
            print("   - IP address is correct")
            print("   - Firewall allows connections on ports 8080-8090")
            return False
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return False
    
    # Start streaming
    print(f"\n🚀 Starting real-time IMU streaming...")
    try:
        manager.start_streaming()
        print("✅ Streaming started successfully")
    except Exception as e:
        print(f"❌ Failed to start streaming: {e}")
        return False
    
    # Display streaming data
    print(f"\n📊 REAL-TIME IMU DATA FROM {watch_ip}")
    print("=" * 80)
    print("Time        | Watch | Accel (m/s²)           | Gyro (rad/s)           | Age(ms)")
    print("-" * 80)
    
    data_count = 0
    last_data_time = time.time()
    
    try:
        while True:
            # Get latest data
            imu_data_list = manager.get_latest_imu_data()
            
            if imu_data_list:
                for data in imu_data_list:
                    data_count += 1
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    watch_name = data.get('watch_name', 'unknown')
                    
                    # Extract accelerometer data
                    accel_x = data.get('accel_x', 0.0)
                    accel_y = data.get('accel_y', 0.0)
                    accel_z = data.get('accel_z', 0.0)
                    
                    # Extract gyroscope data
                    gyro_x = data.get('gyro_x', 0.0)
                    gyro_y = data.get('gyro_y', 0.0)
                    gyro_z = data.get('gyro_z', 0.0)
                    
                    # Calculate data age (time since received)
                    received_at = data.get('received_at', time.time())
                    data_age = (time.time() - received_at) * 1000  # Convert to ms
                    
                    # Format the data nicely
                    accel_str = f"({accel_x:6.3f},{accel_y:6.3f},{accel_z:6.3f})"
                    gyro_str = f"({gyro_x:6.3f},{gyro_y:6.3f},{gyro_z:6.3f})"
                    
                    print(f"{timestamp} | {watch_name:16} | {accel_str:22} | {gyro_str:22} | {data_age:6.1f}")
                    
                last_data_time = time.time()
            else:
                # Check if we haven't received data for a while
                if time.time() - last_data_time > 5.0:
                    print(f"{datetime.now().strftime('%H:%M:%S')} | No data received for 5+ seconds...")
                    last_data_time = time.time()
            
            # Small delay to prevent overwhelming the console
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Streaming stopped by user")
        print(f"📊 Total data points received: {data_count}")
    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            manager.cleanup()
            print("✅ Cleanup completed")
        except:
            pass
    
    return True

def main():
    """Main function."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    if len(sys.argv) != 2:
        print("Usage: python test_watch_streaming.py <watch_ip>")
        print("Example: python test_watch_streaming.py 192.168.1.101")
        sys.exit(1)
    
    watch_ip = sys.argv[1]
    
    # Validate IP format (basic check)
    parts = watch_ip.split('.')
    if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        print(f"❌ Invalid IP address format: {watch_ip}")
        sys.exit(1)
    
    print("🎯 Watch IMU Real-Time Streaming Test")
    print("Press Ctrl+C to stop streaming at any time")
    print()
    
    success = test_watch_streaming(watch_ip)
    
    if success:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()