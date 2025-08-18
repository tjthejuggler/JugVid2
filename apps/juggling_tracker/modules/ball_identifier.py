import numpy as np
import cv2

class BallIdentifier:
    """
    Handles the identification of which blob corresponds to which ball.
    
    This module is responsible for:
    - Using the calibrated colors to identify which blob corresponds to which ball
    - Handling cases where balls may be temporarily occluded
    - Maintaining consistent ball identities across frames
    """
    
    def __init__(self, ball_profile_manager, color_calibration=None):
        """
        Initialize the BallIdentifier module.
        
        Args:
            ball_profile_manager: BallProfileManager instance
            color_calibration: Optional ColorCalibration instance for fallback or general tasks
        """
        self.ball_profile_manager = ball_profile_manager
        self.color_calibration = color_calibration  # Optional, for fallback or general tasks
        self.last_identified_balls = {}  # Dictionary of ball_name -> last blob info
    
    def identify_balls(self, blobs, color_image, depth_in_meters, intrinsics):
        """
        Identify which blob corresponds to which ball using ball profiles.
        
        Args:
            blobs: List of blobs
            color_image: Color image in BGR format
            depth_in_meters: Depth image in meters
            intrinsics: Camera intrinsics
            
        Returns:
            list: List of dictionaries containing identified ball information
        """
        identified_balls = []
        # Ensure ball_profile_manager is not None before calling its methods
        if not self.ball_profile_manager:
            print("Error: BallProfileManager not available in BallIdentifier.")
            return []
            
        active_profiles = self.ball_profile_manager.get_all_profiles()

        if not active_profiles: # No profiles defined, can't identify specific balls
            # print_once("No active ball profiles. Cannot identify specific balls.") # Optional: use print_once
            return [] # Or fall back to generic blob detection if needed

        if color_image is None:
            print("Error: color_image is None in identify_balls.")
            return []
        
        hsv_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)

        for blob in blobs:
            # Basic blob properties
            # Ensure blob structure is as expected, e.g., contains 'position', 'radius', 'contour'
            if not all(k in blob for k in ['position', 'radius', 'contour']):
                # print(f"Warning: Skipping blob with missing keys: {blob}")
                continue

            x, y, r = int(blob['position'][0]), int(blob['position'][1]), int(blob['radius'])
            contour = blob['contour']

            if r < 3: # Min radius
                continue

            # Extract average color from the blob's region in HSV
            mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            
            if np.sum(mask) == 0: # Check if mask has any lit pixels
                continue
            
            blob_hsv_mean = cv2.mean(hsv_image, mask=mask)[:3] # H, S, V

            # Get blob depth
            # Using blob's 'depth_m' if available (e.g., from filter_blobs_by_depth_variance)
            # Fallback to centroid depth from depth_in_meters if 'depth_m' not in blob or invalid
            blob_depth_m = blob.get('depth_m')
            if blob_depth_m is None or blob_depth_m <= 0:
                if depth_in_meters is not None and \
                   0 <= y < depth_in_meters.shape[0] and \
                   0 <= x < depth_in_meters.shape[1]:
                    blob_depth_m = depth_in_meters[y, x]
                else:
                    # print(f"Warning: Invalid coordinates or depth_in_meters for blob at ({x},{y})")
                    continue # Skip if depth cannot be determined

            if blob_depth_m <= 0: # Invalid depth
                continue

            best_match_profile = None
            best_match_score = -1 # Using confidence; higher is better.

            for profile in active_profiles:
                if profile.hsv_low is None or profile.hsv_high is None: # Profile not fully defined
                    continue
                
                # 1. Color Match
                color_match = (profile.hsv_low[0] <= blob_hsv_mean[0] <= profile.hsv_high[0] and
                               profile.hsv_low[1] <= blob_hsv_mean[1] <= profile.hsv_high[1] and
                               profile.hsv_low[2] <= blob_hsv_mean[2] <= profile.hsv_high[2])
                if not color_match:
                    continue

                # 2. Size Match (3D real-world size is more robust)
                size_match = False
                if profile.real_world_radius_m and intrinsics and intrinsics.fx > 0 and blob_depth_m > 0:
                    expected_pixel_r = (profile.real_world_radius_m * intrinsics.fx) / blob_depth_m
                    min_r_expected = expected_pixel_r / profile.radius_confidence_factor
                    max_r_expected = expected_pixel_r * profile.radius_confidence_factor
                    
                    if min_r_expected <= r <= max_r_expected:
                        size_match = True
                else: # Fallback or if 3D info not available/applicable
                    size_match = True # Be lenient if no 3D size info in profile or issues with depth/intrinsics

                if not size_match:
                    continue

                # 3. Shape Match (Circularity)
                shape_match = False
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    area = cv2.contourArea(contour)
                    circularity = 4 * np.pi * area / (perimeter**2)
                    if circularity >= profile.circularity_min:
                        shape_match = True
                
                if not shape_match:
                    continue
                
                # If all checks pass, this is a candidate.
                # For now, first good match wins.
                # A more complex scoring could be:
                # score = (1 if color_match else 0) + (1 if size_match else 0) + (1 if shape_match else 0)
                # For simplicity, if all pass, it's a match.
                current_score = 1.0
                
                if current_score > best_match_score:
                    best_match_score = current_score
                    best_match_profile = profile
                    # break # Uncomment if first match is sufficient

            if best_match_profile:
                # Convert mean HSV color back to BGR for display purposes
                display_color_bgr = cv2.cvtColor(np.uint8([[blob_hsv_mean]]), cv2.COLOR_HSV2BGR)[0][0].tolist()
                
                identified_balls.append({
                    'profile_id': best_match_profile.profile_id,
                    'name': best_match_profile.name,
                    'position': (x, y), # 2D pixel position
                    'radius': r,       # 2D pixel radius
                    'color_bgr': display_color_bgr,
                    'depth_m': blob_depth_m,
                    'contour': contour,
                    'profile_ref': best_match_profile # Keep a reference
                })
        return identified_balls
    
    def draw_identified_balls(self, color_image, identified_balls):
        """
        Draw identified balls on a color image.
        
        Args:
            color_image: Color image in BGR format
            identified_balls: List of dictionaries containing identified ball information
            
        Returns:
            numpy.ndarray: Color image with identified balls drawn
        """
        # Create a copy of the image to draw on
        image_with_balls = color_image.copy()
        
        # Draw each identified ball
        for ball in identified_balls:
            # Get the color for this ball - use detected color or get from color_calibration
            bgr_color = ball.get('color_bgr')
            
            if bgr_color is None and self.color_calibration:
                bgr_color = self.color_calibration.get_ball_bgr_color(ball['name'])
                
            if bgr_color is None:
                bgr_color = (0, 255, 0)  # Default to green if color not found
            
            # Draw the ball
            cv2.circle(image_with_balls, ball['position'], ball['radius'], bgr_color, 2)
            
            # Draw the ball name
            cv2.putText(image_with_balls, ball['name'],
                       (ball['position'][0] - ball['radius'], ball['position'][1] - ball['radius'] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 2)
        
        return image_with_balls
    
    def get_ball_positions(self, identified_balls):
        """
        Get the positions of identified balls.
        
        Args:
            identified_balls: List of dictionaries containing identified ball information
            
        Returns:
            list: List of (x, y) positions
        """
        return [ball['position'] for ball in identified_balls]
    
    def get_ball_depths(self, identified_balls):
        """
        Get the depths of identified balls.
        
        Args:
            identified_balls: List of dictionaries containing identified ball information
            
        Returns:
            list: List of depths in meters
        """
        return [ball['depth_m'] for ball in identified_balls]
    
    def get_ball_radii(self, identified_balls):
        """
        Get the radii of identified balls.
        
        Args:
            identified_balls: List of dictionaries containing identified ball information
            
        Returns:
            list: List of radii
        """
        return [ball['radius'] for ball in identified_balls]
    
    def update_color_calibration(self, identified_balls, color_image):
        """
        Update the color calibration based on identified balls.
        
        Args:
            identified_balls: List of dictionaries containing identified ball information
            color_image: Color image in BGR format
            
        Returns:
            bool: True if the calibration was updated successfully, False otherwise
        """
        if self.color_calibration is None:
            print("Warning: No color_calibration available to update")
            return False
            
        try:
            for ball in identified_balls:
                # Extract the average color of the blob
                mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
                cv2.drawContours(mask, [ball['contour']], -1, 255, -1)
                mean_color = cv2.mean(color_image, mask=mask)[:3]  # BGR format
                
                # Update the color calibration
                self.color_calibration.update_ball_color(ball['name'], mean_color)
            
            return True
        except Exception as e:
            print(f"Error updating color calibration: {e}")
            return False