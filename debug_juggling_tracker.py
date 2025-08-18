#!/usr/bin/env python3
"""
Debug script for Juggling Tracker - Comprehensive issue diagnosis and fixes

This script helps identify and fix:
1. Severe lag problems
2. RealSense camera initialization issues
3. GUI watch connection problems
4. Performance bottlenecks

Usage:
    python debug_juggling_tracker.py --debug --debug-performance --debug-camera --debug-imu --force-camera-restart
"""

import sys
import os
import time
import subprocess

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_system_performance():
    """Check system performance and identify potential lag sources."""
    print("🔍 SYSTEM PERFORMANCE CHECK")
    print("=" * 50)
    
    # Check CPU usage
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        print(f"CPU Usage: {cpu_percent}%")
        print(f"Memory Usage: {memory.percent}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
        
        if cpu_percent > 80:
            print("⚠️  HIGH CPU USAGE detected - this could cause lag")
        if memory.percent > 85:
            print("⚠️  HIGH MEMORY USAGE detected - this could cause lag")
            
    except ImportError:
        print("psutil not available - install with: pip install psutil")
    
    # Check for running processes that might interfere
    print("\n🔍 Checking for interfering processes...")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        interfering_processes = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['realsense', 'camera', 'opencv', 'juggling']):
                if 'python' in line or 'realsense' in line:
                    interfering_processes.append(line.strip())
        
        if interfering_processes:
            print("⚠️  Found potentially interfering processes:")
            for proc in interfering_processes[:5]:  # Show first 5
                print(f"   {proc}")
        else:
            print("✅ No interfering processes found")
            
    except Exception as e:
        print(f"Could not check processes: {e}")

def check_camera_connections():
    """Check camera connections and suggest fixes."""
    print("\n🎥 CAMERA CONNECTION CHECK")
    print("=" * 50)
    
    # Check for RealSense devices
    try:
        import pyrealsense2 as rs
        ctx = rs.context()
        devices = ctx.query_devices()
        
        if len(devices) == 0:
            print("❌ No RealSense devices found")
            print("💡 SOLUTIONS:")
            print("   1. Unplug and replug the RealSense camera")
            print("   2. Try a different USB port (preferably USB 3.0)")
            print("   3. Restart the RealSense service:")
            print("      sudo systemctl restart realsense")
            print("   4. Use --force-camera-restart flag")
        else:
            print(f"✅ Found {len(devices)} RealSense device(s)")
            for i, device in enumerate(devices):
                print(f"   Device {i}: {device.get_info(rs.camera_info.name)}")
                print(f"   Serial: {device.get_info(rs.camera_info.serial_number)}")
                
    except ImportError:
        print("⚠️  pyrealsense2 not available - RealSense support disabled")
    except Exception as e:
        print(f"❌ RealSense check failed: {e}")
        print("💡 Try: sudo systemctl restart realsense")
    
    # Check for webcam devices
    print("\n🔍 Checking webcam devices...")
    try:
        import cv2
        for i in range(5):  # Check first 5 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"✅ Webcam found at index {i}: {frame.shape}")
                cap.release()
            else:
                break
    except Exception as e:
        print(f"Webcam check failed: {e}")

def check_imu_dependencies():
    """Check IMU-related dependencies and network connectivity."""
    print("\n📱 IMU SYSTEM CHECK")
    print("=" * 50)
    
    # Check required packages
    required_packages = ['websockets', 'requests', 'asyncio']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"💡 Install missing packages: pip install {' '.join(missing_packages)}")
    
    # Check network connectivity
    print("\n🔍 Network connectivity check...")
    test_ips = ["192.168.1.1", "8.8.8.8"]  # Router and Google DNS
    
    for ip in test_ips:
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '2', ip], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Network connectivity to {ip}: OK")
            else:
                print(f"❌ Network connectivity to {ip}: FAILED")
        except Exception as e:
            print(f"⚠️  Could not test connectivity to {ip}: {e}")

def run_performance_test():
    """Run a quick performance test to identify bottlenecks."""
    print("\n⏱️  PERFORMANCE TEST")
    print("=" * 50)
    
    # Test frame processing speed
    try:
        import cv2
        import numpy as np
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test basic operations
        operations = [
            ("Image copy", lambda: test_image.copy()),
            ("Color conversion", lambda: cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)),
            ("Gaussian blur", lambda: cv2.GaussianBlur(test_image, (15, 15), 0)),
            ("Resize", lambda: cv2.resize(test_image, (320, 240))),
        ]
        
        for name, operation in operations:
            start_time = time.time()
            for _ in range(100):  # Run 100 times
                operation()
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 100 * 1000  # ms per operation
            print(f"{name}: {avg_time:.2f}ms per operation")
            
            if avg_time > 10:  # If operation takes > 10ms
                print(f"⚠️  {name} is slow - potential bottleneck")
                
    except Exception as e:
        print(f"Performance test failed: {e}")

def suggest_optimizations():
    """Suggest optimizations based on system analysis."""
    print("\n💡 OPTIMIZATION SUGGESTIONS")
    print("=" * 50)
    
    print("1. LAG REDUCTION:")
    print("   • Use --debug-performance to identify slow frames")
    print("   • Reduce frame processing frequency (increase timer interval)")
    print("   • Disable unnecessary visual overlays")
    print("   • Use webcam mode for testing (lower resolution)")
    
    print("\n2. CAMERA ISSUES:")
    print("   • Always use --force-camera-restart flag")
    print("   • Unplug/replug RealSense before starting")
    print("   • Try different USB ports (USB 3.0 preferred)")
    print("   • Use webcam as fallback: --webcam")
    
    print("\n3. IMU CONNECTION:")
    print("   • Ensure watches and computer are on same WiFi")
    print("   • Test watch connectivity manually first")
    print("   • Use --debug-imu to see detailed connection logs")
    print("   • Check firewall settings (allow port 8080-8083)")
    
    print("\n4. PERFORMANCE TUNING:")
    print("   • Close other applications using camera/CPU")
    print("   • Use lower resolution modes when possible")
    print("   • Enable only necessary tracking features")
    print("   • Monitor frame timing with --debug-performance")

def main():
    """Main debug function."""
    print("🐛 JUGGLING TRACKER DEBUG TOOL")
    print("=" * 60)
    print("This tool will help identify and fix common issues:")
    print("• Severe lag problems")
    print("• RealSense camera initialization issues") 
    print("• GUI watch connection problems")
    print("• Performance bottlenecks")
    print("=" * 60)
    
    # Run all checks
    check_system_performance()
    check_camera_connections()
    check_imu_dependencies()
    run_performance_test()
    suggest_optimizations()
    
    print("\n🚀 RECOMMENDED COMMAND TO RUN JUGGLING TRACKER:")
    print("=" * 60)
    print("python apps/juggling_tracker/main.py \\")
    print("    --debug \\")
    print("    --debug-performance \\")
    print("    --debug-camera \\")
    print("    --debug-imu \\")
    print("    --force-camera-restart \\")
    print("    --webcam  # Use this if RealSense has issues")
    
    print("\n📋 DEBUGGING STEPS:")
    print("1. Run the command above")
    print("2. Watch console output for:")
    print("   • 🎥 [DEBUG] messages for camera issues")
    print("   • ⏱️ [DEBUG] messages for performance problems")
    print("   • 📱 [DEBUG] messages for IMU connection issues")
    print("3. Look for SLOW FRAME warnings (>50ms)")
    print("4. Check IMU connection status in GUI")
    print("5. Report specific error messages for further help")

if __name__ == "__main__":
    main()