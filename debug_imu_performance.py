#!/usr/bin/env python3
"""
Comprehensive IMU Performance Debug System

This module provides extensive logging and profiling to identify exactly
where lag is occurring in the IMU streaming system.

Author: Generated for JugVid2 project
Date: 2025-08-18
"""

import time
import threading
import functools
import logging
import sys
import traceback
from typing import Dict, Any, List, Optional
from collections import deque, defaultdict
import json
import psutil
import os

# Configure debug logging
class PerformanceLogger:
    """Comprehensive performance logging system."""
    
    def __init__(self, debug_level: str = "INFO"):
        self.debug_enabled = os.environ.get('IMU_DEBUG', '0') == '1'
        self.performance_data = defaultdict(list)
        self.timing_data = defaultdict(deque)
        self.call_counts = defaultdict(int)
        self.thread_data = defaultdict(dict)
        self.start_time = time.time()
        
        # Setup logging
        log_level = getattr(logging, debug_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s.%(msecs)03d [%(threadName)-10s] %(levelname)-8s %(name)-20s: %(message)s',
            datefmt='%H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('imu_debug.log', mode='w')
            ]
        )
        
        self.logger = logging.getLogger('IMU_DEBUG')
        
        if self.debug_enabled:
            self.logger.info("🔍 IMU Performance Debug System ENABLED")
            self.logger.info(f"Process PID: {os.getpid()}")
            self.logger.info(f"Python version: {sys.version}")
            
    def log_timing(self, operation: str, duration: float, details: Dict = None):
        """Log timing information for an operation."""
        if not self.debug_enabled:
            return
            
        self.timing_data[operation].append(duration)
        if len(self.timing_data[operation]) > 1000:  # Keep last 1000 measurements
            self.timing_data[operation].popleft()
            
        thread_name = threading.current_thread().name
        
        if duration > 0.01:  # Log operations taking >10ms
            self.logger.warning(f"⚠️  SLOW: {operation} took {duration*1000:.2f}ms in {thread_name}")
            if details:
                self.logger.warning(f"    Details: {details}")
        elif duration > 0.005:  # Log operations taking >5ms
            self.logger.info(f"🐌 {operation} took {duration*1000:.2f}ms in {thread_name}")
        else:
            self.logger.debug(f"✅ {operation} took {duration*1000:.3f}ms in {thread_name}")
    
    def log_call(self, function_name: str, args_info: str = ""):
        """Log function calls."""
        if not self.debug_enabled:
            return
            
        self.call_counts[function_name] += 1
        thread_name = threading.current_thread().name
        
        if self.call_counts[function_name] % 100 == 1:  # Log every 100th call
            self.logger.debug(f"📞 {function_name}({args_info}) - Call #{self.call_counts[function_name]} in {thread_name}")
    
    def log_memory_usage(self, operation: str):
        """Log memory usage."""
        if not self.debug_enabled:
            return
            
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        self.logger.info(f"💾 {operation}: Memory={memory_mb:.1f}MB, CPU={cpu_percent:.1f}%")
    
    def log_thread_info(self, operation: str):
        """Log thread information."""
        if not self.debug_enabled:
            return
            
        thread_name = threading.current_thread().name
        thread_count = threading.active_count()
        
        self.logger.debug(f"🧵 {operation} in {thread_name} (Total threads: {thread_count})")
    
    def log_data_flow(self, stage: str, data_size: int, data_type: str = "items"):
        """Log data flow through the system."""
        if not self.debug_enabled:
            return
            
        thread_name = threading.current_thread().name
        self.logger.debug(f"📊 {stage}: {data_size} {data_type} in {thread_name}")
        
        if data_size > 1000:
            self.logger.warning(f"⚠️  HIGH VOLUME: {stage} processing {data_size} {data_type}")
    
    def log_queue_status(self, queue_name: str, size: int, max_size: int = None):
        """Log queue status."""
        if not self.debug_enabled:
            return
            
        if max_size:
            usage_percent = (size / max_size) * 100
            if usage_percent > 80:
                self.logger.warning(f"⚠️  QUEUE FULL: {queue_name} at {usage_percent:.1f}% ({size}/{max_size})")
            elif usage_percent > 50:
                self.logger.info(f"📈 {queue_name} at {usage_percent:.1f}% ({size}/{max_size})")
            else:
                self.logger.debug(f"📊 {queue_name}: {size}/{max_size} items")
        else:
            self.logger.debug(f"📊 {queue_name}: {size} items")
    
    def log_websocket_event(self, event: str, details: Dict = None):
        """Log WebSocket events."""
        if not self.debug_enabled:
            return
            
        self.logger.info(f"🌐 WebSocket {event}")
        if details:
            self.logger.info(f"    {details}")
    
    def log_ui_event(self, event: str, duration: float = None):
        """Log UI events."""
        if not self.debug_enabled:
            return
            
        if duration:
            if duration > 0.016:  # >16ms (60fps threshold)
                self.logger.warning(f"⚠️  UI LAG: {event} took {duration*1000:.2f}ms (>16ms)")
            else:
                self.logger.debug(f"🖥️  UI: {event} took {duration*1000:.2f}ms")
        else:
            self.logger.debug(f"🖥️  UI: {event}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        summary = {
            'uptime_seconds': time.time() - self.start_time,
            'total_calls': dict(self.call_counts),
            'timing_stats': {},
            'thread_count': threading.active_count(),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'cpu_percent': psutil.Process().cpu_percent()
        }
        
        # Calculate timing statistics
        for operation, timings in self.timing_data.items():
            if timings:
                summary['timing_stats'][operation] = {
                    'count': len(timings),
                    'avg_ms': (sum(timings) / len(timings)) * 1000,
                    'max_ms': max(timings) * 1000,
                    'min_ms': min(timings) * 1000
                }
        
        return summary
    
    def print_performance_report(self):
        """Print comprehensive performance report."""
        if not self.debug_enabled:
            return
            
        summary = self.get_performance_summary()
        
        self.logger.info("=" * 80)
        self.logger.info("📊 IMU PERFORMANCE REPORT")
        self.logger.info("=" * 80)
        self.logger.info(f"Uptime: {summary['uptime_seconds']:.1f}s")
        self.logger.info(f"Memory: {summary['memory_mb']:.1f}MB")
        self.logger.info(f"CPU: {summary['cpu_percent']:.1f}%")
        self.logger.info(f"Threads: {summary['thread_count']}")
        
        self.logger.info("\n📞 FUNCTION CALL COUNTS:")
        for func, count in sorted(summary['total_calls'].items(), key=lambda x: x[1], reverse=True):
            self.logger.info(f"  {func}: {count} calls")
        
        self.logger.info("\n⏱️  TIMING STATISTICS:")
        for operation, stats in sorted(summary['timing_stats'].items(), key=lambda x: x[1]['avg_ms'], reverse=True):
            self.logger.info(f"  {operation}:")
            self.logger.info(f"    Avg: {stats['avg_ms']:.2f}ms")
            self.logger.info(f"    Max: {stats['max_ms']:.2f}ms")
            self.logger.info(f"    Count: {stats['count']}")
        
        self.logger.info("=" * 80)

