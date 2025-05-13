from collections import OrderedDict
import numpy as np
import time
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
# from scipy.optimize import linear_sum_assignment # If using Hungarian algorithm later


class MultiBallTracker:
    """
    Handles the tracking of multiple balls in 3D space with profile-specific tracking.
    
    This module is responsible for:
    - Using Kalman filters to track each ball's position and velocity in 3D space
    - Handling ball identity assignment and maintenance based on profile IDs
    - Providing smooth trajectories even with occasional detection failures
    """
    
    def __init__(self, max_disappeared=10, max_distance_px=50): # max_distance_px might need adjustment based on 3D distance logic
        self.next_object_id = 0
        # Stores {object_id: {'kalman': kf, 'profile_id': pid, 'name': name, 'disappeared_frames': N, ...}}
        self.tracked_objects = OrderedDict()
        self.max_disappeared = max_disappeared
        # This max_distance_px might be re-evaluated if using 3D distances for association primarily.
        # For now, it can serve as a fallback or for a 2D pre-check.
        self.max_distance_px = max_distance_px
        self.max_3d_distance_m = 0.2 # New: Max 3D distance for association (e.g., 20cm)


        # Store history: {object_id: [{'position_3d': (x,y,z), 'timestamp': t, ...}]}
        self.history = {}
    
    def _register(self, identified_ball, position_3d, timestamp):
        object_id = self.next_object_id
        self.next_object_id += 1

        kf = KalmanFilter(dim_x=6, dim_z=3) # State: x,y,z, vx,vy,vz; Measurement: x,y,z
        dt = 1/30 # Assume 30 FPS, ideally get actual dt or pass it in
        
        # State transition matrix
        kf.F = np.array([[1,0,0,dt,0,0], [0,1,0,0,dt,0], [0,0,1,0,0,dt],
                         [0,0,0,1,0,0], [0,0,0,0,1,0], [0,0,0,0,0,1]])
        # Measurement function
        kf.H = np.array([[1,0,0,0,0,0], [0,1,0,0,0,0], [0,0,1,0,0,0]])
        # Measurement noise covariance matrix
        kf.R *= 0.5 # Adjust based on measurement uncertainty (e.g., 0.05 for 5cm std dev)
        # Process noise covariance matrix
        # Use filterpy's Q_discrete_white_noise for a basic model
        # Adjust 'var' based on expected process noise (how much velocity can change per step)
        q_var = 0.1 # Variance for process noise
        kf.Q = Q_discrete_white_noise(dim=3, dt=dt, var=q_var, block_size=2, order_by_dim=False)
        # Initial state covariance matrix
        kf.P *= 10.0 # Initial uncertainty in state (position and velocity)
        
        # Initial state vector [x, y, z, vx, vy, vz]
        kf.x = np.array([position_3d[0], position_3d[1], position_3d[2], 0, 0, 0]).T

        self.tracked_objects[object_id] = {
            'kalman': kf,
            'profile_id': identified_ball['profile_id'], # NEW
            'name': identified_ball['name'],             # NEW
            'disappeared_frames': 0,
            'last_seen_timestamp': timestamp,
            'last_position_2d': identified_ball['position'], # Store 2D for display
            'last_radius_px': identified_ball['radius']    # Store radius for display
        }
        self.history[object_id] = [{'position_3d': position_3d.tolist(), 'timestamp': timestamp}] # Store as list for JSON
        # print(f"Registered new track ID {object_id} for profile {identified_ball['profile_id']} ({identified_ball['name']}) at {position_3d}")
    
    def _deregister(self, object_id):
        if object_id in self.tracked_objects: # Check if exists before trying to access
            # print(f"Deregistered track ID {object_id} (Profile: {self.tracked_objects[object_id]['profile_id']}, Name: {self.tracked_objects[object_id]['name']})")
            del self.tracked_objects[object_id]
            if object_id in self.history: # Also check history
                # Optionally, do something with self.history[object_id] (e.g. save it)
                del self.history[object_id]
        else:
            # print(f"Attempted to deregister non-existent track ID {object_id}")
            pass # Silently pass or log warning
    
    def update_trackers(self, identified_balls_list, # Renamed for clarity
                        # ball_positions_2d, # Derived from identified_balls_list
                        # ball_depths_m,   # Derived from identified_balls_list
                        intrinsics, current_time=None): # Pass current_time for consistency
        
        timestamp = current_time if current_time is not None else time.time()

        current_detections = []
        if intrinsics and intrinsics.fx != 0 and intrinsics.fy != 0: # Ensure valid intrinsics
            for ball_data in identified_balls_list:
                pos2d = ball_data['position']
                depth_m = ball_data['depth_m']
                
                px, py = pos2d
                # Ensure cx, cy, fx, fy are present in intrinsics
                if not all(hasattr(intrinsics, attr) for attr in ['ppx', 'ppy', 'fx', 'fy']):
                    # print("Warning: Intrinsics object missing ppx, ppy, fx, or fy.")
                    continue

                cx, cy = intrinsics.ppx, intrinsics.ppy
                fx, fy = intrinsics.fx, intrinsics.fy
                
                # Deprojection:
                x_3d = (px - cx) * depth_m / fx
                y_3d = (py - cy) * depth_m / fy
                z_3d = depth_m # Depth is the Z coordinate in camera space
                pos3d = np.array([x_3d, y_3d, z_3d])
                
                current_detections.append({
                    'profile_id': ball_data['profile_id'],
                    'pos2d': np.array(pos2d),
                    'pos3d': pos3d,
                    'original_ball_data': ball_data # Keep original for registration
                })
        else:
            # print("Warning: Invalid or missing intrinsics. Cannot perform 3D tracking.")
            # Fallback: mark all existing tracks as disappeared if no valid 3D detections
            for obj_id in list(self.tracked_objects.keys()):
                self.tracked_objects[obj_id]['disappeared_frames'] += 1
                if self.tracked_objects[obj_id]['disappeared_frames'] > self.max_disappeared:
                    self._deregister(obj_id)
            return self.get_tracked_ball_info_for_display()


        if not self.tracked_objects and not current_detections: # No tracks and no detections
            return []
        
        if not self.tracked_objects: # No existing tracks, register all new valid detections
            for det in current_detections:
                self._register(det['original_ball_data'], det['pos3d'], timestamp)
            return self.get_tracked_ball_info_for_display()

        # If no current detections, increment disappeared frames for all tracks
        if not current_detections:
            for obj_id in list(self.tracked_objects.keys()): # Use list() for safe iteration while modifying
                self.tracked_objects[obj_id]['disappeared_frames'] += 1
                if self.tracked_objects[obj_id]['disappeared_frames'] > self.max_disappeared:
                    self._deregister(obj_id)
            return self.get_tracked_ball_info_for_display()

        # --- Data Association ---
        object_ids = list(self.tracked_objects.keys())
        
        # Predict next state for all existing tracks
        predicted_positions_3d = []
        for obj_id in object_ids:
            self.tracked_objects[obj_id]['kalman'].predict()
            # Predicted 3D position (x, y, z) from Kalman state
            predicted_positions_3d.append(self.tracked_objects[obj_id]['kalman'].x_prior[:3].flatten())


        # Simple greedy assignment (can be replaced with Hungarian later if needed)
        # This matches each track to its closest valid detection.
        
        # Create a list of detection indices that haven't been matched yet
        unmatched_detection_indices = list(range(len(current_detections)))
        # Keep track of which tracks have been matched
        matched_track_indices = [False] * len(object_ids)

        # Iterate through tracks
        for i, obj_id in enumerate(object_ids):
            track_profile_id = self.tracked_objects[obj_id]['profile_id']
            track_predicted_pos_3d = predicted_positions_3d[i]
            
            best_det_idx = -1
            min_dist_3d = self.max_3d_distance_m # Use the 3D distance threshold

            # Find the best matching detection for the current track
            for k_idx, det_k_original_idx in enumerate(unmatched_detection_indices):
                det_k = current_detections[det_k_original_idx]
                
                if det_k['profile_id'] != track_profile_id:
                    continue # Must match profile ID

                dist_3d = np.linalg.norm(track_predicted_pos_3d - det_k['pos3d'])
                
                if dist_3d < min_dist_3d:
                    min_dist_3d = dist_3d
                    best_det_idx = det_k_original_idx # Store original index of the detection
            
            if best_det_idx != -1: # Found a match for this track
                detection_data = current_detections[best_det_idx]
                self.tracked_objects[obj_id]['kalman'].update(detection_data['pos3d'])
                self.tracked_objects[obj_id]['disappeared_frames'] = 0
                self.tracked_objects[obj_id]['last_seen_timestamp'] = timestamp
                self.tracked_objects[obj_id]['last_position_2d'] = detection_data['original_ball_data']['position']
                self.tracked_objects[obj_id]['last_radius_px'] = detection_data['original_ball_data']['radius']
                
                current_kf_state_3d = self.tracked_objects[obj_id]['kalman'].x[:3].flatten().tolist()
                self.history[obj_id].append({'position_3d': current_kf_state_3d, 'timestamp': timestamp})
                
                # Mark this detection as used by removing its original index from unmatched_detection_indices
                # This needs care if indices shift. Better to mark as used.
                # For simplicity here, we'll rebuild unmatched_detection_indices or use a set.
                # A robust way: unmatched_detection_indices.remove(best_det_idx)
                # For now, let's assume a mechanism to mark 'best_det_idx' as used.
                # A simple way for this loop structure:
                unmatched_detection_indices.remove(best_det_idx)
                matched_track_indices[i] = True


        # Handle unmatched tracks (increment disappeared or deregister)
        for i, obj_id in enumerate(object_ids):
            if not matched_track_indices[i]:
                self.tracked_objects[obj_id]['disappeared_frames'] += 1
                if self.tracked_objects[obj_id]['disappeared_frames'] > self.max_disappeared:
                    self._deregister(obj_id)
        
        # Register new tracks for remaining unmatched detections
        for det_idx in unmatched_detection_indices: # These are original indices of unmatched detections
            det = current_detections[det_idx]
            self._register(det['original_ball_data'], det['pos3d'], timestamp)
            
        return self.get_tracked_ball_info_for_display()
    
    def get_tracked_ball_info_for_display(self, intrinsics=None): # Add intrinsics if projecting 3D to 2D
        display_info = []
        for obj_id, data in self.tracked_objects.items():
            pos2d_display = data['last_position_2d'] # Default to last known 2D
            radius_display = data['last_radius_px']  # Default to last known radius

            # If object is not considered 'disappeared' (or if you want to show predictions)
            # you can project the Kalman filter's 3D state back to 2D for smoother display.
            # This requires intrinsics.
            if data['disappeared_frames'] < self.max_disappeared and intrinsics and \
               all(hasattr(intrinsics, attr) for attr in ['fx', 'fy', 'ppx', 'ppy']):
                
                kf_state_3d = data['kalman'].x[:3].flatten() # x, y, z
                x_3d, y_3d, z_3d = kf_state_3d[0], kf_state_3d[1], kf_state_3d[2]

                if z_3d > 0: # Avoid division by zero or negative depth
                    u_proj = (x_3d * intrinsics.fx / z_3d) + intrinsics.ppx
                    v_proj = (y_3d * intrinsics.fy / z_3d) + intrinsics.ppy
                    pos2d_display = (int(u_proj), int(v_proj))
                    
                    # Optionally, re-calculate radius based on profile's real_world_radius_m and current z_3d
                    profile_ref = data.get('profile_ref') # Assuming profile_ref is stored or accessible
                    # This part is more involved if profile_ref isn't directly in `data`.
                    # For now, use last_radius_px or a fixed default if projecting.
                    # if profile_ref and profile_ref.real_world_radius_m:
                    #    radius_display = int((profile_ref.real_world_radius_m * intrinsics.fx) / z_3d)


            # Only add to display if not too long disappeared, or based on your display preference
            if data['disappeared_frames'] <= self.max_disappeared : # Show even if disappeared a bit, using last known/predicted
                display_info.append({
                    'id': obj_id,
                    'name': data['name'],
                    'position_2d': pos2d_display,
                    'radius_px': radius_display,
                    'profile_id': data['profile_id'],
                    'position_3d_kf': data['kalman'].x[:3].flatten().tolist(), # Current KF 3D state
                    'disappeared_frames': data['disappeared_frames']
                })
        return display_info
    
    def get_tracked_balls(self):
        balls_data = []
        for obj_id, data in self.tracked_objects.items():
             # Ensure Kalman state has expected shape before accessing velocity
            kf_state = data['kalman'].x.flatten()
            position_3d = kf_state[0:3].tolist() if len(kf_state) >=3 else [0,0,0]
            velocity_3d = kf_state[3:6].tolist() if len(kf_state) >=6 else [0,0,0]

            balls_data.append({
                'id': obj_id,
                'profile_id': data['profile_id'],
                'name': data['name'],
                'position_3d': position_3d,
                'velocity_3d': velocity_3d,
                'last_seen_timestamp': data['last_seen_timestamp'],
                'disappeared_frames': data['disappeared_frames'],
                'history': self.history.get(obj_id, [])[-100:] # Last 100 history points
            })
        return balls_data
    
    def get_ball_velocities(self):
        velocities = {}
        for obj_id, data in self.tracked_objects.items():
            kf_state = data['kalman'].x.flatten()
            if len(kf_state) >= 6:
                velocities[obj_id] = kf_state[3:6].tolist() # vx, vy, vz
            else:
                velocities[obj_id] = [0,0,0]
        return velocities
    
    def reset(self):
        """
        Reset all trackers.
        """
        self.tracked_objects = OrderedDict()
        self.history = {}
        self.next_object_id = 0