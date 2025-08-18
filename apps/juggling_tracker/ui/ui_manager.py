import cv2
import numpy as np
import os
import time

class Button:
    """
    Represents a button in the UI.
    """
    
    def __init__(self, x, y, width, height, text, callback=None, color=(100, 100, 100), 
                text_color=(255, 255, 255), hover_color=(150, 150, 150), border_radius=0):
        """
        Initialize a button.
        
        Args:
            x (int): X coordinate of the button
            y (int): Y coordinate of the button
            width (int): Width of the button
            height (int): Height of the button
            text (str): Text to display on the button
            callback (function): Function to call when the button is clicked
            color (tuple): Color of the button (BGR)
            text_color (tuple): Color of the text (BGR)
            hover_color (tuple): Color of the button when hovered (BGR)
            border_radius (int): Radius of the button corners
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.hover_color = hover_color
        self.border_radius = border_radius
        self.hovered = False
        self.active = True
    
    def contains_point(self, x, y):
        """
        Check if a point is inside the button.
        
        Args:
            x (int): X coordinate of the point
            y (int): Y coordinate of the point
            
        Returns:
            bool: True if the point is inside the button, False otherwise
        """
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
    
    def draw(self, frame):
        """
        Draw the button on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with the button drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Get the button color
        color = self.hover_color if self.hovered else self.color
        
        # Draw the button rectangle with rounded corners if border_radius > 0
        if self.border_radius > 0:
            # Create a mask for the rounded rectangle
            mask = np.zeros((self.height, self.width), dtype=np.uint8)
            cv2.rectangle(mask, (self.border_radius, 0), (self.width - self.border_radius, self.height), 255, -1)
            cv2.rectangle(mask, (0, self.border_radius), (self.width, self.height - self.border_radius), 255, -1)
            cv2.circle(mask, (self.border_radius, self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.width - self.border_radius, self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.border_radius, self.height - self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.width - self.border_radius, self.height - self.border_radius), self.border_radius, 255, -1)
            
            # Create a colored rectangle
            colored_rect = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            colored_rect[:] = color
            
            # Apply the mask to the colored rectangle
            masked_rect = cv2.bitwise_and(colored_rect, colored_rect, mask=mask)
            
            # Copy the masked rectangle to the frame
            roi = result[self.y:self.y + self.height, self.x:self.x + self.width]
            result[self.y:self.y + self.height, self.x:self.x + self.width] = cv2.addWeighted(roi, 0, masked_rect, 1, 0)
        else:
            # Draw a simple rectangle
            cv2.rectangle(result, (self.x, self.y), (self.x + self.width, self.y + self.height), color, -1)
        
        # Draw the button text
        text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        text_x = self.x + (self.width - text_size[0]) // 2
        text_y = self.y + (self.height + text_size[1]) // 2
        cv2.putText(result, self.text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.text_color, 2)
        
        return result
    
    def handle_mouse_move(self, x, y):
        """
        Handle mouse movement.
        
        Args:
            x (int): X coordinate of the mouse
            y (int): Y coordinate of the mouse
            
        Returns:
            bool: True if the button state changed, False otherwise
        """
        was_hovered = self.hovered
        self.hovered = self.contains_point(x, y)
        return was_hovered != self.hovered
    
    def handle_mouse_click(self, x, y):
        """
        Handle mouse click.
        
        Args:
            x (int): X coordinate of the mouse
            y (int): Y coordinate of the mouse
            
        Returns:
            bool: True if the button was clicked, False otherwise
        """
        if self.active and self.contains_point(x, y) and self.callback:
            self.callback()
            return True
        return False


