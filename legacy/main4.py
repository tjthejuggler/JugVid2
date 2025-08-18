import pyrealsense2 as rs
import cv2
import numpy as np
import mediapipe as mp
import time

# -------------------------------------------------
# Setup RealSense Pipeline and Align Streams
# -------------------------------------------------
print("Initializing RealSense pipeline...")

# Create pipeline and config
pipeline = rs.pipeline()
config = rs.config()

# Try different approaches to start the pipeline
try:
    # First approach: Try to start with default configuration
    print("Attempting to start pipeline with default configuration...")
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    
    # Add a short delay before starting the pipeline
    time.sleep(1)
    
    # Try to start the pipeline
    profile = pipeline.start(config)
    print("Pipeline started successfully")
    
except Exception as e:
    print(f"First attempt failed: {str(e)}")
    
    # Second approach: Try to find any device
    try:
        print("Attempting to start with device discovery...")
        # Reset the config
        config = rs.config()
        
        # Try to use any available device
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        # Add a longer delay
        time.sleep(2)
        
        profile = pipeline.start(config)
        print("Pipeline started successfully with second approach")
    except Exception as e2:
        print(f"Second attempt failed: {str(e2)}")
        
        # Third approach: Try with a different configuration
        try:
            print("Attempting with minimal configuration...")
            # Reset the config
            config = rs.config()
            
            # Try with just depth stream
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            
            time.sleep(2)
            
            profile = pipeline.start(config)
            print("Pipeline started with depth-only configuration")
            
            # Now try to get the color stream
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        except Exception as e3:
            print(f"All attempts failed. Final error: {str(e3)}")
            raise RuntimeError(f"Could not initialize RealSense camera: {str(e3)}")

# Check if color stream is available
color_stream_available = True
try:
    # Try to get the color stream profile
    color_profile = profile.get_stream(rs.stream.color)
    print("Color stream is available")
    
    # Align depth to color stream
    align_to = rs.stream.color
    align = rs.align(align_to)
    
    # Get camera intrinsics for 3D deprojection from color stream
    intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
except RuntimeError as e:
    print(f"WARNING: Color stream not available: {str(e)}")
    color_stream_available = False
    
    # If color stream is not available, we can't align
    print("Using depth stream only (no alignment)")
    align = None
    
    # Get camera intrinsics from depth stream instead
    depth_profile = profile.get_stream(rs.stream.depth)
    intrinsics = depth_profile.as_video_stream_profile().get_intrinsics()

# -------------------------------------------------
# Initialize MediaPipe Pose for skeleton detection
# -------------------------------------------------
mp_pose = mp.solutions.pose
pose_detector = mp_pose.Pose(static_image_mode=False, 
                             model_complexity=1,
                             enable_segmentation=False,
                             min_detection_confidence=0.5,
                             min_tracking_confidence=0.5)

# -------------------------------------------------
# Setup Kalman Filter for 3D Tracking (6 state: pos & vel)
# -------------------------------------------------
kalman = cv2.KalmanFilter(6, 3)
kalman.measurementMatrix = np.hstack((np.eye(3, dtype=np.float32), np.zeros((3, 3), dtype=np.float32)))
kalman.transitionMatrix = np.array([[1, 0, 0, 1, 0, 0],
                                    [0, 1, 0, 0, 1, 0],
                                    [0, 0, 1, 0, 0, 1],
                                    [0, 0, 0, 1, 0, 0],
                                    [0, 0, 0, 0, 1, 0],
                                    [0, 0, 0, 0, 0, 1]], dtype=np.float32)
kalman.processNoiseCov = np.eye(6, dtype=np.float32) * 1e-2
kalman.measurementNoiseCov = np.eye(3, dtype=np.float32) * 1e-1

# -------------------------------------------------
# Parameters for Depth-Based Ball Segmentation
# -------------------------------------------------
min_depth = 0.3  # in meters
max_depth = 3.0  # in meters

