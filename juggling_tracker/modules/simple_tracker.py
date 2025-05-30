import numpy as np
import cv2
import json
import os
from collections import deque

class SimpleTracker:
    """
    Enhanced simple tracking module that calculates the average position of close objects in the mask.
    
    This provides stable tracking functionality with temporal smoothing, noise reduction,
    and configurable parameters for robust juggling pattern tracking.
    """
    
    def __init__(self):
        """
        Initialize the SimpleTracker module.
        """
        self.last_position = None
        self.position_history = deque(maxlen=30)  # Keep last 30 positions for smoothing
        self.confidence_history = deque(maxlen=30)  # Track confidence over time
        
        # Temporal smoothing parameters
        self.temporal_smoothing_frames = 5  # Number of frames to average
        self.max_position_jump = 100  # Maximum allowed position jump in pixels
        self.confidence_threshold = 0.3  # Minimum confidence to update position
        
        # Mask processing parameters
        self.morphology_kernel_size = 3  # Kernel size for opening/closing operations
        self.gaussian_blur_radius = 1  # Blur radius for noise reduction
        self.min_contour_perimeter = 20  # Minimum contour perimeter
        
        # Stability tracking
        self.stability_score = 0.0  # 0.0 = unstable, 1.0 = very stable
        self.last_valid_position = None
        
    def track_objects(self, proximity_mask, min_object_size=50, max_object_size=5000):
        """
        Track objects in the proximity mask and return the average position with enhanced stability.
        
        Args:
            proximity_mask: Binary mask where close objects are white (255)
            min_object_size: Minimum size (in pixels) for objects to be considered
            max_object_size: Maximum size (in pixels) for objects to be considered
            
        Returns:
            dict: Dictionary containing tracking information:
                - 'average_position': (x, y) tuple of raw average position, or None if no objects
                - 'smoothed_position': (x, y) tuple of temporally smoothed position
                - 'stable_position': (x, y) tuple of the most stable position for extensions
                - 'object_count': Number of objects found
                - 'total_area': Total area of all tracked objects
                - 'individual_positions': List of individual object positions
                - 'confidence': Confidence score (0.0 to 1.0)
                - 'stability_score': Stability score (0.0 to 1.0)
        """
        if proximity_mask is None:
            return self._get_empty_result()
        
        # Apply mask preprocessing
        processed_mask = self._preprocess_mask(proximity_mask)
        
        # Find contours in the processed mask
        contours, _ = cv2.findContours(processed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and perimeter
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            if (min_object_size <= area <= max_object_size and
                perimeter >= self.min_contour_perimeter):
                valid_contours.append(contour)
        
        if not valid_contours:
            # Decrease confidence when no objects found
            confidence = 0.0
            self.confidence_history.append(confidence)
            return self._get_empty_result()
        
        # Calculate centroids of valid contours
        positions = []
        total_area = 0
        
        for contour in valid_contours:
            # Calculate moments to find centroid
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                positions.append((cx, cy))
                total_area += cv2.contourArea(contour)
        
        if not positions:
            confidence = 0.0
            self.confidence_history.append(confidence)
            return self._get_empty_result()
        
        # Calculate raw average position
        avg_x = sum(pos[0] for pos in positions) / len(positions)
        avg_y = sum(pos[1] for pos in positions) / len(positions)
        raw_average_position = (int(avg_x), int(avg_y))
        
        # Calculate confidence based on object count and consistency
        confidence = self._calculate_confidence(len(positions), total_area, raw_average_position)
        self.confidence_history.append(confidence)
        
        # Only update position history if confidence is high enough
        if confidence >= self.confidence_threshold:
            # Check for position jumps
            if (self.last_valid_position is not None and
                self._calculate_distance(raw_average_position, self.last_valid_position) > self.max_position_jump):
                # Large jump detected, use previous position with lower confidence
                confidence *= 0.5
            else:
                self.position_history.append(raw_average_position)
                self.last_valid_position = raw_average_position
        
        # Calculate temporally smoothed position
        smoothed_position = self._calculate_smoothed_position()
        
        # Calculate stability score
        self.stability_score = self._calculate_stability_score()
        
        # The stable position is what extensions should use
        stable_position = smoothed_position if smoothed_position else raw_average_position
        
        return {
            'average_position': raw_average_position,
            'smoothed_position': smoothed_position,
            'stable_position': stable_position,  # This is what extensions should use
            'object_count': len(positions),
            'total_area': total_area,
            'individual_positions': positions,
            'confidence': confidence,
            'stability_score': self.stability_score
        }
    
    def _preprocess_mask(self, mask):
        """
        Apply preprocessing to the mask to reduce noise and improve tracking.
        
        Args:
            mask: Input binary mask
            
        Returns:
            numpy.ndarray: Processed mask
        """
        processed = mask.copy()
        
        # Apply Gaussian blur to reduce noise
        if self.gaussian_blur_radius > 0:
            kernel_size = self.gaussian_blur_radius * 2 + 1
            processed = cv2.GaussianBlur(processed, (kernel_size, kernel_size), 0)
            # Re-threshold after blur
            _, processed = cv2.threshold(processed, 127, 255, cv2.THRESH_BINARY)
        
        # Apply morphological operations
        if self.morphology_kernel_size > 0:
            kernel = np.ones((self.morphology_kernel_size, self.morphology_kernel_size), np.uint8)
            # Opening to remove noise
            processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
            # Closing to fill gaps
            processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def _calculate_confidence(self, object_count, total_area, position):
        """
        Calculate confidence score based on detection quality.
        
        Args:
            object_count: Number of detected objects
            total_area: Total area of detected objects
            position: Current position
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        # Base confidence on object count (prefer 1-3 objects for juggling)
        if object_count == 0:
            count_confidence = 0.0
        elif 1 <= object_count <= 3:
            count_confidence = 1.0
        elif object_count <= 5:
            count_confidence = 0.7
        else:
            count_confidence = 0.3  # Too many objects, likely noise
        
        # Area confidence (prefer reasonable total area)
        area_confidence = min(1.0, total_area / 5000.0)  # Normalize to reasonable area
        
        # Position consistency confidence
        position_confidence = 1.0
        if len(self.position_history) > 1:
            recent_positions = list(self.position_history)[-5:]  # Last 5 positions
            if len(recent_positions) > 1:
                distances = []
                for i in range(1, len(recent_positions)):
                    dist = self._calculate_distance(recent_positions[i], recent_positions[i-1])
                    distances.append(dist)
                avg_movement = sum(distances) / len(distances)
                # Lower confidence for erratic movement
                position_confidence = max(0.1, 1.0 - (avg_movement / 50.0))
        
        # Combine confidences
        overall_confidence = (count_confidence * 0.4 +
                            area_confidence * 0.3 +
                            position_confidence * 0.3)
        
        return min(1.0, max(0.0, overall_confidence))
    
    def _calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two positions."""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _calculate_smoothed_position(self):
        """
        Calculate temporally smoothed position using weighted average.
        
        Returns:
            tuple: Smoothed (x, y) position or None if insufficient data
        """
        if len(self.position_history) == 0:
            return None
        
        # Use only the most recent frames for smoothing
        recent_positions = list(self.position_history)[-self.temporal_smoothing_frames:]
        recent_confidences = list(self.confidence_history)[-len(recent_positions):]
        
        if not recent_positions:
            return None
        
        # Weight recent positions more heavily
        weighted_x = 0
        weighted_y = 0
        total_weight = 0
        
        for i, (pos, conf) in enumerate(zip(recent_positions, recent_confidences)):
            # More recent positions get higher weight
            time_weight = (i + 1) / len(recent_positions)
            # Higher confidence positions get higher weight
            confidence_weight = conf
            # Combine weights
            weight = time_weight * confidence_weight
            
            weighted_x += pos[0] * weight
            weighted_y += pos[1] * weight
            total_weight += weight
        
        if total_weight > 0:
            return (int(weighted_x / total_weight), int(weighted_y / total_weight))
        else:
            return recent_positions[-1]  # Fallback to most recent position
    
    def _calculate_stability_score(self):
        """
        Calculate stability score based on position and confidence history.
        
        Returns:
            float: Stability score between 0.0 and 1.0
        """
        if len(self.position_history) < 3:
            return 0.0
        
        # Calculate position variance
        recent_positions = list(self.position_history)[-10:]  # Last 10 positions
        if len(recent_positions) < 2:
            return 0.0
        
        x_coords = [pos[0] for pos in recent_positions]
        y_coords = [pos[1] for pos in recent_positions]
        
        x_variance = np.var(x_coords)
        y_variance = np.var(y_coords)
        position_stability = 1.0 / (1.0 + (x_variance + y_variance) / 1000.0)
        
        # Calculate confidence stability
        recent_confidences = list(self.confidence_history)[-10:]
        if len(recent_confidences) > 0:
            avg_confidence = sum(recent_confidences) / len(recent_confidences)
            confidence_variance = np.var(recent_confidences)
            confidence_stability = avg_confidence * (1.0 - confidence_variance)
        else:
            confidence_stability = 0.0
        
        # Combine stability measures
        overall_stability = (position_stability * 0.6 + confidence_stability * 0.4)
        return min(1.0, max(0.0, overall_stability))
    
    def _get_empty_result(self):
        """Return empty result dictionary."""
        return {
            'average_position': None,
            'smoothed_position': None,
            'stable_position': self.last_valid_position,  # Keep last known good position
            'object_count': 0,
            'total_area': 0,
            'individual_positions': [],
            'confidence': 0.0,
            'stability_score': self.stability_score
        }
    
    def get_last_position(self):
        """
        Get the last tracked position.
        
        Returns:
            tuple: (x, y) position or None if no position has been tracked
        """
        return self.last_position
    
    def get_stable_position(self):
        """
        Get the stable position that extensions should use.
        
        Returns:
            tuple: (x, y) stable position or None if no stable position available
        """
        if len(self.position_history) > 0:
            return self._calculate_smoothed_position()
        return self.last_valid_position
    
    def reset(self):
        """
        Reset the tracker state.
        """
        self.last_position = None
        self.last_valid_position = None
        self.position_history.clear()
        self.confidence_history.clear()
        self.stability_score = 0.0
    
    # Parameter control methods
    
    def set_temporal_smoothing_frames(self, frames):
        """Set the number of frames to use for temporal smoothing."""
        self.temporal_smoothing_frames = max(1, min(30, frames))
    
    def set_max_position_jump(self, pixels):
        """Set the maximum allowed position jump in pixels."""
        self.max_position_jump = max(10, min(500, pixels))
    
    def set_confidence_threshold(self, threshold):
        """Set the minimum confidence threshold for position updates."""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
    
    def set_morphology_kernel_size(self, size):
        """Set the kernel size for morphological operations."""
        self.morphology_kernel_size = max(0, min(15, size))
    
    def set_gaussian_blur_radius(self, radius):
        """Set the Gaussian blur radius for noise reduction."""
        self.gaussian_blur_radius = max(0, min(10, radius))
    
    def set_min_contour_perimeter(self, perimeter):
        """Set the minimum contour perimeter."""
        self.min_contour_perimeter = max(0, min(200, perimeter))
    
    def get_parameters(self):
        """
        Get all current parameters as a dictionary.
        
        Returns:
            dict: Dictionary containing all parameters
        """
        return {
            'temporal_smoothing_frames': self.temporal_smoothing_frames,
            'max_position_jump': self.max_position_jump,
            'confidence_threshold': self.confidence_threshold,
            'morphology_kernel_size': self.morphology_kernel_size,
            'gaussian_blur_radius': self.gaussian_blur_radius,
            'min_contour_perimeter': self.min_contour_perimeter
        }
    
    def set_parameters(self, params):
        """
        Set parameters from a dictionary.
        
        Args:
            params (dict): Dictionary containing parameters to set
        """
        if 'temporal_smoothing_frames' in params:
            self.set_temporal_smoothing_frames(params['temporal_smoothing_frames'])
        if 'max_position_jump' in params:
            self.set_max_position_jump(params['max_position_jump'])
        if 'confidence_threshold' in params:
            self.set_confidence_threshold(params['confidence_threshold'])
        if 'morphology_kernel_size' in params:
            self.set_morphology_kernel_size(params['morphology_kernel_size'])
        if 'gaussian_blur_radius' in params:
            self.set_gaussian_blur_radius(params['gaussian_blur_radius'])
        if 'min_contour_perimeter' in params:
            self.set_min_contour_perimeter(params['min_contour_perimeter'])
    
    # Settings persistence methods
    
    def save_settings(self, filepath):
        """
        Save current settings to a JSON file.
        
        Args:
            filepath (str): Path to save the settings file
        """
        settings = {
            'simple_tracker_settings': self.get_parameters(),
            'version': '1.0'
        }
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving simple tracker settings: {e}")
            return False
    
    def load_settings(self, filepath):
        """
        Load settings from a JSON file.
        
        Args:
            filepath (str): Path to the settings file
            
        Returns:
            bool: True if settings were loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(filepath):
                return False
                
            with open(filepath, 'r') as f:
                settings = json.load(f)
            
            if 'simple_tracker_settings' in settings:
                self.set_parameters(settings['simple_tracker_settings'])
                return True
            else:
                print("Invalid settings file format")
                return False
                
        except Exception as e:
            print(f"Error loading simple tracker settings: {e}")
            return False
    
    def get_preset_settings(self, preset_name):
        """
        Get predefined preset settings.
        
        Args:
            preset_name (str): Name of the preset ('indoor', 'outdoor', 'low_light', 'default')
            
        Returns:
            dict: Dictionary containing preset parameters
        """
        presets = {
            'default': {
                'temporal_smoothing_frames': 5,
                'max_position_jump': 100,
                'confidence_threshold': 0.3,
                'morphology_kernel_size': 3,
                'gaussian_blur_radius': 1,
                'min_contour_perimeter': 20
            },
            'indoor': {
                'temporal_smoothing_frames': 7,
                'max_position_jump': 80,
                'confidence_threshold': 0.4,
                'morphology_kernel_size': 2,
                'gaussian_blur_radius': 1,
                'min_contour_perimeter': 15
            },
            'outdoor': {
                'temporal_smoothing_frames': 10,
                'max_position_jump': 120,
                'confidence_threshold': 0.2,
                'morphology_kernel_size': 4,
                'gaussian_blur_radius': 2,
                'min_contour_perimeter': 25
            },
            'low_light': {
                'temporal_smoothing_frames': 8,
                'max_position_jump': 90,
                'confidence_threshold': 0.25,
                'morphology_kernel_size': 5,
                'gaussian_blur_radius': 3,
                'min_contour_perimeter': 30
            },
            'stable': {
                'temporal_smoothing_frames': 15,
                'max_position_jump': 50,
                'confidence_threshold': 0.5,
                'morphology_kernel_size': 3,
                'gaussian_blur_radius': 2,
                'min_contour_perimeter': 25
            }
        }
        
        return presets.get(preset_name, presets['default'])
    
    def apply_preset(self, preset_name):
        """
        Apply a predefined preset.
        
        Args:
            preset_name (str): Name of the preset to apply
        """
        preset_params = self.get_preset_settings(preset_name)
        self.set_parameters(preset_params)