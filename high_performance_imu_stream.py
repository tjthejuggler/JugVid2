#!/usr/bin/env python3
"""
High-Performance IMU Streaming Manager

This module implements a complete rewrite of the IMU streaming system optimized for:
- Ultra-low latency (<5ms)
- High throughput (1000+ Hz per watch)
- Minimal CPU usage
- Lock-free data structures
- Memory pooling

Author: Generated for JugVid2 project
Date: 2025-08-18
Version: 2.0 (High-Performance Rewrite)
"""

import asyncio
import websockets
import struct
import time
import threading
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from collections import deque
from dataclasses import dataclass
import numpy as np
from queue import Empty
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IMUReading:
    """Optimized IMU reading structure."""
    timestamp: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    watch_id: int  # 0=left, 1=right for faster processing
    sequence: int  # For detecting dropped packets

class LockFreeRingBuffer:
    """Lock-free ring buffer optimized for single producer, single consumer."""
    
    def __init__(self, capacity: int = 8192):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.write_pos = 0
        self.read_pos = 0
        self.size = 0
        
    def put(self, item) -> bool:
        """Put item in buffer. Returns False if buffer is full."""
        if self.size >= self.capacity:
            return False
            
        self.buffer[self.write_pos] = item
        self.write_pos = (self.write_pos + 1) % self.capacity
        self.size += 1
        return True
        
    def get(self):
        """Get item from buffer. Returns None if buffer is empty."""
        if self.size == 0:
            return None
            
        item = self.buffer[self.read_pos]
        self.buffer[self.read_pos] = None  # Help GC
        self.read_pos = (self.read_pos + 1) % self.capacity
        self.size -= 1
        return item
        
    def get_batch(self, max_items: int = 100) -> List:
        """Get multiple items at once for batch processing."""
        items = []
        for _ in range(min(max_items, self.size)):
            item = self.get()
            if item is None:
                break
            items.append(item)
        return items
        
    def is_empty(self) -> bool:
        return self.size == 0
        
    def is_full(self) -> bool:
        return self.size >= self.capacity
        
    def clear(self):
        """Clear all items from buffer."""
        while not self.is_empty():
            self.get()

