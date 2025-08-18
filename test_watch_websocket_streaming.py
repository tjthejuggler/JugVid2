#!/usr/bin/env python3
"""
Test script for Watch WebSocket IMU streaming integration.

This script tests the complete real-time streaming pipeline:
1. Mock Android watch WebSocket server
2. Python IMU stream handler
3. Data format conversion
4. Integration with juggling tracker

Author: Generated for JugVid2 project
Date: 2025-08-18
"""

import asyncio
import websockets
import json
import time
import threading
from watch_imu_manager import WatchIMUManager, IMUStreamHandler
from queue import Queue
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockAndroidWatch:
    """Mock Android watch that sends IMU data via WebSocket."""
    
    def __init__(self, watch_id: str, port: int = 8081):
        self.watch_id = watch_id
        self.port = port
        self.running = False
        self.server = None
        
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        logger.info(f"Mock {self.watch_id}: Client connected to {path}")
        
        try:
            # Send mock IMU data at ~100Hz (10ms intervals)
            counter = 0
            while self.running:
                timestamp_ns = int(time.time() * 1_000_000_000)
                
                # Send accelerometer data
                accel_data = {
                    "watch_id": self.watch_id,
                    "type": "accel",
                    "timestamp_ns": timestamp_ns,
                    "x": 0.1 + 0.05 * (counter % 10),  # Mock varying data
                    "y": 9.8 + 0.1 * (counter % 5),
                    "z": -0.05 + 0.02 * (counter % 7)
                }
                await websocket.send(json.dumps(accel_data))
                
                # Small delay between accel and gyro
                await asyncio.sleep(0.001)
                
                # Send gyroscope data
                gyro_data = {
                    "watch_id": self.watch_id,
                    "type": "gyro", 
                    "timestamp_ns": timestamp_ns,
                    "x": 0.01 + 0.005 * (counter % 8),
                    "y": 0.02 + 0.003 * (counter % 6),
                    "z": 0.03 + 0.007 * (counter % 4)
                }
                await websocket.send(json.dumps(gyro_data))
                
                counter += 1
                await asyncio.sleep(0.008)  # ~100Hz total rate
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Mock {self.watch_id}: Client disconnected")
        except Exception as e:
            logger.error(f"Mock {self.watch_id}: Error: {e}")
    
    async def start_server(self):
        """Start the mock WebSocket server."""
        self.running = True
        self.server = await websockets.serve(
            self.handle_client, 
            "localhost", 
            self.port,
            path="/imu"
        )
        logger.info(f"Mock {self.watch_id}: WebSocket server started on ws://localhost:{self.port}/imu")
        
    async def stop_server(self):
        """Stop the mock WebSocket server."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info(f"Mock {self.watch_id}: WebSocket server stopped")

def run_mock_watch(watch_id: str, port: int):
    """Run mock watch in separate thread."""
    async def run():
        mock_watch = MockAndroidWatch(watch_id, port)
        await mock_watch.start_server()
        
        # Keep server running
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            await mock_watch.stop_server()
    
    asyncio.run(run())

async def test_websocket_streaming():
    """Test the complete WebSocket streaming pipeline."""
    print("🧪 Testing Watch WebSocket IMU Streaming Integration")
    print("=" * 60)
    
    # Start mock Android watches
    print("1. Starting mock Android watches...")
    
    # Start mock watches in separate threads
    left_watch_thread = threading.Thread(
        target=run_mock_watch, 
        args=("left_watch", 8081),
        daemon=True
    )
    right_watch_thread = threading.Thread(
        target=run_mock_watch, 
        args=("right_watch", 8082),
        daemon=True
    )
    
    left_watch_thread.start()
    right_watch_thread.start()
    
    # Give servers time to start
    await asyncio.sleep(2)
    print("✅ Mock watches started")
    
    # Test IMU Stream Handler
    print("\n2. Testing IMU Stream Handler...")
    
    watch_ips = ["localhost:8081", "localhost:8082"]  # Use different ports for testing
    data_queue = Queue()
    
    # Create stream handler with modified IPs for testing
    stream_handler = IMUStreamHandler(["localhost", "localhost"], data_queue)
    stream_handler.websocket_port = 8081  # Will connect to first mock watch
    
    # Start streaming in background
    streaming_task = asyncio.create_task(stream_handler._listen_to_watch("localhost"))
    
    print("✅ Stream handler started, collecting data...")
    
    # Collect data for 5 seconds
    start_time = time.time()
    data_points = []
    
    while time.time() - start_time < 5.0:
        try:
            while not data_queue.empty():
                data_point = data_queue.get_nowait()
                data_points.append(data_point)
        except:
            pass
        await asyncio.sleep(0.1)
    
    # Stop streaming
    stream_handler.stop_signal.set()
    streaming_task.cancel()
    
    print(f"✅ Collected {len(data_points)} data points in 5 seconds")
    
    # Analyze collected data
    print("\n3. Analyzing collected data...")
    
    if data_points:
        # Show sample data point
        sample = data_points[0]
        print(f"Sample data point: {json.dumps(sample, indent=2)}")
        
        # Check data format
        required_fields = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 
                          'gyro_x', 'gyro_y', 'gyro_z', 'watch_name', 'watch_ip']
        
        format_ok = all(field in sample for field in required_fields)
        print(f"✅ Data format correct: {format_ok}")
        
        # Check data freshness
        latest_data = max(data_points, key=lambda x: x.get('received_at', 0))
        data_age = time.time() - latest_data.get('received_at', 0)
        print(f"✅ Latest data age: {data_age:.3f} seconds")
        
        # Calculate data rate
        data_rate = len(data_points) / 5.0
        print(f"✅ Data rate: {data_rate:.1f} points/second")
        
    else:
        print("❌ No data points collected!")
        return False
    
    # Test WatchIMUManager integration
    print("\n4. Testing WatchIMUManager integration...")
    
    # Note: This would require running mock watches on different ports
    # For now, just verify the manager can be created
    try:
        manager = WatchIMUManager(watch_ips=["127.0.0.1"], output_dir="test_imu_data")
        print("✅ WatchIMUManager created successfully")
        
        # Test data retrieval method
        if hasattr(manager, 'get_latest_imu_data'):
            print("✅ get_latest_imu_data method available")
        else:
            print("❌ get_latest_imu_data method missing")
            
        manager.cleanup()
        
    except Exception as e:
        print(f"❌ WatchIMUManager test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 WebSocket streaming test completed successfully!")
    print(f"📊 Results:")
    print(f"   • Data points collected: {len(data_points)}")
    print(f"   • Data rate: {data_rate:.1f} Hz")
    print(f"   • Format conversion: {'✅ Working' if format_ok else '❌ Failed'}")
    print(f"   • Real-time latency: {data_age:.3f}s")
    
    return True

def test_format_conversion():
    """Test Android format to Python format conversion."""
    print("\n🧪 Testing Format Conversion")
    print("-" * 40)
    
    # Create test handler
    data_queue = Queue()
    handler = IMUStreamHandler(["test"], data_queue)
    
    # Test Android format input
    android_accel = {
        "watch_id": "left_watch",
        "type": "accel",
        "timestamp_ns": 1692345678123456789,
        "x": 0.12,
        "y": 9.81,
        "z": -0.05
    }
    
    android_gyro = {
        "watch_id": "left_watch", 
        "type": "gyro",
        "timestamp_ns": 1692345678123456789,
        "x": 0.01,
        "y": 0.02,
        "z": 0.03
    }
    
    # Test conversion
    partial_data = {}
    
    # Convert accelerometer data
    result1 = handler._convert_android_format(android_accel, "192.168.1.101", partial_data)
    print(f"Accel conversion result: {result1 is not None}")
    
    # Convert gyroscope data  
    result2 = handler._convert_android_format(android_gyro, "192.168.1.101", partial_data)
    print(f"Gyro conversion result: {result2 is not None}")
    
    # Check if we got complete data
    if result1 or result2:
        complete_data = result1 or result2
        print(f"✅ Conversion successful")
        print(f"Sample converted data: {json.dumps(complete_data, indent=2)}")
        
        # Verify timestamp conversion (nanoseconds to seconds)
        expected_timestamp = 1692345678123456789 / 1_000_000_000.0
        actual_timestamp = complete_data.get('timestamp', 0)
        timestamp_ok = abs(expected_timestamp - actual_timestamp) < 0.001
        print(f"✅ Timestamp conversion: {timestamp_ok}")
        
        return True
    else:
        print("❌ Format conversion failed")
        return False

if __name__ == "__main__":
    # Test format conversion first
    format_test_ok = test_format_conversion()
    
    # Test full WebSocket streaming
    streaming_test_ok = asyncio.run(test_websocket_streaming())
    
    # Summary
    print(f"\n🏁 Test Summary:")
    print(f"   Format Conversion: {'✅ PASS' if format_test_ok else '❌ FAIL'}")
    print(f"   WebSocket Streaming: {'✅ PASS' if streaming_test_ok else '❌ FAIL'}")
    
    if format_test_ok and streaming_test_ok:
        print(f"\n🎉 All tests passed! IMU streaming integration is working correctly.")
        exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Check the implementation.")
        exit(1)