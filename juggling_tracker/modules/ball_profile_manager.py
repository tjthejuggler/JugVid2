# juggling_tracker/modules/ball_profile_manager.py
import json
import os
from .ball_profile import BallProfile

class BallProfileManager:
    def __init__(self, config_dir):
        self.profiles = []  # List of BallProfile objects
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True) # Ensure config_dir exists
        self.profiles_filepath = os.path.join(config_dir, "ball_profiles.json")
        self.load_profiles()

    def add_profile(self, profile):
        if isinstance(profile, BallProfile):
            # Check for existing profile with same name (optional, can allow duplicates or rename)
            # for p in self.profiles:
            #     if p.name == profile.name:
            #         profile.name = f"{profile.name}_{len(self.profiles)}" # simple renaming
            #         break
            self.profiles.append(profile)
            print(f"Added profile: {profile.name}")
        else:
            print("Error: Attempted to add non-BallProfile object.")
    
    def remove_profile(self, profile_id):
        self.profiles = [p for p in self.profiles if p.profile_id != profile_id]

    def get_profile_by_id(self, profile_id):
        for p in self.profiles:
            if p.profile_id == profile_id:
                return p
        return None

    def get_all_profiles(self):
        return self.profiles

    def save_profiles(self):
        data_to_save = [p.to_dict() for p in self.profiles]
        try:
            with open(self.profiles_filepath, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            print(f"Saved {len(self.profiles)} ball profiles to {self.profiles_filepath}")
        except Exception as e:
            print(f"Error saving ball profiles: {e}")

    def load_profiles(self):
        if not os.path.exists(self.profiles_filepath):
            print(f"Profile file not found: {self.profiles_filepath}. No profiles loaded.")
            return

        try:
            with open(self.profiles_filepath, 'r') as f:
                loaded_data = json.load(f)
            self.profiles = [BallProfile.from_dict(pd) for pd in loaded_data]
            print(f"Loaded {len(self.profiles)} ball profiles from {self.profiles_filepath}")
        except Exception as e:
            self.profiles = [] # Ensure profiles list is empty on error
            print(f"Error loading ball profiles: {e}. Profiles reset.")