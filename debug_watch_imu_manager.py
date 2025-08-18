#!/usr/bin/env python3
"""
Debug-Instrumented Watch IMU Manager

This is the existing watch_imu_manager.py with comprehensive debug logging
to identify exactly where lag is occurring in the real application.

Author: Generated for JugVid2 project
Date: 2025-08-18
"""

import requests
import time
import threading
import json
import os
import sys
import asyncio
import websockets
from queue import Queue, Empty
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import socket
import csv
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our debug system
from debug_imu_performance import (
    debug_timing, debug_thread, DebugContext, 
    log_data_flow, log_queue_status, log_websocket_event, log_ui_event,
    perf_logger, enable_debug_mode
)

# Enable debug mode if environment variable is set
if os.environ.get('IMU_DEBUG', '0') == '1':
    enable_debug_mode()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DebugIMUStreamHandler:
    """Debug-instrumented IMU stream handler."""

    def __init__(self, watch_ips: List[str], data_queue: Queue):
        self.watch_ips = watch_ips
        self.data_queue = data_queue
        self.websocket_port = 8081
        self.stop_signal = asyncio.Event()
        
        # Debug counters
        self.message_count = 0
        self.conversion_count = 0
        self.queue_put_count = 0
        self.last_debug_time = time.time()
        
        perf_logger.logger.info(f"🔍 DebugIMUStreamHandler initialized with {len(watch_ips)} IPs")

    @debug_timing("websocket_listen")
    async def _listen_to_watch(self, ip: str):
        """Debug-instrumented watch listener."""
        uri = f"ws://{ip}:{self.websocket_port}/imu"
        partial_data = {}
        
        perf_logger.logger.info(f"🌐 Starting WebSocket connection to {uri}")
        
        while not self.stop_signal.is_set():
            try:
                with DebugContext(f"websocket_connection_{ip}"):
                    async with websockets.connect(uri) as websocket:
                        log_websocket_event("connected", {"ip": ip, "uri": uri})
                        
                        while not self.stop_signal.is_set():
                            with DebugContext("websocket_receive"):
                                message = await websocket.recv()
                                self.message_count += 1
                                
                                # Log message rate every 100 messages
                                if self.message_count % 100 == 0:
                                    current_time = time.time()
                                    rate = 100 / (current_time - self.last_debug_time)
                                    perf_logger.logger.info(f"📊 WebSocket rate: {rate:.1f} msg/sec from {ip}")
                                    self.last_debug_time = current_time
                                
                                log_data_flow("websocket_receive", 1, "messages")
                            
                            try:
                                with DebugContext("json_parse"):
                                    raw_data = json.loads(message)
                                
                                with DebugContext("format_conversion"):
                                    converted_data = self._convert_android_format(raw_data, ip, partial_data)
                                    
                                if converted_data:
                                    self.conversion_count += 1
                                    
                                    with DebugContext("queue_put"):
                                        try:
                                            self.data_queue.put_nowait(converted_data)
                                            self.queue_put_count += 1
                                            log_queue_status("imu_data_queue", self.data_queue.qsize(), self.data_queue.maxsize)
                                        except:
                                            perf_logger.logger.warning(f"⚠️  Queue full! Dropping data from {ip}")
                                            log_queue_status("imu_data_queue_FULL", self.data_queue.qsize(), self.data_queue.maxsize)
                                            
                            except json.JSONDecodeError as e:
                                perf_logger.logger.warning(f"⚠️  JSON decode error from {ip}: {e}")
                                
            except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError, OSError) as e:
                log_websocket_event("connection_failed", {"ip": ip, "error": str(e)})
                perf_logger.logger.error(f"❌ WebSocket connection to {ip} failed: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                perf_logger.logger.error(f"❌ Unexpected error with WebSocket for {ip}: {e}")
                await asyncio.sleep(5)

    @debug_timing("android_format_conversion")
    def _convert_android_format(self, raw_data: dict, ip: str, partial_data: dict) -> dict:
        """Debug-instrumented format conversion."""
        try:
            with DebugContext("extract_fields"):
                watch_id = raw_data.get('watch_id', 'unknown')
                data_type = raw_data.get('type', 'unknown')
                timestamp_ns = raw_data.get('timestamp_ns', 0)
                timestamp_s = timestamp_ns / 1_000_000_000.0
                
                x = raw_data.get('x', 0.0)
                y = raw_data.get('y', 0.0)
                z = raw_data.get('z', 0.0)
                
                watch_name = watch_id.replace('_watch', '') if '_watch' in watch_id else watch_id
                timestamp_key = f"{ip}_{timestamp_ns}"
            
            with DebugContext("partial_data_management"):
                if timestamp_key not in partial_data:
                    partial_data[timestamp_key] = {
                        'timestamp': timestamp_s,
                        'watch_name': watch_name,
                        'watch_ip': ip,
                        'received_at': time.time(),
                        'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
                        'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0,
                        'mag_x': 0.0, 'mag_y': 0.0, 'mag_z': 0.0,
                        'has_accel': False, 'has_gyro': False
                    }
                
                current_data = partial_data[timestamp_key]
                
                # Fill in data based on type
                if data_type == 'accel':
                    current_data['accel_x'] = x
                    current_data['accel_y'] = y
                    current_data['accel_z'] = z
                    current_data['has_accel'] = True
                elif data_type == 'gyro':
                    current_data['gyro_x'] = x
                    current_data['gyro_y'] = y
                    current_data['gyro_z'] = z
                    current_data['has_gyro'] = True
                elif data_type == 'mag':
                    current_data['mag_x'] = x
                    current_data['mag_y'] = y
                    current_data['mag_z'] = z
            
            with DebugContext("completion_check"):
                # Return complete data if we have both accel and gyro
                if current_data['has_accel'] and current_data['has_gyro']:
                    complete_data = partial_data.pop(timestamp_key)
                    del complete_data['has_accel']
                    del complete_data['has_gyro']
                    log_data_flow("complete_reading", 1, "readings")
                    return complete_data
                elif current_data['has_accel']:
                    # Return accel data immediately for real-time streaming
                    temp_data = current_data.copy()
                    del temp_data['has_accel']
                    del temp_data['has_gyro']
                    log_data_flow("partial_reading", 1, "readings")
                    return temp_data
            
            with DebugContext("cleanup_partial_data"):
                # Clean up old partial data
                current_time = time.time()
                keys_to_remove = []
                for key, data in partial_data.items():
                    if current_time - data['received_at'] > 1.0:
                        keys_to_remove.append(key)
                
                if keys_to_remove:
                    perf_logger.logger.debug(f"🧹 Cleaning up {len(keys_to_remove)} old partial data entries")
                    for key in keys_to_remove:
                        partial_data.pop(key, None)
                
                # Log partial data size if it's growing
                if len(partial_data) > 50:
                    perf_logger.logger.warning(f"⚠️  Large partial_data dict: {len(partial_data)} entries")
            
            return None
            
        except Exception as e:
            perf_logger.logger.error(f"❌ Error converting Android format from {ip}: {e}")
            return None

    @debug_thread("websocket_main")
    async def _main(self):
        """Debug-instrumented main asyncio task."""
        with DebugContext("websocket_main_setup"):
            tasks = [self._listen_to_watch(ip) for ip in self.watch_ips]
            perf_logger.logger.info(f"🚀 Starting {len(tasks)} WebSocket listener tasks")
        
        await asyncio.gather(*tasks)

    @debug_thread("websocket_thread")
    def run_in_thread(self):
        """Debug-instrumented thread runner."""
        perf_logger.logger.info("🧵 Starting IMU Stream Handler thread...")
        try:
            asyncio.run(self._main())
        except Exception as e:
            perf_logger.logger.error(f"❌ IMU Stream Handler thread failed: {e}")
        finally:
            perf_logger.logger.info("🧵 IMU Stream Handler thread finished.")

class DebugWatchIMUManager:
    """Debug-instrumented Watch IMU Manager."""
    
    def __init__(self, watch_ips: List[str] = None, output_dir: str = "imu_data", 
                 default_port: int = 8080, timeout: int = 5):
        with DebugContext("watch_imu_manager_init", log_memory=True):
            self.watch_ips = watch_ips or []
            self.output_dir = output_dir
            self.default_port = default_port
            self.timeout = timeout
            
            # Setup for real-time data streaming
            self.imu_data_queue = Queue(maxsize=1000)
            self.stream_handler = DebugIMUStreamHandler(self.watch_ips, self.imu_data_queue)
            self.streaming_thread: Optional[threading.Thread] = None

            self.session_start_time: Optional[datetime] = None
            self.session_dir: Optional[str] = None
            self.is_recording = False
            
            # Debug counters
            self.data_retrieval_count = 0
            self.last_data_time = time.time()
            
            os.makedirs(output_dir, exist_ok=True)
            
            perf_logger.logger.info(f"🔍 DebugWatchIMUManager initialized with {len(self.watch_ips)} watch IPs")
    
    @debug_timing("start_streaming")
    def start_streaming(self):
        """Debug-instrumented streaming start."""
        if not self.watch_ips:
            perf_logger.logger.warning("⚠️  No watch IPs configured. Cannot start streaming.")
            return

        if self.streaming_thread and self.streaming_thread.is_alive():
            perf_logger.logger.info("ℹ️  IMU streaming thread already running.")
            return

        with DebugContext("streaming_thread_setup"):
            self.stream_handler.stop_signal.clear()
            self.streaming_thread = threading.Thread(
                target=self.stream_handler.run_in_thread, 
                daemon=True,
                name="IMU-Stream"
            )
            self.streaming_thread.start()
            
        perf_logger.logger.info("🚀 Real-time IMU streaming started.")

    @debug_timing("get_latest_imu_data")
    def get_latest_imu_data(self) -> List[Dict]:
        """Debug-instrumented data retrieval."""
        data_points = []
        
        with DebugContext("queue_drain"):
            items_retrieved = 0
            while not self.imu_data_queue.empty():
                try:
                    with DebugContext("queue_get"):
                        data_point = self.imu_data_queue.get_nowait()
                        data_points.append(data_point)
                        items_retrieved += 1
                        
                        # Log high-frequency data retrieval
                        if items_retrieved > 50:
                            perf_logger.logger.warning(f"⚠️  HIGH VOLUME: Retrieved {items_retrieved} items in single call")
                            
                except Empty:
                    break
            
            if items_retrieved > 0:
                self.data_retrieval_count += items_retrieved
                current_time = time.time()
                
                # Log data rate every 100 items
                if self.data_retrieval_count % 100 == 0:
                    rate = 100 / (current_time - self.last_data_time)
                    perf_logger.logger.info(f"📊 Data retrieval rate: {rate:.1f} items/sec")
                    self.last_data_time = current_time
                
                log_data_flow("data_retrieval", items_retrieved, "items")
                log_queue_status("after_retrieval", self.imu_data_queue.qsize(), self.imu_data_queue.maxsize)
        
        return data_points
    
    @debug_timing("cleanup")
    def cleanup(self):
        """Debug-instrumented cleanup."""
        perf_logger.logger.info("🧹 Cleaning up Debug Watch IMU Manager...")
        
        with DebugContext("streaming_cleanup"):
            if self.streaming_thread and self.streaming_thread.is_alive():
                self.stream_handler.stop_signal.set()
                self.streaming_thread.join(timeout=2.0)
        
        with DebugContext("queue_cleanup"):
            # Clear the queue
            items_cleared = 0
            while not self.imu_data_queue.empty():
                try:
                    self.imu_data_queue.get_nowait()
                    items_cleared += 1
                except Empty:
                    break
            
            if items_cleared > 0:
                perf_logger.logger.info(f"🧹 Cleared {items_cleared} items from queue")
        
        # Print final performance report
        from debug_imu_performance import print_performance_report
        print_performance_report()
        
        perf_logger.logger.info("✅ Debug Watch IMU Manager cleanup complete")

# Monkey patch the original classes for debugging
def enable_debug_imu_manager():
    """Replace the original IMU manager with debug version."""
    import watch_imu_manager
    
    # Replace classes with debug versions
    watch_imu_manager.IMUStreamHandler = DebugIMUStreamHandler
    watch_imu_manager.WatchIMUManager = DebugWatchIMUManager
    
    perf_logger.logger.info("🔍 Debug IMU Manager ENABLED - Original classes replaced")

# Example usage
if __name__ == "__main__":
    # Enable debug mode
    enable_debug_mode()
    
    # Test the debug system
    watch_ips = ["127.0.0.1", "127.0.0.1"]
    manager = DebugWatchIMUManager(watch_ips)
    
    try:
        manager.start_streaming()
        
        # Simulate data retrieval
        for i in range(10):
            time.sleep(1)
            data = manager.get_latest_imu_data()
            print(f"Retrieved {len(data)} items")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        manager.cleanup()