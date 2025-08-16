# Manual Mode for Stillness Recorder with IMU

## Overview

The Enhanced Stillness Recorder now supports a **Manual Mode** that completely disables motion detection and allows you to manually start/stop recordings using keyboard controls. This mode ensures synchronized video and IMU recordings with matching filenames.

## Quick Start

```bash
# Start in manual mode
python3 run_stillness_recorder_with_imu.py --manual

# Or use the manual preset
python3 run_stillness_recorder_with_imu.py --preset manual

# With specific watch IPs
python3 run_stillness_recorder_with_imu.py --manual --left-watch 192.168.1.101 --right-watch 192.168.1.102
```

## Manual Mode Features

### ✅ What's New
- **Motion Detection Disabled**: No automatic triggering based on movement
- **Keyboard Controls**: Simple SPACEBAR to start/stop recordings
- **Synchronized Naming**: Video and IMU files use matching timestamps
- **Real-time Recording**: Records from current moment (not from buffer)
- **Clear Visual Feedback**: UI shows "MANUAL MODE - PRESS SPACEBAR"

### 🎮 Controls

| Key | Action |
|-----|--------|
| `SPACEBAR` | Start/Stop recording (primary) |
| `r` | Start/Stop recording (alternative) |
| `q` | Quit application |
| `i` | Show IMU status |
| `h` | Toggle help overlay |

## File Organization

### Synchronized Naming Convention

All files from the same recording session share the same timestamp ID:

```
manual_recordings/
├── session_20250816_143022/
│   ├── manual_20250816_143022.mp4          # Video file
│   └── imu_20250816_143022/
│       ├── left_20250816_143022.csv        # Left watch IMU data
│       └── right_20250816_143022.csv       # Right watch IMU data
```

### File Name Format

- **Video**: `manual_YYYYMMDD_HHMMSS.mp4`
- **IMU**: `{watch_name}_YYYYMMDD_HHMMSS.csv`
- **Timestamp**: Exact moment recording started

### Directory Structure

```
manual_recordings/
├── session_20250816_143022/     # Session folder
│   ├── manual_20250816_143022.mp4
│   └── imu_20250816_143022/
│       ├── left_20250816_143022.csv
│       └── right_20250816_143022.csv
├── session_20250816_143155/     # Next session
│   ├── manual_20250816_143155.mp4
│   └── imu_20250816_143155/
│       ├── left_20250816_143155.csv
│       └── right_20250816_143155.csv
```

## Configuration Options

### Command Line Arguments

```bash
# Basic manual mode
python3 run_stillness_recorder_with_imu.py --manual

# Manual mode with custom settings
python3 run_stillness_recorder_with_imu.py \
    --manual \
    --record-duration 15 \
    --output-dir my_recordings \
    --left-watch 192.168.1.101 \
    --right-watch 192.168.1.102

# Discover watches automatically
python3 run_stillness_recorder_with_imu.py --manual --discover-watches
```

### Manual Preset Configuration

The manual preset includes these default settings:

```python
'manual': {
    'record_duration': 10.0,        # 10 second recordings
    'motion_threshold': 0,          # Disabled
    'stillness_threshold': 0,       # Disabled
    'stillness_duration': 0,        # Disabled
    'camera_width': 1280,
    'camera_height': 720,
    'camera_fps': 30,
    'output_dir': 'manual_recordings',
    'manual_mode': True
}
```

## Watch Setup

### Prerequisites

1. **Watch App**: Ensure the watch IMU recorder app has the `/data` endpoint fix applied
2. **Network**: Watches and PC must be on the same WiFi network
3. **IP Addresses**: Note the IP addresses shown on the watch screens

### Connection Methods

#### Method 1: Specify Watch IPs
```bash
python3 run_stillness_recorder_with_imu.py --manual \
    --left-watch 192.168.1.101 \
    --right-watch 192.168.1.102
```

#### Method 2: Auto-Discovery
```bash
python3 run_stillness_recorder_with_imu.py --manual --discover-watches
```

#### Method 3: Configure in GUI
1. Start manual mode without specifying watches
2. Use the GUI controls window to add watch IPs
3. Test connections using the "Test Connections" button

## Usage Workflow

### 1. Start Manual Mode
```bash
python3 run_stillness_recorder_with_imu.py --manual --left-watch 192.168.1.101
```