class MemoryPool:
    """Memory pool for IMU readings to reduce allocations."""
    
    def __init__(self, pool_size: int = 1000):
        self.pool = deque()
        self.pool_size = pool_size
        
        # Pre-allocate objects
        for _ in range(pool_size):
            self.pool.append(IMUReading(0, 0, 0, 0, 0, 0, 0, 0, 0))
    
    def get(self) -> IMUReading:
        """Get a reusable IMU reading object."""
        if self.pool:
            return self.pool.popleft()
        else:
            # Pool exhausted, create new object
            return IMUReading(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def put(self, reading: IMUReading):
        """Return an IMU reading object to the pool."""
        if len(self.pool) < self.pool_size:
            # Reset the object
            reading.timestamp = 0
            reading.accel_x = reading.accel_y = reading.accel_z = 0
            reading.gyro_x = reading.gyro_y = reading.gyro_z = 0
            reading.watch_id = 0
            reading.sequence = 0
            self.pool.append(reading)

class FastDataConverter:
    """Optimized data converter with minimal allocations."""
    
    def __init__(self):
        self.watch_id_map = {"left_watch": 0, "right_watch": 1}
        self.pending_data = {}  # Much smaller, only current incomplete readings
        self.sequence_counters = [0, 0]  # Per watch sequence counter
        
    def convert_message(self, raw_data: dict, memory_pool: MemoryPool) -> Optional[IMUReading]:
        """Convert Android message to IMU reading with minimal overhead."""
        try:
            watch_name = raw_data.get('watch_id', 'unknown')
            watch_id = self.watch_id_map.get(watch_name, 0)
            data_type = raw_data.get('type', 'unknown')
            timestamp_ns = raw_data.get('timestamp_ns', 0)
            timestamp_s = timestamp_ns * 1e-9  # Faster than division
            
            x = raw_data.get('x', 0.0)
            y = raw_data.get('y', 0.0)
            z = raw_data.get('z', 0.0)
            
            # Use timestamp as key for combining data
            key = (watch_id, timestamp_ns)
            
            if key not in self.pending_data:
                # Get object from memory pool
                reading = memory_pool.get()
                reading.timestamp = timestamp_s
                reading.watch_id = watch_id
                reading.sequence = self.sequence_counters[watch_id]
                self.sequence_counters[watch_id] += 1
                self.pending_data[key] = reading
            else:
                reading = self.pending_data[key]
            
            # Fill in data based on type
            if data_type == 'accel':
                reading.accel_x = x
                reading.accel_y = y
                reading.accel_z = z
            elif data_type == 'gyro':
                reading.gyro_x = x
                reading.gyro_y = y
                reading.gyro_z = z
            
            # Check if we have complete data (both accel and gyro)
            if (reading.accel_x != 0 or reading.accel_y != 0 or reading.accel_z != 0) and \
               (reading.gyro_x != 0 or reading.gyro_y != 0 or reading.gyro_z != 0):
                # Complete reading, remove from pending and return
                complete_reading = self.pending_data.pop(key)
                return complete_reading
            
            # Cleanup old pending data (keep only last 10 entries per watch)
            if len(self.pending_data) > 20:
                self._cleanup_pending_data(memory_pool)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in fast conversion: {e}")
            return None
    
    def _cleanup_pending_data(self, memory_pool: MemoryPool):
        """Clean up old pending data entries."""
        current_time = time.time()
        keys_to_remove = []
        
        for key, reading in self.pending_data.items():
            if current_time - reading.timestamp > 0.1:  # 100ms old
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            old_reading = self.pending_data.pop(key)
            memory_pool.put(old_reading)

class HighPerformanceStreamHandler:
    """High-performance WebSocket stream handler."""
    
    def __init__(self, watch_ips: List[str], ring_buffer: LockFreeRingBuffer):
        self.watch_ips = watch_ips
        self.ring_buffer = ring_buffer
        self.websocket_port = 8081
        self.running = False
        self.memory_pool = MemoryPool(2000)  # Larger pool for high throughput
        self.converter = FastDataConverter()
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'buffer_overflows': 0,
            'conversion_errors': 0
        }
        
    async def connect_and_stream(self, ip: str):
        """Connect to watch and stream data with optimized processing."""
        uri = f"ws://{ip}:{self.websocket_port}/imu"
        
        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as websocket:
                    logger.info(f"🚀 High-perf connection established: {uri}")
                    
                    # Batch processing variables
                    batch_buffer = []
                    last_batch_time = time.time()
                    
                    while self.running:
                        try:
                            # Receive message
                            message = await websocket.recv()
                            self.stats['messages_received'] += 1
                            
                            # Parse JSON (unavoidable with current watch protocol)
                            raw_data = json.loads(message)
                            
                            # Convert to optimized format
                            reading = self.converter.convert_message(raw_data, self.memory_pool)
                            
                            if reading:
                                batch_buffer.append(reading)
                                self.stats['messages_processed'] += 1
                                
                                # Process batch when it's full or timeout reached
                                current_time = time.time()
                                if len(batch_buffer) >= 10 or (current_time - last_batch_time) > 0.01:
                                    self._process_batch(batch_buffer)
                                    batch_buffer.clear()
                                    last_batch_time = current_time
                                    
                        except json.JSONDecodeError:
                            self.stats['conversion_errors'] += 1
                            continue
                            
                    # Process remaining batch
                    if batch_buffer:
                        self._process_batch(batch_buffer)
                        
            except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError, OSError) as e:
                if self.running:
                    logger.warning(f"Connection lost to {ip}, retrying in 2s: {e}")
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Unexpected error with {ip}: {e}")
                await asyncio.sleep(2)
    
    def _process_batch(self, batch: List[IMUReading]):
        """Process a batch of readings efficiently."""
        for reading in batch:
            if not self.ring_buffer.put(reading):
                # Buffer full, return reading to pool
                self.memory_pool.put(reading)
                self.stats['buffer_overflows'] += 1
    
    async def start_streaming(self):
        """Start streaming from all watches."""
        self.running = True
        tasks = [self.connect_and_stream(ip) for ip in self.watch_ips]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop_streaming(self):
        """Stop streaming."""
        self.running = False
    
    def get_stats(self) -> Dict[str, int]:
        """Get performance statistics."""
        return self.stats.copy()

