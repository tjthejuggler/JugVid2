#!/usr/bin/env python3
"""
Debug Watch Data - Raw Data Inspector

This script connects to a watch and shows the raw WebSocket messages
to help diagnose data format issues.
"""

import asyncio
import websockets
import json
import sys
import time
from datetime import datetime

async def debug_watch_data(watch_ip):
    """Connect to watch and display raw WebSocket messages."""
    uri = f"ws://{watch_ip}:8081/imu"
    
    print(f"🔍 Connecting to {uri} for raw data inspection...")
    print("=" * 80)
    
    message_count = 0
    start_time = time.time()
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            print("📡 Receiving raw messages (showing first 10):")
            print("-" * 80)
            
            while message_count < 10:  # Show first 10 messages
                try:
                    message = await websocket.recv()
                    message_count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    print(f"Message #{message_count} at {timestamp}:")
                    print(f"Raw: {message}")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(message)
                        print(f"JSON: {json.dumps(data, indent=2)}")
                        
                        # Show data types and values
                        print("Field Analysis:")
                        for key, value in data.items():
                            print(f"  {key}: {value} (type: {type(value).__name__})")
                            
                    except json.JSONDecodeError:
                        print("❌ Not valid JSON")
                    
                    print("-" * 40)
                    
                except websockets.exceptions.ConnectionClosedError:
                    print("❌ Connection closed by watch")
                    break
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
                    break
            
            # Continue for a few more seconds to see pattern
            print(f"\n📊 Continuing to monitor for 5 more seconds...")
            end_time = time.time() + 5
            
            while time.time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message_count += 1
                    
                    # Just show a summary for remaining messages
                    try:
                        data = json.loads(message)
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        msg_type = data.get('type', 'unknown')
                        x, y, z = data.get('x', 0), data.get('y', 0), data.get('z', 0)
                        print(f"{timestamp} | {msg_type:5} | ({x:8.3f}, {y:8.3f}, {z:8.3f})")
                    except json.JSONDecodeError:
                        print(f"{timestamp} | Non-JSON: {message[:50]}...")
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosedError:
                    break
                    
    except ConnectionRefusedError:
        print(f"❌ Connection refused to {uri}")
        print("   Make sure the watch app is running and WebSocket streaming is enabled")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    print(f"\n📈 Total messages received: {message_count}")
    print(f"⏱️  Total time: {time.time() - start_time:.1f} seconds")

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_watch_data.py <watch_ip>")
        print("Example: python debug_watch_data.py 10.200.169.205")
        sys.exit(1)
    
    watch_ip = sys.argv[1]
    print(f"🔍 Debug Watch Data Inspector")
    print(f"📱 Target: {watch_ip}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(debug_watch_data(watch_ip))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()