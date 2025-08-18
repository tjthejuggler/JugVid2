#!/usr/bin/env python3
"""
JugVid2 Project Launcher
========================

Main command-line interface for launching all JugVid2 applications and tools.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

class JugVid2Launcher:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.applications = {
            '1': {
                'name': 'Juggling Tracker',
                'description': 'Advanced ball tracking with IMU integration',
                'script': 'apps/juggling_tracker/run_juggling_tracker.py',
                'variants': {
                    'a': ('Basic (Webcam)', ['--webcam']),
                    'b': ('With RealSense', []),
                    'c': ('With IMU Watches', ['--webcam', '--watch-ips', '192.168.1.101', '192.168.1.102']),
                    'd': ('JugVid2cpp Mode', ['--jugvid2cpp']),
                    'e': ('Video Playback', ['--simulation', '--video-path']),
                }
            },
            '2': {
                'name': 'Face Balance Timer',
                'description': 'Pose-based balance timing exercise',
                'script': 'apps/face_balance_timer/run_face_balance_timer.py',
                'variants': None
            },
            '3': {
                'name': 'Stillness Recorder',
                'description': 'Motion-triggered video recording',
                'script': None,  # Has multiple variants
                'variants': {
                    'a': ('Basic Recorder', 'apps/stillness_recorder/run_stillness_recorder.py'),
                    'b': ('Headless Mode', 'apps/stillness_recorder/run_stillness_recorder_headless.py'),
                    'c': ('With IMU Integration', 'apps/stillness_recorder/run_stillness_recorder_with_imu.py'),
                }
            },
            '4': {
                'name': 'Pose Detection Tools',
                'description': 'Simple and improved pose detection',
                'script': None,
                'variants': {
                    'a': ('Simple Pose Detector', 'apps/pose_detection/simple_pose_detector.py'),
                    'b': ('Improved Pose Detector', 'apps/pose_detection/improved_pose_detector.py'),
                }
            }
        }
        
        self.tools = {
            '5': {
                'name': 'Debug Tools',
                'description': 'Performance analysis and debugging',
                'variants': {
                    'a': ('IMU Performance Debug', 'tools/debug/debug_imu_performance.py'),
                    'b': ('Juggling Tracker Debug', 'tools/debug/debug_juggling_tracker.py'),
                    'c': ('Watch Connection Debug', 'tools/debug/debug_watch_imu_connection.py'),
                    'd': ('Run Debug Analysis', 'tools/debug/run_debug_analysis.py'),
                }
            },
            '6': {
                'name': 'Setup & Installation',
                'description': 'Dependency management and setup',
                'variants': {
                    'a': ('Install Dependencies', 'tools/setup/setup_dependencies.py'),
                    'b': ('Fix IMU Integration', 'tools/setup/fix_imu_integration.py'),
                }
            },
            '7': {
                'name': 'Testing Suite',
                'description': 'Comprehensive testing tools',
                'variants': {
                    'a': ('Test All Components', 'tools/testing/test_stillness_recorder.py'),
                    'b': ('Test IMU Integration', 'tools/testing/test_enhanced_imu_integration.py'),
                    'c': ('Test High Performance IMU', 'tools/testing/test_high_performance_imu.py'),
                    'd': ('Validate IMU Integration', 'tools/testing/validate_imu_integration.py'),
                }
            }
        }
        
        self.system_tools = {
            '8': 'Check Dependencies',
            '9': 'System Information'
        }

    def show_main_menu(self):
        """Display the main menu."""
        print("\n" + "="*50)
        print("🎯 JugVid2 Project Launcher")
        print("="*50)
        print("\n📱 Main Applications:")
        for key, app in self.applications.items():
            print(f"  {key}. {app['name']:<20} - {app['description']}")
        
        print("\n🛠️  Tools & Utilities:")
        for key, tool in self.tools.items():
            print(f"  {key}. {tool['name']:<20} - {tool['description']}")
        
        print("\n🔧 System:")
        for key, desc in self.system_tools.items():
            print(f"  {key}. {desc}")
        
        print("\n📖 Options:")
        print("  h. Help                      - Show detailed help")
        print("  q. Quit                      - Exit launcher")
        print("\n" + "="*50)

    def show_variants_menu(self, app_key):
        """Show variants menu for an application."""
        app = self.applications.get(app_key) or self.tools.get(app_key)
        if not app or not app.get('variants'):
            return None
            
        print(f"\n📋 {app['name']} Options:")
        print("-" * 30)
        for key, variant in app['variants'].items():
            if isinstance(variant, tuple):
                name = variant[0]
                print(f"  {key}. {name}")
            else:
                print(f"  {key}. {variant}")
        print("  b. Back to main menu")
        
        choice = input("\nSelect option: ").lower().strip()
        return choice if choice in app['variants'] or choice == 'b' else None

    def run_application(self, app_key, variant_key=None):
        """Run the selected application."""
        try:
            if app_key in self.applications:
                app = self.applications[app_key]
                
                if app['script'] and not variant_key:
                    # Direct script execution
                    script_path = self.project_root / app['script']
                    subprocess.run([sys.executable, str(script_path)])
                    
                elif app['variants'] and variant_key:
                    variant = app['variants'][variant_key]
                    
                    if app_key == '1':  # Juggling Tracker
                        script_path = self.project_root / app['script']
                        args = [sys.executable, str(script_path)] + variant[1]
                        
                        if 'video-path' in variant[1]:
                            video_path = input("Enter video file path: ").strip()
                            if video_path:
                                args.append(video_path)
                        
                        subprocess.run(args)
                    else:
                        # Other applications with variants
                        if isinstance(variant, tuple):
                            script_path = self.project_root / variant[1]
                        else:
                            script_path = self.project_root / variant
                        subprocess.run([sys.executable, str(script_path)])
                        
            elif app_key in self.tools:
                tool = self.tools[app_key]
                if variant_key and variant_key in tool['variants']:
                    variant = tool['variants'][variant_key]
                    if isinstance(variant, tuple):
                        script_path = self.project_root / variant[1]
                    else:
                        script_path = self.project_root / variant
                    subprocess.run([sys.executable, str(script_path)])
                    
        except FileNotFoundError as e:
            print(f"❌ Error: Script not found - {e}")
        except Exception as e:
            print(f"❌ Error running application: {e}")

    def check_dependencies(self):
        """Check system dependencies."""
        print("\n🔍 Checking Dependencies...")
        print("-" * 30)
        
        # Check Python packages
        required_packages = [
            'cv2', 'numpy', 'PyQt6', 'mediapipe', 'websockets', 
            'requests', 'filterpy', 'matplotlib', 'sqlite3'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} - MISSING")
                missing_packages.append(package)
        
        # Check optional dependencies
        print("\n📦 Optional Dependencies:")
        try:
            import pyrealsense2
            print("✅ pyrealsense2 (RealSense support)")
        except ImportError:
            print("⚠️  pyrealsense2 - Not installed (RealSense cameras won't work)")
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Run option 6a (Install Dependencies) to fix this.")
        else:
            print("\n🎉 All required dependencies are installed!")

    def show_system_info(self):
        """Show system information."""
        print("\n💻 System Information")
        print("-" * 30)
        print(f"Python Version: {sys.version}")
        print(f"Project Root: {self.project_root}")
        print(f"Platform: {sys.platform}")
        
        # Check for cameras
        print("\n📹 Camera Check:")
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                print("✅ Webcam detected")
                cap.release()
            else:
                print("❌ No webcam detected")
        except:
            print("❌ OpenCV not available for camera check")

    def show_help(self):
        """Show detailed help information."""
        print("\n📖 JugVid2 Help")
        print("="*50)
        print("""