class HighPerformanceIMUManager:
    """High-performance IMU manager with optimized data pipeline."""
    
    def __init__(self, watch_ips: List[str] = None, buffer_size: int = 8192):
        self.watch_ips = watch_ips or []
        self.ring_buffer = LockFreeRingBuffer(buffer_size)
        self.stream_handler = HighPerformanceStreamHandler(self.watch_ips, self.ring_buffer)
        self.streaming_task = None
        self.processing_thread = None
        self.running = False
        
        # Application interface
        self.latest_data = {}  # Latest data per watch for application
        self.data_callbacks = []  # Callbacks for real-time data
        
        # Performance monitoring
        self.performance_stats = {
            'data_rate': 0.0,
            'latency_ms': 0.0,
            'buffer_usage': 0.0,
            'dropped_packets': 0
        }
        
    def add_data_callback(self, callback):
        """Add callback for real-time data updates."""
        self.data_callbacks.append(callback)
    
    def start_streaming(self):
        """Start high-performance streaming."""
        if self.running:
            return
            
        self.running = True
        
        # Start WebSocket streaming in asyncio thread
        self.streaming_task = threading.Thread(target=self._run_streaming_loop, daemon=True)
        self.streaming_task.start()
        
        # Start data processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        logger.info("🚀 High-performance IMU streaming started")
    
    def stop_streaming(self):
        """Stop streaming."""
        self.running = False
        self.stream_handler.stop_streaming()
        
        if self.streaming_task:
            self.streaming_task.join(timeout=2.0)
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            
        logger.info("🛑 High-performance IMU streaming stopped")
    
    def _run_streaming_loop(self):
        """Run asyncio streaming loop in separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.stream_handler.start_streaming())
        except Exception as e:
            logger.error(f"Streaming loop error: {e}")
        finally:
            loop.close()
    
    def _processing_loop(self):
        """High-performance data processing loop."""
        last_stats_time = time.time()
        data_count = 0
        
        while self.running:
            try:
                # Process data in batches for efficiency
                batch = self.ring_buffer.get_batch(50)
                
                if batch:
                    self._process_data_batch(batch)
                    data_count += len(batch)
                    
                    # Update performance stats
                    current_time = time.time()
                    if current_time - last_stats_time >= 1.0:
                        self.performance_stats['data_rate'] = data_count / (current_time - last_stats_time)
                        self.performance_stats['buffer_usage'] = (self.ring_buffer.size / self.ring_buffer.capacity) * 100
                        data_count = 0
                        last_stats_time = current_time
                else:
                    # No data available, short sleep to prevent busy waiting
                    time.sleep(0.001)  # 1ms
                    
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                time.sleep(0.01)
    
    def _process_data_batch(self, batch: List[IMUReading]):
        """Process a batch of IMU readings."""
        current_time = time.time()
        
        for reading in batch:
            # Calculate latency
            latency_ms = (current_time - reading.timestamp) * 1000
            self.performance_stats['latency_ms'] = latency_ms
            
            # Update latest data for application
            watch_name = "left" if reading.watch_id == 0 else "right"
            self.latest_data[watch_name] = {
                'timestamp': reading.timestamp,
                'accel': (reading.accel_x, reading.accel_y, reading.accel_z),
                'gyro': (reading.gyro_x, reading.gyro_y, reading.gyro_z),
                'accel_magnitude': np.sqrt(reading.accel_x**2 + reading.accel_y**2 + reading.accel_z**2),
                'gyro_magnitude': np.sqrt(reading.gyro_x**2 + reading.gyro_y**2 + reading.gyro_z**2),
                'data_age': latency_ms / 1000.0,
                'sequence': reading.sequence
            }
            
            # Call registered callbacks
            for callback in self.data_callbacks:
                try:
                    callback(watch_name, self.latest_data[watch_name])
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            # Return reading to memory pool
            self.stream_handler.memory_pool.put(reading)
    
    def get_latest_data(self) -> Dict[str, Any]:
        """Get latest IMU data for application integration."""
        return self.latest_data.copy()
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        stats = self.performance_stats.copy()
        stream_stats = self.stream_handler.get_stats()
        stats.update(stream_stats)
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_streaming()
        self.ring_buffer.clear()
        self.latest_data.clear()
        self.data_callbacks.clear()

# Compatibility layer for existing code
class OptimizedWatchIMUManager:
    """Drop-in replacement for existing WatchIMUManager with high performance."""
    
    def __init__(self, watch_ips: List[str] = None, output_dir: str = "imu_data",
                 default_port: int = 8080, timeout: int = 5, **kwargs):
        self.watch_ips = watch_ips or []
        self.output_dir = output_dir
        self.default_port = default_port
        self.timeout = timeout
        self.high_perf_manager = HighPerformanceIMUManager(watch_ips)
        
        # Compatibility properties
        self.is_recording = False
        self.latest_imu_data = {}
        self.watch_ports: Dict[str, int] = {}
        
        # Setup data callback for compatibility
        self.high_perf_manager.add_data_callback(self._update_compatibility_data)
        
        os.makedirs(output_dir, exist_ok=True)
    
    def discover_watches(self) -> Dict[str, int]:
        """
        Discover active watches and their ports (compatibility method).
        
        Returns:
            Dictionary mapping IP addresses to active ports
        """
        logger.info(f"Discovering active watches from list: {self.watch_ips}")
        active_watches = {}
        
        # Ports to try in order
        ports_to_try = [8080, 8081, 8082, 8083, 9090]
        
        for ip in self.watch_ips:
            logger.info(f"Testing connectivity to {ip}...")

            for port in ports_to_try:
                try:
                    import requests
                    url = f"http://{ip}:{port}/ping"
                    # Use a very short timeout to prevent UI freezing
                    response = requests.get(url, timeout=1.0)
                    
                    if response.status_code == 200 and response.text.strip() == "pong":
                        active_watches[ip] = port
                        self.watch_ports[ip] = port
                        logger.info(f"✓ Found active watch at {ip}:{port}")
                        break  # Move to the next IP once a port is found
                        
                except Exception:
                    continue
            
            if ip not in active_watches:
                logger.warning(f"✗ Could not connect to watch at {ip}")
        
        logger.info(f"Discovered {len(active_watches)} active watches")
        return active_watches
    
    def _update_compatibility_data(self, watch_name: str, data: Dict[str, Any]):
        """Update compatibility data structure."""
        self.latest_imu_data[watch_name] = data
    
    def start_streaming(self):
        """Start streaming (compatibility method)."""
        self.high_perf_manager.start_streaming()
    
    def stop_streaming(self):
        """Stop streaming (compatibility method)."""
        self.high_perf_manager.stop_streaming()
    
    def get_latest_imu_data(self) -> List[Dict]:
        """Get latest IMU data (compatibility method)."""
        data_points = []
        for watch_name, data in self.latest_imu_data.items():
            data_point = data.copy()
            data_point['watch_name'] = watch_name
            data_point['watch_ip'] = 'optimized'
            data_point['received_at'] = time.time()
            data_points.append(data_point)
        return data_points
    
    def cleanup(self):
        """Clean up resources."""
        self.high_perf_manager.cleanup()
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        return self.high_perf_manager.get_performance_stats()

if __name__ == "__main__":
    # Test the high-performance streaming
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\nShutting down...")
        manager.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create manager
    watch_ips = ["127.0.0.1", "127.0.0.1"]  # For testing with mock watches
    manager = HighPerformanceIMUManager(watch_ips)
    
    # Add callback to print data
    def print_data(watch_name, data):
        print(f"{watch_name}: A({data['accel'][0]:.3f},{data['accel'][1]:.3f},{data['accel'][2]:.3f}) "
              f"G({data['gyro'][0]:.3f},{data['gyro'][1]:.3f},{data['gyro'][2]:.3f}) "
              f"Latency: {data['data_age']*1000:.1f}ms")
    
    manager.add_data_callback(print_data)
    
    # Start streaming
    manager.start_streaming()
    
    print("High-performance IMU streaming started. Press Ctrl+C to stop.")
    print("Performance stats will be displayed every 5 seconds.")
    
    try:
        while True:
            time.sleep(5)
            stats = manager.get_performance_stats()
            print(f"\n📊 Performance Stats:")
            print(f"   Data Rate: {stats['data_rate']:.1f} Hz")
            print(f"   Latency: {stats['latency_ms']:.1f} ms")
            print(f"   Buffer Usage: {stats['buffer_usage']:.1f}%")
            print(f"   Messages Received: {stats['messages_received']}")
            print(f"   Buffer Overflows: {stats['buffer_overflows']}")
    except KeyboardInterrupt:
        pass
    
    manager.cleanup()