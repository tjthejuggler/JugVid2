#!/usr/bin/env python3
"""
Optimized IMU UI Integration

This module provides optimized UI components that work efficiently with the
high-performance IMU streaming system, minimizing lag and CPU usage.

Author: Generated for JugVid2 project
Date: 2025-08-18
Version: 2.0 (Optimized for High-Performance Streaming)
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from collections import deque
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QProgressBar, QGroupBox, QPushButton, QCheckBox,
    QSpinBox, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPalette, QColor

class OptimizedIMUDataProcessor(QObject):
    """Optimized data processor that handles high-frequency IMU data efficiently."""
    
    # Signals for thread-safe UI updates
    data_updated = pyqtSignal(str, dict)  # watch_name, processed_data
    stats_updated = pyqtSignal(dict)  # performance_stats
    
    def __init__(self, update_rate_hz: int = 30):
        super().__init__()
        self.update_rate_hz = update_rate_hz
        self.update_interval = 1.0 / update_rate_hz
        
        # Data buffers for smoothing and statistics
        self.data_buffers = {
            'left': deque(maxlen=100),   # Keep last 100 samples for smoothing
            'right': deque(maxlen=100)
        }
        
        # Processed data for UI
        self.processed_data = {}
        
        # Statistics
        self.stats = {
            'total_samples': 0,
            'data_rate': 0.0,
            'last_update': time.time(),
            'sample_count': 0
        }
        
        # Threading
        self.processing_thread = None
        self.running = False
        self.last_ui_update = 0
        
    def start_processing(self):
        """Start the optimized data processing thread."""
        if self.running:
            return
            
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
    def stop_processing(self):
        """Stop data processing."""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
    
    def add_data_point(self, watch_name: str, data: Dict[str, Any]):
        """Add new data point (called from high-performance manager)."""
        if watch_name in self.data_buffers:
            self.data_buffers[watch_name].append(data)
            self.stats['total_samples'] += 1
            self.stats['sample_count'] += 1
    
    def _processing_loop(self):
        """Optimized processing loop that updates UI at controlled rate."""
        while self.running:
            current_time = time.time()
            
            # Update UI at controlled rate to prevent lag
            if current_time - self.last_ui_update >= self.update_interval:
                self._process_and_emit_updates()
                self.last_ui_update = current_time
                
                # Update statistics
                time_diff = current_time - self.stats['last_update']
                if time_diff >= 1.0:
                    self.stats['data_rate'] = self.stats['sample_count'] / time_diff
                    self.stats['sample_count'] = 0
                    self.stats['last_update'] = current_time
                    
                    # Emit stats update
                    self.stats_updated.emit(self.stats.copy())
            
            # Sleep to prevent busy waiting
            time.sleep(0.01)  # 10ms sleep
    
    def _process_and_emit_updates(self):
        """Process buffered data and emit UI updates."""
        for watch_name, buffer in self.data_buffers.items():
            if buffer:
                # Get latest data point
                latest_data = buffer[-1]
                
                # Calculate smoothed values using recent samples
                recent_samples = list(buffer)[-10:]  # Last 10 samples
                if len(recent_samples) > 1:
                    smoothed_data = self._calculate_smoothed_data(recent_samples)
                else:
                    smoothed_data = latest_data
                
                # Prepare processed data for UI
                processed = {
                    'raw': latest_data,
                    'smoothed': smoothed_data,
                    'buffer_size': len(buffer),
                    'timestamp': latest_data.get('timestamp', time.time())
                }
                
                self.processed_data[watch_name] = processed
                
                # Emit signal for UI update
                self.data_updated.emit(watch_name, processed)
    
    def _calculate_smoothed_data(self, samples: list) -> Dict[str, Any]:
        """Calculate smoothed data from recent samples."""
        if not samples:
            return {}
        
        # Extract arrays for vectorized operations
        accels = np.array([s['accel'] for s in samples])
        gyros = np.array([s['gyro'] for s in samples])
        
        # Calculate smoothed values
        smoothed_accel = np.mean(accels, axis=0)
        smoothed_gyro = np.mean(gyros, axis=0)
        
        # Calculate magnitudes
        accel_mag = np.linalg.norm(smoothed_accel)
        gyro_mag = np.linalg.norm(smoothed_gyro)
        
        return {
            'accel': tuple(smoothed_accel),
            'gyro': tuple(smoothed_gyro),
            'accel_magnitude': accel_mag,
            'gyro_magnitude': gyro_mag,
            'data_age': samples[-1].get('data_age', 0)
        }

class OptimizedIMUMonitoringWindow(QMainWindow):
    """Optimized IMU monitoring window with minimal lag."""
    
    def __init__(self, parent=None, high_perf_manager=None):
        super().__init__(parent)
        self.high_perf_manager = high_perf_manager
        
        # Optimized data processor
        self.data_processor = OptimizedIMUDataProcessor(update_rate_hz=20)  # 20 Hz UI updates
        
        # UI state
        self.watch_panels = {}
        self.performance_stats = {}
        
        # Setup window
        self.setWindowTitle("Optimized IMU Real-time Monitor")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.data_processor.data_updated.connect(self.update_watch_display)
        self.data_processor.stats_updated.connect(self.update_performance_display)
        
        # Start data processing
        self.data_processor.start_processing()
        
        # Connect to high-performance manager if provided
        if self.high_perf_manager:
            self.high_perf_manager.add_data_callback(self.data_processor.add_data_point)
    
    def setup_ui(self):
        """Setup optimized UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)  # Reduced spacing
        
        # Performance panel
        perf_panel = self.create_performance_panel()
        main_layout.addWidget(perf_panel)
        
        # IMU data panels
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create panels for left and right watches
        for watch_name in ['left', 'right']:
            panel = self.create_optimized_watch_panel(watch_name)
            self.watch_panels[watch_name] = panel
            scroll_layout.addWidget(panel['widget'])
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
    
    def create_performance_panel(self):
        """Create performance monitoring panel."""
        panel = QGroupBox("Performance Monitor")
        layout = QHBoxLayout(panel)
        
        self.data_rate_label = QLabel("Data Rate: 0.0 Hz")
        self.latency_label = QLabel("Latency: 0.0 ms")
        self.buffer_usage_label = QLabel("Buffer: 0.0%")
        self.total_samples_label = QLabel("Samples: 0")
        
        layout.addWidget(self.data_rate_label)
        layout.addWidget(self.latency_label)
        layout.addWidget(self.buffer_usage_label)
        layout.addWidget(self.total_samples_label)
        layout.addStretch()
        
        return panel
    
    def create_optimized_watch_panel(self, watch_name: str):
        """Create optimized watch panel with minimal update overhead."""
        panel_widget = QGroupBox(f"Watch: {watch_name.upper()}")
        layout = QGridLayout(panel_widget)
        
        # Create efficient progress bars and labels
        panel_data = {
            'widget': panel_widget,
            'bars': {},
            'labels': {},
            'last_update': 0
        }
        
        # Accelerometer
        accel_label = QLabel("Accelerometer:")
        accel_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(accel_label, 0, 0, 1, 3)
        
        accel_axes = [('X', 'accel_x'), ('Y', 'accel_y'), ('Z', 'accel_z')]
        for i, (axis, key) in enumerate(accel_axes):
            label = QLabel(f"{axis}:")
            bar = QProgressBar()
            bar.setRange(-2000, 2000)  # -20 to 20 m/s² * 100
            bar.setValue(0)
            value_label = QLabel("0.00 m/s²")
            
            layout.addWidget(label, 1, i*2)
            layout.addWidget(bar, 1, i*2+1)
            layout.addWidget(value_label, 2, i*2+1)
            
            panel_data['bars'][key] = bar
            panel_data['labels'][key] = value_label
        
        # Gyroscope
        gyro_label = QLabel("Gyroscope:")
        gyro_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(gyro_label, 3, 0, 1, 3)
        
        gyro_axes = [('X', 'gyro_x'), ('Y', 'gyro_y'), ('Z', 'gyro_z')]
        for i, (axis, key) in enumerate(gyro_axes):
            label = QLabel(f"{axis}:")
            bar = QProgressBar()
            bar.setRange(-1000, 1000)  # -10 to 10 rad/s * 100
            bar.setValue(0)
            value_label = QLabel("0.00 rad/s")
            
            layout.addWidget(label, 4, i*2)
            layout.addWidget(bar, 4, i*2+1)
            layout.addWidget(value_label, 5, i*2+1)
            
            panel_data['bars'][key] = bar
            panel_data['labels'][key] = value_label
        
        # Magnitude displays
        accel_mag_label = QLabel("Accel Magnitude:")
        accel_mag_bar = QProgressBar()
        accel_mag_bar.setRange(0, 3000)  # 0-30 m/s²
        accel_mag_value = QLabel("0.00 m/s²")
        
        layout.addWidget(accel_mag_label, 6, 0)
        layout.addWidget(accel_mag_bar, 6, 1, 1, 2)
        layout.addWidget(accel_mag_value, 6, 3)
        
        panel_data['bars']['accel_mag'] = accel_mag_bar
        panel_data['labels']['accel_mag'] = accel_mag_value
        
        gyro_mag_label = QLabel("Gyro Magnitude:")
        gyro_mag_bar = QProgressBar()
        gyro_mag_bar.setRange(0, 1000)  # 0-10 rad/s
        gyro_mag_value = QLabel("0.00 rad/s")
        
        layout.addWidget(gyro_mag_label, 7, 0)
        layout.addWidget(gyro_mag_bar, 7, 1, 1, 2)
        layout.addWidget(gyro_mag_value, 7, 3)
        
        panel_data['bars']['gyro_mag'] = gyro_mag_bar
        panel_data['labels']['gyro_mag'] = gyro_mag_value
        
        return panel_data
    
    def create_control_panel(self):
        """Create control panel."""
        panel = QGroupBox("Controls")
        layout = QHBoxLayout(panel)
        
        # Update rate control
        rate_label = QLabel("UI Update Rate (Hz):")
        self.rate_spinbox = QSpinBox()
        self.rate_spinbox.setRange(5, 60)
        self.rate_spinbox.setValue(20)
        self.rate_spinbox.valueChanged.connect(self.update_rate_changed)
        
        layout.addWidget(rate_label)
        layout.addWidget(self.rate_spinbox)
        layout.addStretch()
        
        # Performance test button
        test_btn = QPushButton("Performance Test")
        test_btn.clicked.connect(self.run_performance_test)
        layout.addWidget(test_btn)
        
        return panel
    
    def update_rate_changed(self, value):
        """Update the UI refresh rate."""
        self.data_processor.update_rate_hz = value
        self.data_processor.update_interval = 1.0 / value
    
    def update_watch_display(self, watch_name: str, processed_data: Dict[str, Any]):
        """Update watch display with optimized rendering."""
        if watch_name not in self.watch_panels:
            return
        
        panel_data = self.watch_panels[watch_name]
        current_time = time.time()
        
        # Throttle updates to prevent excessive redraws
        if current_time - panel_data['last_update'] < 0.03:  # Max 30 Hz per panel
            return
        
        panel_data['last_update'] = current_time
        
        # Use smoothed data for display
        smoothed = processed_data.get('smoothed', {})
        if not smoothed:
            return
        
        accel = smoothed.get('accel', (0, 0, 0))
        gyro = smoothed.get('gyro', (0, 0, 0))
        accel_mag = smoothed.get('accel_magnitude', 0)
        gyro_mag = smoothed.get('gyro_magnitude', 0)
        
        # Update accelerometer displays
        accel_keys = ['accel_x', 'accel_y', 'accel_z']
        for i, key in enumerate(accel_keys):
            if key in panel_data['bars']:
                value = accel[i]
                panel_data['bars'][key].setValue(int(value * 100))
                panel_data['labels'][key].setText(f"{value:.3f} m/s²")
        
        # Update gyroscope displays
        gyro_keys = ['gyro_x', 'gyro_y', 'gyro_z']
        for i, key in enumerate(gyro_keys):
            if key in panel_data['bars']:
                value = gyro[i]
                panel_data['bars'][key].setValue(int(value * 100))
                panel_data['labels'][key].setText(f"{value:.3f} rad/s")
        
        # Update magnitudes
        if 'accel_mag' in panel_data['bars']:
            panel_data['bars']['accel_mag'].setValue(int(accel_mag * 100))
            panel_data['labels']['accel_mag'].setText(f"{accel_mag:.3f} m/s²")
        
        if 'gyro_mag' in panel_data['bars']:
            panel_data['bars']['gyro_mag'].setValue(int(gyro_mag * 100))
            panel_data['labels']['gyro_mag'].setText(f"{gyro_mag:.3f} rad/s")
    
    def update_performance_display(self, stats: Dict[str, Any]):
        """Update performance statistics display."""
        self.performance_stats = stats
        
        self.data_rate_label.setText(f"Data Rate: {stats.get('data_rate', 0):.1f} Hz")
        self.total_samples_label.setText(f"Samples: {stats.get('total_samples', 0)}")
        
        # Get additional stats from high-performance manager if available
        if self.high_perf_manager:
            perf_stats = self.high_perf_manager.get_performance_stats()
            latency = perf_stats.get('latency_ms', 0)
            buffer_usage = perf_stats.get('buffer_usage', 0)
            
            self.latency_label.setText(f"Latency: {latency:.1f} ms")
            self.buffer_usage_label.setText(f"Buffer: {buffer_usage:.1f}%")
    
    def run_performance_test(self):
        """Run a performance test to measure system capabilities."""
        if not self.high_perf_manager:
            return
        
        print("🧪 Running performance test...")
        
        # Get current stats
        stats = self.high_perf_manager.get_performance_stats()
        
        print(f"📊 Performance Test Results:")
        print(f"   Data Rate: {stats.get('data_rate', 0):.1f} Hz")
        print(f"   Latency: {stats.get('latency_ms', 0):.1f} ms")
        print(f"   Buffer Usage: {stats.get('buffer_usage', 0):.1f}%")
        print(f"   Messages Received: {stats.get('messages_received', 0)}")
        print(f"   Buffer Overflows: {stats.get('buffer_overflows', 0)}")
        print(f"   UI Update Rate: {self.data_processor.update_rate_hz} Hz")
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.data_processor.stop_processing()
        event.accept()

