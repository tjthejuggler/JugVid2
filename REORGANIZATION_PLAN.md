# JugVid2 Project Reorganization Plan

**Date:** 2025-08-18  
**Status:** Ready for Implementation

## 📋 Overview

This document outlines the complete reorganization plan for the JugVid2 project to improve maintainability, organization, and user experience.

## 🎯 Goals

1. **Organize scattered files** into logical folder structures
2. **Create a unified command-line interface** for all applications
3. **Improve project maintainability** and navigation
4. **Preserve all existing functionality** while improving organization

## 📁 New Folder Structure

```
JugVid2/
├── 📁 apps/                          # Main applications
│   ├── juggling_tracker/             # (existing, already organized)
│   ├── face_balance_timer/           # Face balance timer app
│   │   ├── __init__.py
│   │   ├── face_balance_timer.py
│   │   └── run_face_balance_timer.py
│   ├── stillness_recorder/           # Stillness recorder variants
│   │   ├── __init__.py
│   │   ├── stillness_recorder.py
│   │   ├── stillness_recorder_headless.py
│   │   ├── stillness_recorder_with_imu.py
│   │   ├── run_stillness_recorder.py
│   │   ├── run_stillness_recorder_headless.py
│   │   └── run_stillness_recorder_with_imu.py
│   └── pose_detection/               # Pose detection tools
│       ├── __init__.py
│       ├── simple_pose_detector.py
│       └── improved_pose_detector.py
├── 📁 core/                          # Core shared modules
│   ├── __init__.py
│   ├── camera/                       # Camera and frame acquisition
│   │   ├── __init__.py
│   │   ├── depth.py
│   │   └── color_only_frame_acquisition.py
│   ├── imu/                          # IMU and watch integration
│   │   ├── __init__.py
│   │   ├── watch_imu_manager.py
│   │   ├── high_performance_imu_stream.py
│   │   ├── optimized_imu_ui.py
│   │   └── smart_imu_manager.py
│   ├── motion/                       # Motion detection and processing
│   │   ├── __init__.py
│   │   ├── motion_detector.py
│   │   └── circular_frame_buffer.py
│   └── utils/                        # Shared utilities
│       └── __init__.py
├── 📁 tools/                         # Development and testing tools
│   ├── debug/                        # Debug and analysis tools
│   │   ├── __init__.py
│   │   ├── debug_imu_performance.py
│   │   ├── debug_juggling_tracker.py
│   │   ├── debug_watch_data.py
│   │   ├── debug_watch_imu_connection.py
│   │   ├── debug_watch_imu_manager.py
│   │   └── run_debug_analysis.py
│   ├── setup/                        # Setup and installation scripts
│   │   ├── __init__.py
│   │   ├── setup_dependencies.py
│   │   ├── setup.py
│   │   └── fix_imu_integration.py
│   └── testing/                      # Test scripts
│       ├── __init__.py
│       ├── test_*.py (all test files)
│       └── validate_imu_integration.py
├── 📁 docs/                          # Documentation
│   ├── HIGH_PERFORMANCE_IMU_INTEGRATION_GUIDE.md
│   ├── JUGVID2CPP_INTEGRATION.md
│   ├── MANUAL_MODE_README.md
│   └── juggling_tracker_plan.md
├── 📁 data/                          # Data storage
│   ├── recordings/                   # Video recordings
│   ├── imu_data/                     # IMU data files
│   └── sessions/                     # Session data
│       └── test_recordings/
├── 📁 backup/                        # Backup files
│   └── backup_original_imu/
├── 📁 legacy/                        # Old/deprecated files
│   ├── main.py
│   ├── main2.py
│   ├── main3.py
│   └── main4.py
├── launcher.py                       # Main CLI launcher
├── README.md                         # Updated documentation
├── requirements.txt
├── .gitignore
├── LICENSE
├── notes.txt
├── todo.txt
└── face_balance_sessions.db
```

## 📝 File Categorization and Movement Plan

### 🚀 Main Applications → `apps/`

**Face Balance Timer:**
- `face_balance_timer.py` → `apps/face_balance_timer/face_balance_timer.py`
- `run_face_balance_timer.py` → `apps/face_balance_timer/run_face_balance_timer.py`

**Stillness Recorder:**
- `stillness_recorder.py` → `apps/stillness_recorder/stillness_recorder.py`
- `stillness_recorder_headless.py` → `apps/stillness_recorder/stillness_recorder_headless.py`
- `stillness_recorder_with_imu.py` → `apps/stillness_recorder/stillness_recorder_with_imu.py`
- `run_stillness_recorder.py` → `apps/stillness_recorder/run_stillness_recorder.py`
- `run_stillness_recorder_headless.py` → `apps/stillness_recorder/run_stillness_recorder_headless.py`
- `run_stillness_recorder_with_imu.py` → `apps/stillness_recorder/run_stillness_recorder_with_imu.py`

**Pose Detection:**
- `simple_pose_detector.py` → `apps/pose_detection/simple_pose_detector.py`
- `improved_pose_detector.py` → `apps/pose_detection/improved_pose_detector.py`

**Juggling Tracker:**
- `juggling_tracker/` → `apps/juggling_tracker/` (already organized)
- `run_juggling_tracker.py` → `apps/juggling_tracker/run_juggling_tracker.py`

### 🔧 Core Modules → `core/`

