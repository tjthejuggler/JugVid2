# juggling_tracker/modules/ball_definer.py
import cv2
import numpy as np
from .ball_profile import BallProfile

class BallDefiner:
    def __init__(self, depth_processor):
        self.depth_processor = depth_processor # For depth_to_points, etc.

    def define_ball_from_roi(self, roi_rect, color_image, depth_image_mm, intrinsics, depth_scale):
        """
        Defines a ball profile from a user-selected ROI.
        roi_rect: (x, y, w, h)
        depth_image_mm: raw depth image in millimeters (uint16)
        intrinsics: camera intrinsics object
        depth_scale: to convert depth_image_mm to meters
        """
        x, y, w, h = roi_rect
        if w == 0 or h == 0:
            print("Error: ROI has zero width or height.")
            return None

        roi_color = color_image[y:y+h, x:x+w]
        roi_depth_mm = depth_image_mm[y:y+h, x:x+w]

        if roi_color.size == 0 or roi_depth_mm.size == 0:
            print("Error: ROI is empty or out of bounds.")
            return None

        # 1. Convert ROI to HSV
        roi_hsv = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)

        # 2. Segment the ball within the ROI using depth
        #    Assume ball is the closest substantial object in the ROI center
        #    Get median depth, filter outliers, then find largest contour.
        
        valid_depth_mask = (roi_depth_mm > 0) # Valid depth readings
        if not np.any(valid_depth_mask):
            print("Error: No valid depth data in ROI.")
            return None

        # Get depths in meters
        roi_depth_m_flat = roi_depth_mm[valid_depth_mask].flatten() * depth_scale
        if len(roi_depth_m_flat) == 0:
             print("Error: No valid depth data in ROI after scaling.")
             return None

        # Robust median depth:
        median_depth_m = np.median(roi_depth_m_flat)
        # Define a depth slice around the median depth to isolate the ball
        # This range can be adjusted, e.g. based on expected ball size or fixed value
        depth_range_m = 0.15 # e.g., +/- 15cm around median (for typical juggling ball distances)
        min_object_depth_m = median_depth_m - depth_range_m / 2
        max_object_depth_m = median_depth_m + depth_range_m / 2

        # Create a mask for pixels within this depth slice
        ball_depth_mask = np.zeros_like(roi_depth_mm, dtype=np.uint8)
        ball_depth_mask_local = (roi_depth_mm * depth_scale >= min_object_depth_m) & \
                                (roi_depth_mm * depth_scale <= max_object_depth_m) & \
                                valid_depth_mask
        ball_depth_mask[ball_depth_mask_local] = 255
        
        # Optional: morphological operations to clean mask
        kernel = np.ones((3,3), np.uint8)
        ball_depth_mask = cv2.erode(ball_depth_mask, kernel, iterations=1)
        ball_depth_mask = cv2.dilate(ball_depth_mask, kernel, iterations=2)

        # Find contours on this mask to get the ball's shape
        contours, _ = cv2.findContours(ball_depth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("Error: Could not segment an object in the ROI using depth.")
            return None

        # Assume the largest contour is the ball
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Create a mask for only the largest contour
        final_ball_mask_roi = np.zeros_like(ball_depth_mask, dtype=np.uint8)
        cv2.drawContours(final_ball_mask_roi, [largest_contour], -1, 255, thickness=cv2.FILLED)

        # 3. Extract characteristics using this final_ball_mask_roi
        ball_hsv_pixels = roi_hsv[final_ball_mask_roi == 255]
        ball_depth_pixels_mm = roi_depth_mm[final_ball_mask_roi == 255]
        
        if len(ball_hsv_pixels) < 10 : # Need a minimum number of pixels
            print("Error: Not enough pixels in segmented object to define profile.")
            return None

        profile = BallProfile()
        profile.set_color_characteristics(ball_hsv_pixels)
        
        # Estimate size
        (cx, cy), pixel_radius_roi = cv2.minEnclosingCircle(largest_contour)
        # Average depth of the ball pixels for size estimation
        avg_ball_depth_m = np.mean(ball_depth_pixels_mm) * depth_scale
        profile.set_size_characteristics(pixel_radius_roi, avg_ball_depth_m, intrinsics)
        profile.set_depth_characteristics(ball_depth_pixels_mm * depth_scale) # Store raw depths in meters

        # Optional: Calculate and store circularity
        perimeter = cv2.arcLength(largest_contour, True)
        if perimeter > 0:
            area = cv2.contourArea(largest_contour)
            circularity = 4 * np.pi * area / (perimeter**2)
            profile.circularity_min = max(0.6, circularity * 0.8) # Store 80% of measured, min 0.6
            print(f"Profile {profile.name}: Measured circularity: {circularity:.2f}, setting min to: {profile.circularity_min:.2f}")

        print(f"Defined new ball profile: {profile.name} (ID: {profile.profile_id})")
        print(f"  HSV Low: {profile.hsv_low}, High: {profile.hsv_high}")
        
        return profile