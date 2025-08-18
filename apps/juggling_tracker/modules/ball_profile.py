# juggling_tracker/modules/ball_profile.py
import uuid
import numpy as np

class BallProfile:
    def __init__(self, profile_id=None, name="Unnamed Ball"):
        self.profile_id = profile_id if profile_id else str(uuid.uuid4())
        self.name = name

        # Color characteristics (HSV)
        self.hsv_mean = None  # E.g., np.array([h, s, v])
        self.hsv_std = None   # E.g., np.array([h_std, s_std, v_std])
        self.hsv_low = None   # Derived: mean - N*std
        self.hsv_high = None  # Derived: mean + N*std

        # 3D Size characteristics (more robust than 2D pixel size)
        self.real_world_radius_m = None # Estimated radius in meters
        self.radius_confidence_factor = 1.5 # Allow for some variance, e.g. 1.5 means 0.5x to 1.5x the radius

        # Depth characteristics (at calibration time)
        self.calibration_depth_m = None # Depth at which this profile was created
        
        # Optional: Shape descriptors (e.g., circularity, if needed later)
        self.circularity_min = 0.7 # Example: minimum circularity for a blob to be considered

        # Store raw data for potential re-calibration or advanced analysis
        self.raw_hsv_values = [] # List of HSV values from calibration pixels
        self.raw_depth_values = [] # List of depth values from calibration pixels

    def set_color_characteristics(self, hsv_values_roi):
        """Calculates and sets HSV mean, std, low, and high thresholds."""
        if len(hsv_values_roi) == 0:
            print(f"Warning: No HSV values provided for profile {self.profile_id}")
            return

        self.raw_hsv_values = np.array(hsv_values_roi)
        self.hsv_mean = np.mean(self.raw_hsv_values, axis=0)
        self.hsv_std = np.std(self.raw_hsv_values, axis=0)

        # Define bounds (e.g., 2 standard deviations, configurable)
        # Handle Hue wrap-around for red (0/180) carefully if necessary
        # For simplicity now, just clamp. More sophisticated hue range needed for reds.
        std_multiplier = 2.0 
        self.hsv_low = np.clip(self.hsv_mean - std_multiplier * self.hsv_std, [0, 0, 0], [179, 255, 255]).astype(int)
        self.hsv_high = np.clip(self.hsv_mean + std_multiplier * self.hsv_std, [0, 0, 0], [179, 255, 255]).astype(int)
        
        # Ensure S and V mins are reasonable (e.g. not too dark or desaturated unless intended)
        self.hsv_low[1] = max(self.hsv_low[1], 30) # Min Saturation
        self.hsv_low[2] = max(self.hsv_low[2], 30) # Min Value/Brightness

    def set_size_characteristics(self, pixel_radius, depth_m, intrinsics):
        """Estimates real-world radius using pixel radius, depth, and camera intrinsics."""
        if intrinsics is None or depth_m <= 0:
            print(f"Warning: Cannot set size for {self.profile_id} - missing intrinsics or invalid depth.")
            self.real_world_radius_m = None # Or a default small size
            return

        # Simplified projection: radius_m = (pixel_radius * depth_m) / focal_length_pixels
        # Assuming fx and fy are similar, use average or fx
        fx = intrinsics.fx
        self.real_world_radius_m = (pixel_radius * depth_m) / fx
        self.calibration_depth_m = depth_m
        print(f"Profile {self.name}: Estimated 3D radius: {self.real_world_radius_m:.3f}m at depth {depth_m:.2f}m")

    def set_depth_characteristics(self, depth_values_roi_m):
        """Stores raw depth values for potential analysis."""
        if len(depth_values_roi_m) == 0:
            print(f"Warning: No depth values provided for profile {self.profile_id}")
            return
        self.raw_depth_values = np.array(depth_values_roi_m)
        # self.calibration_depth_m could also be set here from mean(depth_values_roi_m)

    def to_dict(self):
        """Serialize to dictionary for saving."""
        return {
            'profile_id': self.profile_id,
            'name': self.name,
            'hsv_mean': self.hsv_mean.tolist() if self.hsv_mean is not None else None,
            'hsv_std': self.hsv_std.tolist() if self.hsv_std is not None else None,
            'hsv_low': self.hsv_low.tolist() if self.hsv_low is not None else None,
            'hsv_high': self.hsv_high.tolist() if self.hsv_high is not None else None,
            'real_world_radius_m': self.real_world_radius_m,
            'radius_confidence_factor': self.radius_confidence_factor,
            'calibration_depth_m': self.calibration_depth_m,
            'circularity_min': self.circularity_min,
            # raw_values are usually not saved unless for debug/advanced features
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize from dictionary."""
        profile = cls(profile_id=data['profile_id'], name=data.get('name', "Unnamed Ball"))
        profile.hsv_mean = np.array(data['hsv_mean']) if data['hsv_mean'] is not None else None
        profile.hsv_std = np.array(data['hsv_std']) if data['hsv_std'] is not None else None
        profile.hsv_low = np.array(data['hsv_low']) if data['hsv_low'] is not None else None
        profile.hsv_high = np.array(data['hsv_high']) if data['hsv_high'] is not None else None
        profile.real_world_radius_m = data.get('real_world_radius_m')
        profile.radius_confidence_factor = data.get('radius_confidence_factor', 1.5)
        profile.calibration_depth_m = data.get('calibration_depth_m')
        profile.circularity_min = data.get('circularity_min', 0.7)
        return profile