import numpy as np
import cv2
import json
import os
import time

class ColorCalibration:
    """
    Handles the calibration of ball colors.
    
    This module is responsible for:
    - Allowing adding new balls by tossing them and automatically detecting their color
    - Maintaining a database of ball colors with customizable names
    - Providing functions to save and load calibrations
    - Supporting adjusting existing calibrations
    """
    
    def __init__(self, name="Default", config_dir=None):
        """
        Initialize the ColorCalibration module.
        
        Args:
            name (str): Name of the calibration set
            config_dir (str): Directory to save calibration files (default: None, will use ./config)
        """
        self.name = name
        self.balls = {}  # Dictionary of ball_name -> color_info
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
    
    def add_ball(self, ball_name, color_sample, initial_variance=None):
        """
        Add a new ball to the calibration.
        
        Args:
            ball_name (str): Name of the ball
            color_sample (numpy.ndarray): BGR color sample
            initial_variance (numpy.ndarray): Initial color variance (default: None)
            
        Returns:
            bool: True if the ball was added successfully, False otherwise
        """
        try:
            # Convert to LAB color space for better color comparison
            lab_color = cv2.cvtColor(np.uint8([[color_sample]]), cv2.COLOR_BGR2LAB)[0][0]
            
            # Use default variance if not provided
            if initial_variance is None:
                initial_variance = np.array([10, 10, 10])
            
            # Store color information
            self.balls[ball_name] = {
                'lab_color': lab_color,
                'color_variance': initial_variance,
                'bgr_color': color_sample,
                'last_update': time.time(),
                'samples': 1
            }
            
            return True
        except Exception as e:
            print(f"Error adding ball: {e}")
            return False
    
    def update_ball_color(self, ball_name, color_sample, weight=0.1):
        """
        Update the color of an existing ball.
        
        Args:
            ball_name (str): Name of the ball
            color_sample (numpy.ndarray): BGR color sample
            weight (float): Weight of the new sample (0-1)
            
        Returns:
            bool: True if the ball was updated successfully, False otherwise
        """
        if ball_name not in self.balls:
            return False
            
        try:
            # Convert to LAB color space for better color comparison
            lab_color = cv2.cvtColor(np.uint8([[color_sample]]), cv2.COLOR_BGR2LAB)[0][0]
            
            # Update with weighted average
            current = self.balls[ball_name]['lab_color']
            self.balls[ball_name]['lab_color'] = (1 - weight) * current + weight * lab_color
            
            # Update BGR color
            self.balls[ball_name]['bgr_color'] = color_sample
            
            # Update last update time
            self.balls[ball_name]['last_update'] = time.time()
            
            # Update sample count
            self.balls[ball_name]['samples'] += 1
            
            # Adjust variance based on new sample
            if self.balls[ball_name]['samples'] > 1:
                # Calculate the difference between the new sample and the current average
                diff = np.abs(lab_color - self.balls[ball_name]['lab_color'])
                
                # Update variance with a weighted average
                current_var = self.balls[ball_name]['color_variance']
                self.balls[ball_name]['color_variance'] = (1 - weight) * current_var + weight * diff
            
            return True
        except Exception as e:
            print(f"Error updating ball color: {e}")
            return False
    
    def remove_ball(self, ball_name):
        """
        Remove a ball from the calibration.
        
        Args:
            ball_name (str): Name of the ball
            
        Returns:
            bool: True if the ball was removed successfully, False otherwise
        """
        if ball_name in self.balls:
            del self.balls[ball_name]
            return True
        return False
    
    def get_ball_color(self, ball_name):
        """
        Get the color of a ball.
        
        Args:
            ball_name (str): Name of the ball
            
        Returns:
            tuple: (lab_color, color_variance) or (None, None) if the ball doesn't exist
        """
        if ball_name in self.balls:
            return self.balls[ball_name]['lab_color'], self.balls[ball_name]['color_variance']
        return None, None
    
    def get_ball_bgr_color(self, ball_name):
        """
        Get the BGR color of a ball.
        
        Args:
            ball_name (str): Name of the ball
            
        Returns:
            numpy.ndarray: BGR color or None if the ball doesn't exist
        """
        if ball_name in self.balls:
            return self.balls[ball_name]['bgr_color']
        return None
    
    def get_all_balls(self):
        """
        Get all balls in the calibration.
        
        Returns:
            dict: Dictionary of ball_name -> color_info
        """
        return self.balls
    
    def calculate_color_distance(self, color1, color2):
        """
        Calculate the distance between two colors in LAB space.
        
        Args:
            color1 (numpy.ndarray): First color in LAB space
            color2 (numpy.ndarray): Second color in LAB space
            
        Returns:
            float: Distance between the colors
        """
        return np.linalg.norm(color1 - color2)
    
    def match_color(self, color_sample, max_distance=40.0):
        """
        Match a color sample to a calibrated ball.
        
        Args:
            color_sample (numpy.ndarray): BGR color sample
            max_distance (float): Maximum acceptable color distance
            
        Returns:
            tuple: (ball_name, distance) or (None, None) if no match is found
        """
        try:
            # Convert to LAB color space for better color comparison
            lab_color = cv2.cvtColor(np.uint8([[color_sample]]), cv2.COLOR_BGR2LAB)[0][0]
            
            best_match = None
            best_distance = float('inf')
            
            for ball_name, ball_info in self.balls.items():
                # Calculate the Mahalanobis distance (weighted by variance)
                variance = ball_info['color_variance']
                # Avoid division by zero
                variance = np.maximum(variance, 0.1)
                
                # Calculate the normalized distance
                diff = lab_color - ball_info['lab_color']
                normalized_diff = diff / variance
                distance = np.linalg.norm(normalized_diff)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = ball_name
            
            if best_match is not None and best_distance <= max_distance:
                return best_match, best_distance
            
            return None, None
        except Exception as e:
            print(f"Error matching color: {e}")
            return None, None
    
    def save(self, filename=None):
        """
        Save the calibration to a file.
        
        Args:
            filename (str): Name of the file (default: None, will use the calibration name)
            
        Returns:
            bool: True if the calibration was saved successfully, False otherwise
        """
        try:
            if filename is None:
                filename = f"{self.name.replace(' ', '_').lower()}.json"
            
            # Ensure the filename has a .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Create the full path
            filepath = os.path.join(self.config_dir, filename)
            
            # Prepare the data for saving
            data = {
                'name': self.name,
                'balls': {}
            }
            
            for ball_name, ball_info in self.balls.items():
                data['balls'][ball_name] = {
                    'lab_color': ball_info['lab_color'].tolist(),
                    'color_variance': ball_info['color_variance'].tolist(),
                    'bgr_color': ball_info['bgr_color'].tolist(),
                    'last_update': ball_info['last_update'],
                    'samples': ball_info['samples']
                }
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False
    
    def load(self, filename):
        """
        Load a calibration from a file.
        
        Args:
            filename (str): Name of the file
            
        Returns:
            bool: True if the calibration was loaded successfully, False otherwise
        """
        try:
            # Ensure the filename has a .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Create the full path
            filepath = os.path.join(self.config_dir, filename)
            
            # Load from file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Update the calibration
            self.name = data['name']
            self.balls = {}
            
            for ball_name, ball_info in data['balls'].items():
                self.balls[ball_name] = {
                    'lab_color': np.array(ball_info['lab_color']),
                    'color_variance': np.array(ball_info['color_variance']),
                    'bgr_color': np.array(ball_info['bgr_color']),
                    'last_update': ball_info['last_update'],
                    'samples': ball_info['samples']
                }
            
            return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False
    
    def list_calibrations(self):
        """
        List all available calibration files.
        
        Returns:
            list: List of calibration filenames
        """
        try:
            # Get all .json files in the config directory
            files = [f for f in os.listdir(self.config_dir) if f.endswith('.json')]
            return files
        except Exception as e:
            print(f"Error listing calibrations: {e}")
            return []
    
    def get_calibration_info(self, filename):
        """
        Get information about a calibration file.
        
        Args:
            filename (str): Name of the file
            
        Returns:
            dict: Dictionary with calibration information or None if the file doesn't exist
        """
        try:
            # Ensure the filename has a .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Create the full path
            filepath = os.path.join(self.config_dir, filename)
            
            # Check if the file exists
            if not os.path.exists(filepath):
                return None
            
            # Load from file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Extract basic information
            info = {
                'name': data['name'],
                'num_balls': len(data['balls']),
                'ball_names': list(data['balls'].keys())
            }
            
            return info
        except Exception as e:
            print(f"Error getting calibration info: {e}")
            return None