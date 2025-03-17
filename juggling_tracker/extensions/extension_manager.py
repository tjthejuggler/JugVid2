import importlib
import os
import inspect
import time

class Extension:
    """
    Base class for all extensions.
    
    Extensions should inherit from this class and implement the required methods.
    """
    
    def initialize(self):
        """
        Initialize the extension.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        return True
    
    def process_frame(self, frame_data):
        """
        Process a frame of data.
        
        Args:
            frame_data: A dictionary containing:
                - color_image: The color image
                - depth_image: The depth image
                - tracked_balls: A list of tracked balls with positions and velocities
                - hand_positions: A list of hand positions
                - timestamp: The timestamp of the frame
                
        Returns:
            dict: Results of processing the frame
        """
        return {}
    
    def get_results(self):
        """
        Get the results of the extension.
        
        Returns:
            dict: A dictionary containing the results of the extension
        """
        return {}
    
    def get_name(self):
        """
        Get the name of the extension.
        
        Returns:
            str: The name of the extension
        """
        return self.__class__.__name__
    
    def get_description(self):
        """
        Get the description of the extension.
        
        Returns:
            str: The description of the extension
        """
        return self.__doc__ or "No description available"
    
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
        return "Unknown"
    
    def get_settings(self):
        """
        Get the settings of the extension.
        
        Returns:
            dict: A dictionary containing the settings of the extension
        """
        return {}
    
    def update_settings(self, settings):
        """
        Update the settings of the extension.
        
        Args:
            settings: A dictionary containing the new settings
            
        Returns:
            bool: True if the settings were updated successfully, False otherwise
        """
        return True
    
    def cleanup(self):
        """
        Clean up resources used by the extension.
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        return True


