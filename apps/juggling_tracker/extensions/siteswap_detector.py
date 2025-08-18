import numpy as np
from juggling_tracker.extensions.extension_manager import Extension

class SiteswapDetector(Extension):
    """
    Detects the siteswap pattern in a juggling sequence.
    
    This extension analyzes the trajectories of juggling balls to determine the siteswap pattern.
    It provides the detected pattern and a confidence score.
    """
    
    def __init__(self):
        """
        Initialize the SiteswapDetector extension.
        """
        self.pattern = ""
        self.confidence = 0.0
        self.throw_heights = []
        self.last_throw_times = {}
        self.last_catch_times = {}
        self.throw_threshold = 0.5  # m/s
        self.catch_threshold = 0.2  # m/s
        self.min_pattern_length = 2
        self.max_pattern_length = 10
        self.pattern_candidates = {}
        self.current_sequence = []
        self.sequence_history = []
        self.max_history_length = 10
    
    def initialize(self):
        """
        Initialize the extension.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.reset()
        return True
    
    def reset(self):
        """
        Reset the detector.
        """
        self.pattern = ""
        self.confidence = 0.0
        self.throw_heights = []
        self.last_throw_times = {}
        self.last_catch_times = {}
        self.pattern_candidates = {}
        self.current_sequence = []
        self.sequence_history = []
    
    def process_frame(self, frame_data):
        """
        Process a frame of data.
        
        Args:
            frame_data: A dictionary containing:
                - color_image: The color image
                - depth_image: The depth image
                - tracked_balls: Dictionary of ball_name -> ball_info
                - ball_positions: Dictionary of ball_name -> 3D position
                - ball_velocities: Dictionary of ball_name -> 3D velocity
                - hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
                - timestamp: The timestamp of the frame
                
        Returns:
            dict: Results of processing the frame
        """
        # Extract data from frame_data
        ball_positions = frame_data.get('ball_positions', {})
        ball_velocities = frame_data.get('ball_velocities', {})
        hand_positions = frame_data.get('hand_positions', (None, None))
        timestamp = frame_data.get('timestamp', 0)
        
        # Detect throws and catches
        for ball_name, velocity in ball_velocities.items():
            position = ball_positions.get(ball_name)
            if position is None:
                continue
            
            # Check for throws (ball moving up fast)
            if velocity[1] > self.throw_threshold:  # Positive y velocity means moving up
                if ball_name not in self.last_throw_times or timestamp - self.last_throw_times[ball_name] > 0.5:
                    self.last_throw_times[ball_name] = timestamp
                    self.throw_heights.append(position[1])  # Record the height at throw time
                    
                    # If we have enough throw heights, estimate the siteswap value
                    if len(self.throw_heights) > 1:
                        # Normalize the height to get an approximate siteswap value
                        normalized_height = self.normalize_height(position[1])
                        self.current_sequence.append(normalized_height)
                        
                        # Keep the sequence at a reasonable length
                        if len(self.current_sequence) > self.max_pattern_length:
                            self.current_sequence.pop(0)
                        
                        # If we have enough throws, try to detect a pattern
                        if len(self.current_sequence) >= self.min_pattern_length:
                            self.detect_pattern()
            
            # Check for catches (ball moving down and close to a hand)
            if velocity[1] < -self.catch_threshold:  # Negative y velocity means moving down
                left_hand, right_hand = hand_positions
                
                if left_hand is not None:
                    left_hand_3d = (left_hand[0], left_hand[1], position[2])  # Approximate 3D position
                    left_distance = np.linalg.norm(np.array(position) - np.array(left_hand_3d))
                    if left_distance < 0.2:  # 20 cm
                        if ball_name not in self.last_catch_times or timestamp - self.last_catch_times[ball_name] > 0.5:
                            self.last_catch_times[ball_name] = timestamp
                
                if right_hand is not None:
                    right_hand_3d = (right_hand[0], right_hand[1], position[2])  # Approximate 3D position
                    right_distance = np.linalg.norm(np.array(position) - np.array(right_hand_3d))
                    if right_distance < 0.2:  # 20 cm
                        if ball_name not in self.last_catch_times or timestamp - self.last_catch_times[ball_name] > 0.5:
                            self.last_catch_times[ball_name] = timestamp
        
        # Return results
        return self.get_results()
    
    def normalize_height(self, height):
        """
        Normalize a throw height to a siteswap value.
        
        Args:
            height (float): Throw height in meters
            
        Returns:
            int: Approximate siteswap value
        """
        # This is a very simplified approach
        # In a real implementation, you would need to calibrate this based on the juggler's style
        
        # Map height to siteswap value (1-9)
        # Assuming a 3 is about 1 meter high
        normalized = int(round(height * 3))
        
        # Clamp to reasonable range
        return max(1, min(9, normalized))
    
    def detect_pattern(self):
        """
        Detect a pattern in the current sequence.
        """
        # Try different pattern lengths
        for pattern_length in range(self.min_pattern_length, min(self.max_pattern_length, len(self.current_sequence) // 2 + 1)):
            # Check if the sequence repeats
            is_pattern = True
            
            for i in range(pattern_length):
                for j in range(1, len(self.current_sequence) // pattern_length):
                    if i + j * pattern_length < len(self.current_sequence) and self.current_sequence[i] != self.current_sequence[i + j * pattern_length]:
                        is_pattern = False
                        break
                
                if not is_pattern:
                    break
            
            if is_pattern:
                # Extract the pattern
                pattern = ''.join(str(x) for x in self.current_sequence[:pattern_length])
                
                # Update pattern candidates
                if pattern in self.pattern_candidates:
                    self.pattern_candidates[pattern] += 1
                else:
                    self.pattern_candidates[pattern] = 1
                
                # Update the detected pattern
                if self.pattern_candidates[pattern] > self.pattern_candidates.get(self.pattern, 0):
                    self.pattern = pattern
                    
                    # Calculate confidence based on how many times we've seen this pattern
                    total_counts = sum(self.pattern_candidates.values())
                    self.confidence = self.pattern_candidates[pattern] / total_counts if total_counts > 0 else 0.0
                
                # Add to sequence history
                self.sequence_history.append(pattern)
                if len(self.sequence_history) > self.max_history_length:
                    self.sequence_history.pop(0)
                
                break
    
    def get_results(self):
        """
        Get the results of the extension.
        
        Returns:
            dict: A dictionary containing the results of the extension
        """
        return {
            'pattern': self.pattern,
            'confidence': f"{self.confidence:.2f}",
            'candidates': ', '.join(f"{p}:{c}" for p, c in sorted(self.pattern_candidates.items(), key=lambda x: x[1], reverse=True)[:3])
        }
    
    def get_name(self):
        """
        Get the name of the extension.
        
        Returns:
            str: The name of the extension
        """
        return "SiteswapDetector"
    
    def get_description(self):
        """
        Get the description of the extension.
        
        Returns:
            str: The description of the extension
        """
        return "Detects the siteswap pattern in a juggling sequence."
    
    def get_version(self):
        """
        Get the version of the extension.
        
        Returns:
            str: The version of the extension
        """
        return "1.0.0"
    
    def get_author(self):
        """
        Get the author of the extension.
        
        Returns:
            str: The author of the extension
        """
        return "Juggling Tracker Team"
    
    def get_settings(self):
        """
        Get the settings of the extension.
        
        Returns:
            dict: A dictionary containing the settings of the extension
        """
        return {
            'throw_threshold': self.throw_threshold,
            'catch_threshold': self.catch_threshold,
            'min_pattern_length': self.min_pattern_length,
            'max_pattern_length': self.max_pattern_length
        }
    
    def update_settings(self, settings):
        """
        Update the settings of the extension.
        
        Args:
            settings: A dictionary containing the new settings
            
        Returns:
            bool: True if the settings were updated successfully, False otherwise
        """
        try:
            if 'throw_threshold' in settings:
                self.throw_threshold = float(settings['throw_threshold'])
            
            if 'catch_threshold' in settings:
                self.catch_threshold = float(settings['catch_threshold'])
            
            if 'min_pattern_length' in settings:
                self.min_pattern_length = int(settings['min_pattern_length'])
            
            if 'max_pattern_length' in settings:
                self.max_pattern_length = int(settings['max_pattern_length'])
            
            return True
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False
    
    def cleanup(self):
        """
        Clean up resources used by the extension.
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        self.reset()
        return True