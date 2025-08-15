# JugVid2 - Computer Vision Projects

A collection of computer vision applications using Intel RealSense depth cameras, including juggling ball tracking and face balance timing.

## Projects

### 1. Juggling Tracker
A robust juggling ball tracking system using Intel RealSense depth cameras.

**Features:**
- Real-time juggling ball tracking using color and depth data.
- Skeleton detection for hand position estimation.
- Blob detection and filtering for ball identification.
- Color calibration for balls.
- Ball profile management for defining and saving different types of juggling balls.
- Multi-ball tracking with Kalman filters.
- Simple tracking mode for basic object following.
- Extensible architecture for adding custom processing modules.
- Qt-based graphical user interface.
- **Video Playback Mode**:
    - The application can play back standard video files (e.g., .mp4, .avi) as a simulated live feed. This is useful for testing tracking algorithms without a live camera.
    - To use, select "Recorded Feed (Video)" from the "Feed Source" panel and choose a video file. The video will loop automatically.
    - Note: Standard video files do not contain depth data, so depth-dependent features will be limited in this mode.
- **RealSense BAG File Recording**:
    - The application can record color and depth streams from a connected RealSense camera into a `.bag` file.
    - This allows capturing full sensor data for later analysis or playback (Note: Direct playback of `.bag` files with depth data within this application is a potential future enhancement).
    - To use, ensure "Live Feed (Camera)" is active with a RealSense camera. Use the "Start Recording" button in the "Recording" panel, choose a save location for the `.bag` file. Click "Stop Recording" to finalize the file.
    - _(Updated: 2025-05-31)_

### 2. Face Balance Timer ⭐ IMPROVED!
An automatic timer for face balancing exercises using pose detection with advanced state management.

**Features:**
- **Smart State Machine**: Prevents timer from triggering too often with proper cooldown periods
- **Larger Display**: Increased window size (1280x720) with very large timer display during timing
- **Database Storage**: All session data stored in SQLite database with timestamps and session tracking
- **Session Graphs**: Automatic performance graphs shown when program closes
- **Minimal Terminal Output**: Reduced noise, only essential messages displayed
- **Automatic Start/Stop**: Timer starts when arms go down to sides, stops when hand goes above head
- **RealSense Integration**: Uses color-only stream to avoid bandwidth issues, with webcam fallback
- **Pose Detection**: Uses MediaPipe for accurate skeletal tracking, with motion-based fallback when unavailable
- **Audio Feedback**: Distinct sound effects - high pitch (800Hz) for start, low pitch (400Hz) for stop
- **Session Tracking**: Records all attempts, tracks best times, and provides detailed session summaries

**State Machine Logic:**
1. **WAITING**: Put arms down to prepare
2. **READY_TO_START**: Arms are down, timer will start immediately
3. **TIMING**: Timer is running, raise hand to stop
4. **COOLDOWN**: 2-second cooldown prevents immediate restart

**Usage:**
```bash
python3 run_face_balance_timer.py
```

**Controls:**
- Put both arms down at your sides to start the timer
- Raise one hand above your head to stop the timer
- Wait for cooldown period before next attempt
- Press 'r' to reset session
- Press 'q' to quit

**Technical Details:**
- Uses RealSense color-only stream (1280x720 @ 30fps) for larger, clearer display
- Falls back to motion-based pose detection when MediaPipe is unavailable
- Automatic webcam fallback if RealSense fails
- SQLite database stores all session data with timestamps
- Matplotlib graphs show session performance and time distribution
- State machine prevents false triggers and ensures proper timing flow

**Requirements:**
- RealSense camera (uses color-only stream) or regular webcam
- OpenCV for video processing
- MediaPipe for pose detection (optional, falls back to motion detection)
- SQLite3 for database storage
- Matplotlib for session graphs
- speaker-test for audio feedback (with fallback to system beep)

_(Added: 2025-08-12, Updated: 2025-08-12)_

### 3. Stillness Recorder ⭐ IMPROVED!
A motion-triggered video recorder that automatically saves video clips when stillness is detected.

**Features:**
- **Automatic Recording**: Records the preceding X seconds of video when stillness is detected
- **Motion Detection**: Uses advanced background subtraction and frame differencing for robust motion detection
- **Circular Buffer**: Efficiently stores recent frames in memory for instant recording
- **Configurable Parameters**: Adjustable recording duration, motion threshold, and stillness duration
- **Real-time Display**: Shows live video feed with motion statistics and recording status (1280x720 resolution)
- **RealSense Integration**: Uses RealSense color-only stream for optimal performance
- **Interactive Controls**: Keyboard shortcuts and GUI controls window for real-time parameter adjustment
- **Multiple Presets**: Quick, Normal, and Sensitive presets for different use cases
- **Memory Optimized**: Fixed memory leaks and improved performance for long-running sessions
- **GUI Controls Window**: Dedicated tkinter window with text input fields for easy parameter adjustment

**How It Works:**
1. Continuously monitors video feed for motion
2. When motion drops below threshold for specified duration, triggers recording
3. Saves the last X seconds of video (before stillness was detected) to MP4 file
4. Perfect for capturing moments just before an object comes to rest

