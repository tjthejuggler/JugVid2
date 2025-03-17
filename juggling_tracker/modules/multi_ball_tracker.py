import numpy as np
import cv2
import time

class BallTracker:
    """
    Tracks a single ball using a Kalman filter.
    """
    
    def __init__(self, ball_name, initial_position, initial_color=None, process_noise=1e-2, measurement_noise=1e-1):
        """
        Initialize a ball tracker.
        
        Args:
            ball_name (str): Name of the ball
            initial_position (tuple): Initial 3D position (x, y, z)
            initial_color: Initial color of the ball (optional)
            process_noise (float): Process noise for the Kalman filter
            measurement_noise (float): Measurement noise for the Kalman filter
        """
        self.ball_name = ball_name
        self.color = initial_color
        self.last_update_time = time.time()
        self.visible = True
        self.consecutive_misses = 0
        self.max_consecutive_misses = 30  # Number of frames before considering the ball lost
        
        # Initialize Kalman filter (6 state: pos & vel)
        self.kalman = cv2.KalmanFilter(6, 3)
        self.kalman.measurementMatrix = np.hstack((np.eye(3, dtype=np.float32), 
                                                  np.zeros((3, 3), dtype=np.float32)))
        self.kalman.transitionMatrix = np.array([
            [1, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 1],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]], dtype=np.float32)
        self.kalman.processNoiseCov = np.eye(6, dtype=np.float32) * process_noise
        self.kalman.measurementNoiseCov = np.eye(3, dtype=np.float32) * measurement_noise
        
        # Initialize state
        self.kalman.statePost = np.array([
            initial_position[0], initial_position[1], initial_position[2],
            0, 0, 0], dtype=np.float32).reshape(6, 1)
        
        # History of positions for trajectory analysis
        self.position_history = [initial_position]
        self.max_history_length = 100  # Maximum number of positions to keep in history
    
    def predict(self):
        """
        Predict the next position of the ball.
        
        Returns:
            tuple: Predicted 3D position (x, y, z)
        """
        prediction = self.kalman.predict()
        return prediction[:3].reshape(3)
    
    def update(self, position):
        """
        Update the tracker with a new position measurement.
        
        Args:
            position (tuple): New 3D position (x, y, z)
            
        Returns:
            tuple: Updated 3D position (x, y, z)
        """
        measurement = np.array(position, dtype=np.float32).reshape(3, 1)
        self.kalman.correct(measurement)
        self.last_update_time = time.time()
        self.visible = True
        self.consecutive_misses = 0
        
        # Add position to history
        current_position = self.get_position()
        self.position_history.append((current_position[0], current_position[1], current_position[2]))
        
        # Trim history if it gets too long
        if len(self.position_history) > self.max_history_length:
            self.position_history = self.position_history[-self.max_history_length:]
        
        return self.get_position()
    
    def miss_update(self):
        """
        Handle a missed update (ball not detected).
        
        Returns:
            bool: True if the ball is still being tracked, False if it's considered lost
        """
        self.consecutive_misses += 1
        self.visible = False
        
        # If we've missed too many updates, consider the ball lost
        if self.consecutive_misses > self.max_consecutive_misses:
            return False
        
        # Otherwise, just use the predicted position
        prediction = self.predict()
        self.position_history.append((prediction[0], prediction[1], prediction[2]))
        
        # Trim history if it gets too long
        if len(self.position_history) > self.max_history_length:
            self.position_history = self.position_history[-self.max_history_length:]
        
        return True
    
    def get_position(self):
        """
        Get the current position of the ball.
        
        Returns:
            tuple: Current 3D position (x, y, z)
        """
        return self.kalman.statePost[:3].reshape(3)
    
    def get_velocity(self):
        """
        Get the current velocity of the ball.
        
        Returns:
            tuple: Current 3D velocity (vx, vy, vz)
        """
        return self.kalman.statePost[3:].reshape(3)
    
    def get_trajectory(self):
        """
        Get the trajectory of the ball.
        
        Returns:
            list: List of 3D positions
        """
        return self.position_history
    
    def is_visible(self):
        """
        Check if the ball is currently visible.
        
        Returns:
            bool: True if the ball is visible, False otherwise
        """
        return self.visible
    
    def time_since_last_update(self):
        """
        Get the time since the last update.
        
        Returns:
            float: Time in seconds since the last update
        """
        return time.time() - self.last_update_time