# Global performance logger instance
perf_logger = PerformanceLogger()

def debug_timing(operation_name: str = None):
    """Decorator to measure and log function execution time."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # Log function call
            args_info = f"{len(args)} args, {len(kwargs)} kwargs" if args or kwargs else "no args"
            perf_logger.log_call(op_name, args_info)
            
            # Measure execution time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                perf_logger.log_timing(op_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_logger.log_timing(f"{op_name}_ERROR", duration, {"error": str(e)})
                perf_logger.logger.error(f"❌ {op_name} failed after {duration*1000:.2f}ms: {e}")
                perf_logger.logger.error(f"Traceback: {traceback.format_exc()}")
                raise
        return wrapper
    return decorator

def debug_thread(thread_name: str = None):
    """Decorator to log thread information."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = thread_name or f"{func.__module__}.{func.__name__}"
            perf_logger.log_thread_info(f"Starting {op_name}")
            
            try:
                result = func(*args, **kwargs)
                perf_logger.log_thread_info(f"Completed {op_name}")
                return result
            except Exception as e:
                perf_logger.log_thread_info(f"Failed {op_name}: {e}")
                raise
        return wrapper
    return decorator

class DebugContext:
    """Context manager for debugging operations."""
    
    def __init__(self, operation: str, log_memory: bool = False):
        self.operation = operation
        self.log_memory = log_memory
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        perf_logger.log_thread_info(f"Starting {self.operation}")
        if self.log_memory:
            perf_logger.log_memory_usage(f"Before {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            perf_logger.log_timing(f"{self.operation}_ERROR", duration, {"error": str(exc_val)})
            perf_logger.logger.error(f"❌ {self.operation} failed: {exc_val}")
        else:
            perf_logger.log_timing(self.operation, duration)
        
        if self.log_memory:
            perf_logger.log_memory_usage(f"After {self.operation}")

# Utility functions for debugging
def log_data_flow(stage: str, data_size: int, data_type: str = "items"):
    """Log data flow through the system."""
    perf_logger.log_data_flow(stage, data_size, data_type)

def log_queue_status(queue_name: str, size: int, max_size: int = None):
    """Log queue status."""
    perf_logger.log_queue_status(queue_name, size, max_size)

def log_websocket_event(event: str, details: Dict = None):
    """Log WebSocket events."""
    perf_logger.log_websocket_event(event, details)

def log_ui_event(event: str, duration: float = None):
    """Log UI events."""
    perf_logger.log_ui_event(event, duration)

def print_performance_report():
    """Print performance report."""
    perf_logger.print_performance_report()

def enable_debug_mode():
    """Enable debug mode programmatically."""
    os.environ['IMU_DEBUG'] = '1'
    perf_logger.debug_enabled = True
    perf_logger.logger.info("🔍 Debug mode ENABLED programmatically")

def disable_debug_mode():
    """Disable debug mode programmatically."""
    os.environ['IMU_DEBUG'] = '0'
    perf_logger.debug_enabled = False

# Example usage and testing
if __name__ == "__main__":
    # Enable debug mode
    enable_debug_mode()
    
    # Test the debugging system
    @debug_timing("test_function")
    def test_function():
        time.sleep(0.01)  # Simulate work
        return "test result"
    
    @debug_thread("test_thread")
    def test_thread_function():
        for i in range(5):
            test_function()
            time.sleep(0.005)
    
    # Test timing decorator
    result = test_function()
    
    # Test context manager
    with DebugContext("test_operation", log_memory=True):
        time.sleep(0.02)
    
    # Test thread decorator
    test_thread_function()
    
    # Test logging functions
    log_data_flow("test_stage", 100, "messages")
    log_queue_status("test_queue", 50, 100)
    log_websocket_event("connection_established", {"ip": "192.168.1.101"})
    log_ui_event("update_display", 0.008)
    
    # Print performance report
    print_performance_report()