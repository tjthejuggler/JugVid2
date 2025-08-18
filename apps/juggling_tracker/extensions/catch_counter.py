import numpy as np
from juggling_tracker.extensions.extension_manager import Extension

class CatchCounter(Extension):
    """
    Counts the number of catches and drops in a juggling pattern.
    
    This extension analyzes the trajectories of juggling balls to detect catches and drops.
    It provides statistics on the number of catches, drops, and the current streak.
    """
    
    def __init__(self):
        """
        Initialize the CatchCounter extension.
        """
        self.catches = 0
        self.drops = 0
        self.current_streak = 0
        self.max_streak = 0
        self.last_ball_positions = {}
        self.hand_positions = None
        self.catch_threshold = 0.1  # meters
        self.drop_threshold = 0.5  # meters
        self.min_velocity_for_drop = 0.5  # meters/second
        self.last_catch_time = 0
        self.last_drop_time = 0
        self.catch_cooldown = 0.5  # seconds
        self.drop_cooldown = 1.0  # seconds
    
    def initialize(self):
        """
        Initialize the extension.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.reset_counters()
        return True
    
    def reset_counters(self):
        """
        Reset all counters.
        """
        self.catches = 0
        self.drops = 0
        self.current_streak = 0
        self.max_streak = 0
        self.last_ball_positions = {}
        self.hand_positions = None
        self.last_catch_time = 0
        self.last_drop_time = 0
    
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
        
        # Update hand positions
        self.hand_positions = hand_positions
        
        # Check for catches and drops
        for ball_name, position in ball_positions.items():
            # Get the ball's velocity
            velocity = ball_velocities.get(ball_name, (0, 0, 0))
            velocity_magnitude = np.linalg.norm(velocity)
            
            # Check if this is a new ball
            if ball_name not in self.last_ball_positions:
                self.last_ball_positions[ball_name] = position
                continue
            
            # Get the last position
            last_position = self.last_ball_positions[ball_name]
            
            # Check for catches (ball close to hand and moving slowly)
            if self.is_catch(position, velocity_magnitude, hand_positions, timestamp):
                self.catches += 1
                self.current_streak += 1
                self.max_streak = max(self.max_streak, self.current_streak)
                self.last_catch_time = timestamp
            
            # Check for drops (ball moving down fast and far from hands)
            if self.is_drop(position, velocity, hand_positions, timestamp):
                self.drops += 1
                self.current_streak = 0
                self.last_drop_time = timestamp
            
            # Update last position
            self.last_ball_positions[ball_name] = position
        
        # Return results
        return self.get_results()
    
    def is_catch(self, ball_position, velocity_magnitude, hand_positions, timestamp):
        """
        Check if a ball has been caught.
        
        Args:
            ball_position: 3D position of the ball
            velocity_magnitude: Magnitude of the ball's velocity
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
            timestamp: Current timestamp
            
        Returns:
            bool: True if the ball has been caught, False otherwise
        """
        # Check if we're in the catch cooldown period
        if timestamp - self.last_catch_time < self.catch_cooldown:
            return False
        
        # Check if the ball is moving slowly
        if velocity_magnitude > 0.5:  # m/s
            return False
        
        # Check if the ball is close to a hand
        left_hand, right_hand = hand_positions
        
        if left_hand is not None:
            left_hand_3d = (left_hand[0], left_hand[1], ball_position[2])  # Approximate 3D position
            left_distance = np.linalg.norm(np.array(ball_position) - np.array(left_hand_3d))
            if left_distance < self.catch_threshold:
                return True
        
        if right_hand is not None:
            right_hand_3d = (right_hand[0], right_hand[1], ball_position[2])  # Approximate 3D position
            right_distance = np.linalg.norm(np.array(ball_position) - np.array(right_hand_3d))
            if right_distance < self.catch_threshold:
                return True
        
        return False
    
    def is_drop(self, ball_position, ball_velocity, hand_positions, timestamp):
        """
        Check if a ball has been dropped.
        
        Args:
            ball_position: 3D position of the ball
            ball_velocity: 3D velocity of the ball
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
            timestamp: Current timestamp
            
        Returns:
            bool: True if the ball has been dropped, False otherwise
        """
        # Check if we're in the drop cooldown period
        if timestamp - self.last_drop_time < self.drop_cooldown:
            return False
        
        # Check if the ball is moving down fast
        if ball_velocity[1] < -self.min_velocity_for_drop:  # Negative y velocity means moving down
            # Check if the ball is far from both hands
            left_hand, right_hand = hand_positions
            
            min_distance = float('inf')
            
            if left_hand is not None:
                left_hand_3d = (left_hand[0], left_hand[1], ball_position[2])  # Approximate 3D position
                left_distance = np.linalg.norm(np.array(ball_position) - np.array(left_hand_3d))
                min_distance = min(min_distance, left_distance)
            
            if right_hand is not None:
                right_hand_3d = (right_hand[0], right_hand[1], ball_position[2])  # Approximate 3D position
                right_distance = np.linalg.norm(np.array(ball_position) - np.array(right_hand_3d))
                min_distance = min(min_distance, right_distance)
            
            # If the ball is far from both hands and moving down fast, it's a drop
            if min_distance > self.drop_threshold:
                return True
        
        return False
    
    def get_results(self):
        """
        Get the results of the extension.
        
        Returns:
            dict: A dictionary containing the results of the extension
        """
        return {
            'catches': self.catches,
            'drops': self.drops,
            'current_streak': self.current_streak,
            'max_streak': self.max_streak
        }
    
    def get_name(self):
        """
        Get the name of the extension.
        
        Returns:
            str: The name of the extension
        """
        return "CatchCounter"
    
    def get_description(self):
        """
        Get the description of the extension.
        
        Returns:
            str: The description of the extension
        """
        return "Counts the number of catches and drops in a juggling pattern."
    
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
            'catch_threshold': self.catch_threshold,
            'drop_threshold': self.drop_threshold,
            'min_velocity_for_drop': self.min_velocity_for_drop,
            'catch_cooldown': self.catch_cooldown,
            'drop_cooldown': self.drop_cooldown
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
            if 'catch_threshold' in settings:
                self.catch_threshold = float(settings['catch_threshold'])
            
            if 'drop_threshold' in settings:
                self.drop_threshold = float(settings['drop_threshold'])
            
            if 'min_velocity_for_drop' in settings:
                self.min_velocity_for_drop = float(settings['min_velocity_for_drop'])
            
            if 'catch_cooldown' in settings:
                self.catch_cooldown = float(settings['catch_cooldown'])
            
            if 'drop_cooldown' in settings:
                self.drop_cooldown = float(settings['drop_cooldown'])
            
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
        self.reset_counters()
        return True