#!/usr/bin/env python3
"""
Runner script for Enhanced Stillness Recorder with IMU

This script provides an easy way to launch the stillness recorder with
Watch OS IMU integration using predefined configurations.

Author: Generated for JugVid2 project
Date: 2025-08-15
"""

import sys
import os
import argparse
from stillness_recorder_with_imu import StillnessRecorderWithIMU

def main():
    """Main runner with enhanced integration guide configurations."""
    parser = argparse.ArgumentParser(description="Run Enhanced Stillness Recorder with IMU using Complete Python Integration Guide")
    
    # Preset configurations
    parser.add_argument('--preset', choices=['juggling', 'demo', 'test', 'manual'], default='juggling',
                       help='Use preset configuration (default: juggling)')
    
    # Manual mode
    parser.add_argument('--manual', action='store_true',
                       help='Enable manual recording mode (disables motion detection)')
    
    # Enhanced IMU arguments (from integration guide)
    parser.add_argument('--watch-ips', type=str, nargs='+', default=None,
                       help='List of watch IP addresses (e.g., 192.168.1.101 192.168.1.102)')
    parser.add_argument('--left-watch', type=str, default=None,
                       help='Left watch IP address')
    parser.add_argument('--right-watch', type=str, default=None,
                       help='Right watch IP address')
    parser.add_argument('--discover-watches', action='store_true',
                       help='Auto-discover watches using integration guide functionality')
    parser.add_argument('--discover', action='store_true',
                       help='Auto-discover watches on network (legacy)')
    parser.add_argument('--disable-imu', action='store_true',
                       help='Disable IMU functionality')
    parser.add_argument('--no-imu', action='store_true',
                       help='Disable IMU functionality (legacy)')
    parser.add_argument('--imu-timeout', type=int, default=5,
                       help='IMU connection timeout in seconds (default: 5)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Custom output directory')
    parser.add_argument('--label', type=str, default=None,
                       help='Recording label to add to filenames (e.g., "cascade", "flash")')
    
    args = parser.parse_args()
    
    # Handle legacy arguments
    if args.discover:
        args.discover_watches = True
    if args.no_imu:
        args.disable_imu = True
    
    # Prepare watch IPs list
    watch_ips = []
    if args.watch_ips:
        watch_ips.extend(args.watch_ips)
    if args.left_watch and args.left_watch not in watch_ips:
        watch_ips.append(args.left_watch)
    if args.right_watch and args.right_watch not in watch_ips:
        watch_ips.append(args.right_watch)
    
    # Define presets
    presets = {
        'juggling': {
            'record_duration': 15.0,
            'motion_threshold': 1200,
            'stillness_threshold': 400,
            'stillness_duration': 2.5,
            'camera_width': 1280,
            'camera_height': 720,
            'camera_fps': 30,
            'output_dir': 'juggling_recordings',
            'manual_mode': False
        },
        'demo': {
            'record_duration': 8.0,
            'motion_threshold': 800,
            'stillness_threshold': 300,
            'stillness_duration': 2.0,
            'camera_width': 640,
            'camera_height': 480,
            'camera_fps': 30,
            'output_dir': 'demo_recordings',
            'manual_mode': False
        },
        'test': {
            'record_duration': 5.0,
            'motion_threshold': 500,
            'stillness_threshold': 200,
            'stillness_duration': 1.5,
            'camera_width': 640,
            'camera_height': 480,
            'camera_fps': 30,
            'output_dir': 'test_recordings',
            'manual_mode': False
        },
        'manual': {
            'record_duration': 10.0,
            'motion_threshold': 0,  # Disabled in manual mode
            'stillness_threshold': 0,  # Disabled in manual mode
            'stillness_duration': 0,  # Disabled in manual mode
            'camera_width': 1280,
            'camera_height': 720,
            'camera_fps': 30,
            'output_dir': 'manual_recordings',
            'manual_mode': True
        }
    }
    
    # Handle manual mode override
    if args.manual:
        args.preset = 'manual'
    
    # Get preset configuration
    config = presets[args.preset].copy()
    
    # Apply overrides
    if args.output_dir:
        config['output_dir'] = args.output_dir
    
    print(f"🚀 Starting Enhanced Stillness Recorder with '{args.preset}' preset")
    print(f"📁 Output directory: {config['output_dir']}")
    print(f"📹 Record duration: {config['record_duration']}s")
    if config['manual_mode']:
        print("🎮 Manual recording mode: Motion detection DISABLED")
        print("   Use SPACEBAR to start/stop recordings")
    else:
        print(f"🎯 Motion threshold: {config['motion_threshold']}")
        print(f"⏱️  Stillness duration: {config['stillness_duration']}s")
    print(f"📱 IMU enabled: {not args.disable_imu}")
    
    # Create enhanced recorder with integration guide functionality
    recorder = StillnessRecorderWithIMU(
        record_duration=config['record_duration'],
        motion_threshold=config['motion_threshold'],
        stillness_threshold=config['stillness_threshold'],
        stillness_duration=config['stillness_duration'],
        output_dir=config['output_dir'],
        camera_width=config['camera_width'],
        camera_height=config['camera_height'],
        camera_fps=config['camera_fps'],
        enable_imu=not args.disable_imu,
        watch_ips=watch_ips,
        manual_mode=config['manual_mode'],
        default_label=args.label
    )
    
    # Configure enhanced IMU if enabled
    if not args.disable_imu and recorder.imu_manager:
        if args.discover_watches:
            print("🔍 Discovering watches using integration guide functionality...")
            discovered = recorder.imu_manager.discover_watches()
            if discovered:
                print(f"✅ Found {len(discovered)} watches using enhanced discovery")
                # Auto-assign discovered watches
                watch_names = ["left", "right"]
                for i, (ip, port) in enumerate(discovered.items()):
                    if i < len(watch_names):
                        recorder.imu_manager.add_watch(watch_names[i], ip, port)
                        print(f"   ✅ Auto-assigned {watch_names[i]} watch to {ip}:{port}")
            else:
                print("⚠️  No watches found during enhanced discovery")
        else:
            # Manual configuration
            if args.left_watch:
                success = recorder.imu_manager.add_watch("left", args.left_watch)
                print(f"{'✅' if success else '⚠️'} Left watch: {args.left_watch}")
            
            if args.right_watch:
                success = recorder.imu_manager.add_watch("right", args.right_watch)
                print(f"{'✅' if success else '⚠️'} Right watch: {args.right_watch}")
            
            if not watch_ips:
                print("💡 No watch IPs specified. You can:")
                print("   - Use --discover-watches to auto-find watches")
                print("   - Use --watch-ips to specify multiple IPs")
                print("   - Use --left-watch and --right-watch to specify individual IPs")
                print("   - Configure watches in the GUI after startup")
        
        # Print enhanced IMU status
        if recorder.imu_manager.watches:
            print("\n📱 Enhanced IMU Configuration:")
            recorder.imu_manager.print_status()
        else:
            print("⚠️  No watches configured for enhanced IMU functionality")
    
    print("\n" + "="*60)
    print("CONTROLS:")
    print("  q - Quit")
    if config['manual_mode']:
        print("  SPACEBAR - Start/Stop recording (Manual Mode)")
        print("  r - Manual record trigger (alternative)")
    else:
        print("  r - Manual record trigger")
        print("  c - Reset movement detection")
        print("  m - Toggle motion mask")
    print("  i - Show IMU status")
    print("  h - Toggle help overlay")
    print("="*60)
    
    # Run the recorder
    try:
        success = recorder.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())