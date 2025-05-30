#!/usr/bin/env python3
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt

class SimpleTrackingWindow(QDialog):
    """
    Separate window for simple tracking settings and controls.
    """
    
    def __init__(self, parent=None, app=None, config_dir=None):
        """
        Initialize the Simple Tracking Settings window.
        
        Args:
            parent: Parent widget (MainWindow)
            app: Reference to the main application
            config_dir: Configuration directory path
        """
        super().__init__(parent)
        
        self.app = app
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        
        # Set window properties
        self.setWindowTitle("Simple Tracking Settings")
        self.setMinimumSize(400, 600)
        self.setMaximumSize(500, 800)
        
        # Make it non-modal so user can interact with main window
        self.setModal(False)
        
        # Set up the UI
        self.setup_ui()
        
        # Initialize sliders with current tracker values
        self.update_sliders_from_tracker()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Basic tracking controls
        basic_group = QGroupBox("Basic Controls")
        basic_layout = QVBoxLayout()
        basic_group.setLayout(basic_layout)
        
        # Proximity threshold slider
        proximity_layout = QHBoxLayout()
        proximity_layout.addWidget(QLabel("Proximity Threshold:"))
        self.proximity_slider = QSlider(Qt.Orientation.Horizontal)
        self.proximity_slider.setMinimum(5)   # 0.05m
        self.proximity_slider.setMaximum(50)  # 0.50m
        self.proximity_slider.setValue(15)    # 0.15m default
        self.proximity_slider.valueChanged.connect(self.on_proximity_changed)
        proximity_layout.addWidget(self.proximity_slider)
        self.proximity_label = QLabel("0.15m")
        proximity_layout.addWidget(self.proximity_label)
        basic_layout.addLayout(proximity_layout)
        
        # Min object size slider
        min_size_layout = QHBoxLayout()
        min_size_layout.addWidget(QLabel("Min Object Size:"))
        self.min_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_size_slider.setMinimum(10)
        self.min_size_slider.setMaximum(500)
        self.min_size_slider.setValue(50)
        self.min_size_slider.valueChanged.connect(self.on_min_size_changed)
        min_size_layout.addWidget(self.min_size_slider)
        self.min_size_label = QLabel("50px")
        min_size_layout.addWidget(self.min_size_label)
        basic_layout.addLayout(min_size_layout)
        
        # Max object size slider
        max_size_layout = QHBoxLayout()
        max_size_layout.addWidget(QLabel("Max Object Size:"))
        self.max_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_size_slider.setMinimum(100)
        self.max_size_slider.setMaximum(10000)
        self.max_size_slider.setValue(5000)
        self.max_size_slider.valueChanged.connect(self.on_max_size_changed)
        max_size_layout.addWidget(self.max_size_slider)
        self.max_size_label = QLabel("5000px")
        max_size_layout.addWidget(self.max_size_label)
        basic_layout.addLayout(max_size_layout)
        
        layout.addWidget(basic_group)
        
        # Advanced tracking controls
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QVBoxLayout()
        advanced_group.setLayout(advanced_layout)
        
        # Temporal smoothing frames slider
        temporal_layout = QHBoxLayout()
        temporal_layout.addWidget(QLabel("Temporal Smoothing:"))
        self.temporal_slider = QSlider(Qt.Orientation.Horizontal)
        self.temporal_slider.setMinimum(1)
        self.temporal_slider.setMaximum(500)
        self.temporal_slider.setValue(5)
        self.temporal_slider.valueChanged.connect(self.on_temporal_changed)
        temporal_layout.addWidget(self.temporal_slider)
        self.temporal_label = QLabel("5 frames")
        temporal_layout.addWidget(self.temporal_label)
        advanced_layout.addLayout(temporal_layout)
        
        # Max position jump slider
        jump_layout = QHBoxLayout()
        jump_layout.addWidget(QLabel("Max Position Jump:"))
        self.jump_slider = QSlider(Qt.Orientation.Horizontal)
        self.jump_slider.setMinimum(10)
        self.jump_slider.setMaximum(1000)
        self.jump_slider.setValue(100)
        self.jump_slider.valueChanged.connect(self.on_jump_changed)
        jump_layout.addWidget(self.jump_slider)
        self.jump_label = QLabel("100px")
        jump_layout.addWidget(self.jump_label)
        advanced_layout.addLayout(jump_layout)
        
        # Confidence threshold slider
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Threshold:"))
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setMinimum(0)
        self.confidence_slider.setMaximum(100)
        self.confidence_slider.setValue(30)
        self.confidence_slider.valueChanged.connect(self.on_confidence_changed)
        confidence_layout.addWidget(self.confidence_slider)
        self.confidence_label = QLabel("0.30")
        confidence_layout.addWidget(self.confidence_label)
        advanced_layout.addLayout(confidence_layout)
        
        # Morphology kernel size slider
        morph_layout = QHBoxLayout()
        morph_layout.addWidget(QLabel("Noise Reduction:"))
        self.morph_slider = QSlider(Qt.Orientation.Horizontal)
        self.morph_slider.setMinimum(0)
        self.morph_slider.setMaximum(50)
        self.morph_slider.setValue(3)
        self.morph_slider.valueChanged.connect(self.on_morph_changed)
        morph_layout.addWidget(self.morph_slider)
        self.morph_label = QLabel("3px")
        morph_layout.addWidget(self.morph_label)
        advanced_layout.addLayout(morph_layout)
        
        # Gaussian blur radius slider
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("Blur Radius:"))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(25)
        self.blur_slider.setValue(1)
        self.blur_slider.valueChanged.connect(self.on_blur_changed)
        blur_layout.addWidget(self.blur_slider)
        self.blur_label = QLabel("1px")
        blur_layout.addWidget(self.blur_label)
        advanced_layout.addLayout(blur_layout)
        
        layout.addWidget(advanced_group)
        
        # Preset buttons
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout()
        preset_group.setLayout(preset_layout)
        
        preset_row1 = QHBoxLayout()
        self.preset_indoor_btn = QPushButton("Indoor")
        self.preset_indoor_btn.clicked.connect(lambda: self.apply_preset("indoor"))
        preset_row1.addWidget(self.preset_indoor_btn)
        
        self.preset_outdoor_btn = QPushButton("Outdoor")
        self.preset_outdoor_btn.clicked.connect(lambda: self.apply_preset("outdoor"))
        preset_row1.addWidget(self.preset_outdoor_btn)
        
        preset_layout.addLayout(preset_row1)
        
        preset_row2 = QHBoxLayout()
        self.preset_stable_btn = QPushButton("Stable")
        self.preset_stable_btn.clicked.connect(lambda: self.apply_preset("stable"))
        preset_row2.addWidget(self.preset_stable_btn)
        
        self.preset_default_btn = QPushButton("Default")
        self.preset_default_btn.clicked.connect(lambda: self.apply_preset("default"))
        preset_row2.addWidget(self.preset_default_btn)
        
        preset_layout.addLayout(preset_row2)
        
        layout.addWidget(preset_group)
        
        # Save/Load settings buttons
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)
        
        settings_row = QHBoxLayout()
        self.save_tracking_btn = QPushButton("Save Settings")
        self.save_tracking_btn.clicked.connect(self.save_tracking_settings)
        settings_row.addWidget(self.save_tracking_btn)
        
        self.load_tracking_btn = QPushButton("Load Settings")
        self.load_tracking_btn.clicked.connect(self.load_tracking_settings)
        settings_row.addWidget(self.load_tracking_btn)
        
        settings_layout.addLayout(settings_row)
        
        layout.addWidget(settings_group)
        
        # Position display
        position_group = QGroupBox("Current Tracking Position")
        position_layout = QVBoxLayout()
        position_group.setLayout(position_layout)
        
        self.position_label = QLabel("Position: Not tracking")
        self.position_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        position_layout.addWidget(self.position_label)
        
        self.stability_label = QLabel("Stability: 0.0")
        self.stability_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        position_layout.addWidget(self.stability_label)
        
        self.confidence_display_label = QLabel("Confidence: 0.0")
        self.confidence_display_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        position_layout.addWidget(self.confidence_display_label)
        
        layout.addWidget(position_group)
        
        # Simple tracking mask view toggle
        mask_view_group = QGroupBox("Tracking Mask View")
        mask_view_layout = QVBoxLayout()
        mask_view_group.setLayout(mask_view_layout)
        
        self.show_tracking_mask_btn = QPushButton("Show Simple Tracking Mask")
        self.show_tracking_mask_btn.setCheckable(True)
        self.show_tracking_mask_btn.clicked.connect(self.toggle_tracking_mask_view)
        mask_view_layout.addWidget(self.show_tracking_mask_btn)
        
        layout.addWidget(mask_view_group)
    
    # Callback methods for sliders
    
    def on_proximity_changed(self, value):
        """Handle proximity threshold slider changes."""
        threshold = value / 100.0  # Convert to meters
        self.proximity_label.setText(f"{threshold:.2f}m")
        
        # Update the depth processor if available
        if self.app and hasattr(self.app, 'depth_processor'):
            self.app.depth_processor.set_proximity_threshold(threshold)
    
    def on_min_size_changed(self, value):
        """Handle minimum object size slider changes."""
        self.min_size_label.setText(f"{value}px")
        
        # Update the depth processor if available
        if self.app and hasattr(self.app, 'depth_processor'):
            max_size = self.max_size_slider.value()
            self.app.depth_processor.set_object_size_range(value, max_size)
    
    def on_max_size_changed(self, value):
        """Handle maximum object size slider changes."""
        self.max_size_label.setText(f"{value}px")
        
        # Update the depth processor if available
        if self.app and hasattr(self.app, 'depth_processor'):
            min_size = self.min_size_slider.value()
            self.app.depth_processor.set_object_size_range(min_size, value)
    
    def on_temporal_changed(self, value):
        """Handle temporal smoothing frames slider changes."""
        self.temporal_label.setText(f"{value} frames")
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.set_temporal_smoothing_frames(value)
    
    def on_jump_changed(self, value):
        """Handle max position jump slider changes."""
        self.jump_label.setText(f"{value}px")
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.set_max_position_jump(value)
    
    def on_confidence_changed(self, value):
        """Handle confidence threshold slider changes."""
        threshold = value / 100.0
        self.confidence_label.setText(f"{threshold:.2f}")
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.set_confidence_threshold(threshold)
    
    def on_morph_changed(self, value):
        """Handle morphology kernel size slider changes."""
        self.morph_label.setText(f"{value}px")
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.set_morphology_kernel_size(value)
    
    def on_blur_changed(self, value):
        """Handle Gaussian blur radius slider changes."""
        self.blur_label.setText(f"{value}px")
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.set_gaussian_blur_radius(value)
    
    def apply_preset(self, preset_name):
        """Apply a tracking preset."""
        if self.app and hasattr(self.app, 'simple_tracker'):
            self.app.simple_tracker.apply_preset(preset_name)
            # Update UI sliders to reflect preset values
            self.update_sliders_from_tracker()
            if hasattr(self.parent(), 'status_bar'):
                self.parent().status_bar.showMessage(f"Applied {preset_name} preset", 3000)
    
    def update_sliders_from_tracker(self):
        """Update UI sliders to match current tracker parameters."""
        if self.app and hasattr(self.app, 'simple_tracker'):
            params = self.app.simple_tracker.get_parameters()
            
            self.temporal_slider.setValue(params['temporal_smoothing_frames'])
            self.temporal_label.setText(f"{params['temporal_smoothing_frames']} frames")
            
            self.jump_slider.setValue(params['max_position_jump'])
            self.jump_label.setText(f"{params['max_position_jump']}px")
            
            confidence_percent = int(params['confidence_threshold'] * 100)
            self.confidence_slider.setValue(confidence_percent)
            self.confidence_label.setText(f"{params['confidence_threshold']:.2f}")
            
            self.morph_slider.setValue(params['morphology_kernel_size'])
            self.morph_label.setText(f"{params['morphology_kernel_size']}px")
            
            self.blur_slider.setValue(params['gaussian_blur_radius'])
            self.blur_label.setText(f"{params['gaussian_blur_radius']}px")
        
        # Also update basic sliders from depth processor
        if self.app and hasattr(self.app, 'depth_processor'):
            threshold = self.app.depth_processor.get_proximity_threshold()
            self.proximity_slider.setValue(int(threshold * 100))
            self.proximity_label.setText(f"{threshold:.2f}m")
            
            min_size, max_size = self.app.depth_processor.get_object_size_range()
            self.min_size_slider.setValue(min_size)
            self.min_size_label.setText(f"{min_size}px")
            self.max_size_slider.setValue(max_size)
            self.max_size_label.setText(f"{max_size}px")
    
    def save_tracking_settings(self):
        """Save current tracking settings to a file."""
        if not self.app or not hasattr(self.app, 'simple_tracker'):
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Tracking Settings", 
            os.path.join(self.config_dir, "tracking_settings.json"),
            "JSON Files (*.json)"
        )
        
        if filepath:
            if self.app.simple_tracker.save_settings(filepath):
                if hasattr(self.parent(), 'status_bar'):
                    self.parent().status_bar.showMessage(f"Settings saved to {os.path.basename(filepath)}", 3000)
    
    def load_tracking_settings(self):
        """Load tracking settings from a file."""
        if not self.app or not hasattr(self.app, 'simple_tracker'):
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Tracking Settings", 
            self.config_dir,
            "JSON Files (*.json)"
        )
        
        if filepath:
            if self.app.simple_tracker.load_settings(filepath):
                self.update_sliders_from_tracker()
                if hasattr(self.parent(), 'status_bar'):
                    self.parent().status_bar.showMessage(f"Settings loaded from {os.path.basename(filepath)}", 3000)
    
    def update_tracking_position_display(self, simple_tracking_result):
        """Update the position display with current tracking data."""
        if simple_tracking_result:
            stable_pos = simple_tracking_result.get('stable_position')
            confidence = simple_tracking_result.get('confidence', 0.0)
            stability = simple_tracking_result.get('stability_score', 0.0)
            
            if stable_pos:
                self.position_label.setText(f"Position: ({stable_pos[0]}, {stable_pos[1]})")
            else:
                self.position_label.setText("Position: Not tracking")
            
            self.confidence_display_label.setText(f"Confidence: {confidence:.2f}")
            self.stability_label.setText(f"Stability: {stability:.2f}")
        else:
            self.position_label.setText("Position: Not tracking")
            self.confidence_display_label.setText("Confidence: 0.00")
            self.stability_label.setText("Stability: 0.00")
    
    def toggle_tracking_mask_view(self, checked):
        """Toggle the simple tracking mask view in the main window."""
        if self.app and hasattr(self.app, 'main_window'):
            # Use the main window's toggle method to keep everything in sync
            self.app.main_window.toggle_simple_tracking_mask(checked)