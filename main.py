import cv2
import numpy as np
import pyrealsense2 as rs
import mediapipe as mp
import time
import math

# -------------------------------
# Parameters and Global Variables
# -------------------------------
CALIB_BOX_TOPLEFT = (10, 10)    # top-left corner of calibration box
CALIB_BOX_SIZE = (100, 100)     # width, height of calibration box
MATCH_THRESHOLD = 2.0           # maximum normalized distance for candidate matching
SIZE_CHANGE_WEIGHT = 0.7        # weight for size difference in matching score
COLOR_CHANGE_WEIGHT = 0.5       # weight for color difference in matching score
TRACK_EXPIRY = 1.0              # seconds: if no update, drop the tracked ball
RADIUS_TOLERANCE = 0.3          # tolerance for radius ratio error (30%)
COLOR_MATCH_THRESHOLD = 40.0    # maximum acceptable color difference in LAB

tracked_ball = None             # Will hold the calibrated ball (None until calibration)
last_update_time = None         # Timestamp of the last update for the tracked ball

# -------------------------------
# 1. RealSense Setup
# -------------------------------
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Align depth to color stream
align = rs.align(rs.stream.color)

# Get camera intrinsics for 3D deprojection
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print(f"Depth Scale is: {depth_scale:.3f} meters")
color_profile = profile.get_stream(rs.stream.color)
intr = color_profile.as_video_stream_profile().get_intrinsics()

