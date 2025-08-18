#!/usr/bin/env python3
"""
Test script for the enhanced IMU monitoring features.
This script can be used to verify that the new IMU display enhancements work correctly.
"""

import sys
import os
import time
import random
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from juggling_tracker.ui.imu_monitoring_window import IMUMonitoringWindow

class MockApp:
    """Mock application class to simulate IMU data for testing."""
    
    def __init__(self):
        self.latest_imu_data = {}
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.generate_mock_data)
        self.data_timer.start(50)  # Generate data every 50ms (20 Hz)
    
    def generate_mock_data(self):
        """Generate mock IMU data for testing."""
        # Simulate data from two watches
        watches = ['left', 'right']
        
        for watch_name in watches:
            # Generate realistic IMU data with some motion patterns
            t = time.time()
            
            # Simulate some periodic motion for testing
            accel_x = 2.0 * random.random() - 1.0 + 0.5 * math.sin(t * 2)
            accel_y = 2.0 * random.random() - 1.0 + 0.3 * math.cos(t * 1.5)
            accel_z = 9.8 + 2.0 * random.random() - 1.0  # Gravity + noise
            
            gyro_x = 1.0 * random.random() - 0.5 + 0.2 * math.sin(t * 3)
            gyro_y = 1.0 * random.random() - 0.5 + 0.1 * math.cos(t * 2.5)
            gyro_z = 1.0 * random.random() - 0.5
            
            # Calculate magnitudes
            accel_magnitude = (accel_x**2 + accel_y**2 + accel_z**2)**0.5
            gyro_magnitude = (gyro_x**2 + gyro_y**2 + gyro_z**2)**0.5
            
            self.latest_imu_data[watch_name] = {
                'accel': (accel_x, accel_y, accel_z),
                'gyro': (gyro_x, gyro_y, gyro_z),
                'accel_magnitude': accel_magnitude,
                'gyro_magnitude': gyro_magnitude,
                'data_age': random.uniform(0.01, 0.1),  # 10-100ms age
                'timestamp': t,
                'watch_ip': f'192.168.1.{101 if watch_name == "left" else 102}'
            }

def main():
    """Main test function."""
    import math  # Import here to avoid issues with mock data generation
    
    print("🧪 Testing Enhanced IMU Monitoring Features")
    print("=" * 50)
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create mock app with simulated IMU data
    mock_app = MockApp()
    
    # Create IMU monitoring window
    imu_window = IMUMonitoringWindow(parent=None, app=mock_app)
    
    print("✅ Created IMU monitoring window")
    print("📊 Generating mock IMU data at 20 Hz")
    print("🎯 Features to test:")
    print("   - Real-time progress bars for all 6 axes")
    print("   - Magnitude calculations and display")
    print("   - Data rate monitoring")
    print("   - Raw data stream")
    print("   - CSV logging (select a file to test)")
    print("   - Configurable update rates")
    print()
    print("💡 Instructions:")
    print("   1. The window should show data from 'left' and 'right' watches")
    print("   2. Progress bars should move in real-time")
    print("   3. Data rate should show ~40 Hz (20 Hz per watch)")
    print("   4. Try enabling logging and selecting a CSV file")
    print("   5. Adjust the update rate slider to see changes")
    print("   6. Check the raw data stream for live updates")
    print()
    print("🚀 Opening IMU monitoring window...")
    
    # Show the window
    imu_window.show()
    imu_window.raise_()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()