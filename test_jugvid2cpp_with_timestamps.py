#!/usr/bin/env python3
"""
Standalone test for JugVid2cpp ball tracking with timestamps.

This script tests the JugVid2cpp interface and adds timestamps to the ball tracking data
when printed to the console.
"""

import sys
import time
import signal
from datetime import datetime
from typing import Dict, List

# Add the project root to the path
sys.path.append('.')

from apps.juggling_tracker.modules.jugvid2cpp_interface import JugVid2cppInterface

class TimestampedJugVid2cppTest:
    """Test class for JugVid2cpp with timestamped output."""
    
    def __init__(self):
        self.interface = None
        self.running = False
        self.ball_count_stats = {}
        self.start_time = None
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print(f"\n🛑 Received signal {signum}, stopping test...")
        self.stop()
        sys.exit(0)
    
    def start_test(self):
        """Start the JugVid2cpp test with timestamps."""
        print("🎯 JUGVID2CPP BALL TRACKING TEST WITH TIMESTAMPS")
        print("=" * 60)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Initialize the interface
            print("📦 Initializing JugVid2cpp interface...")
            self.interface = JugVid2cppInterface()
            
            if not self.interface.start():
                print("❌ Failed to start JugVid2cpp interface")
                return False
            
            print("✅ JugVid2cpp interface started successfully")
            print("🎥 Starting ball tracking with timestamps...")
            print("   Press Ctrl+C to stop")
            print("-" * 60)
            
            self.running = True
            self.start_time = time.time()
            
            # Main tracking loop
            frame_count = 0
            last_status_time = time.time()
            
            while self.running:
                try:
                    # Get the latest frame and ball data
                    _, _, _, video_frame = self.interface.get_frames()
                    identified_balls = self.interface.get_identified_balls()
                    
                    # Get current timestamp
                    current_time = time.time()
                    timestamp_str = datetime.fromtimestamp(current_time).strftime("%H:%M:%S.%f")[:-3]
                    elapsed_time = current_time - self.start_time
                    
                    # Print timestamped ball data if balls are detected
                    if identified_balls:
                        ball_count = len(identified_balls)
                        
                        # Update ball count statistics
                        if ball_count not in self.ball_count_stats:
                            self.ball_count_stats[ball_count] = 0
                        self.ball_count_stats[ball_count] += 1
                        
                        print(f"[{timestamp_str}] ({elapsed_time:.1f}s) 🏀 {ball_count} balls detected:")
                        
                        for i, ball in enumerate(identified_balls):
                            profile_id = ball.get('profile_id', 'unknown')
                            position_2d = ball.get('position', (0, 0))
                            depth_m = ball.get('depth_m', 0.0)
                            original_3d = ball.get('original_3d', (0, 0, 0))
                            
                            print(f"  └─ Ball {i+1}: {profile_id}")
                            print(f"     📍 2D: ({position_2d[0]}, {position_2d[1]}) px")
                            print(f"     📏 3D: ({original_3d[0]:.3f}, {original_3d[1]:.3f}, {original_3d[2]:.3f}) m")
                            print(f"     🎯 Depth: {depth_m:.3f} m")
                        
                        print()  # Empty line for readability
                    
                    frame_count += 1
                    
                    # Print status every 5 seconds
                    if current_time - last_status_time >= 5.0:
                        status = self.interface.get_status()
                        print(f"[{timestamp_str}] 📊 Status: Frames processed: {frame_count}, "
                              f"Queue size: {status['queue_size']}, "
                              f"Running: {status['is_running']}")
                        
                        if status['error_state']:
                            print(f"[{timestamp_str}] ⚠️  Error: {status['error_message']}")
                        
                        last_status_time = current_time
                    
                    # Small delay to prevent overwhelming output
                    time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"[{timestamp_str}] ❌ Error in tracking loop: {e}")
                    time.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self):
        """Stop the test and cleanup."""
        self.running = False
        
        if self.interface:
            print("\n🧹 Stopping JugVid2cpp interface...")
            self.interface.stop()
            
            # Print final statistics
            if self.start_time:
                total_time = time.time() - self.start_time
                print(f"\n📊 FINAL STATISTICS:")
                print(f"   ⏱️  Total runtime: {total_time:.1f} seconds")
                
                if self.ball_count_stats:
                    print(f"   🏀 Ball count distribution:")
                    for count, frames in sorted(self.ball_count_stats.items()):
                        percentage = (frames / sum(self.ball_count_stats.values())) * 100
                        print(f"      {count} balls: {frames} frames ({percentage:.1f}%)")
                else:
                    print(f"   ⚠️  No balls were detected during the test")
            
            print("✅ Test completed")

def main():
    """Main function to run the test."""
    test = TimestampedJugVid2cppTest()
    
    try:
        success = test.start_test()
        if success:
            print("🎉 Test completed successfully!")
        else:
            print("❌ Test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()