#!/usr/bin/env python3
"""
Debug-Enabled Juggling Tracker Launcher

This script launches the juggling tracker with comprehensive debug logging
to identify exactly where lag is occurring in the IMU streaming system.

Usage:
    # Enable debug mode and run
    IMU_DEBUG=1 python debug_juggling_tracker.py --webcam --watch-ips 192.168.1.101 192.168.1.102
    
    # Or enable debug programmatically
    python debug_juggling_tracker.py --debug --webcam --watch-ips 192.168.1.101 192.168.1.102

Author: Generated for JugVid2 project
Date: 2025-08-18
"""

import sys
import os
import time
import argparse
import threading
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import debug system first
from debug_imu_performance import (
    enable_debug_mode, disable_debug_mode, perf_logger, 
    debug_timing, DebugContext, log_ui_event, print_performance_report
)

# Import debug IMU manager
from debug_watch_imu_manager import enable_debug_imu_manager

def setup_debug_environment(debug_enabled: bool = False):
    """Setup debug environment."""
    if debug_enabled or os.environ.get('IMU_DEBUG', '0') == '1':
        enable_debug_mode()
        enable_debug_imu_manager()
        
        perf_logger.logger.info("🔍 DEBUG MODE ENABLED")
        perf_logger.logger.info("=" * 60)
        perf_logger.logger.info("Debug features:")
        perf_logger.logger.info("• Comprehensive timing measurements")
        perf_logger.logger.info("• Memory usage monitoring")
        perf_logger.logger.info("• Thread activity logging")
        perf_logger.logger.info("• Queue status monitoring")
        perf_logger.logger.info("• WebSocket event logging")
        perf_logger.logger.info("• UI performance tracking")
        perf_logger.logger.info("=" * 60)
        
        # Start performance monitoring thread
        monitor_thread = threading.Thread(target=performance_monitor, daemon=True, name="PerfMonitor")
        monitor_thread.start()
        
        return True
    else:
        perf_logger.logger.info("ℹ️  Debug mode disabled. Use --debug or IMU_DEBUG=1 to enable.")
        return False

def performance_monitor():
    """Background performance monitoring."""
    while True:
        time.sleep(10)  # Report every 10 seconds
        
        if perf_logger.debug_enabled:
            summary = perf_logger.get_performance_summary()
            
            # Log critical performance metrics
            perf_logger.logger.info("📊 PERFORMANCE CHECKPOINT:")
            perf_logger.logger.info(f"   Memory: {summary['memory_mb']:.1f}MB")
            perf_logger.logger.info(f"   CPU: {summary['cpu_percent']:.1f}%")
            perf_logger.logger.info(f"   Threads: {summary['thread_count']}")
            
            # Check for performance issues
            if summary['memory_mb'] > 500:
                perf_logger.logger.warning(f"⚠️  HIGH MEMORY USAGE: {summary['memory_mb']:.1f}MB")
            
            if summary['cpu_percent'] > 80:
                perf_logger.logger.warning(f"⚠️  HIGH CPU USAGE: {summary['cpu_percent']:.1f}%")
            
            if summary['thread_count'] > 20:
                perf_logger.logger.warning(f"⚠️  HIGH THREAD COUNT: {summary['thread_count']}")
            
            # Log slowest operations
            if summary['timing_stats']:
                slowest = max(summary['timing_stats'].items(), key=lambda x: x[1]['avg_ms'])
                if slowest[1]['avg_ms'] > 10:
                    perf_logger.logger.warning(f"⚠️  SLOWEST OPERATION: {slowest[0]} avg {slowest[1]['avg_ms']:.2f}ms")