class Menu:
    """
    Represents a menu in the UI.
    """
    
    def __init__(self, x, y, width, items=None, color=(70, 70, 70), 
                text_color=(255, 255, 255), hover_color=(150, 150, 150), border_radius=5):
        """
        Initialize a menu.
        
        Args:
            x (int): X coordinate of the menu
            y (int): Y coordinate of the menu
            width (int): Width of the menu
            items (list): List of (text, callback) tuples
            color (tuple): Color of the menu (BGR)
            text_color (tuple): Color of the text (BGR)
            hover_color (tuple): Color of the item when hovered (BGR)
            border_radius (int): Radius of the menu corners
        """
        self.x = x
        self.y = y
        self.width = width
        self.items = items or []
        self.color = color
        self.text_color = text_color
        self.hover_color = hover_color
        self.border_radius = border_radius
        self.visible = False
        self.buttons = []
        self.item_height = 30
        self.update_buttons()
    
    def update_buttons(self):
        """
        Update the buttons in the menu.
        """
        self.buttons = []
        for i, (text, callback) in enumerate(self.items):
            button = Button(
                self.x, self.y + (i + 1) * self.item_height, 
                self.width, self.item_height, 
                text, callback, 
                self.color, self.text_color, self.hover_color
            )
            self.buttons.append(button)
    
    def add_item(self, text, callback):
        """
        Add an item to the menu.
        
        Args:
            text (str): Text to display for the item
            callback (function): Function to call when the item is clicked
        """
        self.items.append((text, callback))
        self.update_buttons()
    
    def remove_item(self, text):
        """
        Remove an item from the menu.
        
        Args:
            text (str): Text of the item to remove
            
        Returns:
            bool: True if the item was removed, False otherwise
        """
        for i, (item_text, _) in enumerate(self.items):
            if item_text == text:
                self.items.pop(i)
                self.update_buttons()
                return True
        return False
    
    def draw(self, frame):
        """
        Draw the menu on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with the menu drawn
        """
        if not self.visible:
            return frame
        
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Calculate menu height
        height = (len(self.items) + 1) * self.item_height
        
        # Draw the menu background with rounded corners
        if self.border_radius > 0:
            # Create a mask for the rounded rectangle
            mask = np.zeros((height, self.width), dtype=np.uint8)
            cv2.rectangle(mask, (self.border_radius, 0), (self.width - self.border_radius, height), 255, -1)
            cv2.rectangle(mask, (0, self.border_radius), (self.width, height - self.border_radius), 255, -1)
            cv2.circle(mask, (self.border_radius, self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.width - self.border_radius, self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.border_radius, height - self.border_radius), self.border_radius, 255, -1)
            cv2.circle(mask, (self.width - self.border_radius, height - self.border_radius), self.border_radius, 255, -1)
            
            # Create a colored rectangle
            colored_rect = np.zeros((height, self.width, 3), dtype=np.uint8)
            colored_rect[:] = self.color
            
            # Apply the mask to the colored rectangle
            masked_rect = cv2.bitwise_and(colored_rect, colored_rect, mask=mask)
            
            # Copy the masked rectangle to the frame
            roi = result[self.y:self.y + height, self.x:self.x + self.width]
            
            # Make sure the ROI is within the frame bounds
            if roi.shape[0] == masked_rect.shape[0] and roi.shape[1] == masked_rect.shape[1]:
                result[self.y:self.y + height, self.x:self.x + self.width] = cv2.addWeighted(roi, 0, masked_rect, 1, 0)
        else:
            # Draw a simple rectangle
            cv2.rectangle(result, (self.x, self.y), (self.x + self.width, self.y + height), self.color, -1)
        
        # Draw the menu items
        for button in self.buttons:
            result = button.draw(result)
        
        return result
    
    def handle_mouse_move(self, x, y):
        """
        Handle mouse movement.
        
        Args:
            x (int): X coordinate of the mouse
            y (int): Y coordinate of the mouse
            
        Returns:
            bool: True if any button state changed, False otherwise
        """
        if not self.visible:
            return False
        
        changed = False
        for button in self.buttons:
            if button.handle_mouse_move(x, y):
                changed = True
        
        return changed
    
    def handle_mouse_click(self, x, y):
        """
        Handle mouse click.
        
        Args:
            x (int): X coordinate of the mouse
            y (int): Y coordinate of the mouse
            
        Returns:
            bool: True if any button was clicked, False otherwise
        """
        if not self.visible:
            return False
        
        for button in self.buttons:
            if button.handle_mouse_click(x, y):
                self.visible = False
                return True
        
        return False
    
    def toggle_visibility(self):
        """
        Toggle the visibility of the menu.
        
        Returns:
            bool: New visibility state
        """
        self.visible = not self.visible
        return self.visible
    
    def hide(self):
        """
        Hide the menu.
        """
        self.visible = False


