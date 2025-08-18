#!/bin/bash
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