# Integration helper for existing applications
class OptimizedIMUIntegration:
    """Helper class to integrate optimized IMU streaming into existing applications."""
    
    def __init__(self, app, watch_ips: list = None):
        self.app = app
        self.watch_ips = watch_ips or ["127.0.0.1", "127.0.0.1"]
        
        # Import high-performance manager
        from high_performance_imu_stream import OptimizedWatchIMUManager
        
        # Create optimized manager
        self.imu_manager = OptimizedWatchIMUManager(watch_ips=self.watch_ips)
        
        # Create optimized UI
        self.monitoring_window = None
        
        # Compatibility layer
        self.latest_imu_data = {}
        
        # Setup data callback
        self.imu_manager.high_perf_manager.add_data_callback(self._update_app_data)
    
    def _update_app_data(self, watch_name: str, data: Dict[str, Any]):
        """Update application data structure for compatibility."""
        self.latest_imu_data[watch_name] = data
        
        # Update app's latest_imu_data if it exists
        if hasattr(self.app, 'latest_imu_data'):
            self.app.latest_imu_data[watch_name] = data
    
    def start_streaming(self):
        """Start optimized streaming."""
        self.imu_manager.start_streaming()
    
    def stop_streaming(self):
        """Stop streaming."""
        self.imu_manager.stop_streaming()
    
    def show_monitoring_window(self):
        """Show optimized monitoring window."""
        if not self.monitoring_window:
            self.monitoring_window = OptimizedIMUMonitoringWindow(
                parent=None,
                high_perf_manager=self.imu_manager.high_perf_manager
            )
        
        self.monitoring_window.show()
        self.monitoring_window.raise_()
        self.monitoring_window.activateWindow()
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        return self.imu_manager.get_performance_stats()
    
    def cleanup(self):
        """Clean up resources."""
        if self.monitoring_window:
            self.monitoring_window.close()
        self.imu_manager.cleanup()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from high_performance_imu_stream import HighPerformanceIMUManager
    
    app = QApplication(sys.argv)
    
    # Create high-performance manager
    manager = HighPerformanceIMUManager(["127.0.0.1", "127.0.0.1"])
    
    # Create optimized UI
    window = OptimizedIMUMonitoringWindow(high_perf_manager=manager)
    window.show()
    
    # Start streaming
    manager.start_streaming()
    
    try:
        sys.exit(app.exec())
    finally:
        manager.cleanup()