@debug_timing("main_application_startup")
def main():
    """Main debug-enabled application launcher."""
    parser = argparse.ArgumentParser(description="Debug-enabled Juggling Tracker")
    
    # Debug options
    parser.add_argument('--debug', action='store_true', help='Enable comprehensive debug logging')
    parser.add_argument('--debug-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Debug logging level')
    
    # Application options (same as original)
    parser.add_argument('--webcam', action='store_true', help='Use webcam instead of RealSense')
    parser.add_argument('--watch-ips', nargs='+', help='Watch IP addresses for IMU streaming')
    parser.add_argument('--no-realsense', action='store_true', help='Disable RealSense camera')
    parser.add_argument('--camera-index', type=int, default=0, help='Webcam index')
    parser.add_argument('--jugvid2cpp', action='store_true', help='Use JugVid2cpp integration')
    parser.add_argument('--simulation', action='store_true', help='Enable video playback mode')
    parser.add_argument('--video-path', type=str, help='Path to video file for playback')
    parser.add_argument('--config-dir', type=str, help='Configuration directory')
    
    args = parser.parse_args()
    
    # Setup debug environment
    debug_enabled = setup_debug_environment(args.debug)
    
    try:
        with DebugContext("application_import", log_memory=True):
            # Import the main juggling tracker
            from juggling_tracker.main import main as juggling_main
            from juggling_tracker.main import JugglingTracker
            
        perf_logger.logger.info("🚀 Starting debug-enabled juggling tracker...")
        
        # Prepare arguments for the main application
        sys.argv = ['juggling_tracker']  # Reset argv
        
        if args.webcam:
            sys.argv.append('--webcam')
        if args.no_realsense:
            sys.argv.append('--no-realsense')
        if args.camera_index != 0:
            sys.argv.extend(['--camera-index', str(args.camera_index)])
        if args.jugvid2cpp:
            sys.argv.append('--jugvid2cpp')
        if args.simulation:
            sys.argv.append('--simulation')
        if args.video_path:
            sys.argv.extend(['--video-path', args.video_path])
        if args.config_dir:
            sys.argv.extend(['--config-dir', args.config_dir])
        if args.watch_ips:
            sys.argv.extend(['--watch-ips'] + args.watch_ips)
        
        perf_logger.logger.info(f"🎯 Launching with args: {sys.argv[1:]}")
        
        # Launch the main application with debug instrumentation
        with DebugContext("main_application_run", log_memory=True):
            result = juggling_main()
            
        perf_logger.logger.info("✅ Application completed successfully")
        return result
        
    except KeyboardInterrupt:
        perf_logger.logger.info("⚠️  Application interrupted by user")
        return 0
    except Exception as e:
        perf_logger.logger.error(f"❌ Application failed: {e}")
        import traceback
        perf_logger.logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    finally:
        if debug_enabled:
            perf_logger.logger.info("📊 Generating final performance report...")
            print_performance_report()

class DebugJugglingTracker:
    """Debug-instrumented wrapper for JugglingTracker."""
    
    def __init__(self, *args, **kwargs):
        with DebugContext("juggling_tracker_init", log_memory=True):
            # Import the original class
            from juggling_tracker.main import JugglingTracker
            self.tracker = JugglingTracker(*args, **kwargs)
            
            # Wrap key methods with debug instrumentation
            self._wrap_methods()
    
    def _wrap_methods(self):
        """Wrap key methods with debug instrumentation."""
        original_update_imu_display = getattr(self.tracker, 'update_imu_display', None)
        if original_update_imu_display:
            @debug_timing("update_imu_display")
            def debug_update_imu_display():
                with DebugContext("imu_display_update"):
                    return original_update_imu_display()
            
            self.tracker.update_imu_display = debug_update_imu_display
        
        # Wrap other critical methods
        original_process_frame = getattr(self.tracker, 'process_frame', None)
        if original_process_frame:
            @debug_timing("process_frame")
            def debug_process_frame(*args, **kwargs):
                with DebugContext("frame_processing"):
                    return original_process_frame(*args, **kwargs)
            
            self.tracker.process_frame = debug_process_frame
    
    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped tracker."""
        return getattr(self.tracker, name)

def create_debug_launcher_script():
    """Create a simple launcher script for easy debugging."""
    script_content = '''#!/bin/bash
# Debug IMU Streaming Launcher
# This script makes it easy to launch the juggling tracker with debug logging

echo "🔍 Starting Juggling Tracker with IMU Debug Logging"
echo "=================================================="

# Set debug environment
export IMU_DEBUG=1

# Launch with debug logging
python debug_juggling_tracker.py --debug --webcam --watch-ips 192.168.1.101 192.168.1.102

echo "=================================================="
echo "Debug session completed. Check imu_debug.log for detailed logs."
'''
    
    with open('debug_imu_launcher.sh', 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod('debug_imu_launcher.sh', 0o755)
    
    print("✅ Created debug_imu_launcher.sh")
    print("Usage: ./debug_imu_launcher.sh")

if __name__ == "__main__":
    # Create launcher script
    create_debug_launcher_script()
    
    # Run main application
    exit_code = main()
    sys.exit(exit_code)