### 2. Verify Connections
- Check the GUI status window for watch connections
- Look for green indicators: 🟢 ✅ LEFT (192.168.1.101:8080)
- Press `i` to show detailed IMU status

### 3. Record Sessions
1. **Start Recording**: Press `SPACEBAR`
   - Video recording begins immediately
   - IMU recording starts on connected watches
   - UI shows "MANUAL RECORDING" status

2. **Stop Recording**: Recording stops automatically after duration
   - Default: 10 seconds
   - Files are saved with synchronized names
   - IMU data is retrieved from watches

### 4. Find Your Files
```bash
ls manual_recordings/session_*/
# Shows: manual_YYYYMMDD_HHMMSS.mp4 and imu_YYYYMMDD_HHMMSS/ folder
```

## Troubleshooting

### Common Issues

#### 1. Empty IMU Folders
**Problem**: IMU folders created but no CSV files
**Solution**: 
- Ensure watch app has the `/data` endpoint fix
- Test with: `python3 test_watch_connection_complete.py 192.168.1.101`
- Check watch app is running and recording

#### 2. Connection Issues
**Problem**: Watches show as disconnected
**Solution**:
- Verify IP addresses on watch screens
- Test network connectivity: `ping 192.168.1.101`
- Try different ports: watches may use 8080, 8081, 8082, etc.

#### 3. Mismatched Filenames
**Problem**: Video and IMU files have different timestamps
**Solution**: This should not happen with the new synchronized naming system

### Debug Tools

#### Test Watch Connection
```bash
python3 test_watch_connection_complete.py 192.168.1.101
```

#### Test Manual Mode
```bash
python3 test_manual_mode.py
```

#### Comprehensive Diagnostics
```bash
python3 debug_watch_imu_connection.py --watch-ips 192.168.1.101 192.168.1.102
```

## Comparison: Manual vs Automatic Mode

| Feature | Manual Mode | Automatic Mode |
|---------|-------------|----------------|
| **Triggering** | SPACEBAR key | Motion detection |
| **Recording Source** | Live camera feed | Circular buffer (past frames) |
| **Motion Detection** | Disabled | Active |
| **File Naming** | `manual_TIMESTAMP` | `auto_TIMESTAMP` |
| **Use Case** | Controlled recording | Hands-free capture |
| **Precision** | Exact timing control | Captures pre-movement |

## Advanced Configuration

### Custom Record Duration
```bash
python3 run_stillness_recorder_with_imu.py --manual --record-duration 20
```

### Custom Output Directory
```bash
python3 run_stillness_recorder_with_imu.py --manual --output-dir juggling_practice
```

### Multiple Watch Setup
```bash
python3 run_stillness_recorder_with_imu.py --manual \
    --watch-ips 192.168.1.101 192.168.1.102 192.168.1.103
```

## File Format Details

### Video Files
- **Format**: MP4 (H.264)
- **Resolution**: 1280x720 (configurable)
- **Frame Rate**: 30 FPS (configurable)
- **Duration**: 10 seconds (configurable)

### IMU CSV Files
- **Format**: CSV with headers
- **Columns**: timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z, watch_name
- **Sample Rate**: ~200Hz (watch-dependent)
- **Metadata**: Session ID, device ID, start time, sample count

## Integration with Analysis Tools

The synchronized naming makes it easy to process recordings:

```python
import pandas as pd
import cv2

# Load synchronized data
timestamp = "20250816_143022"
video = cv2.VideoCapture(f"manual_recordings/session_{timestamp}/manual_{timestamp}.mp4")
left_imu = pd.read_csv(f"manual_recordings/session_{timestamp}/imu_{timestamp}/left_{timestamp}.csv")
right_imu = pd.read_csv(f"manual_recordings/session_{timestamp}/imu_{timestamp}/right_{timestamp}.csv")

# Now you have perfectly synchronized video and IMU data!
```

## Support

If you encounter issues:

1. **Test Connection**: Use `test_watch_connection_complete.py`
2. **Check Logs**: Look for error messages in the terminal
3. **Verify Setup**: Ensure watch app has the `/data` endpoint fix
4. **Network Issues**: Confirm watches and PC are on same WiFi network

---

**Last Updated**: 2025-08-16  
**Version**: 1.0 with Manual Mode and Synchronized Naming