import pyrealsense2 as rs
import cv2
import numpy as np

# -------------------------------------------------
# Setup RealSense Pipeline and Align Streams
# -------------------------------------------------
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Align depth to color stream
align_to = rs.stream.color
align = rs.align(align_to)

# Get camera intrinsics for 3D deprojection
color_profile = profile.get_stream(rs.stream.color)
intrinsics = color_profile.as_video_stream_profile().get_intrinsics()

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
# Main Loop
# -------------------------------------------------
while True:
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()
    if not depth_frame or not color_frame:
        continue

    # Convert frames to numpy arrays
    depth_image = np.asanyarray(depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())

    # Convert depth from raw units to meters
    depth_units = depth_frame.get_units()  # e.g., ~0.001 for RealSense
    depth_in_meters = depth_image * depth_units

    # -------------------------------------------------
    # Create a Proximity Mask Based on the Closest Objects
    # -------------------------------------------------
    # Find the minimum non-zero depth (ignore zero values)
    valid_depths = depth_in_meters[depth_in_meters > 0]
    if valid_depths.size == 0:
        continue
    min_depth_val = np.min(valid_depths)

    # Define a margin (in meters) to include objects near the closest one.
    delta = 0.15  # Adjust as needed (e.g., 15 cm margin)
    proximity_mask = cv2.inRange(depth_in_meters, min_depth_val, min_depth_val + delta)

    # Optional: Smooth the mask with morphology to reduce noise.
    kernel = np.ones((5, 5), np.uint8)
    proximity_mask = cv2.morphologyEx(proximity_mask, cv2.MORPH_OPEN, kernel)
    proximity_mask = cv2.morphologyEx(proximity_mask, cv2.MORPH_CLOSE, kernel)

    # -------------------------------------------------
    # Find Contours in the Proximity Mask
    # -------------------------------------------------
    contours, _ = cv2.findContours(proximity_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ball_center = None
    best_score = 0  # you can use circularity or combined criteria
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter by area: adjust thresholds based on your expected ball size in the image.
        if area < 50 or area > 2000:
            continue
        # Approximate the contour with a circle.
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        if radius <= 0:
            continue
        circle_area = np.pi * (radius ** 2)
        circularity = area / circle_area
        # Additionally, check that the depth variance inside the blob is low.
        mask = np.zeros_like(depth_in_meters, dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        region_depth = depth_in_meters[mask == 255]
        depth_variance = np.var(region_depth)
        # Combine criteria: close to min depth, sufficiently circular, and low depth variance.
        score = circularity - (depth_variance * 10)  # adjust weight as needed
        if score > best_score and circularity > 0.6:
            best_score = score
            ball_center = (int(x), int(y))
            ball_radius = int(radius)

    # If a candidate ball is detected
    if ball_center is not None:
        x, y = ball_center
        # Use a small window around the center to compute average depth.
        region = depth_in_meters[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        depth_val = np.mean(region)
        # Deproject the 2D pixel to 3D point using camera intrinsics.
        ball_3d = rs.rs2_deproject_pixel_to_point(intrinsics, [x, y], depth_val)
        measurement = np.array(ball_3d, dtype=np.float32).reshape(3, 1)

        # Kalman filter prediction and correction
        kalman.predict()
        kalman.correct(measurement)
        tracked_state = kalman.statePost[:3].reshape(3)

        # Draw detected ball and display 3D position
        cv2.circle(color_image, ball_center, ball_radius, (0, 255, 0), 2)
        cv2.putText(color_image,
                    f"3D: {tracked_state[0]:.2f}, {tracked_state[1]:.2f}, {tracked_state[2]:.2f}",
                    (ball_center[0] + 10, ball_center[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Create masked color image
    masked_color = np.zeros_like(color_image)
    masked_color[proximity_mask == 255] = color_image[proximity_mask == 255]

    # Display the color frame, proximity mask, and masked color image
    cv2.imshow("Color", color_image)
    cv2.imshow("Proximity Mask", proximity_mask)
    cv2.imshow("Masked Color", masked_color)
    key = cv2.waitKey(1)
    if key == 27 or key == ord('q'):
        break

pipeline.stop()
cv2.destroyAllWindows()