**Usage:**
```bash
# Run with default settings
python3 run_stillness_recorder.py

# Run with preset configurations
python3 run_stillness_recorder.py --preset quick      # 5s recording, 2s stillness
python3 run_stillness_recorder.py --preset normal     # 10s recording, 3s stillness
python3 run_stillness_recorder.py --preset sensitive  # 15s recording, 5s stillness

# Run with custom parameters
python3 stillness_recorder.py --record-duration 8 --motion-threshold 800 --stillness-duration 2.5
```

**Keyboard Controls:**
- `q` - Quit application
- `h` - Toggle help display
- `m` - Toggle motion mask view
- `r` - Manual recording trigger
- `c` - Clear motion detector state
- `+/-` - Increase/decrease motion threshold
- `[/]` - Decrease/increase record duration

**Configuration Options:**
- **Record Duration**: How many seconds of video to save (1-60 seconds)
- **Motion Threshold**: Sensitivity for motion detection (lower = more sensitive)
- **Stillness Duration**: How long stillness must be maintained to trigger recording
- **Output Directory**: Where to save recorded video files

**Use Cases:**
- Recording juggling catches when balls come to rest
- Capturing the moment objects stop moving
- Automated surveillance recording
- Sports analysis for stationary moments
- Scientific experiments requiring motion cessation detection

**Technical Details:**
- Uses MOG2 background subtraction with frame differencing backup
- Circular buffer stores frames with timestamps for precise timing
- Multi-threaded video saving to prevent UI blocking
- MP4 output format with configurable FPS
- Real-time motion statistics and buffer utilization display

**Requirements:**
- RealSense camera (color-only stream) or webcam fallback
- OpenCV for video processing and motion detection
- NumPy for frame processing
- Threading support for background video saving
- Tkinter for GUI controls window

**Recent Improvements (2025-08-15):**
- Fixed video stretching issue by correcting display dimensions (now 1280x720)
- Fixed memory leaks by optimizing tkinter event processing and frame resizing
- Improved circular buffer management with proper cleanup
- Enhanced controls window layout for better visibility
- Added proper exception handling and resource cleanup
- Reduced CPU usage through optimized frame processing

_(Added: 2025-08-15, Updated: 2025-08-15)_

## Setup and Installation

(Instructions for setup and installation will be added here)

## Usage

### Juggling Tracker
Run the juggling tracker using:
```bash
python run_juggling_tracker.py
```

Or directly:
```bash
python juggling_tracker/main.py [arguments]
```

### Face Balance Timer
Run the face balance timer using:
```bash
python3 run_face_balance_timer.py
```

### Stillness Recorder
Run the stillness recorder using:
```bash
# Quick start with default settings
python3 run_stillness_recorder.py

# With preset configurations
python3 run_stillness_recorder.py --preset quick
python3 run_stillness_recorder.py --preset normal
python3 run_stillness_recorder.py --preset sensitive

# With custom parameters
python3 stillness_recorder.py --record-duration 10 --motion-threshold 1000 --stillness-duration 3
```

### Testing
Run component tests to verify everything is working:
```bash
python3 test_stillness_recorder.py
```

### Command-Line Arguments:
-   `--config-dir <path>`: Directory to save/load configuration files.
-   `--no-realsense`: Disable RealSense camera (attempts webcam or other fallbacks).
-   `--webcam`: Force use of a webcam.
-   `--camera-index <index>`: Specify the webcam index (default: 0).
-   `--simulation`: Enable video playback mode. Requires `--video-path`.
-   `--video-path <path>`: Path to the video file to be used in playback mode.

### UI Controls:
-   **Feed Source Panel**:
    -   **Feed Mode**: Switch between "Live Feed (Camera)" and "Recorded Feed (Video)".
    -   **Select Video File...**: Appears when "Recorded Feed" is selected; allows choosing a video for playback.
-   **Recording Panel**:
    -   **Start Recording**: Appears when "Live Feed" with a RealSense camera is active; prompts for a `.bag` file location and starts recording.
    -   **Stop Recording**: Stops the current recording.
    -   Status labels indicate recording state and file path.
-   Other UI controls for ball definition, calibration, view toggles, etc.

## Modules

### Core Modules
-   `frame_acquisition`: Handles camera input (RealSense, Webcam, Video File, BAG File Recording).
-   `color_only_frame_acquisition`: Simplified RealSense color-only stream acquisition.
-   `depth_processor`: Processes depth data.
-   `skeleton_detector`: Detects human skeletons and hand positions.
-   `blob_detector`: Detects potential ball-like objects (blobs).
-   `color_calibration`: Manages color profiles for ball identification.
-   `ball_identifier`: Identifies balls based on color and other features.
-   `multi_ball_tracker`: Tracks multiple balls over time.
-   `simple_tracker`: Provides basic object tracking based on masks.
-   `ui`: Contains Qt-based UI components (`main_window`, etc.).
-   `extensions`: Framework for adding plugins and extensions.

### Stillness Recorder Modules
-   `motion_detector`: Advanced motion detection using background subtraction and frame differencing.
-   `circular_frame_buffer`: Thread-safe circular buffer for storing recent video frames with timestamps.
-   `stillness_recorder`: Main application for motion-triggered video recording.
-   `run_stillness_recorder`: Runner script with preset configurations.
-   `test_stillness_recorder`: Comprehensive test suite for all stillness recorder components.

## Contributing

(Guidelines for contributing will be added here)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE:1) file for details.