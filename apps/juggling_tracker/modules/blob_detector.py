import numpy as np
import cv2
import math

class BlobDetector:
    """
    Handles the detection of potential ball candidates in the filtered depth mask.
    
    This module is responsible for:
    - Finding contours in the filtered depth mask
    - Applying circularity and size filters to identify potential ball candidates
    - Providing 2D positions and radii of detected blobs
    """
    
    def __init__(self, min_area=50, max_area=2000, min_circularity=0.6):
        """
        Initialize the BlobDetector module.
        
        Args:
            min_area (float): Minimum area of a blob in pixels
            max_area (float): Maximum area of a blob in pixels
            min_circularity (float): Minimum circularity of a blob (0-1)
        """
        self.min_area = min_area
        self.max_area = max_area
        self.min_circularity = min_circularity
    
    def detect_blobs(self, mask):
        """
        Detect blobs in a binary mask.
        
        Args:
            mask: Binary mask where potential balls are white (255)
            
        Returns:
            list: List of detected blobs, each represented as a dictionary with keys:
                - center: (x, y) tuple of the blob center
                - radius: Radius of the blob in pixels
                - contour: Contour points of the blob
                - area: Area of the blob in pixels
                - circularity: Circularity of the blob (0-1)
        """
        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and circularity
        filtered_contours = self.filter_contours(contours)
        
        # Extract blob properties
        blobs = [self.get_blob_properties(contour) for contour in filtered_contours]
        
        return blobs
    
    def filter_contours(self, contours):
        """
        Filter contours by size and circularity.
        
        Args:
            contours: List of contours
            
        Returns:
            list: Filtered list of contours
        """
        filtered_contours = []
        
        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < self.min_area or area > self.max_area:
                continue
            
            # Calculate circularity
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
                
            circularity = 4 * math.pi * area / (perimeter * perimeter)
            
            # Filter by circularity
            if circularity < self.min_circularity:
                continue
            
            filtered_contours.append(contour)
        
        return filtered_contours
    
    def get_blob_properties(self, contour):
        """
        Extract properties of a blob from its contour.
        
        Args:
            contour: Contour points of the blob
            
        Returns:
            dict: Dictionary with blob properties:
                - center: (x, y) tuple of the blob center
                - radius: Radius of the blob in pixels
                - contour: Contour points of the blob
                - area: Area of the blob in pixels
                - circularity: Circularity of the blob (0-1)
        """
        # Calculate area
        area = cv2.contourArea(contour)
        
        # Calculate circularity
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * math.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # Get the minimum enclosing circle
        (x, y), radius = cv2.minEnclosingCircle(contour)
        center = (int(x), int(y))
        radius = int(radius)
        
        # Create a dictionary with blob properties
        blob = {
            'center': center,
            'radius': radius,
            'contour': contour,
            'area': area,
            'circularity': circularity
        }
        
        return blob
    
    def draw_blobs(self, image, blobs, color=(0, 255, 0), thickness=2):
        """
        Draw detected blobs on an image.
        
        Args:
            image: Image to draw on
            blobs: List of blobs
            color: Color of the circles (BGR)
            thickness: Thickness of the circles
            
        Returns:
            numpy.ndarray: Image with blobs drawn
        """
        # Create a copy of the image to draw on
        image_with_blobs = image.copy()
        
        # Draw circles for each blob
        for blob in blobs:
            cv2.circle(image_with_blobs, blob['center'], blob['radius'], color, thickness)
        
        return image_with_blobs
    
    def filter_blobs_by_depth_variance(self, blobs, depth_in_meters, max_variance=0.001):
        """
        Filter blobs by depth variance.
        
        Args:
            blobs: List of blobs
            depth_in_meters: Depth image in meters
            max_variance: Maximum allowed depth variance within a blob
            
        Returns:
            list: Filtered list of blobs
        """
        filtered_blobs = []
        
        for blob in blobs:
            # Create a mask for the blob
            mask = np.zeros_like(depth_in_meters, dtype=np.uint8)
            cv2.drawContours(mask, [blob['contour']], -1, 255, -1)
            
            # Get depth values within the blob
            region_depth = depth_in_meters[mask == 255]
            
            # Filter out zero depth values
            region_depth = region_depth[region_depth > 0]
            
            if region_depth.size == 0:
                continue
            
            # Calculate depth variance
            depth_variance = np.var(region_depth)
            
            # Filter by depth variance
            if depth_variance <= max_variance:
                # Add depth information to the blob
                blob['depth_mean'] = np.mean(region_depth)
                blob['depth_variance'] = depth_variance
                filtered_blobs.append(blob)
        
        return filtered_blobs