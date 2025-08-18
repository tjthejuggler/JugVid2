#!/usr/bin/env python3
"""
Debug script to test IMU data flow in the juggling tracker
"""

import time
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imu_data_flow():
    """Test the complete IMU data flow from watch to UI"""
    
    print("🔍 Testing IMU Data Flow")
    print("=" * 50)
    
    # Test 1: Import the smart manager
    try:
        from smart_imu_manager import WatchIMUManager
        print("✅ Smart IMU Manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Smart IMU Manager: {e}")
        return False
    
    # Test 2: Create manager instance
    try:
        watch_ips = ["10.200.169.205"]
        manager = WatchIMUManager(watch_ips=watch_ips)
        print(f"✅ Manager created for IPs: {watch_ips}")
    except Exception as e:
        print(f"❌ Failed to create manager: {e}")
        return False
    
    # Test 3: Check if high-performance system is being used
    if hasattr(manager, 'system_type'):
        print(f"📊 System Type: {manager.system_type}")
        if manager.system_type == "high_performance":
            print("🚀 Using high-performance system")
        else:
            print("⚠️  Using legacy system")
    
    # Test 4: Start streaming
    try:
        manager.start_streaming()
        print("✅ Streaming started")
        time.sleep(2)  # Give it time to connect
    except Exception as e:
        print(f"❌ Failed to start streaming: {e}")
        return False
    
    # Test 5: Check for data
    print("\n🔄 Testing data retrieval...")
    data_received = False
    for i in range(10):
        try:
            imu_data = manager.get_latest_imu_data()
            if imu_data:
                print(f"✅ Iteration {i+1}: Got {len(imu_data)} data points")
                for data_point in imu_data:
                    watch_name = data_point.get('watch_name', 'unknown')
                    accel = data_point.get('accel', (0, 0, 0))
                    gyro = data_point.get('gyro', (0, 0, 0))
                    data_age = data_point.get('data_age', 0) * 1000
                    print(f"   {watch_name}: A({accel[0]:.3f},{accel[1]:.3f},{accel[2]:.3f}) "
                          f"G({gyro[0]:.3f},{gyro[1]:.3f},{gyro[2]:.3f}) Age:{data_age:.1f}ms")
                data_received = True
                break
            else:
                print(f"⏳ Iteration {i+1}: No data yet...")
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error getting data: {e}")
            break
    
    if not data_received:
        print("❌ No data received after 10 attempts - continuing with diagnostics...")
    
    # Test 6: Check internal data structures
    if hasattr(manager, 'latest_imu_data'):
        print(f"\n📊 Internal data structure has {len(manager.latest_imu_data)} entries")
        for watch_name, data in manager.latest_imu_data.items():
            print(f"   {watch_name}: {data}")
    
    # Test 6b: Check high-performance manager internal state
    if hasattr(manager, 'high_perf_manager'):
        high_perf = manager.high_perf_manager
        print(f"\n🔍 High-Performance Manager State:")
        print(f"   Running: {high_perf.running}")
        print(f"   Latest Data: {len(high_perf.latest_data)} entries")
        for watch_name, data in high_perf.latest_data.items():
            print(f"     {watch_name}: {data}")
        
        # Check ring buffer
        if hasattr(high_perf, 'ring_buffer'):
            print(f"   Ring Buffer Size: {high_perf.ring_buffer.size}")
            print(f"   Ring Buffer Empty: {high_perf.ring_buffer.is_empty()}")
        
        # Check stream handler stats
        if hasattr(high_perf, 'stream_handler'):
            stats = high_perf.stream_handler.get_stats()
            print(f"   Stream Stats: {stats}")
    
    # Test 7: Performance stats
    if hasattr(manager, 'get_performance_stats'):
        try:
            stats = manager.get_performance_stats()
            print(f"\n📈 Performance Stats:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        except Exception as e:
            print(f"⚠️  Could not get performance stats: {e}")
    
    # Cleanup
    try:
        manager.cleanup()
        print("\n✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")
    
    return data_received

if __name__ == "__main__":
    success = test_imu_data_flow()
    if success:
        print("\n🎉 IMU data flow test completed successfully!")
    else:
        print("\n❌ IMU data flow test failed!")
    
    sys.exit(0 if success else 1)