**Camera:**
- `depth.py` → `core/camera/depth.py`
- `color_only_frame_acquisition.py` → `core/camera/color_only_frame_acquisition.py`

**IMU:**
- `watch_imu_manager.py` → `core/imu/watch_imu_manager.py`
- `high_performance_imu_stream.py` → `core/imu/high_performance_imu_stream.py`
- `optimized_imu_ui.py` → `core/imu/optimized_imu_ui.py`
- `smart_imu_manager.py` → `core/imu/smart_imu_manager.py`

**Motion:**
- `motion_detector.py` → `core/motion/motion_detector.py`
- `circular_frame_buffer.py` → `core/motion/circular_frame_buffer.py`

### 🛠️ Tools → `tools/`

**Debug:**
- `debug_*.py` → `tools/debug/`
- `run_debug_analysis.py` → `tools/debug/run_debug_analysis.py`

**Setup:**
- `setup_dependencies.py` → `tools/setup/setup_dependencies.py`
- `setup.py` → `tools/setup/setup.py`
- `fix_imu_integration.py` → `tools/setup/fix_imu_integration.py`

**Testing:**
- All `test_*.py` files → `tools/testing/`
- `validate_imu_integration.py` → `tools/testing/validate_imu_integration.py`

### 📚 Documentation → `docs/`

- `HIGH_PERFORMANCE_IMU_INTEGRATION_GUIDE.md` → `docs/`
- `JUGVID2CPP_INTEGRATION.md` → `docs/`
- `MANUAL_MODE_README.md` → `docs/`
- `juggling_tracker_plan.md` → `docs/`

### 💾 Data → `data/`

- `imu_data/` → `data/imu_data/`
- `test_recordings/` → `data/sessions/test_recordings/`
- Create `data/recordings/` for future recordings

### 🗄️ Backup → `backup/`

- `backup_original_imu/` → `backup/backup_original_imu/`

### 📜 Legacy → `legacy/`

- `main.py` → `legacy/main.py`
- `main2.py` → `legacy/main2.py`
- `main3.py` → `legacy/main3.py`
- `main4.py` → `legacy/main4.py`

## 🚀 Command-Line Interface Design

### Main Launcher (`launcher.py`)

```
JugVid2 Project Launcher
========================

Main Applications:
  1. Juggling Tracker          - Advanced ball tracking with IMU
  2. Face Balance Timer        - Pose-based balance timing
  3. Stillness Recorder        - Motion-triggered video recording
  4. Pose Detection Tools      - Simple and improved pose detection

Tools & Utilities:
  5. Debug Tools               - Performance analysis and debugging
  6. Setup & Installation      - Dependency management
  7. Testing Suite             - Comprehensive testing tools

System Status:
  8. Check Dependencies        - Verify all requirements
  9. System Information        - Camera and hardware status

Options:
  h. Help                      - Show detailed help
  q. Quit                      - Exit launcher

Enter your choice (1-9, h, q): 
```

### Features:
- **Interactive menu** with numbered options
- **Direct command access**: `python launcher.py juggling` or `python launcher.py 1`
- **Submenus** for applications with multiple variants
- **System checks** for cameras, dependencies, and hardware
- **Help system** with detailed usage instructions
- **Configuration options** for common settings

## 🔄 Import Path Updates

All import statements will need to be updated to reflect the new structure:

**Before:**
```python
from watch_imu_manager import WatchIMUManager
from motion_detector import MotionDetector
```

**After:**
```python
from core.imu.watch_imu_manager import WatchIMUManager
from core.motion.motion_detector import MotionDetector
```

## 📋 Implementation Steps

1. **Create folder structure** with all necessary directories and `__init__.py` files
2. **Move files** to their new locations systematically
3. **Update import paths** in all Python files
4. **Create the main launcher** with CLI interface
5. **Update runner scripts** to work with new structure
6. **Update README.md** with new organization and usage
7. **Test all applications** to ensure functionality is preserved
8. **Create simple launcher script** for easy access

## 🧪 Testing Strategy

After reorganization, test each application:

1. **Juggling Tracker**: `python launcher.py 1` or `python apps/juggling_tracker/run_juggling_tracker.py`
2. **Face Balance Timer**: `python launcher.py 2` or `python apps/face_balance_timer/run_face_balance_timer.py`
3. **Stillness Recorder**: `python launcher.py 3` (with submenu for variants)
4. **Pose Detection**: `python launcher.py 4` (with submenu for variants)
5. **All import paths** work correctly
6. **All dependencies** are still accessible

## 📖 Documentation Updates

- **README.md**: Update with new structure and launcher usage
- **Add timestamps** to all documentation changes
- **Create migration guide** for users familiar with old structure
- **Update all file paths** in documentation

## 🎯 Expected Benefits

1. **Improved Organization**: Clear separation of concerns
2. **Better Maintainability**: Easier to find and modify code
3. **Enhanced User Experience**: Single entry point for all applications
4. **Simplified Development**: Logical structure for adding new features
5. **Better Documentation**: Centralized docs with clear organization

## ⚠️ Considerations

- **Preserve all existing functionality**
- **Maintain backward compatibility** where possible
- **Update all documentation** to reflect changes
- **Test thoroughly** before considering complete
- **Keep backup** of original structure during transition

---

**Ready for Implementation**: This plan is comprehensive and ready to be executed in Code mode.