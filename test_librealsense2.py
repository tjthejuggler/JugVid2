import pyrealsense2 as rs
import numpy as np
import cv2

# Create a pipeline
pipeline = rs.pipeline()

# Create a config and enable the depth stream
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
profile = pipeline.start(config)

# Get the depth sensor's depth scale (see rs-align example)
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print("Depth Scale is: {:.3f} meters".format(depth_scale))

# Align depth frame to color frame
align_to = rs.stream.color
align = rs.align(align_to)

try:
    while True:
        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)

        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Get image dimensions and compute center pixel
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        center_x, center_y = width // 2, height // 2

        # Get the distance at the center pixel
        distance = depth_frame.get_distance(center_x, center_y)
        print("Distance at center ({}, {}): {:.3f} meters".format(center_x, center_y, distance))

        # Optional: display the color image with the center point marked
        cv2.circle(color_image, (center_x, center_y), 5, (0, 0, 255), -1)
        cv2.imshow('Color Stream', color_image)
        key = cv2.waitKey(1)
        if key & 0xFF == ord('q'):
            break

finally:
    # Stop streaming
    pipeline.stop()
    cv2.destroyAllWindows()
