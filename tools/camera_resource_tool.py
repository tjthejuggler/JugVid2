#!/usr/bin/env python3
"""
RealSense Camera Resource Management Tool

This utility helps diagnose and resolve camera resource conflicts
that prevent the juggling tracker from accessing the RealSense camera.

Usage:
    python tools/camera_resource_tool.py --check
    python tools/camera_resource_tool.py --fix
    python tools/camera_resource_tool.py --force-reset

Author: Roo (2025-08-18)
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.camera.camera_resource_manager import (
    CameraResourceManager, 
    check_camera_conflicts, 
    cleanup_camera_resources
)


def print_header():
    """Print tool header."""
    print("=" * 60)
    print("🎥 RealSense Camera Resource Management Tool")
    print("=" * 60)
    print()


def check_camera_status():
    """Check and display camera resource status."""
    print("🔍 Checking camera resource status...")
    print()
    
    manager = CameraResourceManager(debug=True)
    
    # Check availability
    available, message = manager.check_camera_availability()
    
    if available:
        print("✅ Camera Status: AVAILABLE")
        print(f"   {message}")
    else:
        print("❌ Camera Status: UNAVAILABLE")
        print(f"   {message}")
    
    print()
    
    # Check for conflicting processes
    has_conflicts, processes = check_camera_conflicts()
    
    if has_conflicts:
        print(f"⚠️  Found {len(processes)} potential camera conflicts:")
        print()
        for i, proc in enumerate(processes, 1):
            print(f"   {i}. PID {proc['pid']}: {proc['name']}")
            print(f"      Age: {proc['age_seconds']:.1f} seconds")
            if proc['cmdline']:
                cmd_short = proc['cmdline'][:60] + "..." if len(proc['cmdline']) > 60 else proc['cmdline']
                print(f"      Command: {cmd_short}")
            print()
    else:
        print("✅ No camera resource conflicts detected")
    
    return available, has_conflicts


def fix_camera_conflicts():
    """Attempt to fix camera resource conflicts."""
    print("🔧 Attempting to fix camera resource conflicts...")
    print()
    
    # First check what we're dealing with
    available, has_conflicts = check_camera_status()
    
    if available and not has_conflicts:
        print("✅ No issues detected - camera should be available")
        return True
    
    if has_conflicts:
        print("🔄 Attempting to resolve conflicts...")
        success = cleanup_camera_resources(force=False)
        
        if success:
            print("✅ Camera resource conflicts resolved!")
            
            # Verify the fix
            print()
            print("🔍 Verifying fix...")
            available, has_conflicts = check_camera_status()
            
            if available and not has_conflicts:
                print("✅ Verification successful - camera is now available")
                return True
            else:
                print("⚠️  Issues may persist - try --force-reset")
                return False
        else:
            print("❌ Failed to resolve conflicts automatically")
            print("💡 Try running with --force-reset for more aggressive cleanup")
            return False
    
    return False


def force_reset_camera():
    """Force reset camera resources."""
    print("🔄 Force resetting camera resources...")
    print("⚠️  This will terminate all processes using the camera")
    print()
    
    # Confirm with user
    response = input("Continue with force reset? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Force reset cancelled")
        return False
    
    print()
    print("🔄 Performing force reset...")
    
    manager = CameraResourceManager(debug=True)
    success = manager.force_camera_reset()
    
    if success:
        print("✅ Force reset completed successfully!")
        
        # Verify the reset
        print()
        print("🔍 Verifying reset...")
        available, has_conflicts = check_camera_status()
        
        if available and not has_conflicts:
            print("✅ Camera is now available for use")
            return True
        else:
            print("⚠️  Some issues may persist")
            print("💡 Try unplugging and reconnecting the RealSense camera")
            return False
    else:
        print("❌ Force reset failed")
        return False


def show_troubleshooting_tips():
    """Show troubleshooting tips."""
    print("💡 TROUBLESHOOTING TIPS")
    print("-" * 30)
    print()
    print("If camera issues persist, try these steps:")
    print()
    print("1. 🔌 Hardware Reset:")
    print("   - Unplug the RealSense camera")
    print("   - Wait 10 seconds")
    print("   - Plug it back in")
    print()
    print("2. 🔄 Restart Applications:")
    print("   - Close all applications that might use the camera")
    print("   - Restart the juggling tracker")
    print()
    print("3. 🖥️  System Restart:")
    print("   - If issues persist, restart your computer")
    print()
    print("4. 🔧 Advanced Debugging:")
    print("   - Run: python apps/juggling_tracker/main.py --debug-camera")
    print("   - Check system logs: dmesg | grep -i realsense")
    print()
    print("5. 📞 Get Help:")
    print("   - Report issues with debug output")
    print("   - Include camera model and system information")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RealSense Camera Resource Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/camera_resource_tool.py --check        # Check camera status
  python tools/camera_resource_tool.py --fix          # Fix conflicts automatically  
  python tools/camera_resource_tool.py --force-reset  # Force reset all resources
  python tools/camera_resource_tool.py --help-tips    # Show troubleshooting tips
        """
    )
    
    parser.add_argument('--check', action='store_true', 
                       help='Check camera resource status')
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to fix camera resource conflicts')
    parser.add_argument('--force-reset', action='store_true',
                       help='Force reset camera resources (terminates processes)')
    parser.add_argument('--help-tips', action='store_true',
                       help='Show troubleshooting tips')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any([args.check, args.fix, args.force_reset, args.help_tips]):
        parser.print_help()
        return
    
    print_header()
    
    try:
        if args.help_tips:
            show_troubleshooting_tips()
        
        elif args.check:
            available, has_conflicts = check_camera_status()
            
            if not available or has_conflicts:
                print()
                print("💡 To fix issues, run:")
                print("   python tools/camera_resource_tool.py --fix")
        
        elif args.fix:
            success = fix_camera_conflicts()
            
            if not success:
                print()
                print("💡 For more aggressive cleanup, try:")
                print("   python tools/camera_resource_tool.py --force-reset")
        
        elif args.force_reset:
            success = force_reset_camera()
            
            if not success:
                print()
                show_troubleshooting_tips()
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print()
        print("💡 For help, run:")
        print("   python tools/camera_resource_tool.py --help-tips")


if __name__ == "__main__":
    main()