import cv2
import numpy as np
import time

class Visualizer:
    """
    Handles the display of tracking results and UI elements.
    
    This module is responsible for:
    - Displaying the color stream with overlaid ball tracking information
    - Showing depth information when needed
    - Providing debugging visualizations for development
    """
    
    def __init__(self, window_name="Juggling Tracker", window_size=(1280, 720)):
        """
        Initialize the Visualizer module.
        
        Args:
            window_name (str): Name of the main window
            window_size (tuple): Size of the main window (width, height)
        """
        self.window_name = window_name
        self.window_size = window_size
        self.debug_mode = False
        self.show_depth = False
        self.show_masks = False
        self.show_fps = True
        self.show_extension_results = True
        self.last_frame_time = time.time()
        self.fps = 0
        self.frame_count = 0
        self.fps_update_interval = 10  # Update FPS every 10 frames
        
        # Create a clean window without the OpenCV toolbar
        # Use cv2.WINDOW_NORMAL with cv2.WINDOW_GUI_NORMAL to hide the toolbar
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow(self.window_name, *self.window_size)
        
        # Set window properties
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
        
        # Disable OpenCV's default toolbar
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_NORMAL)
    
    def draw_tracked_balls(self, frame, identified_balls, ball_colors=None):
        """
        Draw tracked balls on a frame.
        
        Args:
            frame: Color image in BGR format
            identified_balls: Dictionary of ball_name -> blob
            ball_colors: Dictionary of ball_name -> BGR color (optional)
            
        Returns:
            numpy.ndarray: Frame with tracked balls drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Draw each identified ball
        for ball_name, blob in identified_balls.items():
            # Get the color for this ball
            if ball_colors is not None and ball_name in ball_colors:
                color = ball_colors[ball_name]
            else:
                # Generate a color based on the ball name
                hash_val = hash(ball_name) % 0xFFFFFF
                color = (hash_val & 0xFF, (hash_val >> 8) & 0xFF, (hash_val >> 16) & 0xFF)
            
            # Draw the ball
            cv2.circle(result, blob['center'], blob['radius'], color, 2)
            
            # Draw the ball name
            cv2.putText(result, ball_name, 
                       (blob['center'][0] - blob['radius'], blob['center'][1] - blob['radius'] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return result
    
    def draw_hand_positions(self, frame, hand_positions, left_color=(0, 0, 255), right_color=(0, 255, 0), radius=10):
        """
        Draw hand positions on a frame.
        
        Args:
            frame: Color image in BGR format
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y))
            left_color: Color for the left hand (BGR)
            right_color: Color for the right hand (BGR)
            radius: Radius of the circles
            
        Returns:
            numpy.ndarray: Frame with hand positions drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        left_hand, right_hand = hand_positions
        
        # Draw circles for the hands
        if left_hand is not None:
            cv2.circle(result, left_hand, radius, left_color, -1)
            cv2.putText(result, "L", (left_hand[0] - 5, left_hand[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        if right_hand is not None:
            cv2.circle(result, right_hand, radius, right_color, -1)
            cv2.putText(result, "R", (right_hand[0] - 5, right_hand[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return result
    
    def draw_fps(self, frame):
        """
        Draw FPS information on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with FPS information drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Calculate FPS
        current_time = time.time()
        self.frame_count += 1
        
        if self.frame_count % self.fps_update_interval == 0:
            time_diff = current_time - self.last_frame_time
            if time_diff > 0:
                self.fps = self.fps_update_interval / time_diff
            self.last_frame_time = current_time
        
        # Draw FPS in the bottom-right corner instead of top-left
        fps_text = f"FPS: {self.fps:.1f}"
        text_size = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        text_x = result.shape[1] - text_size[0] - 10
        text_y = result.shape[0] - 10
        
        cv2.putText(result, fps_text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result
    
    def draw_extension_results(self, frame, extension_results):
        """
        Draw extension results on a frame.
        
        Args:
            frame: Color image in BGR format
            extension_results: Dictionary of extension_name -> results
            
        Returns:
            numpy.ndarray: Frame with extension results drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Draw extension results
        y_offset = 70  # Start below FPS
        
        for extension_name, results in extension_results.items():
            # Draw extension name
            cv2.putText(result, f"{extension_name}:", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_offset += 25
            
            # Draw extension results
            for key, value in results.items():
                cv2.putText(result, f"  {key}: {value}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 20
            
            y_offset += 10  # Add some space between extensions
        
        return result
    
    def draw_debug_info(self, frame, debug_info):
        """
        Draw debug information on a frame.
        
        Args:
            frame: Color image in BGR format
            debug_info: Dictionary of debug information
            
        Returns:
            numpy.ndarray: Frame with debug information drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Draw debug information
        y_offset = 70  # Start below FPS
        
        for key, value in debug_info.items():
            cv2.putText(result, f"{key}: {value}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_offset += 20
        
        return result
    
    def create_composite_view(self, color_image, depth_image=None, masks=None):
        """
        Create a composite view with color and depth images.
        
        Args:
            color_image: Color image in BGR format
            depth_image: Depth image (optional)
            masks: Dictionary of mask_name -> mask (optional)
            
        Returns:
            numpy.ndarray: Composite image
        """
        # Start with the color image
        composite = color_image.copy()
        
        # If depth image is available and should be shown
        if depth_image is not None and self.show_depth:
            # Convert depth image to 8-bit and apply colormap
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03), 
                cv2.COLORMAP_JET
            )
            
            # Resize depth colormap to match color image size
            depth_colormap = cv2.resize(
                depth_colormap, 
                (color_image.shape[1], color_image.shape[0])
            )
            
            # Create a composite image (side by side)
            composite = np.hstack((color_image, depth_colormap))
        
        # If masks are available and should be shown
        if masks is not None and self.show_masks:
            mask_images = []
            
            for mask_name, mask in masks.items():
                # Convert mask to BGR for visualization
                mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                
                # Add the mask name
                cv2.putText(mask_bgr, mask_name, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Resize mask to a smaller size
                mask_small = cv2.resize(mask_bgr, (320, 240))
                
                mask_images.append(mask_small)
            
            # Combine masks horizontally
            if mask_images:
                masks_row = np.hstack(mask_images)
                
                # Add padding to match the width of the composite image
                if masks_row.shape[1] < composite.shape[1]:
                    padding = np.zeros((masks_row.shape[0], composite.shape[1] - masks_row.shape[1], 3), dtype=np.uint8)
                    masks_row = np.hstack((masks_row, padding))
                
                # Combine with the composite image
                composite = np.vstack((composite, masks_row))
        
        return composite
    
    def show_frame(self, color_image, depth_image=None, masks=None, identified_balls=None, 
                  hand_positions=None, extension_results=None, debug_info=None, ball_colors=None):
        """
        Show a frame with tracking information.
        
        Args:
            color_image: Color image in BGR format
            depth_image: Depth image (optional)
            masks: Dictionary of mask_name -> mask (optional)
            identified_balls: Dictionary of ball_name -> blob (optional)
            hand_positions: Tuple of ((left_hand_x, left_hand_y), (right_hand_x, right_hand_y)) (optional)
            extension_results: Dictionary of extension_name -> results (optional)
            debug_info: Dictionary of debug information (optional)
            ball_colors: Dictionary of ball_name -> BGR color (optional)
            
        Returns:
            int: Key pressed by the user
        """
        # Draw tracked balls
        if identified_balls:
            color_image = self.draw_tracked_balls(color_image, identified_balls, ball_colors)
        
        # Draw hand positions
        if hand_positions:
            color_image = self.draw_hand_positions(color_image, hand_positions)
        
        # Draw FPS
        if self.show_fps:
            color_image = self.draw_fps(color_image)
        
        # Draw extension results
        if extension_results and self.show_extension_results:
            color_image = self.draw_extension_results(color_image, extension_results)
        
        # Draw debug information
        if debug_info and self.debug_mode:
            color_image = self.draw_debug_info(color_image, debug_info)
        
        # Create composite view
        composite = self.create_composite_view(color_image, depth_image, masks)
        
        # Show the frame
        cv2.imshow(self.window_name, composite)
        
        # Check if the window is still open
        if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
            return 27  # Return ESC key code to signal window close
        
        # Wait for a key press
        return cv2.waitKey(1)
    
    def toggle_debug_mode(self):
        """
        Toggle debug mode.
        
        Returns:
            bool: New debug mode state
        """
        self.debug_mode = not self.debug_mode
        return self.debug_mode
    
    def toggle_depth_view(self):
        """
        Toggle depth view.
        
        Returns:
            bool: New depth view state
        """
        self.show_depth = not self.show_depth
        return self.show_depth
    
    def toggle_masks_view(self):
        """
        Toggle masks view.
        
        Returns:
            bool: New masks view state
        """
        self.show_masks = not self.show_masks
        return self.show_masks
    
    def toggle_fps_display(self):
        """
        Toggle FPS display.
        
        Returns:
            bool: New FPS display state
        """
        self.show_fps = not self.show_fps
        return self.show_fps
    
    def toggle_extension_results(self):
        """
        Toggle extension results display.
        
        Returns:
            bool: New extension results display state
        """
        self.show_extension_results = not self.show_extension_results
        return self.show_extension_results
    
    def cleanup(self):
        """
        Clean up resources used by the visualizer.
        """
        cv2.destroyAllWindows()