class MultiBallTracker:
    """
    Handles the tracking of multiple balls in 3D space.
    
    This module is responsible for:
    - Using Kalman filters to track each ball's position and velocity in 3D space
    - Handling ball identity assignment and maintenance
    - Providing smooth trajectories even with occasional detection failures
    """
    
    def __init__(self, max_tracking_age=2.0):
        """
        Initialize the MultiBallTracker module.
        
        Args:
            max_tracking_age (float): Maximum time in seconds to keep tracking a ball without updates
        """
        self.trackers = {}  # Dictionary of ball_name -> BallTracker
        self.max_tracking_age = max_tracking_age
    
    def update_trackers(self, identified_balls, ball_positions, ball_depths, intrinsics=None):
        """
        Update the trackers with new ball positions.
        
        Args:
            identified_balls: Dictionary of ball_name -> blob
            ball_positions: Dictionary of ball_name -> (x, y) position
            ball_depths: Dictionary of ball_name -> depth
            intrinsics: Camera intrinsics for 3D deprojection (optional)
            
        Returns:
            dict: Dictionary of ball_name -> 3D position
        """
        # Predict next positions for all trackers
        for ball_name, tracker in list(self.trackers.items()):
            tracker.predict()
        
        # Update trackers with new measurements
        updated_positions = {}
        
        for ball_name, position_2d in ball_positions.items():
            depth = ball_depths.get(ball_name, 0.0)
            
            # Skip if depth is invalid
            if depth <= 0.0:
                continue
            
            # Convert 2D position and depth to 3D position
            if intrinsics is not None:
                import pyrealsense2 as rs
                position_3d = rs.rs2_deproject_pixel_to_point(intrinsics, [position_2d[0], position_2d[1]], depth)
            else:
                # Simple 3D position without deprojection
                position_3d = (position_2d[0], position_2d[1], depth)
            
            # If we already have a tracker for this ball, update it
            if ball_name in self.trackers:
                updated_position = self.trackers[ball_name].update(position_3d)
                updated_positions[ball_name] = updated_position
            else:
                # Otherwise, create a new tracker
                blob = identified_balls.get(ball_name)
                color = blob.get('color') if blob else None
                self.trackers[ball_name] = BallTracker(ball_name, position_3d, color)
                updated_positions[ball_name] = position_3d
        
        # Handle missed updates
        for ball_name, tracker in list(self.trackers.items()):
            if ball_name not in updated_positions:
                # If the ball wasn't updated, mark it as missed
                if not tracker.miss_update():
                    # If we've missed too many updates, remove the tracker
                    del self.trackers[ball_name]
                else:
                    # Otherwise, use the predicted position
                    updated_positions[ball_name] = tracker.get_position()
        
        # Clean up old trackers
        self.cleanup_lost_balls()
        
        return updated_positions
    
    def predict_positions(self):
        """
        Predict the next positions of all tracked balls.
        
        Returns:
            dict: Dictionary of ball_name -> predicted 3D position
        """
        return {ball_name: tracker.predict() for ball_name, tracker in self.trackers.items()}
    
    def get_tracked_balls(self):
        """
        Get all currently tracked balls.
        
        Returns:
            dict: Dictionary of ball_name -> BallTracker
        """
        return self.trackers
    
    def get_ball_positions(self):
        """
        Get the current positions of all tracked balls.
        
        Returns:
            dict: Dictionary of ball_name -> 3D position
        """
        return {ball_name: tracker.get_position() for ball_name, tracker in self.trackers.items()}
    
    def get_ball_velocities(self):
        """
        Get the current velocities of all tracked balls.
        
        Returns:
            dict: Dictionary of ball_name -> 3D velocity
        """
        return {ball_name: tracker.get_velocity() for ball_name, tracker in self.trackers.items()}
    
    def get_ball_trajectories(self):
        """
        Get the trajectories of all tracked balls.
        
        Returns:
            dict: Dictionary of ball_name -> list of 3D positions
        """
        return {ball_name: tracker.get_trajectory() for ball_name, tracker in self.trackers.items()}
    
    def get_visible_balls(self):
        """
        Get all currently visible balls.
        
        Returns:
            dict: Dictionary of ball_name -> BallTracker
        """
        return {ball_name: tracker for ball_name, tracker in self.trackers.items() if tracker.is_visible()}
    
    def cleanup_lost_balls(self):
        """
        Clean up trackers for balls that haven't been updated in a while.
        """
        for ball_name, tracker in list(self.trackers.items()):
            if tracker.time_since_last_update() > self.max_tracking_age:
                del self.trackers[ball_name]
    
    def reset(self):
        """
        Reset all trackers.
        """
        self.trackers = {}