# -------------------------------
# 2. MediaPipe Pose Setup for Skeleton Tracking
# -------------------------------
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# -------------------------------
# 3. Main Loop
# -------------------------------
print("Place the ball inside the calibration box (upper left) and press ENTER to calibrate.")
try:
    while True:
        # Grab frames from RealSense
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert frames to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Convert to LAB for color analysis
        lab_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2LAB)

        # Prepare a depth visualization (for reference)
        depth_image_8bit = cv2.convertScaleAbs(depth_image, alpha=0.03)
        depth_colormap = cv2.applyColorMap(depth_image_8bit, cv2.COLORMAP_JET)

        # -------------------------------
        # 3a. Skeleton (Pose) Detection
        # -------------------------------
        image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(color_image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # -------------------------------
        # 3b. Draw Calibration Box (if no ball is tracked yet)
        # -------------------------------
        if tracked_ball is None:
            x0, y0 = CALIB_BOX_TOPLEFT
            w_box, h_box = CALIB_BOX_SIZE
            cv2.rectangle(color_image, (x0, y0), (x0 + w_box, y0 + h_box), (0, 0, 255), 2)
            cv2.putText(color_image, "Place ball here & press ENTER", (x0, y0 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # -------------------------------
        # 3c. Ball Detection (HoughCircles)
        # -------------------------------
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        # Adjust circle detection parameters based on tracked ball status
        min_radius = 10
        max_radius = 50
        param2 = 30  # Detection threshold - lower makes it more lenient
        
        if tracked_ball is not None:
            current_radius = tracked_ball['radius']
            # Allow a wider range when tracking (in case of depth changes)
            min_radius = max(5, int(current_radius * 0.4))
            max_radius = min(150, int(current_radius * 2.5))
            param2 = 25  # Slightly more lenient when tracking
            
        circles = cv2.HoughCircles(
            gray_blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min_radius * 2,
            param1=50,
            param2=param2,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        detections = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                detections.append((x, y, r))
                # Draw candidate circles only during calibration to reduce clutter
                if tracked_ball is None:
                    cv2.circle(color_image, (x, y), r, (0, 100, 0), 1)
                    cv2.circle(color_image, (x, y), 2, (0, 0, 100), 2)

        # -------------------------------
        # 3d. Calibration on ENTER Press
        # -------------------------------
        key = cv2.waitKey(1)
        if key & 0xFF == 13:  # ENTER key pressed (ASCII 13)
            if tracked_ball is None:
                # Look for a candidate detection inside the calibration box.
                x0, y0 = CALIB_BOX_TOPLEFT
                w_box, h_box = CALIB_BOX_SIZE
                candidate = None
                for (x, y, r) in detections:
                    if x0 <= x <= x0 + w_box and y0 <= y <= y0 + h_box:
                        candidate = (x, y, r)
                        break
                if candidate is not None:
                    x, y, r = candidate
                    frame_width = depth_frame.get_width()
                    frame_height = depth_frame.get_height()
                    if not (0 <= x < frame_width and 0 <= y < frame_height):
                        print("Ball detection out of frame bounds.")
                        continue
                    try:
                        depth = depth_frame.get_distance(int(x), int(y))
                    except RuntimeError:
                        print("Error reading depth value.")
                        continue
                    if depth <= 0 or depth > 2.0:
                        print("Invalid depth reading.")
                        continue
                    
                    # Compute the ball's average color in LAB using a circular mask
                    mask = np.zeros(gray.shape, dtype=np.uint8)
                    cv2.circle(mask, (x, y), r, 255, -1)
                    avg_color = cv2.mean(lab_image, mask=mask)[:3]
                    
                    point3d = rs.rs2_deproject_pixel_to_point(intr, [x, y], depth)
                    tracked_ball = {
                        'center': (int(x), int(y)),
                        'radius': r,
                        'depth': depth,
                        'point3d': point3d,
                        'color': avg_color  # store calibrated color (LAB)
                    }
                    last_update_time = time.time()
                    print(f"Calibrated ball at ({x}, {y}) with radius {r} and color {avg_color}")
                else:
                    print("No ball detected in calibration box.")

        # -------------------------------
        # 3e. Update Tracked Ball (if calibrated)
        # -------------------------------
        current_time = time.time()
        if tracked_ball is not None:
            best_detection = None
            best_score = float('inf')
            last_x, last_y = tracked_ball['center']
            last_r = tracked_ball['radius']
            last_depth = tracked_ball['depth']
            last_color = np.array(tracked_ball['color'])
            
            for (x, y, r) in detections:
                frame_width = depth_frame.get_width()
                frame_height = depth_frame.get_height()
                if not (0 <= x < frame_width and 0 <= y < frame_height):
                    continue
                try:
                    current_depth = depth_frame.get_distance(int(x), int(y))
                except RuntimeError:
                    continue
                if current_depth <= 0:
                    continue

                # Compute the expected radius based on depth change
                expected_r = last_r * (last_depth / current_depth)
                if expected_r == 0:
                    continue
                # Compute the normalized position difference
                pos_dist = math.hypot(x - last_x, y - last_y) / last_r
                # Compute the relative error between measured and expected radius
                radius_ratio_error = abs(r - expected_r) / expected_r

                # Only consider candidates within the set tolerance for radius
                if radius_ratio_error > RADIUS_TOLERANCE:
                    continue

                # Compute candidate's average color in LAB
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.circle(mask, (x, y), r, 255, -1)
                candidate_color = cv2.mean(lab_image, mask=mask)[:3]
                candidate_color = np.array(candidate_color)
                color_diff = np.linalg.norm(candidate_color - last_color)
                
                # If color difference exceeds threshold, skip this candidate
                if color_diff > COLOR_MATCH_THRESHOLD:
                    continue

                # Combined score: position, size, and color difference components
                score = pos_dist + SIZE_CHANGE_WEIGHT * radius_ratio_error + COLOR_CHANGE_WEIGHT * (color_diff / COLOR_MATCH_THRESHOLD)
                if score < best_score and pos_dist < MATCH_THRESHOLD:
                    best_detection = (x, y, r)
                    best_score = score
            
            if best_detection is not None:
                x, y, r = best_detection
                depth = depth_frame.get_distance(x, y)
                try:
                    point3d = rs.rs2_deproject_pixel_to_point(intr, [x, y], depth) if depth > 0 else None
                except Exception:
                    point3d = None
                # Smooth the update using a weighted average
                new_center = (int(0.7 * last_x + 0.3 * x), int(0.7 * last_y + 0.3 * y))
                new_radius = int(0.7 * last_r + 0.3 * r)
                # Update color similarly by averaging the LAB values
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.circle(mask, (x, y), r, 255, -1)
                new_color = cv2.mean(lab_image, mask=mask)[:3]
                new_color = tuple(0.7 * np.array(last_color) + 0.3 * np.array(new_color))
                
                tracked_ball['center'] = new_center
                tracked_ball['radius'] = new_radius
                tracked_ball['depth'] = depth
                tracked_ball['point3d'] = point3d
                tracked_ball['color'] = new_color
                last_update_time = current_time
            else:
                # Drop the tracked ball if no update occurs for a while
                if current_time - last_update_time > TRACK_EXPIRY:
                    print("Lost tracked ball due to lack of detections.")
                    tracked_ball = None

        # -------------------------------
        # 3f. Visualization of Tracked Ball
        # -------------------------------
        if tracked_ball is not None:
            x, y = tracked_ball['center']
            cv2.circle(color_image, (x, y), tracked_ball['radius'], (255, 0, 255), 2)
            cv2.putText(color_image, "TRACKED BALL", (x - 40, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

        # -------------------------------
        # 3g. Display Windows
        # -------------------------------
        cv2.imshow('Color Stream', color_image)
        cv2.imshow('Depth Stream', depth_colormap)
        if key & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
