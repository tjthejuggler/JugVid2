import mediapipe as mp
import numpy as np
import cv2

class SkeletonDetector:
    """
    Handles the detection of the juggler's skeleton and extraction of hand positions.
    
    This module is responsible for:
    - Using MediaPipe Pose for skeleton detection
    - Extracting hand positions from the skeleton
    - Creating masks to exclude hands from ball detection
    """
    
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """
        Initialize the SkeletonDetector module.
        
        Args:
            min_detection_confidence (float): Minimum confidence value for the detection to be considered successful
            min_tracking_confidence (float): Minimum confidence value for the tracking to be considered successful
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
    def detect_skeleton(self, color_image):
        """
        Detect the skeleton in a color image.
        
        Args:
            color_image: Color image in BGR format
            
        Returns:
            mediapipe.framework.formats.landmark_pb2.NormalizedLandmarkList: Pose landmarks
        """
        # Convert BGR image to RGB
        image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
        
        # Process the image and detect the pose
        results = self.pose.process(image_rgb)
        
        return results.pose_landmarks
    
    def get_hand_positions(self, pose_landmarks, image_shape):
        """
        Extract hand positions from the pose landmarks.
        
        Args:
            pose_landmarks: Pose landmarks from MediaPipe
            image_shape: Shape of the image (height, width, channels)
            
        Returns:
            tuple: ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y)) or (None, None) if hands not detected
        """
        if not pose_landmarks:
            return None, None
            
        img_height, img_width = image_shape[:2]
        
        # Get the wrist landmarks
        left_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Convert normalized coordinates to pixel values
        left_hand_x = int(left_wrist.x * img_width)
        left_hand_y = int(left_wrist.y * img_height)
        right_hand_x = int(right_wrist.x * img_width)
        right_hand_y = int(right_wrist.y * img_height)
        
        return (left_hand_x, left_hand_y), (right_hand_x, right_hand_y)
    
    def create_hand_mask(self, hand_positions, image_shape, hand_radius=30):
        """
        Create a mask to exclude hands from ball detection.
        
        Args:
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
            image_shape: Shape of the image (height, width, channels)
            hand_radius: Radius of the hand mask in pixels
            
        Returns:
            numpy.ndarray: Binary mask where hands are white (255)
        """
        left_hand, right_hand = hand_positions
        
        # Create an empty mask
        hand_mask = np.zeros((image_shape[0], image_shape[1]), dtype=np.uint8)
        
        # Draw circles for the hands
        if left_hand is not None:
            cv2.circle(hand_mask, left_hand, hand_radius, 255, -1)
        
        if right_hand is not None:
            cv2.circle(hand_mask, right_hand, hand_radius, 255, -1)
        
        return hand_mask
    
    def draw_skeleton(self, color_image, pose_landmarks):
        """
        Draw the skeleton on a color image.
        
        Args:
            color_image: Color image in BGR format
            pose_landmarks: Pose landmarks from MediaPipe
            
        Returns:
            numpy.ndarray: Color image with skeleton drawn
        """
        if pose_landmarks:
            # Create a copy of the image to draw on
            image_with_skeleton = color_image.copy()
            
            # Draw the pose landmarks
            self.mp_drawing.draw_landmarks(
                image_with_skeleton,
                pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )
            
            return image_with_skeleton
        
        return color_image
    
    def draw_hands(self, color_image, hand_positions, left_color=(0, 0, 255), right_color=(0, 255, 0), radius=10):
        """
        Draw the hand positions on a color image.
        
        Args:
            color_image: Color image in BGR format
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
            left_color: Color for the left hand (BGR)
            right_color: Color for the right hand (BGR)
            radius: Radius of the circles
            
        Returns:
            numpy.ndarray: Color image with hands drawn
        """
        left_hand, right_hand = hand_positions
        
        # Create a copy of the image to draw on
        image_with_hands = color_image.copy()
        
        # Draw circles for the hands
        if left_hand is not None:
            cv2.circle(image_with_hands, left_hand, radius, left_color, -1)
            cv2.putText(image_with_hands, "L", (left_hand[0] - 5, left_hand[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        if right_hand is not None:
            cv2.circle(image_with_hands, right_hand, radius, right_color, -1)
            cv2.putText(image_with_hands, "R", (right_hand[0] - 5, right_hand[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return image_with_hands