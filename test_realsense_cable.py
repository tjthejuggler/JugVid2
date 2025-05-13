import pyrealsense2 as rs
import time
import numpy as np
import cv2

def test_usb_connection():
    """Test the USB connection quality with the RealSense camera."""
    print("\n=== RealSense Camera USB Connection Test ===\n")
    
    # Create a context to discover RealSense devices
    ctx = rs.context()
    devices = list(ctx.query_devices())
    
    if not devices:
        print("❌ ERROR: No RealSense devices detected!")
        return False
    
    # Print device information
    print(f"✅ Found {len(devices)} RealSense device(s)")
    for i, dev in enumerate(devices):
        print(f"\nDevice {i+1}:")
        print(f"  Name: {dev.get_info(rs.camera_info.name)}")
        print(f"  Serial Number: {dev.get_info(rs.camera_info.serial_number)}")
        
        # Check USB connection type if available
        try:
            usb_type = dev.get_info(rs.camera_info.usb_type_descriptor)
            print(f"  USB Type: {usb_type}")
        except:
            print("  USB Type: Unknown")
            
        # Check firmware version
        try:
            fw_version = dev.get_info(rs.camera_info.firmware_version)
            print(f"  Firmware Version: {fw_version}")
        except:
            print("  Firmware Version: Unknown")
    
    print("\n=== Testing Data Transfer Rates ===\n")
    
    # Test different stream configurations
    configs_to_test = [
        {"name": "Depth Only (Low Res)", "depth": (480, 270, 30)},
        {"name": "Depth Only (Medium Res)", "depth": (640, 480, 30)},
        {"name": "Depth + Color (Low Res)", "depth": (480, 270, 30), "color": (480, 270, 30)},
        {"name": "Depth + Color (Medium Res)", "depth": (640, 480, 30), "color": (640, 480, 30)}
    ]
    
    results = []
    
    for config_info in configs_to_test:
        print(f"\nTesting: {config_info['name']}")
        
        # Create pipeline and config
        pipeline = rs.pipeline()
        config = rs.config()
        
        # Configure streams based on test case
        if "depth" in config_info:
            width, height, fps = config_info["depth"]
            config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            print(f"  Configured Depth: {width}x{height} @ {fps}fps")
            
        if "color" in config_info:
            width, height, fps = config_info["color"]
            config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            print(f"  Configured Color: {width}x{height} @ {fps}fps")
        
        # Try to start the pipeline
        try:
            print("  Starting pipeline...")
            profile = pipeline.start(config)
            print("  Pipeline started successfully")
            
            # Test frame retrieval
            print("  Testing frame retrieval (5 seconds)...")
            start_time = time.time()
            frame_count = 0
            timeout_count = 0
            error_count = 0
            
            # Run for 5 seconds
            while time.time() - start_time < 5:
                try:
                    # Try to get frames with a short timeout
                    frames = pipeline.wait_for_frames(timeout_ms=1000)
                    frame_count += 1
                    
                    # Check if all expected frames are available
                    if "depth" in config_info and not frames.get_depth_frame():
                        print("  ⚠️ Missing depth frame")
                    if "color" in config_info and not frames.get_color_frame():
                        print("  ⚠️ Missing color frame")
                        
                except RuntimeError as e:
                    if "Frame didn't arrive" in str(e):
                        timeout_count += 1
                    else:
                        error_count += 1
                        print(f"  ❌ Error: {str(e)}")
            
            # Calculate metrics
            duration = time.time() - start_time
            fps = frame_count / duration
            
            print(f"  Results:")
            print(f"    Frames received: {frame_count}")
            print(f"    Timeouts: {timeout_count}")
            print(f"    Other errors: {error_count}")
            print(f"    Effective FPS: {fps:.2f}")
            
            # Store results
            results.append({
                "config": config_info["name"],
                "success": True,
                "frames": frame_count,
                "timeouts": timeout_count,
                "errors": error_count,
                "fps": fps
            })
            
            # Stop the pipeline
            pipeline.stop()
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            results.append({
                "config": config_info["name"],
                "success": False,
                "error": str(e)
            })
            try:
                pipeline.stop()
            except:
                pass
    
    # Print summary
    print("\n=== Test Summary ===\n")
    for result in results:
        if result["success"]:
            status = "✅ PASS" if result["timeouts"] == 0 and result["fps"] > 25 else "⚠️ PARTIAL"
            if result["timeouts"] > 10:
                status = "❌ FAIL"
            print(f"{status} - {result['config']}: {result['fps']:.2f} FPS, {result['timeouts']} timeouts")
        else:
            print(f"❌ FAIL - {result['config']}: {result['error']}")
    
    # Provide cable recommendations
    print("\n=== Cable Recommendations ===\n")
    
    any_failure = any(not r["success"] or r["timeouts"] > 10 for r in results)
    high_timeouts = any(r["success"] and 5 <= r["timeouts"] <= 10 for r in results)
    
    if any_failure:
        print("❌ Your cable appears to be INCOMPATIBLE with the RealSense camera.")
        print("Recommendations:")
        print("1. Use a USB 3.0 or USB 3.1 cable (SuperSpeed)")
        print("2. Use a shorter cable (under 3 feet/1 meter is best)")
        print("3. Use a cable with proper shielding")
        print("4. Try connecting directly to your computer's USB port (not through a hub)")
    elif high_timeouts:
        print("⚠️ Your cable may be MARGINALLY COMPATIBLE with the RealSense camera.")
        print("Recommendations:")
        print("1. Try a higher quality USB 3.0 or USB 3.1 cable")
        print("2. Use a shorter cable if possible")
        print("3. Make sure the cable is properly connected at both ends")
    else:
        print("✅ Your cable appears to be COMPATIBLE with the RealSense camera.")
        print("If you're still experiencing issues, they may be related to:")
        print("1. Software configuration")
        print("2. Camera firmware")
        print("3. USB port power delivery")
        print("4. Other system issues")
    
    return True

if __name__ == "__main__":
    test_usb_connection()