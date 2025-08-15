#!/usr/bin/env python3
"""
Watch IMU Manager - Enhanced communication with Watch OS IMU recording apps

This module implements the complete Python integration guide functionality for
synchronizing IMU data recording from dual Watch OS apps with the stillness recorder.

Based on the Complete Python Integration Guide for Watch IMU Recorder.

Features:
- Complete WatchController functionality from integration guide
- Multi-port discovery and connection (8080-9090)
- Synchronized recording sessions with state management
- Comprehensive error handling and retry logic
- Concurrent watch communication
- Status monitoring and health checks
- IMU data retrieval and CSV storage
- Connection status monitoring with automatic reconnection

Author: Generated for JugVid2 project
Date: 2025-08-15
"""

import requests
import time
import threading
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import socket
import csv
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WatchController:
    """Controller for managing multiple Watch IMU Recorders (from integration guide)"""
    
    def __init__(self, watch_ips: List[str], default_port: int = 8080, timeout: int = 5):
        """
        Initialize watch controller
        
        Args:
            watch_ips: List of watch IP addresses
            default_port: Default port to try first
            timeout: HTTP request timeout in seconds
        """
        self.watch_ips = watch_ips
        self.default_port = default_port
        self.timeout = timeout
        self.watch_ports = {}  # Store discovered ports for each watch
        
    def discover_watches(self) -> Dict[str, int]:
        """
        Discover active watches and their ports
        
        Returns:
            Dictionary mapping IP addresses to active ports
        """
        logger.info("Discovering active watches...")
        active_watches = {}
        
        # Ports to try in order
        ports_to_try = [8080, 8081, 8082, 8083, 9090]
        
        for ip in self.watch_ips:
            logger.info(f"Testing connectivity to {ip}...")
            
            for port in ports_to_try:
                try:
                    url = f"http://{ip}:{port}/ping"
                    response = requests.get(url, timeout=self.timeout)
                    
                    if response.status_code == 200 and response.text.strip() == "pong":
                        active_watches[ip] = port
                        self.watch_ports[ip] = port
                        logger.info(f"✓ Found active watch at {ip}:{port}")
                        break
                        
                except requests.RequestException:
                    continue
            
            if ip not in active_watches:
                logger.warning(f"✗ Could not connect to watch at {ip}")
        
        logger.info(f"Discovered {len(active_watches)} active watches")
        return active_watches
    
    def send_command_to_watch(self, ip: str, endpoint: str) -> Tuple[str, bool, str]:
        """
        Send command to a single watch
        
        Args:
            ip: Watch IP address
            endpoint: API endpoint (start, stop, status, ping)
            
        Returns:
            Tuple of (ip, success, response_text)
        """
        port = self.watch_ports.get(ip, self.default_port)
        url = f"http://{ip}:{port}/{endpoint}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            success = response.status_code == 200
            return ip, success, response.text
            
        except requests.RequestException as e:
            return ip, False, str(e)
    
    def send_command_to_all_watches(self, endpoint: str) -> Dict[str, Tuple[bool, str]]:
        """
        Send command to all active watches simultaneously
        
        Args:
            endpoint: API endpoint to call
            
        Returns:
            Dictionary mapping IP addresses to (success, response) tuples
        """
        results = {}
        
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=len(self.watch_ips)) as executor:
            # Submit all requests
            future_to_ip = {
                executor.submit(self.send_command_to_watch, ip, endpoint): ip 
                for ip in self.watch_ips if ip in self.watch_ports
            }
            
            # Collect results
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    _, success, response = future.result()
                    results[ip] = (success, response)
                except Exception as e:
                    results[ip] = (False, str(e))
        
        return results
    
    def start_recording_all(self) -> bool:
        """
        Start recording on all watches
        
        Returns:
            True if all watches started successfully
        """
        logger.info("Starting recording on all watches...")
        results = self.send_command_to_all_watches("start")
        
        all_success = True
        for ip, (success, response) in results.items():
            if success:
                logger.info(f"✓ {ip}: {response}")
            else:
                logger.error(f"✗ {ip}: {response}")
                all_success = False
        
        return all_success
    
    def stop_recording_all(self) -> bool:
        """
        Stop recording on all watches
        
        Returns:
            True if all watches stopped successfully
        """
        logger.info("Stopping recording on all watches...")
        results = self.send_command_to_all_watches("stop")
        
        all_success = True
        for ip, (success, response) in results.items():
            if success:
                logger.info(f"✓ {ip}: {response}")
            else:
                logger.error(f"✗ {ip}: {response}")
                all_success = False
        
        return all_success
    
    def get_status_all(self) -> Dict[str, Optional[Dict]]:
        """
        Get status from all watches
        
        Returns:
            Dictionary mapping IP addresses to status dictionaries
        """
        results = self.send_command_to_all_watches("status")
        status_data = {}
        
        for ip, (success, response) in results.items():
            if success:
                try:
                    status_data[ip] = json.loads(response)
                except json.JSONDecodeError:
                    status_data[ip] = None
                    logger.error(f"Invalid JSON response from {ip}: {response}")
            else:
                status_data[ip] = None
                logger.error(f"Failed to get status from {ip}: {response}")
        
        return status_data
    
    def wait_for_recording_state(self, target_state: str, max_wait: int = 10) -> bool:
        """
        Wait for all watches to reach a specific recording state
        
        Args:
            target_state: Target state (IDLE, RECORDING, STOPPING)
            max_wait: Maximum wait time in seconds
            
        Returns:
            True if all watches reached target state
        """
        logger.info(f"Waiting for all watches to reach state: {target_state}")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_data = self.get_status_all()
            
            all_ready = True
            for ip, status in status_data.items():
                if status is None:
                    all_ready = False
                    break
                    
                current_state = status.get("recording_state", "UNKNOWN")
                if current_state != target_state:
                    all_ready = False
                    break
            
            if all_ready:
                logger.info(f"All watches reached state: {target_state}")
                return True
            
            time.sleep(0.5)
        
        logger.warning(f"Timeout waiting for state: {target_state}")
        return False
    
    def synchronized_recording_session(self, duration: float) -> bool:
        """
        Perform a synchronized recording session
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            True if session completed successfully
        """
        logger.info(f"Starting synchronized recording session ({duration}s)")
        
        # 1. Check initial state
        if not self.wait_for_recording_state("IDLE", max_wait=5):
            logger.error("Not all watches are in IDLE state")
            return False
        
        # 2. Start recording on all watches
        if not self.start_recording_all():
            logger.error("Failed to start recording on all watches")
            return False
        
        # 3. Wait for recording state
        if not self.wait_for_recording_state("RECORDING", max_wait=5):
            logger.error("Not all watches entered RECORDING state")
            return False
        
        # 4. Record for specified duration
        logger.info(f"Recording for {duration} seconds...")
        time.sleep(duration)
        
        # 5. Stop recording on all watches
        if not self.stop_recording_all():
            logger.error("Failed to stop recording on all watches")
            return False
        
        # 6. Wait for idle state
        if not self.wait_for_recording_state("IDLE", max_wait=10):
            logger.warning("Not all watches returned to IDLE state")
        
        logger.info("Synchronized recording session completed")
        return True


