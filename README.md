# Juggling Tracker

A robust juggling ball tracking system that uses a RealSense depth camera to track multiple juggling balls and the juggler's hands in real-time.

## Features

- Track 3-5 different colored juggling balls in real-time
- Track the juggler's hands
- Save and load color calibrations for different environments
- Extensible architecture for adding new functionality
- Simple UI with a menu bar for file operations and color calibration management
- Fallback modes for webcam and simulation when RealSense camera is not available

## Requirements

- Python 3.6+
- Intel RealSense camera (optional, can use webcam or simulation mode)
- OpenCV
- NumPy
- PyRealSense2 (optional, only needed for RealSense camera)
- MediaPipe

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/juggling-tracker.git
   cd juggling-tracker
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure your RealSense camera is connected to your computer (if using RealSense mode).

## Usage

1. Run the application:
   ```
   python run_juggling_tracker.py
   ```

   The script will automatically set up the PYTHONPATH environment variable if needed to find the librealsense library.

2. Command-line options:
   ```
   python run_juggling_tracker.py --help
   ```

   Available options:
   - `--config-dir PATH`: Directory to save configuration files
   - `--no-realsense`: Disable RealSense camera
   - `--webcam`: Use webcam instead of RealSense
   - `--simulation`: Use simulation mode
   - `--camera-index INDEX`: Index of the webcam to use (default: 0)

3. Calibrate the balls:
   - Click on "Calibration" in the menu bar, then "New Ball"
   - Enter a name for the ball (e.g., "Red Ball")
   - Toss the ball back and forth in the camera's view
   - The system will automatically detect the ball and learn its color
   - Repeat for each ball you want to track

4. Save the calibration:
   - Click on "File" in the menu bar, then "Save Calibration"
   - Enter a name for the calibration set (e.g., "Living Room Lighting")

5. Load a saved calibration:
   - Click on "File" in the menu bar, then "Load Calibration"
   - Select the calibration set you want to load

6. Track balls:
   - Once calibrated, the system will automatically track the balls
   - Each ball will be highlighted with a circle and labeled with its name
   - Hand positions will be marked with different symbols

7. Use extensions:
   - Click on "Extensions" in the menu bar
   - Enable or disable available extensions
   - Extension results will be displayed in the UI

## Keyboard Shortcuts

- `q` or `ESC`: Quit the application
- `p`: Pause/resume processing
- `d`: Toggle debug mode
- `m`: Toggle masks view
- `v`: Toggle depth view
- `f`: Toggle FPS display
- `e`: Toggle extension results display
- `r`: Reset tracking

## Fallback Modes

The application supports three modes of operation:

1. **RealSense Mode** (default): Uses the Intel RealSense depth camera for tracking. This provides the best results with accurate depth information.

2. **Webcam Mode**: Uses a standard webcam for tracking. This mode doesn't have real depth information, so tracking may be less accurate.

3. **Simulation Mode**: Generates simulated balls and hands for testing. This mode doesn't require any camera.

If the RealSense camera is not available, the application will automatically try to fall back to webcam mode, and if that fails, to simulation mode.

You can explicitly select a mode using the command-line options:
```
python run_juggling_tracker.py --webcam
python run_juggling_tracker.py --simulation
```

## Architecture

The system is built with a modular architecture that separates concerns and allows for easy extension and modification.

### Core Components

1. **Frame Acquisition Module**: Handles the camera setup and frame capture
2. **Depth Processing Module**: Processes depth data to identify potential ball candidates
3. **Skeleton Detection Module**: Detects the juggler's skeleton and extracts hand positions
4. **Blob Detection Module**: Detects potential ball candidates in the filtered depth mask
5. **Color Calibration Module**: Handles the calibration of ball colors
6. **Ball Identification Module**: Identifies which blob corresponds to which ball
7. **Multi-Ball Tracking Module**: Tracks multiple balls in 3D space
8. **Visualization Module**: Displays the tracking results and UI elements
9. **UI Manager**: Handles the user interface for the application
10. **Extension Manager**: Manages the registration and execution of extensions

## Extending the System

The system is designed to be extensible, with clear entry points for adding new functionality.

### Creating a New Extension

1. Create a new Python file in the `juggling_tracker/extensions` directory
2. Define a class that inherits from `Extension`
3. Implement the required methods:
   - `initialize()`: Initialize the extension
   - `process_frame(frame_data)`: Process a frame of data
   - `get_results()`: Get the results of the extension
   - `get_name()`: Get the name of the extension
4. The extension will be automatically discovered and can be enabled/disabled from the UI

Example:

```python
from juggling_tracker.extensions.extension_manager import Extension

class MyExtension(Extension):
    def __init__(self):
        self.count = 0
    
    def initialize(self):
        return True
    
    def process_frame(self, frame_data):
        # Process the frame data
        self.count += 1
        return {'count': self.count}
    
    def get_results(self):
        return {'count': self.count}
    
    def get_name(self):
        return "MyExtension"
```

## Included Extensions

The system comes with two example extensions:

1. **Catch Counter**: Counts the number of catches and drops in a juggling pattern
2. **Siteswap Detector**: Analyzes ball trajectories to determine the siteswap pattern

## Future Extensions

The system is designed to be extended with new functionality, such as:

1. **Improved Siteswap Detection**: More accurate pattern recognition with validation
2. **Training Mode**: Guide users through juggling exercises
3. **Pattern Consistency Rating**: Analyze the consistency of juggling patterns
4. **Trick Recognition**: Identify common juggling tricks
5. **Multi-Person Tracking**: Track multiple jugglers simultaneously

## Troubleshooting

### RealSense Camera Issues

If you encounter issues with the RealSense camera, try the following:

1. Make sure the RealSense SDK is installed correctly
2. Try running the application with the `--webcam` or `--simulation` option to use a fallback mode
3. If you have a custom build of librealsense, the application will automatically try to find it in `~/Projects/librealsense/build/Release`

### Webcam Issues

If you encounter issues with the webcam, try the following:

1. Make sure your webcam is connected and working
2. Try a different webcam index with the `--camera-index` option
3. Try running the application in simulation mode with the `--simulation` option

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Intel for the RealSense SDK
- OpenCV for the computer vision algorithms
- MediaPipe for the skeleton detection