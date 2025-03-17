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
    
    def __init__(self, color_calibration, max_color_distance=40.0):
        """
        Initialize the BallIdentifier module.
        
        Args:
            color_calibration: ColorCalibration instance
            max_color_distance (float): Maximum acceptable color distance for matching
        """
        self.color_calibration = color_calibration
        self.max_color_distance = max_color_distance
        self.last_identified_balls = {}  # Dictionary of ball_name -> last blob info
    
    def identify_balls(self, blobs, color_image):
        """
        Identify which blob corresponds to which ball.
        
        Args:
            blobs: List of blobs
            color_image: Color image in BGR format
            
        Returns:
            dict: Dictionary of ball_name -> blob
        """
        identified_balls = {}
        unmatched_blobs = list(blobs)  # Copy the list to avoid modifying the original
        
        # First pass: Try to match blobs to balls based on color
        for blob in blobs:
            # Extract the average color of the blob
            mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
            cv2.drawContours(mask, [blob['contour']], -1, 255, -1)
            mean_color = cv2.mean(color_image, mask=mask)[:3]  # BGR format
            
            # Match the color to a calibrated ball
            ball_name, distance = self.color_calibration.match_color(mean_color, self.max_color_distance)
            
            if ball_name is not None:
                # If this ball is already identified, keep the better match
                if ball_name in identified_balls:
                    existing_blob = identified_balls[ball_name]
                    existing_mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
                    cv2.drawContours(existing_mask, [existing_blob['contour']], -1, 255, -1)
                    existing_color = cv2.mean(color_image, mask=existing_mask)[:3]
                    _, existing_distance = self.color_calibration.match_color(existing_color, self.max_color_distance)
                    
                    # Keep the better match (lower distance)
                    if distance < existing_distance:
                        identified_balls[ball_name] = blob
                        if existing_blob in unmatched_blobs:
                            unmatched_blobs.remove(existing_blob)
                        if blob in unmatched_blobs:
                            unmatched_blobs.remove(blob)
                else:
                    identified_balls[ball_name] = blob
                    if blob in unmatched_blobs:
                        unmatched_blobs.remove(blob)
        
        # Second pass: Try to match remaining blobs based on proximity to last known positions
        for ball_name, last_blob in self.last_identified_balls.items():
            if ball_name not in identified_balls and unmatched_blobs:
                # Find the closest unmatched blob to the last known position
                last_center = last_blob['center']
                closest_blob = None
                min_distance = float('inf')
                
                for blob in unmatched_blobs:
                    center = blob['center']
                    distance = np.linalg.norm(np.array(center) - np.array(last_center))
                    
                    # Scale by the radius to account for different sized blobs
                    scaled_distance = distance / (blob['radius'] + 1e-6)
                    
                    if scaled_distance < min_distance:
                        min_distance = scaled_distance
                        closest_blob = blob
                
                # Only match if the blob is close enough to the last known position
                if closest_blob is not None and min_distance < 5.0:  # Threshold for proximity matching
                    identified_balls[ball_name] = closest_blob
                    unmatched_blobs.remove(closest_blob)
        
        # Update last identified balls
        self.last_identified_balls = identified_balls.copy()
        
        return identified_balls
    
    def draw_identified_balls(self, color_image, identified_balls):
        """
        Draw identified balls on a color image.
        
        Args:
            color_image: Color image in BGR format
            identified_balls: Dictionary of ball_name -> blob
            
        Returns:
            numpy.ndarray: Color image with identified balls drawn
        """
        # Create a copy of the image to draw on
        image_with_balls = color_image.copy()
        
        # Draw each identified ball
        for ball_name, blob in identified_balls.items():
            # Get the color for this ball
            bgr_color = self.color_calibration.get_ball_bgr_color(ball_name)
            
            if bgr_color is None:
                bgr_color = (0, 255, 0)  # Default to green if color not found
            
            # Draw the ball
            cv2.circle(image_with_balls, blob['center'], blob['radius'], bgr_color, 2)
            
            # Draw the ball name
            cv2.putText(image_with_balls, ball_name, 
                       (blob['center'][0] - blob['radius'], blob['center'][1] - blob['radius'] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 2)
        
        return image_with_balls
    
    def get_ball_positions(self, identified_balls):
        """
        Get the positions of identified balls.
        
        Args:
            identified_balls: Dictionary of ball_name -> blob
            
        Returns:
            dict: Dictionary of ball_name -> (x, y) position
        """
        return {ball_name: blob['center'] for ball_name, blob in identified_balls.items()}
    
    def get_ball_depths(self, identified_balls):
        """
        Get the depths of identified balls.
        
        Args:
            identified_balls: Dictionary of ball_name -> blob
            
        Returns:
            dict: Dictionary of ball_name -> depth
        """
        return {ball_name: blob.get('depth_mean', 0.0) for ball_name, blob in identified_balls.items()}
    
    def get_ball_radii(self, identified_balls):
        """
        Get the radii of identified balls.
        
        Args:
            identified_balls: Dictionary of ball_name -> blob
            
        Returns:
            dict: Dictionary of ball_name -> radius
        """
        return {ball_name: blob['radius'] for ball_name, blob in identified_balls.items()}
    
    def update_color_calibration(self, identified_balls, color_image):
        """
        Update the color calibration based on identified balls.
        
        Args:
            identified_balls: Dictionary of ball_name -> blob
            color_image: Color image in BGR format
            
        Returns:
            bool: True if the calibration was updated successfully, False otherwise
        """
        try:
            for ball_name, blob in identified_balls.items():
                # Extract the average color of the blob
                mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
                cv2.drawContours(mask, [blob['contour']], -1, 255, -1)
                mean_color = cv2.mean(color_image, mask=mask)[:3]  # BGR format
                
                # Update the color calibration
                self.color_calibration.update_ball_color(ball_name, mean_color)
            
            return True
        except Exception as e:
            print(f"Error updating color calibration: {e}")
            return False