class ExtensionManager:
    """
    Manages the registration and execution of extensions.
    
    This module is responsible for:
    - Managing the registration and execution of extensions
    - Providing a standardized interface for extensions to access tracking data
    - Collecting and displaying results from extensions
    """
    
    def __init__(self, extensions_dir=None):
        """
        Initialize the ExtensionManager module.
        
        Args:
            extensions_dir (str): Directory containing extension modules (default: None)
        """
        self.extensions = {}  # Dictionary of extension_name -> extension_instance
        self.extensions_dir = extensions_dir or os.path.dirname(__file__)
        self.enabled_extensions = set()  # Set of enabled extension names
        self.extension_results = {}  # Dictionary of extension_name -> latest_results
        self.extension_stats = {}  # Dictionary of extension_name -> stats (time, etc.)
    
    def discover_extensions(self):
        """
        Discover available extensions in the extensions directory.
        
        Returns:
            list: List of discovered extension names
        """
        extension_names = []
        
        # Get all Python files in the extensions directory
        for filename in os.listdir(self.extensions_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                try:
                    # Import the module
                    module_path = f"juggling_tracker.extensions.{module_name}"
                    module = importlib.import_module(module_path)
                    
                    # Find all classes in the module that inherit from Extension
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, Extension) and obj != Extension:
                            extension_names.append(name)
                except Exception as e:
                    print(f"Error discovering extension {module_name}: {e}")
        
        return extension_names
    
    def register_extension(self, extension_class):
        """
        Register an extension.
        
        Args:
            extension_class: Extension class to register
            
        Returns:
            bool: True if the extension was registered successfully, False otherwise
        """
        try:
            # Create an instance of the extension
            extension = extension_class()
            
            # Initialize the extension
            if not extension.initialize():
                print(f"Failed to initialize extension: {extension.get_name()}")
                return False
            
            # Register the extension
            self.extensions[extension.get_name()] = extension
            
            # Initialize stats
            self.extension_stats[extension.get_name()] = {
                'total_time': 0.0,
                'num_frames': 0,
                'avg_time': 0.0,
                'last_time': 0.0
            }
            
            return True
        except Exception as e:
            print(f"Error registering extension: {e}")
            return False
    
    def register_extension_by_name(self, extension_name):
        """
        Register an extension by name.
        
        Args:
            extension_name (str): Name of the extension to register
            
        Returns:
            bool: True if the extension was registered successfully, False otherwise
        """
        try:
            # Find the extension class
            for filename in os.listdir(self.extensions_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = filename[:-3]  # Remove .py extension
                    try:
                        # Import the module
                        module_path = f"juggling_tracker.extensions.{module_name}"
                        module = importlib.import_module(module_path)
                        
                        # Find the extension class
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if name == extension_name and issubclass(obj, Extension) and obj != Extension:
                                return self.register_extension(obj)
                    except Exception as e:
                        print(f"Error importing module {module_name}: {e}")
            
            print(f"Extension not found: {extension_name}")
            return False
        except Exception as e:
            print(f"Error registering extension: {e}")
            return False
    
    def unregister_extension(self, extension_name):
        """
        Unregister an extension.
        
        Args:
            extension_name (str): Name of the extension to unregister
            
        Returns:
            bool: True if the extension was unregistered successfully, False otherwise
        """
        if extension_name in self.extensions:
            try:
                # Clean up the extension
                self.extensions[extension_name].cleanup()
                
                # Remove the extension
                del self.extensions[extension_name]
                
                # Remove from enabled extensions
                if extension_name in self.enabled_extensions:
                    self.enabled_extensions.remove(extension_name)
                
                # Remove results and stats
                if extension_name in self.extension_results:
                    del self.extension_results[extension_name]
                
                if extension_name in self.extension_stats:
                    del self.extension_stats[extension_name]
                
                return True
            except Exception as e:
                print(f"Error unregistering extension: {e}")
                return False
        else:
            print(f"Extension not registered: {extension_name}")
            return False
    
    def enable_extension(self, extension_name):
        """
        Enable an extension.
        
        Args:
            extension_name (str): Name of the extension to enable
            
        Returns:
            bool: True if the extension was enabled successfully, False otherwise
        """
        if extension_name in self.extensions:
            self.enabled_extensions.add(extension_name)
            return True
        else:
            print(f"Extension not registered: {extension_name}")
            return False
    
    def disable_extension(self, extension_name):
        """
        Disable an extension.
        
        Args:
            extension_name (str): Name of the extension to disable
            
        Returns:
            bool: True if the extension was disabled successfully, False otherwise
        """
        if extension_name in self.enabled_extensions:
            self.enabled_extensions.remove(extension_name)
            return True
        else:
            print(f"Extension not enabled: {extension_name}")
            return False
    
    def is_extension_enabled(self, extension_name):
        """
        Check if an extension is enabled.
        
        Args:
            extension_name (str): Name of the extension to check
            
        Returns:
            bool: True if the extension is enabled, False otherwise
        """
        return extension_name in self.enabled_extensions
    
    def process_frame(self, frame_data):
        """
        Process a frame with all enabled extensions.
        
        Args:
            frame_data: A dictionary containing:
                - color_image: The color image
                - depth_image: The depth image
                - tracked_balls: A list of tracked balls with positions and velocities
                - hand_positions: A list of hand positions
                - timestamp: The timestamp of the frame
                
        Returns:
            dict: Dictionary of extension_name -> results
        """
        results = {}
        
        for extension_name in self.enabled_extensions:
            if extension_name in self.extensions:
                extension = self.extensions[extension_name]
                try:
                    # Measure processing time
                    start_time = time.time()
                    
                    # Process the frame
                    extension_result = extension.process_frame(frame_data)
                    
                    # Update timing stats
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    stats = self.extension_stats[extension_name]
                    stats['total_time'] += processing_time
                    stats['num_frames'] += 1
                    stats['avg_time'] = stats['total_time'] / stats['num_frames']
                    stats['last_time'] = processing_time
                    
                    # Store the results
                    results[extension_name] = extension_result
                    self.extension_results[extension_name] = extension_result
                except Exception as e:
                    print(f"Error processing frame with extension {extension_name}: {e}")
        
        return results
    
    def get_extension_results(self, extension_name=None):
        """
        Get the latest results from extensions.
        
        Args:
            extension_name (str): Name of the extension to get results from (default: None, get all)
            
        Returns:
            dict: Dictionary of extension_name -> results, or results for a specific extension
        """
        if extension_name is not None:
            return self.extension_results.get(extension_name, {})
        else:
            return self.extension_results
    
    def get_extension_stats(self, extension_name=None):
        """
        Get statistics for extensions.
        
        Args:
            extension_name (str): Name of the extension to get stats for (default: None, get all)
            
        Returns:
            dict: Dictionary of extension_name -> stats, or stats for a specific extension
        """
        if extension_name is not None:
            return self.extension_stats.get(extension_name, {})
        else:
            return self.extension_stats
    
    def get_registered_extensions(self):
        """
        Get all registered extensions.
        
        Returns:
            dict: Dictionary of extension_name -> extension_instance
        """
        return self.extensions
    
    def get_enabled_extensions(self):
        """
        Get all enabled extensions.
        
        Returns:
            list: List of enabled extension names
        """
        return list(self.enabled_extensions)
    
    def get_extension_info(self, extension_name):
        """
        Get information about an extension.
        
        Args:
            extension_name (str): Name of the extension
            
        Returns:
            dict: Dictionary containing information about the extension
        """
        if extension_name in self.extensions:
            extension = self.extensions[extension_name]
            return {
                'name': extension.get_name(),
                'description': extension.get_description(),
                'version': extension.get_version(),
                'author': extension.get_author(),
                'settings': extension.get_settings(),
                'enabled': extension_name in self.enabled_extensions
            }
        else:
            return None
    
    def update_extension_settings(self, extension_name, settings):
        """
        Update the settings of an extension.
        
        Args:
            extension_name (str): Name of the extension
            settings: Dictionary containing the new settings
            
        Returns:
            bool: True if the settings were updated successfully, False otherwise
        """
        if extension_name in self.extensions:
            return self.extensions[extension_name].update_settings(settings)
        else:
            print(f"Extension not registered: {extension_name}")
            return False
    
    def cleanup(self):
        """
        Clean up all extensions.
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        success = True
        
        for extension_name, extension in list(self.extensions.items()):
            try:
                if not extension.cleanup():
                    print(f"Failed to clean up extension: {extension_name}")
                    success = False
            except Exception as e:
                print(f"Error cleaning up extension {extension_name}: {e}")
                success = False
        
        self.extensions = {}
        self.enabled_extensions = set()
        self.extension_results = {}
        self.extension_stats = {}
        
        return success