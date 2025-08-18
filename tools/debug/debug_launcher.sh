#!/bin/bash
# IMU Debug Launcher
echo "🔍 Starting IMU Debug Analysis..."

# Enable debug mode
export IMU_DEBUG=1

# Run with debug logging
python debug_juggling_tracker.py --debug --webcam --watch-ips 192.168.1.101 192.168.1.102 2>&1 | tee debug_output.log

echo "Debug analysis complete. Check debug_output.log and imu_debug.log for results."