# -------------------------------------------------
# Main Loop
# -------------------------------------------------
try:
    print("Starting main loop. Press 'q' or ESC to exit.")
    while True:
        try:
            # Get frames from the pipeline with a timeout
            frames = pipeline.wait_for_frames(timeout_ms=1000)  # Reduced timeout from default 5000ms
        except RuntimeError as timeout_error:
            if "Frame didn't arrive within" in str(timeout_error):
                print("Frame timeout, retrying...")
                continue
            else:
                # Re-raise other runtime errors
                raise
            
        # Process frames based on available streams
        if align is not None:
            # If alignment is available (color stream exists)
            aligned_frames = align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                continue
                
            # Convert frames to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
        else:
            # If only depth stream is available
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                continue
                
            # Convert depth frame to numpy array
            depth_image = np.asanyarray(depth_frame.get_data())
            
            # Create a grayscale visualization of depth for display purposes
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03),
                cv2.COLORMAP_JET
            )
            # Use the depth colormap as our "color" image for visualization
            color_image = depth_colormap

        # Convert depth from raw units to meters
        depth_units = depth_frame.get_units()  # typically ~0.001 for RealSense
        depth_in_meters = depth_image * depth_units

        # -------------------------------------------------
        # Create a Proximity Mask Based on the Closest Objects
        # -------------------------------------------------
        valid_depths = depth_in_meters[depth_in_meters > 0]
        if valid_depths.size == 0:
            continue
        min_depth_val = np.min(valid_depths)
        delta = 0.15  # margin in meters (adjust based on your scene)
        proximity_mask = cv2.inRange(depth_in_meters, min_depth_val, min_depth_val + delta)

        # Smooth the mask with morphological operations
        kernel = np.ones((5, 5), np.uint8)
        proximity_mask = cv2.morphologyEx(proximity_mask, cv2.MORPH_OPEN, kernel)
        proximity_mask = cv2.morphologyEx(proximity_mask, cv2.MORPH_CLOSE, kernel)

        # -------------------------------------------------
        # Skeleton Detection to Mask Out Human Parts (if color stream available)
        # -------------------------------------------------
        skeleton_mask = np.zeros_like(proximity_mask)  # same size as depth image (640x480)
        
        if align is not None:  # Only do skeleton detection if color stream is available
            rgb_for_pose = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            results = pose_detector.process(rgb_for_pose)
            if results.pose_landmarks:
                img_h, img_w, _ = color_image.shape
                for landmark in results.pose_landmarks.landmark:
                    # Convert normalized coordinates to pixel values
                    lx = int(landmark.x * img_w)
                    ly = int(landmark.y * img_h)
                    # Draw a filled circle (adjust radius as needed)
                    cv2.circle(skeleton_mask, (lx, ly), 20, 255, -1)
                    
                # Draw skeleton on color image for visualization
                cv2.putText(color_image, "Human detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # If no color stream, we can't do skeleton detection
            print("Skipping skeleton detection (no color stream)")
            
        # Invert skeleton mask: regions with human parts will be 0.
        skeleton_mask_inv = cv2.bitwise_not(skeleton_mask)

        # Combine proximity mask and inverted skeleton mask.
        combined_mask = cv2.bitwise_and(proximity_mask, skeleton_mask_inv)

        # -------------------------------------------------
        # Find Contours in the Combined Mask
        # -------------------------------------------------
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        ball_center = None
        best_score = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50 or area > 2000:
                continue
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            if radius <= 0:
                continue
            circle_area = np.pi * (radius ** 2)
            circularity = area / circle_area
            # Check depth variance inside the blob
            mask_tmp = np.zeros_like(depth_in_meters, dtype=np.uint8)
            cv2.drawContours(mask_tmp, [cnt], -1, 255, -1)
            region_depth = depth_in_meters[mask_tmp == 255]
            depth_variance = np.var(region_depth)
            # Combine criteria: circularity and low depth variance
            score = circularity - (depth_variance * 10)
            if score > best_score and circularity > 0.6:
                best_score = score
                ball_center = (int(x), int(y))
                ball_radius = int(radius)

        # -------------------------------------------------
        # 3D Position Calculation and Kalman Filtering
        # -------------------------------------------------
        if ball_center is not None:
            x, y = ball_center
            region = depth_in_meters[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
            depth_val = np.mean(region)
            ball_3d = rs.rs2_deproject_pixel_to_point(intrinsics, [x, y], depth_val)
            measurement = np.array(ball_3d, dtype=np.float32).reshape(3, 1)
            kalman.predict()
            kalman.correct(measurement)
            tracked_state = kalman.statePost[:3].reshape(3)
            cv2.circle(color_image, ball_center, ball_radius, (0, 255, 0), 2)
            cv2.putText(color_image,
                        f"3D: {tracked_state[0]:.2f}, {tracked_state[1]:.2f}, {tracked_state[2]:.2f}",
                        (ball_center[0] + 10, ball_center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Display outputs
        cv2.imshow("Color", color_image)
        cv2.imshow("Combined Mask", combined_mask)
        key = cv2.waitKey(1)
        if key == 27 or key == ord('q'):
            break
except Exception as e:
    print(f"Error in main loop: {str(e)}")
finally:
    print("Stopping pipeline and cleaning up resources...")
    pipeline.stop()
    cv2.destroyAllWindows()
    print("Cleanup complete")
