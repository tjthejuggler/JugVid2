#!/usr/bin/env python3
import os
import time
import csv
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QProgressBar, QGroupBox, QPushButton, QCheckBox,
    QSpinBox, QFileDialog, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

class IMUMonitoringWindow(QMainWindow):
    """
    Dedicated window for real-time IMU data monitoring with sliders, logging, and visualization.
    """
    
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.parent_window = parent
        
        # Data logging setup
        self.logging_enabled = False
        self.log_file_path = None
        self.log_file = None
        self.log_writer = None
        
        # Data storage for rate calculation
        self.data_count = 0
        self.last_rate_update = time.time()
        self.data_rate = 0.0
        
        # Setup window
        self.setWindowTitle("IMU Real-time Monitor")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Setup UI
        self.setup_ui()
        
        # Setup timer for IMU updates (reduced frequency to prevent lag)
        self.imu_timer = QTimer()
        self.imu_timer.timeout.connect(self.update_imu_display)
        self.imu_timer.start(200)  # 5 Hz updates (200ms interval) - much less laggy
        
        # Setup rate calculation timer
        self.rate_timer = QTimer()
        self.rate_timer.timeout.connect(self.update_data_rate)
        self.rate_timer.start(1000)  # Update rate every second
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Status panel
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
        
        # IMU data panels in a scroll area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create IMU panels for each potential watch
        self.imu_panels = {}
        
        # Add placeholder panel
        placeholder_panel = self.create_placeholder_panel()
        scroll_layout.addWidget(placeholder_panel)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        # Raw data display
        raw_data_panel = self.create_raw_data_panel()
        main_layout.addWidget(raw_data_panel)
    
    def create_control_panel(self):
        """Create the control panel with logging and settings."""
        panel = QGroupBox("Controls")
        layout = QHBoxLayout(panel)
        
        # Logging controls
        self.logging_checkbox = QCheckBox("Enable Data Logging")
        self.logging_checkbox.toggled.connect(self.toggle_logging)
        layout.addWidget(self.logging_checkbox)
        
        self.select_log_file_btn = QPushButton("Select Log File...")
        self.select_log_file_btn.clicked.connect(self.select_log_file)
        layout.addWidget(self.select_log_file_btn)
        
        self.log_file_label = QLabel("No log file selected")
        self.log_file_label.setWordWrap(True)
        layout.addWidget(self.log_file_label)
        
        layout.addStretch()
        
        # Update frequency control
        freq_label = QLabel("Update Rate (Hz):")
        layout.addWidget(freq_label)
        
        self.freq_spinbox = QSpinBox()
        self.freq_spinbox.setRange(1, 20)  # Reduced max to prevent lag
        self.freq_spinbox.setValue(5)     # Default to 5 Hz
        self.freq_spinbox.valueChanged.connect(self.update_frequency_changed)
        layout.addWidget(self.freq_spinbox)
        
        return panel
    
    def create_status_panel(self):
        """Create the status panel showing connection and data rate info."""
        panel = QGroupBox("Status")
        layout = QHBoxLayout(panel)
        
        self.connection_status_label = QLabel("Connection: Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label)
        
        self.data_rate_label = QLabel("Data Rate: 0.0 Hz")
        layout.addWidget(self.data_rate_label)
        
        self.total_samples_label = QLabel("Total Samples: 0")
        layout.addWidget(self.total_samples_label)
        
        layout.addStretch()
        
        return panel
    
    def create_placeholder_panel(self):
        """Create a placeholder panel when no IMU data is available."""
        panel = QGroupBox("IMU Data")
        layout = QVBoxLayout(panel)
        
        self.placeholder_label = QLabel("No IMU data available. Connect watches to see real-time data.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: gray; font-size: 14px; padding: 20px;")
        layout.addWidget(self.placeholder_label)
        
        return panel
    
    def create_imu_panel(self, watch_name):
        """Create an IMU panel for a specific watch."""
        panel = QGroupBox(f"Watch: {watch_name}")
        layout = QGridLayout(panel)
        
        # Create progress bars for each axis
        axes = [
            ('Accel X', 'accel_x', -20, 20, 'm/s²'),
            ('Accel Y', 'accel_y', -20, 20, 'm/s²'),
            ('Accel Z', 'accel_z', -20, 20, 'm/s²'),
            ('Gyro X', 'gyro_x', -10, 10, 'rad/s'),
            ('Gyro Y', 'gyro_y', -10, 10, 'rad/s'),
            ('Gyro Z', 'gyro_z', -10, 10, 'rad/s'),
        ]
        
        panel_data = {
            'panel': panel,
            'bars': {},
            'labels': {},
            'values': {}
        }
        
        for i, (name, key, min_val, max_val, unit) in enumerate(axes):
            row = i // 3
            col = (i % 3) * 3
            
            # Label
            label = QLabel(f"{name}:")
            label.setMinimumWidth(80)
            layout.addWidget(label, row, col)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setRange(int(min_val * 100), int(max_val * 100))
            progress_bar.setValue(0)
            progress_bar.setMinimumWidth(200)
            layout.addWidget(progress_bar, row, col + 1)
            
            # Value label
            value_label = QLabel("0.00 " + unit)
            value_label.setMinimumWidth(100)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(value_label, row, col + 2)
            
            panel_data['bars'][key] = progress_bar
            panel_data['labels'][key] = value_label
            panel_data['values'][key] = 0.0
        
        # Add magnitude displays
        mag_row = len(axes) // 3 + 1
        
        # Acceleration magnitude
        accel_mag_label = QLabel("Accel Mag:")
        layout.addWidget(accel_mag_label, mag_row, 0)
        
        accel_mag_bar = QProgressBar()
        accel_mag_bar.setRange(0, 2000)  # 0-20 m/s²
        accel_mag_bar.setValue(0)
        layout.addWidget(accel_mag_bar, mag_row, 1)
        
        accel_mag_value = QLabel("0.00 m/s²")
        accel_mag_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(accel_mag_value, mag_row, 2)
        
        panel_data['bars']['accel_mag'] = accel_mag_bar
        panel_data['labels']['accel_mag'] = accel_mag_value
        
        # Gyroscope magnitude
        gyro_mag_label = QLabel("Gyro Mag:")
        layout.addWidget(gyro_mag_label, mag_row, 3)
        
        gyro_mag_bar = QProgressBar()
        gyro_mag_bar.setRange(0, 1000)  # 0-10 rad/s
        gyro_mag_bar.setValue(0)
        layout.addWidget(gyro_mag_bar, mag_row, 4)
        
        gyro_mag_value = QLabel("0.00 rad/s")
        gyro_mag_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(gyro_mag_value, mag_row, 5)
        
        panel_data['bars']['gyro_mag'] = gyro_mag_bar
        panel_data['labels']['gyro_mag'] = gyro_mag_value
        
        return panel_data
    
    def create_raw_data_panel(self):
        """Create a panel for raw data display."""
        panel = QGroupBox("Raw Data Stream")
        layout = QVBoxLayout(panel)
        
        self.raw_data_text = QTextEdit()
        self.raw_data_text.setMaximumHeight(150)
        self.raw_data_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.raw_data_text)
        
        # Controls for raw data
        controls_layout = QHBoxLayout()
        
        self.show_raw_data_checkbox = QCheckBox("Show Raw Data Stream")
        self.show_raw_data_checkbox.setChecked(True)
        controls_layout.addWidget(self.show_raw_data_checkbox)
        
        self.clear_raw_data_btn = QPushButton("Clear")
        self.clear_raw_data_btn.clicked.connect(self.clear_raw_data)
        controls_layout.addWidget(self.clear_raw_data_btn)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return panel
    
    def update_frequency_changed(self, value):
        """Update the timer frequency."""
        interval = int(1000 / value)  # Convert Hz to milliseconds
        self.imu_timer.setInterval(interval)
    
    def toggle_logging(self, enabled):
        """Toggle data logging on/off."""
        if enabled:
            # Check if log file path is set
            if not self.log_file_path:
                # Automatically select a default log file
                default_filename = f"imu_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                self.log_file_path = os.path.join(os.getcwd(), default_filename)
                self.log_file_label.setText(f"Log: {os.path.basename(self.log_file_path)}")
                print(f"Auto-selected log file: {self.log_file_path}")
            
            # Try to start logging
            if not self.start_logging():
                # If logging failed, uncheck the checkbox
                self.logging_checkbox.setChecked(False)
                return
            
            self.logging_enabled = True
        else:
            self.logging_enabled = False
            self.stop_logging()
    
    def select_log_file(self):
        """Select a file for data logging."""
        default_filename = f"imu_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select IMU Log File", default_filename, "CSV Files (*.csv)"
        )
        
        if file_path:
            self.log_file_path = file_path
            self.log_file_label.setText(f"Log: {os.path.basename(file_path)}")
            
            if self.logging_enabled:
                self.start_logging()
    
    def start_logging(self):
        """Start logging IMU data to file.
        
        Returns:
            bool: True if logging started successfully, False otherwise
        """
        if not self.log_file_path:
            print("Error: No log file path specified")
            return False
        
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(self.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Close any existing log file first
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.log_writer = None
            
            self.log_file = open(self.log_file_path, 'w', newline='')
            self.log_writer = csv.writer(self.log_file)
            
            # Write header
            header = [
                'timestamp', 'watch_name', 'accel_x', 'accel_y', 'accel_z',
                'gyro_x', 'gyro_y', 'gyro_z', 'accel_magnitude', 'gyro_magnitude',
                'data_age_ms'
            ]
            self.log_writer.writerow(header)
            self.log_file.flush()
            
            print(f"Started logging IMU data to: {self.log_file_path}")
            return True
            
        except Exception as e:
            print(f"Error starting IMU logging: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up on error
            if self.log_file:
                try:
                    self.log_file.close()
                except:
                    pass
                self.log_file = None
                self.log_writer = None
            
            return False
    
    def stop_logging(self):
        """Stop logging IMU data."""
        try:
            if self.log_file:
                self.log_file.close()
                print(f"Stopped logging IMU data")
        except Exception as e:
            print(f"Error closing log file: {e}")
        finally:
            self.log_file = None
            self.log_writer = None
    
    def log_imu_data(self, watch_name, data):
        """Log a single IMU data point."""
        if not self.logging_enabled or not self.log_writer or not self.log_file:
            return
        
        try:
            timestamp = time.time()
            accel = data.get('accel', (0, 0, 0))
            gyro = data.get('gyro', (0, 0, 0))
            accel_magnitude = data.get('accel_magnitude', 0)
            gyro_magnitude = data.get('gyro_magnitude', 0)
            data_age_ms = data.get('data_age', 0) * 1000
            
            row = [
                timestamp, watch_name,
                accel[0], accel[1], accel[2],
                gyro[0], gyro[1], gyro[2],
                accel_magnitude, gyro_magnitude,
                data_age_ms
            ]
            
            self.log_writer.writerow(row)
            self.log_file.flush()
            
        except Exception as e:
            print(f"Error logging IMU data: {e}")
            # Disable logging on error to prevent further crashes
            self.logging_enabled = False
            self.logging_checkbox.setChecked(False)
            self.stop_logging()
    
    def update_imu_display(self):
        """Update the IMU display with latest data."""
        if not self.app or not hasattr(self.app, 'latest_imu_data'):
            return
        
        latest_imu_data = getattr(self.app, 'latest_imu_data', {})
        
        if latest_imu_data:
            # Update connection status
            self.connection_status_label.setText("Connection: Connected")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Hide placeholder if it exists
            if hasattr(self, 'placeholder_label'):
                self.placeholder_label.hide()
            
            # Process each watch's data
            for watch_name, data in latest_imu_data.items():
                self.data_count += 1
                
                # Create panel if it doesn't exist
                if watch_name not in self.imu_panels:
                    panel_data = self.create_imu_panel(watch_name)
                    self.imu_panels[watch_name] = panel_data
                    
                    # Add to scroll area
                    scroll_widget = self.centralWidget().findChild(QScrollArea).widget()
                    scroll_widget.layout().addWidget(panel_data['panel'])
                
                # Update panel data
                self.update_watch_panel(watch_name, data)
                
                # Log data if enabled
                self.log_imu_data(watch_name, data)
                
                # Update raw data display (less frequently to reduce lag)
                if self.show_raw_data_checkbox.isChecked() and self.data_count % 3 == 0:  # Only every 3rd update
                    self.update_raw_data_display(watch_name, data)
        else:
            # Update connection status
            self.connection_status_label.setText("Connection: Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def update_watch_panel(self, watch_name, data):
        """Update a specific watch panel with new data."""
        if watch_name not in self.imu_panels:
            return
        
        panel_data = self.imu_panels[watch_name]
        accel = data.get('accel', (0, 0, 0))
        gyro = data.get('gyro', (0, 0, 0))
        accel_magnitude = data.get('accel_magnitude', 0)
        gyro_magnitude = data.get('gyro_magnitude', 0)
        
        # Update individual axes
        axes_data = {
            'accel_x': accel[0],
            'accel_y': accel[1],
            'accel_z': accel[2],
            'gyro_x': gyro[0],
            'gyro_y': gyro[1],
            'gyro_z': gyro[2],
        }
        
        for key, value in axes_data.items():
            if key in panel_data['bars']:
                # Update progress bar
                bar = panel_data['bars'][key]
                bar.setValue(int(value * 100))
                
                # Update value label
                label = panel_data['labels'][key]
                unit = 'm/s²' if 'accel' in key else 'rad/s'
                label.setText(f"{value:.3f} {unit}")
                
                # Color coding based on magnitude
                if abs(value) > (15 if 'accel' in key else 5):
                    bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
                elif abs(value) > (10 if 'accel' in key else 2):
                    bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
                else:
                    bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
        
        # Update magnitudes
        if 'accel_mag' in panel_data['bars']:
            bar = panel_data['bars']['accel_mag']
            bar.setValue(int(accel_magnitude * 100))
            label = panel_data['labels']['accel_mag']
            label.setText(f"{accel_magnitude:.3f} m/s²")
        
        if 'gyro_mag' in panel_data['bars']:
            bar = panel_data['bars']['gyro_mag']
            bar.setValue(int(gyro_magnitude * 100))
            label = panel_data['labels']['gyro_mag']
            label.setText(f"{gyro_magnitude:.3f} rad/s")
    
    def update_raw_data_display(self, watch_name, data):
        """Update the raw data text display."""
        if not self.show_raw_data_checkbox.isChecked():
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        accel = data.get('accel', (0, 0, 0))
        gyro = data.get('gyro', (0, 0, 0))
        data_age = data.get('data_age', 0) * 1000
        
        line = (f"{timestamp} | {watch_name:10} | "
                f"A({accel[0]:6.3f},{accel[1]:6.3f},{accel[2]:6.3f}) | "
                f"G({gyro[0]:6.3f},{gyro[1]:6.3f},{gyro[2]:6.3f}) | "
                f"Age:{data_age:5.1f}ms")
        
        self.raw_data_text.append(line)
        
        # Limit text length to prevent memory issues
        if self.raw_data_text.document().lineCount() > 100:
            cursor = self.raw_data_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 10)
            cursor.removeSelectedText()
    
    def update_data_rate(self):
        """Update the data rate calculation."""
        current_time = time.time()
        time_diff = current_time - self.last_rate_update
        
        if time_diff >= 1.0:
            self.data_rate = self.data_count / time_diff
            self.data_rate_label.setText(f"Data Rate: {self.data_rate:.1f} Hz")
            self.total_samples_label.setText(f"Total Samples: {self.data_count}")
            
            self.data_count = 0
            self.last_rate_update = current_time
    
    def clear_raw_data(self):
        """Clear the raw data display."""
        self.raw_data_text.clear()
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.stop_logging()
        event.accept()