class UIManager:
    """
    Manages the user interface for the application.
    
    This module is responsible for:
    - Providing a menu bar for file operations and color calibration management
    - Handling user input for calibration and configuration
    - Displaying the tracking results and UI elements
    """
    
    def __init__(self, window_name="Juggling Tracker", config_dir=None):
        """
        Initialize the UIManager module.
        
        Args:
            window_name (str): Name of the main window
            config_dir (str): Directory to save configuration files (default: None)
        """
        self.window_name = window_name
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # UI state
        self.mouse_x = 0
        self.mouse_y = 0
        self.calibration_mode = False
        self.calibration_ball_name = ""
        self.calibration_samples = 0
        self.calibration_max_samples = 30
        self.calibration_start_time = 0
        self.calibration_timeout = 10  # seconds
        
        # Reference to the main application (for exit functionality)
        self.app = None
        
        # Create buttons
        self.buttons = []
        self.menus = {}
        
        # Create menu bar buttons
        self.create_menu_bar()
        
        # Set up mouse callback
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
    
    def set_app(self, app):
        """
        Set the reference to the main application.
        
        Args:
            app: Reference to the main application
        """
        self.app = app
    
    def create_menu_bar(self):
        """
        Create the menu bar buttons and menus.
        """
        # Menu bar background color
        self.menu_bar_color = (50, 50, 50)  # Dark gray
        self.menu_bar_height = 40
        
        # Button colors
        button_color = (60, 60, 60)  # Slightly lighter than menu bar
        button_hover_color = (80, 80, 80)  # Even lighter when hovered
        button_text_color = (220, 220, 220)  # Light gray text
        
        # File menu button
        file_button = Button(10, 5, 80, 30, "File", self.toggle_file_menu, 
                            color=button_color, text_color=button_text_color, 
                            hover_color=button_hover_color, border_radius=5)
        self.buttons.append(file_button)
        
        # File menu
        file_menu = Menu(10, self.menu_bar_height, 180, color=(60, 60, 60), 
                        text_color=button_text_color, hover_color=button_hover_color, 
                        border_radius=5)
        file_menu.add_item("Load Calibration", self.load_calibration)
        file_menu.add_item("Save Calibration", self.save_calibration)
        file_menu.add_item("Save Calibration As", self.save_calibration_as)
        file_menu.add_item("Exit", self.exit_application)
        self.menus["file"] = file_menu
        
        # Calibration menu button
        calibration_button = Button(100, 5, 120, 30, "Calibration", self.toggle_calibration_menu,
                                   color=button_color, text_color=button_text_color, 
                                   hover_color=button_hover_color, border_radius=5)
        self.buttons.append(calibration_button)
        
        # Calibration menu
        calibration_menu = Menu(100, self.menu_bar_height, 180, color=(60, 60, 60), 
                               text_color=button_text_color, hover_color=button_hover_color, 
                               border_radius=5)
        calibration_menu.add_item("New Ball", self.new_ball)
        calibration_menu.add_item("Edit Ball", self.edit_ball)
        calibration_menu.add_item("Remove Ball", self.remove_ball)
        self.menus["calibration"] = calibration_menu
        
        # View menu button
        view_button = Button(230, 5, 80, 30, "View", self.toggle_view_menu,
                            color=button_color, text_color=button_text_color, 
                            hover_color=button_hover_color, border_radius=5)
        self.buttons.append(view_button)
        
        # View menu
        view_menu = Menu(230, self.menu_bar_height, 180, color=(60, 60, 60), 
                        text_color=button_text_color, hover_color=button_hover_color, 
                        border_radius=5)
        view_menu.add_item("Toggle Depth", self.toggle_depth)
        view_menu.add_item("Toggle Masks", self.toggle_masks)
        view_menu.add_item("Toggle Debug", self.toggle_debug)
        view_menu.add_item("Toggle FPS", self.toggle_fps)
        self.menus["view"] = view_menu
        
        # Extensions menu button
        extensions_button = Button(320, 5, 120, 30, "Extensions", self.toggle_extensions_menu,
                                  color=button_color, text_color=button_text_color, 
                                  hover_color=button_hover_color, border_radius=5)
        self.buttons.append(extensions_button)
        
        # Extensions menu (will be populated dynamically)
        extensions_menu = Menu(320, self.menu_bar_height, 180, color=(60, 60, 60), 
                              text_color=button_text_color, hover_color=button_hover_color, 
                              border_radius=5)
        self.menus["extensions"] = extensions_menu
    
    def update_extensions_menu(self, extension_manager):
        """
        Update the extensions menu with available extensions.
        
        Args:
            extension_manager: ExtensionManager instance
        """
        # Clear the menu
        self.menus["extensions"].items = []
        
        # Add extensions
        extensions = extension_manager.get_registered_extensions()
        enabled_extensions = extension_manager.get_enabled_extensions()
        
        for name in extensions:
            # Create a closure to capture the extension name
            def toggle_extension(ext_name=name):
                if extension_manager.is_extension_enabled(ext_name):
                    extension_manager.disable_extension(ext_name)
                else:
                    extension_manager.enable_extension(ext_name)
            
            # Add a checkmark for enabled extensions
            prefix = "✓ " if name in enabled_extensions else "  "
            self.menus["extensions"].add_item(f"{prefix}{name}", toggle_extension)
    
    def draw_menu_bar(self, frame):
        """
        Draw the menu bar on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with the menu bar drawn
        """
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Draw menu bar background
        cv2.rectangle(result, (0, 0), (result.shape[1], self.menu_bar_height), self.menu_bar_color, -1)
        
        # Draw buttons
        for button in self.buttons:
            result = button.draw(result)
        
        # Draw menus
        for menu in self.menus.values():
            result = menu.draw(result)
        
        return result
    
    def draw_calibration_ui(self, frame):
        """
        Draw the calibration UI on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with the calibration UI drawn
        """
        if not self.calibration_mode:
            return frame
        
        # Create a copy of the frame to draw on
        result = frame.copy()
        
        # Draw a semi-transparent overlay
        overlay = result.copy()
        cv2.rectangle(overlay, (0, 0), (result.shape[1], result.shape[0]), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, result, 0.5, 0, result)
        
        # Draw calibration instructions
        cv2.putText(result, f"Calibrating: {self.calibration_ball_name}", (result.shape[1] // 2 - 150, result.shape[0] // 2 - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(result, "Toss the ball back and forth", (result.shape[1] // 2 - 150, result.shape[0] // 2),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Draw progress bar
        progress = min(1.0, self.calibration_samples / self.calibration_max_samples)
        bar_width = 400
        bar_height = 30
        bar_x = (result.shape[1] - bar_width) // 2
        bar_y = result.shape[0] // 2 + 50
        
        # Draw background
        cv2.rectangle(result, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
        
        # Draw progress
        cv2.rectangle(result, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + bar_height), (0, 255, 0), -1)
        
        # Draw text
        cv2.putText(result, f"{int(progress * 100)}%", (bar_x + bar_width // 2 - 20, bar_y + bar_height // 2 + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw cancel button
        cancel_button = Button(result.shape[1] // 2 - 50, bar_y + bar_height + 20, 100, 40, "Cancel", self.cancel_calibration)
        result = cancel_button.draw(result)
        
        # Check for timeout
        if time.time() - self.calibration_start_time > self.calibration_timeout:
            self.cancel_calibration()
        
        return result
    
    def draw_ui(self, frame):
        """
        Draw the UI on a frame.
        
        Args:
            frame: Color image in BGR format
            
        Returns:
            numpy.ndarray: Frame with the UI drawn
        """
        # Create a new frame with space for the menu bar
        height, width = frame.shape[:2]
        ui_frame = np.zeros((height + self.menu_bar_height, width, 3), dtype=np.uint8)
        
        # Draw the menu bar at the top
        ui_frame[:self.menu_bar_height, :] = self.menu_bar_color
        
        # Copy the original frame below the menu bar
        ui_frame[self.menu_bar_height:, :] = frame
        
        # Draw the menu bar
        ui_frame = self.draw_menu_bar(ui_frame)
        
        # Draw the calibration UI if needed
        if self.calibration_mode:
            ui_frame = self.draw_calibration_ui(ui_frame)
        
        return ui_frame
    
    def mouse_callback(self, event, x, y, flags, param):
        """
        Handle mouse events.
        
        Args:
            event (int): Mouse event type
            x (int): X coordinate of the mouse
            y (int): Y coordinate of the mouse
            flags (int): Event flags
            param: User data
        """
        self.mouse_x = x
        self.mouse_y = y
        
        if event == cv2.EVENT_MOUSEMOVE:
            # Handle mouse movement
            for button in self.buttons:
                button.handle_mouse_move(x, y)
            
            for menu in self.menus.values():
                menu.handle_mouse_move(x, y)
        
        elif event == cv2.EVENT_LBUTTONDOWN:
            # Handle mouse click
            menu_clicked = False
            
            # Check if a menu was clicked
            for menu in self.menus.values():
                if menu.handle_mouse_click(x, y):
                    menu_clicked = True
                    break
            
            # If no menu was clicked, check if a button was clicked
            if not menu_clicked:
                for button in self.buttons:
                    if button.handle_mouse_click(x, y):
                        # Hide all menus when a button is clicked (except the one that was just toggled)
                        for menu_name, menu in self.menus.items():
                            if menu_name not in ["file", "calibration", "view", "extensions"]:
                                menu.hide()
                        break
    
    def toggle_file_menu(self):
        """
        Toggle the file menu.
        """
        self.menus["file"].toggle_visibility()
        
        # Hide other menus
        for menu_name, menu in self.menus.items():
            if menu_name != "file":
                menu.hide()
    
    def toggle_calibration_menu(self):
        """
        Toggle the calibration menu.
        """
        self.menus["calibration"].toggle_visibility()
        
        # Hide other menus
        for menu_name, menu in self.menus.items():
            if menu_name != "calibration":
                menu.hide()
    
    def toggle_view_menu(self):
        """
        Toggle the view menu.
        """
        self.menus["view"].toggle_visibility()
        
        # Hide other menus
        for menu_name, menu in self.menus.items():
            if menu_name != "view":
                menu.hide()
    
    def toggle_extensions_menu(self):
        """
        Toggle the extensions menu.
        """
        self.menus["extensions"].toggle_visibility()
        
        # Hide other menus
        for menu_name, menu in self.menus.items():
            if menu_name != "extensions":
                menu.hide()
    
    def load_calibration(self):
        """
        Load a color calibration.
        """
        # This would typically open a file dialog, but for simplicity we'll just print a message
        print("Load Calibration")
        
        # In a real implementation, you would:
        # 1. Show a file dialog to select a calibration file
        # 2. Load the calibration using the ColorCalibration module
        # 3. Update the UI to reflect the loaded calibration
    
    def save_calibration(self):
        """
        Save the current color calibration.
        """
        # This would typically save to the current file, but for simplicity we'll just print a message
        print("Save Calibration")
        
        # In a real implementation, you would:
        # 1. Save the calibration using the ColorCalibration module
        # 2. Show a confirmation message
    
    def save_calibration_as(self):
        """
        Save the current color calibration with a new name.
        """
        # This would typically open a file dialog, but for simplicity we'll just print a message
        print("Save Calibration As")
        
        # In a real implementation, you would:
        # 1. Show a file dialog to select a new file name
        # 2. Save the calibration using the ColorCalibration module
        # 3. Update the UI to reflect the new file name
    
    def new_ball(self):
        """
        Start calibration for a new ball.
        """
        # This would typically open a dialog to enter the ball name, but for simplicity we'll use a default name
        self.calibration_ball_name = f"Ball {len(self.get_calibrated_balls()) + 1}"
        self.start_calibration()
    
    def edit_ball(self):
        """
        Edit an existing ball calibration.
        """
        # This would typically open a dialog to select a ball, but for simplicity we'll just print a message
        print("Edit Ball")
        
        # In a real implementation, you would:
        # 1. Show a dialog to select a ball
        # 2. Start calibration for the selected ball
    
    def remove_ball(self):
        """
        Remove an existing ball calibration.
        """
        # This would typically open a dialog to select a ball, but for simplicity we'll just print a message
        print("Remove Ball")
        
        # In a real implementation, you would:
        # 1. Show a dialog to select a ball
        # 2. Remove the ball from the calibration
        # 3. Update the UI to reflect the change
    
    def toggle_depth(self):
        """
        Toggle the depth view.
        """
        # This would typically toggle the depth view in the visualizer
        print("Toggle Depth")
        
        # In a real implementation, you would:
        # 1. Toggle the depth view in the visualizer
        # 2. Update the UI to reflect the change
    
    def toggle_masks(self):
        """
        Toggle the masks view.
        """
        # This would typically toggle the masks view in the visualizer
        print("Toggle Masks")
        
        # In a real implementation, you would:
        # 1. Toggle the masks view in the visualizer
        # 2. Update the UI to reflect the change
    
    def toggle_debug(self):
        """
        Toggle debug mode.
        """
        # This would typically toggle debug mode in the visualizer
        print("Toggle Debug")
        
        # In a real implementation, you would:
        # 1. Toggle debug mode in the visualizer
        # 2. Update the UI to reflect the change
    
    def toggle_fps(self):
        """
        Toggle the FPS display.
        """
        # This would typically toggle the FPS display in the visualizer
        print("Toggle FPS")
        
        # In a real implementation, you would:
        # 1. Toggle the FPS display in the visualizer
        # 2. Update the UI to reflect the change
    
    def exit_application(self):
        """
        Exit the application.
        """
        print("Exit Application")
        
        # Set the running flag to False in the main application
        if self.app:
            self.app.running = False
        else:
            # If we don't have a reference to the main application, try to exit directly
            import sys
            sys.exit(0)
    
    def start_calibration(self):
        """
        Start the calibration process.
        """
        self.calibration_mode = True
        self.calibration_samples = 0
        self.calibration_start_time = time.time()
    
    def update_calibration(self, blob=None, color_image=None):
        """
        Update the calibration with a new sample.
        
        Args:
            blob: Blob information (optional)
            color_image: Color image in BGR format (optional)
            
        Returns:
            bool: True if calibration is complete, False otherwise
        """
        if not self.calibration_mode:
            return False
        
        if blob is not None and color_image is not None:
            # Extract the average color of the blob
            mask = np.zeros((color_image.shape[0], color_image.shape[1]), dtype=np.uint8)
            cv2.drawContours(mask, [blob['contour']], -1, 255, -1)
            mean_color = cv2.mean(color_image, mask=mask)[:3]  # BGR format
            
            # Update the calibration
            # In a real implementation, you would:
            # 1. Update the color calibration with the new sample
            # 2. Update the UI to reflect the change
            
            self.calibration_samples += 1
            
            # Check if calibration is complete
            if self.calibration_samples >= self.calibration_max_samples:
                self.complete_calibration()
                return True
        
        return False
    
    def complete_calibration(self):
        """
        Complete the calibration process.
        """
        self.calibration_mode = False
        
        # In a real implementation, you would:
        # 1. Finalize the color calibration
        # 2. Update the UI to reflect the change
        # 3. Show a confirmation message
    
    def cancel_calibration(self):
        """
        Cancel the calibration process.
        """
        self.calibration_mode = False
    
    def get_calibrated_balls(self):
        """
        Get the list of calibrated balls.
        
        Returns:
            list: List of ball names
        """
        # In a real implementation, you would:
        # 1. Get the list of calibrated balls from the ColorCalibration module
        return []
    
    def is_calibrating(self):
        """
        Check if calibration is in progress.
        
        Returns:
            bool: True if calibration is in progress, False otherwise
        """
        return self.calibration_mode
    
    def get_calibration_ball_name(self):
        """
        Get the name of the ball being calibrated.
        
        Returns:
            str: Name of the ball being calibrated
        """
        return self.calibration_ball_name
    
    def cleanup(self):
        """
        Clean up resources used by the UI manager.
        """
        # In a real implementation, you would:
        # 1. Clean up any resources used by the UI manager
        pass