@dataclass
class WatchConfig:
    """Configuration for a single watch."""
    name: str  # "left" or "right"
    ip: str
    port: int = 8080
    timeout: float = 5.0  # Increased timeout as per guide
    
    def get_url(self, endpoint: str) -> str:
        """Get full URL for an endpoint."""
        return f"http://{self.ip}:{self.port}/{endpoint.lstrip('/')}"


@dataclass
class IMUReading:
    """Single IMU reading from a watch."""
    timestamp: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    watch_name: str
    mag_x: float = 0.0  # Added magnetometer support
    mag_y: float = 0.0
    mag_z: float = 0.0


class WatchConnection:
    """Enhanced watch connection with multi-port discovery and better error handling."""
    
    def __init__(self, config: WatchConfig):
        self.config = config
        self.is_connected = False
        self.is_recording = False
        self.last_ping_time = 0
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.last_error = None
        self.recording_state = "IDLE"  # IDLE, RECORDING, STOPPING
        self.sample_count = 0
        
    def discover_port(self, ip: str) -> Optional[int]:
        """Discover the active port for a watch IP."""
        ports_to_try = [8080, 8081, 8082, 8083, 9090]
        
        for port in ports_to_try:
            try:
                url = f"http://{ip}:{port}/ping"
                response = requests.get(url, timeout=2.0)
                
                if response.status_code == 200 and response.text.strip() == "pong":
                    logger.info(f"✓ Found active watch at {ip}:{port}")
                    return port
                    
            except requests.RequestException:
                continue
        
        return None
    
    def ping(self) -> bool:
        """Enhanced ping with port discovery."""
        # First try the configured port
        try:
            response = requests.get(
                self.config.get_url("/ping"), 
                timeout=self.config.timeout
            )
            if response.status_code == 200 and response.text.strip() == "pong":
                self.is_connected = True
                self.last_ping_time = time.time()
                self.connection_attempts = 0
                self.last_error = None
                return True
        except requests.RequestException:
            pass
        
        # If configured port fails, try port discovery
        discovered_port = self.discover_port(self.config.ip)
        if discovered_port and discovered_port != self.config.port:
            logger.info(f"Updating port for {self.config.name} from {self.config.port} to {discovered_port}")
            self.config.port = discovered_port
            return self.ping()  # Retry with new port
        
        self.last_error = f"No response from watch at {self.config.ip}"
        self.is_connected = False
        self.connection_attempts += 1
        return False
    
    def send_command(self, command: str) -> Tuple[bool, str]:
        """Enhanced command sending with better error handling."""
        if not self.is_connected and not self.ping():
            return False, f"Watch not connected: {self.last_error}"
            
        try:
            response = requests.get(
                self.config.get_url(f"/{command}"), 
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                if command == "start":
                    self.is_recording = True
                    self.recording_state = "RECORDING"
                elif command == "stop":
                    self.is_recording = False
                    self.recording_state = "STOPPING"
                return True, response.text.strip()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.last_error = error_msg
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = str(e)
            self.last_error = error_msg
            self.is_connected = False
            return False, error_msg
    
    def get_watch_status(self) -> Optional[Dict[str, Any]]:
        """Get detailed status from the watch."""
        if not self.is_connected:
            return None
            
        try:
            response = requests.get(
                self.config.get_url("/status"), 
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                status_data = json.loads(response.text)
                self.recording_state = status_data.get("recording_state", "UNKNOWN")
                self.sample_count = status_data.get("sample_count", 0)
                return status_data
            
        except (requests.RequestException, json.JSONDecodeError) as e:
            self.last_error = str(e)
            
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the watch connection."""
        return {
            'name': self.config.name,
            'ip': self.config.ip,
            'port': self.config.port,
            'connected': self.is_connected,
            'recording': self.is_recording,
            'recording_state': self.recording_state,
            'sample_count': self.sample_count,
            'last_ping': self.last_ping_time,
            'connection_attempts': self.connection_attempts,
            'last_error': self.last_error
        }


class WatchIMUManager:
    """
    Enhanced Watch IMU Manager implementing complete WatchController functionality.
    
    Based on the Complete Python Integration Guide for Watch IMU Recorder.
    
    This class provides:
    - Complete WatchController functionality from integration guide
    - Multi-port discovery and connection (8080-9090)
    - Synchronized recording sessions with state management
    - Comprehensive error handling and retry logic
    - Concurrent watch communication
    - Status monitoring and health checks
    - IMU data retrieval and CSV storage
    """
    
    def __init__(self, watch_ips: List[str] = None, output_dir: str = "imu_data", 
                 default_port: int = 8080, timeout: int = 5):
        """
        Initialize the Enhanced Watch IMU Manager.
        
        Args:
            watch_ips: List of watch IP addresses
            output_dir: Directory to save IMU data files
            default_port: Default port to try first
            timeout: HTTP request timeout in seconds
        """
        self.watch_ips = watch_ips or []
        self.output_dir = output_dir
        self.default_port = default_port
        self.timeout = timeout
        self.watches: Dict[str, WatchConnection] = {}
        self.watch_ports: Dict[str, int] = {}  # Store discovered ports for each watch
        
        # Initialize WatchController for advanced functionality
        self.controller = WatchController(self.watch_ips, default_port, timeout)
        
        self.session_start_time: Optional[datetime] = None
        self.session_dir: Optional[str] = None
        self.is_recording = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Statistics
        self.total_recordings = 0
        self.last_sync_time = 0
        
        logger.info(f"WatchIMUManager initialized with {len(self.watch_ips)} watch IPs")
    
    def discover_watches(self) -> Dict[str, int]:
        """
        Discover active watches and their ports (from integration guide).
        
        Returns:
            Dictionary mapping IP addresses to active ports
        """
        active_watches = self.controller.discover_watches()
        self.watch_ports.update(active_watches)
        return active_watches
    
    def add_watch(self, name: str, ip: str, port: int = None, timeout: float = None) -> bool:
        """
        Add a watch to the manager with enhanced discovery.
        
        Args:
            name: Watch identifier ("left" or "right")
            ip: IP address of the watch
            port: Port number (will be discovered if None)
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if watch was added successfully
        """
        if name in self.watches:
            logger.warning(f"Watch '{name}' already exists, updating configuration")
        
        # Add IP to watch_ips if not already there
        if ip not in self.watch_ips:
            self.watch_ips.append(ip)
            self.controller.watch_ips.append(ip)
        
        # Discover port if not provided
        if port is None:
            discovered_port = None
            for test_port in [8080, 8081, 8082, 8083, 9090]:
                try:
                    response = requests.get(f"http://{ip}:{test_port}/ping", timeout=2.0)
                    if response.status_code == 200 and response.text.strip() == "pong":
                        discovered_port = test_port
                        break
                except requests.RequestException:
                    continue
            
            if discovered_port:
                port = discovered_port
                self.watch_ports[ip] = port
                self.controller.watch_ports[ip] = port
            else:
                port = self.default_port
        
        config = WatchConfig(
            name=name, 
            ip=ip, 
            port=port, 
            timeout=timeout or self.timeout
        )
        connection = WatchConnection(config)
        
        # Test initial connection
        if connection.ping():
            self.watches[name] = connection
            logger.info(f"✅ Watch '{name}' added and connected ({ip}:{port})")
            return True
        else:
            logger.warning(f"⚠️  Watch '{name}' added but not connected ({ip}:{port})")
            if connection.last_error:
                logger.warning(f"   Error: {connection.last_error}")
            self.watches[name] = connection  # Add anyway for later retry
            return False
    
    def start_monitoring(self):
        """Start background monitoring of watch connections."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("📡 Started watch connection monitoring")
    
    def stop_monitoring_thread(self):
        """Stop background monitoring."""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        logger.info("📡 Stopped watch connection monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while not self.stop_monitoring:
            current_time = time.time()
            
            # Ping all watches every 10 seconds
            if current_time - self.last_sync_time > 10.0:
                for watch in self.watches.values():
                    if not watch.is_connected or current_time - watch.last_ping_time > 30.0:
                        watch.ping()
                
                self.last_sync_time = current_time
            
            time.sleep(1.0)
    
    def synchronized_recording_session(self, duration: float) -> bool:
        """
        Perform a synchronized recording session (from integration guide).
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            True if session completed successfully
        """
        logger.info(f"Starting synchronized recording session ({duration}s)")
        
        # Create session directory
        self.session_start_time = datetime.now()
        session_name = f"imu_session_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.join(self.output_dir, session_name)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Use the controller for synchronized recording
        success = self.controller.synchronized_recording_session(duration)
        
        if success:
            self.is_recording = False
            self.total_recordings += 1
            # Retrieve data from watches
            self._retrieve_imu_data()
        
        return success
    
    def start_recording(self) -> bool:
        """
        Start IMU recording on all connected watches.
        
        Returns:
            bool: True if recording started successfully on at least one watch
        """
        if self.is_recording:
            logger.warning("Recording already in progress")
            return True
        
        logger.info("Starting IMU recording on all watches...")
        
        # Create session directory
        self.session_start_time = datetime.now()
        session_name = f"imu_session_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.join(self.output_dir, session_name)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Use controller if available and has watches configured
        if self.controller.watch_ports:
            success = self.controller.start_recording_all()
            if success:
                self.is_recording = True
            return success
        
        # Fallback to individual watch connections
        success_count = 0
        failed_watches = []
        
        # Send start command to all watches
        for name, watch in self.watches.items():
            success, response = watch.send_command("start")
            if success:
                logger.info(f"✅ Started recording on {name} watch ({watch.config.ip})")
                success_count += 1
            else:
                logger.error(f"❌ Failed to start recording on {name} watch ({watch.config.ip})")
                logger.error(f"   Error: {response}")
                failed_watches.append(name)
        
        if success_count > 0:
            self.is_recording = True
            logger.info(f"🎬 IMU recording started on {success_count}/{len(self.watches)} watches")
            if failed_watches:
                logger.warning(f"⚠️  Failed watches: {', '.join(failed_watches)}")
            return True
        else:
            logger.error("❌ Failed to start recording on any watch")
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop IMU recording on all watches.
        
        Returns:
            bool: True if recording stopped successfully
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return True
        
        logger.info("Stopping IMU recording on all watches...")
        
        # Use controller if available and has watches configured
        if self.controller.watch_ports:
            success = self.controller.stop_recording_all()
            if success:
                self.is_recording = False
                self.total_recordings += 1
                # Retrieve data from watches
                self._retrieve_imu_data()
            return success
        
        # Fallback to individual watch connections
        success_count = 0
        failed_watches = []
        
        # Send stop command to all watches
        for name, watch in self.watches.items():
            success, response = watch.send_command("stop")
            if success:
                logger.info(f"✅ Stopped recording on {name} watch ({watch.config.ip})")
                success_count += 1
            else:
                logger.error(f"❌ Failed to stop recording on {name} watch ({watch.config.ip})")
                logger.error(f"   Error: {response}")
                failed_watches.append(name)
        
        self.is_recording = False
        self.total_recordings += 1
        
        if success_count > 0:
            logger.info(f"🛑 IMU recording stopped on {success_count}/{len(self.watches)} watches")
            if failed_watches:
                logger.warning(f"⚠️  Failed watches: {', '.join(failed_watches)}")
            
            # Retrieve data from watches
            self._retrieve_imu_data()
            return True
        else:
            logger.error("❌ Failed to stop recording on any watch")
            return False
    
    def _retrieve_imu_data(self):
        """Retrieve IMU data from all watches after recording stops."""
        if not self.session_dir:
            logger.error("No session directory available for data retrieval")
            return
        
        logger.info("📥 Retrieving IMU data from watches...")
        
        # Try to retrieve from controller first
        if self.controller.watch_ports:
            for ip in self.controller.watch_ports:
                self._retrieve_from_ip(ip)
        
        # Also try individual watch connections
        for name, watch in self.watches.items():
            if not watch.is_connected:
                logger.warning(f"Skipping data retrieval from disconnected {name} watch")
                continue
            
            try:
                # Request data from watch
                response = requests.get(
                    watch.config.get_url("/data"), 
                    timeout=10.0  # Longer timeout for data transfer
                )
                
                if response.status_code == 200:
                    # Save data to CSV file
                    filename = f"{name}_watch_imu.csv"
                    filepath = os.path.join(self.session_dir, filename)
                    
                    # Parse JSON data and save as CSV
                    try:
                        imu_data = response.json()
                        self._save_imu_data_to_csv(imu_data, filepath, name)
                        logger.info(f"✅ Retrieved IMU data from {name} watch: {filepath}")
                    except json.JSONDecodeError:
                        # Fallback: save raw response
                        with open(filepath.replace('.csv', '.txt'), 'w') as f:
                            f.write(response.text)
                        logger.warning(f"⚠️  Saved raw data from {name} watch (JSON parse failed)")
                        
                else:
                    logger.error(f"Failed to retrieve data from {name} watch: HTTP {response.status_code}")
                    
            except requests.RequestException as e:
                logger.error(f"Error retrieving data from {name} watch: {e}")
    
    def _retrieve_from_ip(self, ip: str):
        """Retrieve data from a specific IP address."""
        try:
            port = self.controller.watch_ports.get(ip, self.default_port)
            url = f"http://{ip}:{port}/data"
            response = requests.get(url, timeout=10.0)
            
            if response.status_code == 200:
                # Save data to CSV file
                filename = f"watch_{ip.replace('.', '_')}_imu.csv"
                filepath = os.path.join(self.session_dir, filename)
                
                try:
                    imu_data = response.json()
                    self._save_imu_data_to_csv(imu_data, filepath, f"watch_{ip}")
                    logger.info(f"✅ Retrieved IMU data from {ip}: {filepath}")
                except json.JSONDecodeError:
                    # Fallback: save raw response
                    with open(filepath.replace('.csv', '.txt'), 'w') as f:
                        f.write(response.text)
                    logger.warning(f"⚠️  Saved raw data from {ip} (JSON parse failed)")
            else:
                logger.error(f"Failed to retrieve data from {ip}: HTTP {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Error retrieving data from {ip}: {e}")
    
    def _save_imu_data_to_csv(self, imu_data: List[Dict], filepath: str, watch_name: str):
        """Save IMU data to CSV file with magnetometer support."""
        if not imu_data:
            logger.warning(f"No IMU data received from {watch_name} watch")
            return
        
        with open(filepath, 'w', newline='') as csvfile:
            # Include magnetometer fields as per integration guide
            fieldnames = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 
                         'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z', 'watch_name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header with session metadata
            csvfile.write(f"# Session ID: {self.session_start_time.strftime('%Y%m%d_%H%M%S')}\n")
            csvfile.write(f"# Device ID: {watch_name}\n")
            csvfile.write(f"# Start Time: {int(self.session_start_time.timestamp() * 1000)}\n")
            csvfile.write(f"# Sample Count: {len(imu_data)}\n")
            csvfile.write(f"# Generated by Watch IMU Recorder\n")
            
            writer.writeheader()
            for reading in imu_data:
                # Ensure all required fields are present
                row = {
                    'timestamp': reading.get('timestamp', 0),
                    'accel_x': reading.get('accel_x', 0),
                    'accel_y': reading.get('accel_y', 0),
                    'accel_z': reading.get('accel_z', 0),
                    'gyro_x': reading.get('gyro_x', 0),
                    'gyro_y': reading.get('gyro_y', 0),
                    'gyro_z': reading.get('gyro_z', 0),
                    'mag_x': reading.get('mag_x', 0),
                    'mag_y': reading.get('mag_y', 0),
                    'mag_z': reading.get('mag_z', 0),
                    'watch_name': watch_name
                }
                writer.writerow(row)
        
        logger.info(f"📊 Saved {len(imu_data)} IMU readings to {filepath}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all watch connections."""
        status = {
            'total_watches': len(self.watches),
            'connected_watches': sum(1 for w in self.watches.values() if w.is_connected),
            'recording': self.is_recording,
            'total_recordings': self.total_recordings,
            'session_dir': self.session_dir,
            'watches': {}
        }
        
        for name, watch in self.watches.items():
            status['watches'][name] = watch.get_status()
        
        return status
    
    def print_status(self):
        """Print current status to console."""
        status = self.get_connection_status()
        
        logger.info(f"\n📱 WATCH IMU STATUS")
        logger.info(f"   Connected: {status['connected_watches']}/{status['total_watches']} watches")
        logger.info(f"   Recording: {'Yes' if status['recording'] else 'No'}")
        logger.info(f"   Total Sessions: {status['total_recordings']}")
        
        for name, watch_status in status['watches'].items():
            conn_status = "🟢" if watch_status['connected'] else "🔴"
            rec_status = "🎬" if watch_status['recording'] else "⏸️"
            logger.info(f"   {conn_status} {rec_status} {name.upper()} ({watch_status['ip']})")
            if watch_status['last_error']:
                logger.info(f"      Error: {watch_status['last_error']}")
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up Watch IMU Manager...")
        
        # Stop recording if in progress
        if self.is_recording:
            self.stop_recording()
        
        # Stop monitoring
        self.stop_monitoring_thread()
        
        # Clear connections
        self.watches.clear()
        
        logger.info("✅ Watch IMU Manager cleanup complete")


def record_video_and_imu(duration: float, video_output: str, watch_ips: List[str]):
    """
    Record video and IMU data simultaneously (from integration guide).
    
    Args:
        duration: Recording duration in seconds
        video_output: Output video file path
        watch_ips: List of watch IP addresses
    """
    manager = WatchIMUManager(watch_ips)
    manager.discover_watches()
    
    # Start IMU recording
    logger.info("Starting IMU recording...")
    if not manager.start_recording():
        logger.error("Failed to start IMU recording")
        return False
    
    # Start video recording (example using ffmpeg)
    import subprocess
    video_cmd = [
        "ffmpeg", "-f", "v4l2", "-i", "/dev/video0",
        "-t", str(duration), "-y", video_output
    ]
    
    logger.info("Starting video recording...")
    video_process = subprocess.Popen(video_cmd)
    
    # Wait for recording to complete
    video_process.wait()
    
    # Stop IMU recording
    logger.info("Stopping IMU recording...")
    manager.stop_recording()
    
    logger.info("Synchronized recording completed")
    return True


def retrieve_imu_files(output_dir: str = "./imu_data"):
    """
    Retrieve IMU CSV files from connected watches via ADB (from integration guide).
    
    Args:
        output_dir: Local directory to save files
    """
    import subprocess
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of connected devices
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    devices = []
    
    for line in result.stdout.split('\n')[1:]:
        if '\tdevice' in line:
            devices.append(line.split('\t')[0])
    
    logger.info(f"Found {len(devices)} connected devices")
    
    for device in devices:
        logger.info(f"Retrieving files from device: {device}")
        
        # List files on device
        list_cmd = [
            "adb", "-s", device, "shell", "ls",
            "/Android/data/com.example.watchimurecorder/files/recordings/"
        ]
        
        result = subprocess.run(list_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            
            for file in files:
                if file.endswith('.csv'):
                    # Pull file from device
                    remote_path = f"/Android/data/com.example.watchimurecorder/files/recordings/{file}"
                    local_path = os.path.join(output_dir, f"{device}_{file}")
                    
                    pull_cmd = ["adb", "-s", device, "pull", remote_path, local_path]
                    subprocess.run(pull_cmd)
                    
                    logger.info(f"Retrieved: {local_path}")
        else:
            logger.warning(f"Could not access files on device: {device}")


def debug_watch(ip: str, port: int = 8080):
    """Debug connectivity to a single watch (from integration guide)."""
    endpoints = ["ping", "status"]
    
    for endpoint in endpoints:
        try:
            url = f"http://{ip}:{port}/{endpoint}"
            response = requests.get(url, timeout=5)
            print(f"{endpoint}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"{endpoint}: ERROR - {e}")


def record_juggling_session():
    """
    Complete example: Record juggling session with synchronized IMU data (from integration guide).
    """
    # Your watch IP addresses (get these from the watch screens)
    WATCH_IPS = ["192.168.1.101", "192.168.1.102"]
    
    # Create manager
    manager = WatchIMUManager(WATCH_IPS)
    
    # Discover watches
    active_watches = manager.discover_watches()
    print(f"Found {len(active_watches)} active watches")
    
    if len(active_watches) < 2:
        print("Need at least 2 watches for juggling analysis")
        return
    
    # Record 30-second juggling session
    print("Starting juggling recording session...")
    print("Get ready to juggle!")
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("START JUGGLING!")
    
    # Start synchronized recording
    success = manager.synchronized_recording_session(duration=30.0)
    
    if success:
        print("Recording completed successfully!")
        print("Files saved on watches. Use ADB to retrieve them.")
    else:
        print("Recording failed. Check watch connections.")


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    WATCH_IPS = ["192.168.1.101", "192.168.1.102"]
    manager = WatchIMUManager(WATCH_IPS)
    
    # Add watches manually (replace with actual IPs)
    manager.add_watch("left", "192.168.1.101")
    manager.add_watch("right", "192.168.1.102")
    
    # Or discover watches automatically
    discovered = manager.discover_watches()
    
    # Start monitoring
    manager.start_monitoring()
    
    try:
        # Test recording
        print("Testing IMU recording...")
        manager.print_status()
        
        if manager.synchronized_recording_session(duration=10.0):
            print("Synchronized recording session completed!")
        
        manager.print_status()
        
    except KeyboardInterrupt:
        print("\nShutdown requested")
    finally:
        manager.cleanup()