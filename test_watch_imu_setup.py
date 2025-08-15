#!/usr/bin/env python3
"""
Test script for Watch IMU Setup

This script tests the dual watch IMU functionality without requiring
the full stillness recorder setup. It's useful for verifying that
your Watch OS apps are working correctly.

Author: Generated for JugVid2 project
Date: 2025-08-15
"""

import time
import argparse
import sys
from watch_imu_manager import WatchIMUManager

def test_watch_discovery():
    """Test automatic watch discovery."""
    print("🔍 Testing watch discovery...")
    manager = WatchIMUManager("test_imu_data")
    
    discovered = manager.discover_watches()
    
    if discovered:
        print(f"✅ Discovery successful! Found {len(discovered)} watches:")
        for ip, name in discovered:
            print(f"   • {name} at {ip}")
        return discovered
    else:
        print("❌ No watches found during discovery")
        return []

def test_manual_connection(left_ip=None, right_ip=None):
    """Test manual watch connections."""
    print("🔗 Testing manual watch connections...")
    manager = WatchIMUManager("test_imu_data")
    
    success_count = 0
    
    if left_ip:
        print(f"   Testing left watch at {left_ip}...")
        if manager.add_watch("left", left_ip):
            print("   ✅ Left watch connected successfully")
            success_count += 1
        else:
            print("   ❌ Left watch connection failed")
    
    if right_ip:
        print(f"   Testing right watch at {right_ip}...")
        if manager.add_watch("right", right_ip):
            print("   ✅ Right watch connected successfully")
            success_count += 1
        else:
            print("   ❌ Right watch connection failed")
    
    return manager, success_count

def test_recording_cycle(manager, duration=5):
    """Test a complete recording cycle."""
    print(f"🎬 Testing {duration}-second recording cycle...")
    
    # Start monitoring
    manager.start_monitoring()
    
    try:
        # Show initial status
        print("📊 Initial status:")
        manager.print_status()
        
        # Start recording
        print(f"\n🎬 Starting IMU recording for {duration} seconds...")
        if manager.start_recording():
            print("✅ Recording started successfully")
            
            # Wait for recording duration
            for i in range(duration):
                print(f"   Recording... {i+1}/{duration}s")
                time.sleep(1)
            
            # Stop recording
            print("\n🛑 Stopping IMU recording...")
            if manager.stop_recording():
                print("✅ Recording stopped successfully")
                print("📊 Final status:")
                manager.print_status()
                return True
            else:
                print("❌ Failed to stop recording")
                return False
        else:
            print("❌ Failed to start recording")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        manager.stop_recording()
        return False
    finally:
        manager.stop_monitoring_thread()

def test_data_retrieval(manager):
    """Test IMU data retrieval and parsing."""
    print("📥 Testing data retrieval...")
    
    status = manager.get_connection_status()
    if status['total_recordings'] > 0:
        print(f"✅ Found {status['total_recordings']} recording sessions")
        print(f"📁 Data saved to: {manager.output_dir}")
        
        # List files in output directory
        import os
        if os.path.exists(manager.output_dir):
            files = os.listdir(manager.output_dir)
            if files:
                print("📄 Generated files:")
                for file in files:
                    print(f"   • {file}")
            else:
                print("⚠️  No files found in output directory")
        
        return True
    else:
        print("⚠️  No recordings found to test data retrieval")
        return False

def run_interactive_test():
    """Run an interactive test session."""
    print("🧪 Interactive Watch IMU Test")
    print("=" * 50)
    
    manager = WatchIMUManager("interactive_test_data")
    
    while True:
        print("\nChoose an option:")
        print("1. Discover watches")
        print("2. Add left watch manually")
        print("3. Add right watch manually")
        print("4. Show connection status")
        print("5. Test recording (5 seconds)")
        print("6. Test recording (10 seconds)")
        print("7. Quit")
        
        try:
            choice = input("\nEnter choice (1-7): ").strip()
            
            if choice == '1':
                discovered = manager.discover_watches()
                if discovered:
                    print("\nAuto-connect to discovered watches? (y/n): ", end="")
                    if input().lower().startswith('y'):
                        for ip, name in discovered:
                            if name.lower() in ['left', 'right']:
                                manager.add_watch(name.lower(), ip)
                            else:
                                watch_name = "left" if len(manager.watches) == 0 else "right"
                                manager.add_watch(watch_name, ip)
            
            elif choice == '2':
                ip = input("Enter left watch IP: ").strip()
                if ip:
                    manager.add_watch("left", ip)
            
            elif choice == '3':
                ip = input("Enter right watch IP: ").strip()
                if ip:
                    manager.add_watch("right", ip)
            
            elif choice == '4':
                manager.print_status()
            
            elif choice == '5':
                test_recording_cycle(manager, 5)
            
            elif choice == '6':
                test_recording_cycle(manager, 10)
            
            elif choice == '7':
                break
            
            else:
                print("Invalid choice. Please enter 1-7.")
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Cleanup
    manager.cleanup()
    print("✅ Interactive test completed")

def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test Watch IMU Setup")
    
    parser.add_argument('--mode', choices=['auto', 'manual', 'interactive'], default='auto',
                       help='Test mode (default: auto)')
    parser.add_argument('--left-watch', type=str, default=None,
                       help='Left watch IP address for manual mode')
    parser.add_argument('--right-watch', type=str, default=None,
                       help='Right watch IP address for manual mode')
    parser.add_argument('--duration', type=int, default=5,
                       help='Recording test duration in seconds (default: 5)')
    parser.add_argument('--skip-recording', action='store_true',
                       help='Skip the recording test')
    
    args = parser.parse_args()
    
    print("🧪 Watch IMU Setup Test")
    print("=" * 40)
    print(f"Mode: {args.mode}")
    print(f"Test duration: {args.duration}s")
    print("=" * 40)
    
    if args.mode == 'interactive':
        run_interactive_test()
        return 0
    
    manager = None
    success_count = 0
    
    try:
        if args.mode == 'auto':
            # Test discovery first
            discovered = test_watch_discovery()
            if discovered:
                manager = WatchIMUManager("auto_test_data")
                for ip, name in discovered:
                    if name.lower() in ['left', 'right']:
                        if manager.add_watch(name.lower(), ip):
                            success_count += 1
                    else:
                        watch_name = "left" if len(manager.watches) == 0 else "right"
                        if manager.add_watch(watch_name, ip):
                            success_count += 1
            else:
                print("❌ Auto mode failed - no watches discovered")
                return 1
        
        elif args.mode == 'manual':
            if not args.left_watch and not args.right_watch:
                print("❌ Manual mode requires --left-watch and/or --right-watch")
                return 1
            
            manager, success_count = test_manual_connection(args.left_watch, args.right_watch)
        
        if manager and success_count > 0:
            print(f"\n✅ Successfully connected to {success_count} watch(es)")
            
            if not args.skip_recording:
                # Test recording cycle
                if test_recording_cycle(manager, args.duration):
                    print("✅ Recording test passed")
                    
                    # Test data retrieval
                    if test_data_retrieval(manager):
                        print("✅ Data retrieval test passed")
                    else:
                        print("⚠️  Data retrieval test had issues")
                else:
                    print("❌ Recording test failed")
                    return 1
            else:
                print("⏭️  Skipping recording test")
            
            print("\n🎉 All tests completed successfully!")
            return 0
        else:
            print("❌ No watches connected - cannot run tests")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 1
    finally:
        if manager:
            manager.cleanup()

if __name__ == "__main__":
    exit(main())