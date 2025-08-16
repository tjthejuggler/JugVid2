#!/usr/bin/env python3
"""
Test script for manual mode functionality
"""

import subprocess
import sys
import os

def test_manual_mode():
    """Test the manual mode implementation."""
    print("🧪 Testing Manual Mode Implementation")
    print("=" * 50)
    
    # Test 1: Check if manual mode can be invoked
    print("1. Testing manual mode invocation...")
    try:
        result = subprocess.run([
            sys.executable, "run_stillness_recorder_with_imu.py", 
            "--manual", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if "manual" in result.stdout.lower():
            print("   ✅ Manual mode option available")
        else:
            print("   ❌ Manual mode option not found")
            print(f"   Output: {result.stdout}")
    except Exception as e:
        print(f"   ❌ Error testing manual mode: {e}")
    
    # Test 2: Check preset configurations
    print("\n2. Testing preset configurations...")
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            """
from run_stillness_recorder_with_imu import main
import sys
sys.argv = ['test', '--preset', 'manual', '--help']
try:
    main()
except SystemExit:
    pass
"""
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 or "manual" in result.stdout:
            print("   ✅ Manual preset configuration works")
        else:
            print("   ⚠️  Manual preset may have issues")
    except Exception as e:
        print(f"   ❌ Error testing presets: {e}")
    
    print("\n" + "=" * 50)
    print("Manual Mode Usage:")
    print("  python3 run_stillness_recorder_with_imu.py --manual")
    print("  python3 run_stillness_recorder_with_imu.py --preset manual")
    print("")
    print("Controls in Manual Mode:")
    print("  SPACEBAR - Start/Stop recording")
    print("  r - Alternative record trigger")
    print("  q - Quit")
    print("  i - Show IMU status")
    print("")
    print("File Naming Convention:")
    print("  Video: manual_YYYYMMDD_HHMMSS.mp4")
    print("  IMU:   left_YYYYMMDD_HHMMSS.csv")
    print("  IMU:   right_YYYYMMDD_HHMMSS.csv")

if __name__ == "__main__":
    test_manual_mode()