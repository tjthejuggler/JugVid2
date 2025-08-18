#!/usr/bin/env python3
"""
Setup script for JugVid2 dependencies.

This script installs all required dependencies for the juggling tracker
and IMU streaming functionality.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up JugVid2 dependencies...")
    print("=" * 50)
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        sys.exit(1)
    else:
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
    
    # List of required packages
    packages = [
        "numpy>=1.19.0",
        "opencv-python>=4.5.0", 
        "PyQt6>=6.4.0",
        "filterpy",
        "websockets",
        "requests",
        "mediapipe>=0.8.10"
    ]
    
    print(f"\n📋 Installing {len(packages)} required packages...")
    
    # Install each package
    failed_packages = []
    for package in packages:
        package_name = package.split('>=')[0].split('==')[0]
        success = run_command(f"pip install {package}", f"Installing {package_name}")
        if not success:
            failed_packages.append(package_name)
    
    # Summary
    print("\n" + "=" * 50)
    if failed_packages:
        print(f"⚠️  Setup completed with {len(failed_packages)} failures:")
        for package in failed_packages:
            print(f"   ❌ {package}")
        print(f"\n✅ Successfully installed: {len(packages) - len(failed_packages)}/{len(packages)} packages")
        print("\n🔧 To fix failed packages, try:")
        print("   pip install --upgrade pip")
        print("   pip install --user <package_name>")
    else:
        print("🎉 All dependencies installed successfully!")
    
    # Test imports
    print(f"\n🧪 Testing critical imports...")
    
    test_imports = [
        ("numpy", "NumPy"),
        ("cv2", "OpenCV"),
        ("PyQt6", "PyQt6"),
        ("filterpy", "FilterPy"),
        ("websockets", "WebSockets"),
        ("requests", "Requests")
    ]
    
    import_failures = []
    for module, name in test_imports:
        try:
            __import__(module)
            print(f"✅ {name} import successful")
        except ImportError as e:
            print(f"❌ {name} import failed: {e}")
            import_failures.append(name)
    
    # Final status
    print("\n" + "=" * 50)
    if import_failures:
        print(f"⚠️  Setup completed with import issues:")
        for name in import_failures:
            print(f"   ❌ {name}")
        print(f"\n🔧 Try running: pip install --force-reinstall <package_name>")
        return False
    else:
        print("🎉 Setup completed successfully!")
        print("\n🚀 You can now run:")
        print("   python run_juggling_tracker.py --webcam")
        print("   python run_juggling_tracker.py --webcam --watch-ips 10.200.169.205")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)