🎯 MAIN APPLICATIONS:

1. Juggling Tracker
   - Advanced computer vision ball tracking
   - Supports RealSense cameras, webcams, and video files
   - Real-time IMU integration with Android watches
   - JugVid2cpp high-performance mode available
   
2. Face Balance Timer
   - Automatic timing for face balancing exercises
   - Uses pose detection to start/stop timer
   - Stores session data in SQLite database
   
3. Stillness Recorder
   - Records video when motion stops
   - Three variants: basic, headless, and with IMU
   - Configurable motion thresholds and recording duration
   
4. Pose Detection Tools
   - Simple and improved pose detection utilities
   - Useful for testing and development

🛠️ TOOLS & UTILITIES:

5. Debug Tools - Performance analysis and troubleshooting
6. Setup & Installation - Dependency management
7. Testing Suite - Comprehensive testing tools
8. Check Dependencies - Verify all requirements
9. System Information - Hardware and software status

💡 TIPS:
- Use option 8 first to check if all dependencies are installed
- Most applications support both RealSense cameras and webcams
- IMU features require Android watches with custom apps
- Check the docs/ folder for detailed documentation

🚀 QUICK START:
1. Run option 8 to check dependencies
2. Try option 2 (Face Balance Timer) for a simple test
3. Use option 1a (Juggling Tracker - Basic) for main functionality
        """)

    def run_interactive(self):
        """Run the interactive launcher."""
        while True:
            self.show_main_menu()
            choice = input("\nEnter your choice (1-9, h, q): ").strip().lower()
            
            if choice == 'q':
                print("\n👋 Goodbye!")
                break
            elif choice == 'h':
                self.show_help()
                input("\nPress Enter to continue...")
            elif choice == '8':
                self.check_dependencies()
                input("\nPress Enter to continue...")
            elif choice == '9':
                self.show_system_info()
                input("\nPress Enter to continue...")
            elif choice in self.applications:
                app = self.applications[choice]
                if app.get('variants'):
                    variant_choice = self.show_variants_menu(choice)
                    if variant_choice == 'b':
                        continue
                    elif variant_choice:
                        self.run_application(choice, variant_choice)
                else:
                    self.run_application(choice)
            elif choice in self.tools:
                variant_choice = self.show_variants_menu(choice)
                if variant_choice == 'b':
                    continue
                elif variant_choice:
                    self.run_application(choice, variant_choice)
            else:
                print("❌ Invalid choice. Please try again.")

    def run_direct(self, app_name):
        """Run application directly by name."""
        # Map common names to app keys
        name_mapping = {
            'juggling': '1',
            'tracker': '1',
            'face': '2',
            'balance': '2',
            'stillness': '3',
            'recorder': '3',
            'pose': '4',
            'debug': '5',
            'setup': '6',
            'test': '7',
            'deps': '8',
            'info': '9'
        }
        
        app_key = name_mapping.get(app_name.lower())
        if app_key:
            if app_key in ['8', '9']:
                if app_key == '8':
                    self.check_dependencies()
                else:
                    self.show_system_info()
            else:
                self.run_application(app_key)
        else:
            print(f"❌ Unknown application: {app_name}")
            print("Available: juggling, face, stillness, pose, debug, setup, test, deps, info")

def main():
    parser = argparse.ArgumentParser(description='JugVid2 Project Launcher')
    parser.add_argument('app', nargs='?', help='Application to run directly')
    parser.add_argument('--list', action='store_true', help='List all available applications')
    
    args = parser.parse_args()
    launcher = JugVid2Launcher()
    
    if args.list:
        launcher.show_main_menu()
    elif args.app:
        launcher.run_direct(args.app)
    else:
        launcher.run_interactive()

if __name__ == '__main__':
    main()