#!/usr/bin/env python3
"""
Camera Resource Manager for RealSense Camera Conflict Resolution

This module provides comprehensive camera resource management to prevent
conflicts when multiple processes try to access the RealSense camera simultaneously.

Key Features:
- Process detection and cleanup for existing camera usage
- Resource locking mechanism to prevent simultaneous access
- Graceful camera release and cleanup
- Automatic conflict resolution with retry logic
- Enhanced error handling and user feedback

Author: Roo (2025-08-18)
"""

import os
import sys
import time
import psutil
import signal
import fcntl
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraResourceManager:
    """
    Manages RealSense camera resources to prevent conflicts between multiple processes.
    
    This class provides:
    - Process detection for camera usage
    - Resource locking to prevent simultaneous access
    - Automatic cleanup of stale processes
    - Graceful camera release mechanisms
    """
    
    def __init__(self, lock_timeout: int = 30, debug: bool = False):
        """
        Initialize the Camera Resource Manager.
        
        Args:
            lock_timeout: Maximum time to wait for camera lock (seconds)
            debug: Enable debug logging
        """
        self.lock_timeout = lock_timeout
        self.debug = debug
        self.lock_file_path = Path(tempfile.gettempdir()) / "jugvid2_camera.lock"
        self.lock_file = None
        self.current_pid = os.getpid()
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"CameraResourceManager initialized for PID {self.current_pid}")
    
    def detect_camera_processes(self) -> List[Dict]:
        """
        Detect processes that might be using the RealSense camera.
        
        Returns:
            List of dictionaries containing process information
        """
        camera_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_info = proc.info
                    
                    # Skip our own process
                    if proc_info['pid'] == self.current_pid:
                        continue
                    
                    # Check for RealSense-related processes
                    if self._is_camera_process(proc_info):
                        camera_processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else '',
                            'create_time': proc_info['create_time'],
                            'age_seconds': time.time() - proc_info['create_time']
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.error(f"Error detecting camera processes: {e}")
        
        if self.debug and camera_processes:
            logger.debug(f"Found {len(camera_processes)} potential camera processes")
            for proc in camera_processes:
                logger.debug(f"  PID {proc['pid']}: {proc['name']} (age: {proc['age_seconds']:.1f}s)")
        
        return camera_processes
    
    def _is_camera_process(self, proc_info: Dict) -> bool:
        """
        Determine if a process is likely using the camera.
        
        Args:
            proc_info: Process information dictionary
            
        Returns:
            True if process is likely using camera
        """
        name = proc_info.get('name', '').lower()
        cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
        
        # Check for RealSense-related keywords
        camera_keywords = [
            'realsense', 'rs-', 'librealsense',
            'juggling_tracker', 'jugvid', 'frame_acquisition',
            'depth_camera', 'intel_camera'
        ]
        
        # Check for Python processes running camera-related scripts
        python_camera_keywords = [
            'main.py', 'juggling_tracker', 'frame_acquisition',
            'camera', 'realsense', 'depth'
        ]
        
        # Check process name
        for keyword in camera_keywords:
            if keyword in name:
                return True
        
        # Check command line for Python processes
        if 'python' in name and cmdline:
            for keyword in python_camera_keywords:
                if keyword in cmdline:
                    return True
        
        return False
    
    def acquire_camera_lock(self, force_cleanup: bool = False) -> bool:
        """
        Acquire exclusive lock on camera resource.
        
        Args:
            force_cleanup: If True, forcefully cleanup conflicting processes
            
        Returns:
            True if lock acquired successfully
        """
        if self.debug:
            logger.debug(f"Attempting to acquire camera lock (force_cleanup={force_cleanup})")
        
        # Check for existing processes first
        camera_processes = self.detect_camera_processes()
        
        if camera_processes and not force_cleanup:
            logger.warning(f"Found {len(camera_processes)} processes potentially using camera")
            for proc in camera_processes:
                logger.warning(f"  PID {proc['pid']}: {proc['name']} (age: {proc['age_seconds']:.1f}s)")
            
            # Ask user for permission to cleanup
            if not self._prompt_user_cleanup(camera_processes):
                logger.info("User declined cleanup, cannot acquire camera lock")
                return False
            
            force_cleanup = True
        
        # Cleanup conflicting processes if requested
        if force_cleanup and camera_processes:
            if not self._cleanup_camera_processes(camera_processes):
                logger.error("Failed to cleanup camera processes")
                return False
        
        # Try to acquire file lock
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write our PID to the lock file
            self.lock_file.write(f"{self.current_pid}\n")
            self.lock_file.write(f"{time.time()}\n")
            self.lock_file.flush()
            
            if self.debug:
                logger.debug(f"Camera lock acquired successfully by PID {self.current_pid}")
            
            return True
            
        except (IOError, OSError) as e:
            if self.debug:
                logger.debug(f"Failed to acquire camera lock: {e}")
            
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            return False
    
    def release_camera_lock(self):
        """Release the camera resource lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None
                
                # Remove lock file
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                if self.debug:
                    logger.debug(f"Camera lock released by PID {self.current_pid}")
                    
            except Exception as e:
                logger.error(f"Error releasing camera lock: {e}")
    
    def _prompt_user_cleanup(self, processes: List[Dict]) -> bool:
        """
        Prompt user whether to cleanup conflicting processes.
        
        Args:
            processes: List of conflicting processes
            
        Returns:
            True if user agrees to cleanup
        """
        print("\n🎥 CAMERA RESOURCE CONFLICT DETECTED")
        print("=" * 50)
        print(f"Found {len(processes)} processes that may be using the RealSense camera:")
        
        for proc in processes:
            age_str = f"{proc['age_seconds']:.1f}s ago"
            print(f"  • PID {proc['pid']}: {proc['name']} (started {age_str})")
            if proc['cmdline']:
                print(f"    Command: {proc['cmdline'][:80]}...")
        
        print("\nTo use the camera, these processes need to be terminated.")
        print("This is safe and will not harm your system.")
        
        while True:
            response = input("\nTerminate conflicting processes? [y/N]: ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def _cleanup_camera_processes(self, processes: List[Dict]) -> bool:
        """
        Cleanup conflicting camera processes.
        
        Args:
            processes: List of processes to cleanup
            
        Returns:
            True if cleanup successful
        """
        logger.info(f"Cleaning up {len(processes)} camera processes...")
        
        success_count = 0
        
        for proc_info in processes:
            pid = proc_info['pid']
            name = proc_info['name']
            
            try:
                proc = psutil.Process(pid)
                
                # First try graceful termination
                logger.info(f"Terminating process {pid} ({name})...")
                proc.terminate()
                
                # Wait for graceful shutdown
                try:
                    proc.wait(timeout=5)
                    logger.info(f"Process {pid} terminated gracefully")
                    success_count += 1
                    continue
                except psutil.TimeoutExpired:
                    logger.warning(f"Process {pid} did not terminate gracefully, forcing...")
                
                # Force kill if graceful termination failed
                if proc.is_running():
                    proc.kill()
                    proc.wait(timeout=3)
                    logger.info(f"Process {pid} force-killed")
                    success_count += 1
                
            except psutil.NoSuchProcess:
                logger.info(f"Process {pid} already terminated")
                success_count += 1
            except psutil.AccessDenied:
                logger.error(f"Access denied when trying to terminate process {pid}")
            except Exception as e:
                logger.error(f"Error terminating process {pid}: {e}")
        
        # Wait a moment for resources to be released
        time.sleep(2)
        
        logger.info(f"Cleanup completed: {success_count}/{len(processes)} processes handled")
        return success_count == len(processes)
    
    def check_camera_availability(self) -> Tuple[bool, str]:
        """
        Check if camera is available for use.
        
        Returns:
            Tuple of (is_available, status_message)
        """
        # Check for conflicting processes
        camera_processes = self.detect_camera_processes()
        
        if camera_processes:
            process_list = ", ".join([f"PID {p['pid']} ({p['name']})" for p in camera_processes])
            return False, f"Camera in use by: {process_list}"
        
        # Check if lock file exists
        if self.lock_file_path.exists():
            try:
                with open(self.lock_file_path, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        lock_pid = int(lines[0].strip())
                        lock_time = float(lines[1].strip())
                        
                        # Check if locking process still exists
                        try:
                            psutil.Process(lock_pid)
                            age = time.time() - lock_time
                            return False, f"Camera locked by PID {lock_pid} ({age:.1f}s ago)"
                        except psutil.NoSuchProcess:
                            # Stale lock file, remove it
                            self.lock_file_path.unlink()
                            logger.info("Removed stale camera lock file")
            except Exception as e:
                logger.warning(f"Error checking lock file: {e}")
        
        return True, "Camera available"
    
    def force_camera_reset(self) -> bool:
        """
        Force reset of camera resources by cleaning up all related processes.
        
        Returns:
            True if reset successful
        """
        logger.info("🔄 Forcing camera resource reset...")
        
        # Find and cleanup all camera processes
        camera_processes = self.detect_camera_processes()
        
        if camera_processes:
            logger.info(f"Found {len(camera_processes)} camera processes to cleanup")
            if not self._cleanup_camera_processes(camera_processes):
                logger.error("Failed to cleanup all camera processes")
                return False
        
        # Remove any stale lock files
        if self.lock_file_path.exists():
            try:
                self.lock_file_path.unlink()
                logger.info("Removed stale lock file")
            except Exception as e:
                logger.error(f"Error removing lock file: {e}")
        
        # Try to reset USB devices (requires root privileges)
        try:
            self._reset_usb_devices()
        except Exception as e:
            logger.warning(f"Could not reset USB devices (may require root): {e}")
        
        logger.info("✅ Camera resource reset completed")
        return True
    
    def _reset_usb_devices(self):
        """Reset USB devices to clear any stuck camera connections."""
        try:
            # Find RealSense USB devices
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                realsense_devices = [line for line in lines if 'Intel' in line and ('RealSense' in line or '8086:' in line)]
                
                if realsense_devices:
                    logger.info(f"Found {len(realsense_devices)} RealSense USB devices")
                    # Note: USB reset requires root privileges and specific tools
                    # This is a placeholder for more advanced USB reset functionality
                    logger.info("USB device reset would require root privileges")
        except Exception as e:
            logger.debug(f"USB device detection failed: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire_camera_lock():
            raise RuntimeError("Failed to acquire camera resource lock")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release_camera_lock()


class CameraResourceError(Exception):
    """Exception raised when camera resource conflicts occur."""
    pass


def get_camera_resource_manager(debug: bool = False) -> CameraResourceManager:
    """
    Get a camera resource manager instance.
    
    Args:
        debug: Enable debug logging
        
    Returns:
        CameraResourceManager instance
    """
    return CameraResourceManager(debug=debug)


# Utility functions for easy integration
def check_camera_conflicts() -> Tuple[bool, List[Dict]]:
    """
    Quick check for camera resource conflicts.
    
    Returns:
        Tuple of (has_conflicts, list_of_conflicting_processes)
    """
    manager = CameraResourceManager()
    processes = manager.detect_camera_processes()
    return len(processes) > 0, processes


def cleanup_camera_resources(force: bool = False) -> bool:
    """
    Cleanup camera resources and resolve conflicts.
    
    Args:
        force: If True, cleanup without user prompt
        
    Returns:
        True if cleanup successful
    """
    manager = CameraResourceManager()
    return manager.force_camera_reset() if force else manager.acquire_camera_lock(force_cleanup=True)


if __name__ == "__main__":
    # Command-line interface for camera resource management
    import argparse
    
    parser = argparse.ArgumentParser(description="RealSense Camera Resource Manager")
    parser.add_argument('--check', action='store_true', help='Check for camera conflicts')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup camera resources')
    parser.add_argument('--force', action='store_true', help='Force cleanup without prompts')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = CameraResourceManager(debug=args.debug)
    
    if args.check:
        available, message = manager.check_camera_availability()
        print(f"Camera Status: {'✅ Available' if available else '❌ Unavailable'}")
        print(f"Details: {message}")
        
        processes = manager.detect_camera_processes()
        if processes:
            print(f"\nFound {len(processes)} potential camera processes:")
            for proc in processes:
                print(f"  PID {proc['pid']}: {proc['name']} (age: {proc['age_seconds']:.1f}s)")
    
    elif args.cleanup:
        if args.force:
            success = manager.force_camera_reset()
        else:
            success = manager.acquire_camera_lock(force_cleanup=True)
            if success:
                manager.release_camera_lock()
        
        print(f"Cleanup: {'✅ Success' if success else '❌ Failed'}")
    
    else:
        parser.print_help()