#!/usr/bin/env python3
"""
Test the WatchIMUManager data conversion specifically
"""

import asyncio
import websockets
import json
import sys
import time
from datetime import datetime
from core.imu.watch_imu_manager import IMUStreamHandler
from queue import Queue

async def test_conversion(watch_ip):
    """Test the actual conversion logic used by WatchIMUManager."""
    
    # Create the same setup as WatchIMUManager
    data_queue = Queue(maxsize=100)
    stream_handler = IMUStreamHandler([watch_ip], data_queue)
    
    print(f"🔍 Testing WatchIMUManager conversion with {watch_ip}")
    print("=" * 60)
    
    # Connect directly and test conversion
    uri = f"ws://{watch_ip}:8081/imu"
    partial_data = {}  # Same as in the handler
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            print("📡 Testing conversion (first 10 messages):")
            print("-" * 60)
            
            message_count = 0
            converted_count = 0
            
            while message_count < 20:  # Test more messages
                try:
                    message = await websocket.recv()
                    message_count += 1
                    
                    # Parse raw data
                    raw_data = json.loads(message)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    print(f"Message #{message_count} at {timestamp}:")
                    print(f"  Raw: {raw_data}")
                    
                    # Test the conversion method
                    converted_data = stream_handler._convert_android_format(raw_data, watch_ip, partial_data)
                    
                    if converted_data:
                        converted_count += 1
                        print(f"  ✅ Converted: {converted_data}")
                        print(f"     Accel: ({converted_data['accel_x']:.3f}, {converted_data['accel_y']:.3f}, {converted_data['accel_z']:.3f})")
                        print(f"     Gyro:  ({converted_data['gyro_x']:.3f}, {converted_data['gyro_y']:.3f}, {converted_data['gyro_z']:.3f})")
                    else:
                        print(f"  ⏳ Waiting for more data (partial)")
                    
                    print(f"  Partial data keys: {list(partial_data.keys())}")
                    print("-" * 40)
                    
                except websockets.exceptions.ConnectionClosedError:
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
            
            print(f"\n📊 Summary:")
            print(f"   Total messages: {message_count}")
            print(f"   Converted records: {converted_count}")
            print(f"   Conversion rate: {converted_count/message_count*100:.1f}%")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_conversion.py <watch_ip>")
        sys.exit(1)
    
    watch_ip = sys.argv[1]
    asyncio.run(test_conversion(watch_ip))

if __name__ == "__main__":
    main()