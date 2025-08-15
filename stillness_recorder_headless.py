#!/usr/bin/env python3
"""
Stillness Recorder (Headless) - Motion-triggered video recorder without GUI

This version works without requiring a display/GUI and provides console-based feedback.
Perfect for headless environments or when GUI display is not available.
"""

import cv2
import numpy as np
import time
import threading
import argparse
import os
from datetime import datetime

# Import our custom modules
try:
    from color_only_frame_acquisition import ColorOnlyFrameAcquisition
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    print("Warning: RealSense modules not available")

from motion_detector import MotionDetector
from circular_frame_buffer import CircularFrameBuffer, FrameBufferRecorder

class StillnessRecorderHeadless:
    """
    Headless version of the stillness-triggered recorder.
    """
    
    def __init__(self, 
                 record_duration=10.0,
                 motion_threshold=1000,
                 stillness_duration=3.0,
                 output_dir="recordings",
                 camera_width=640,
                 camera_height=480,
                 camera_fps=30,
                 max_runtime=300):  # 5 minutes default
        """
        Initialize the headless stillness recorder.
        """
        self.record_duration = record_duration
        self.motion_threshold = motion_threshold
        self.stillness_duration = stillness_duration
        self.output_dir = output_dir
        self.max_runtime = max_runtime
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.camera = None
        self.use_webcam = False
        self.webcam_capture = None
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.camera_fps = camera_fps
        
        self.motion_detector = MotionDetector(motion_threshold, stillness_duration)
        self.frame_buffer = CircularFrameBuffer(record_duration + 2.0, camera_fps)
        self.recorder = FrameBufferRecorder(output_dir)
        
        # Application state
        self.running = False
        self.recording_in_progress = False
        self.total_recordings = 0
        self.last_recording_time = None
        
        # Statistics
        self.frame_count = 0
        self.start_time = None
        self.last_status_time = 0
        
    def initialize(self):
        """Initialize the camera and other components."""
        print("Initializing Headless Stillness Recorder...")
        print(f"Record Duration: {self.record_duration}s")
        print(f"Motion Threshold: {self.motion_threshold}")
        print(f"Stillness Duration: {self.stillness_duration}s")
        print(f"Output Directory: {self.output_dir}")
        print(f"Max Runtime: {self.max_runtime}s")
        
        # Try RealSense first
        if REALSENSE_AVAILABLE:
            print("Attempting to initialize RealSense camera...")
            try:
                self.camera = ColorOnlyFrameAcquisition(self.camera_width, self.camera_height, self.camera_fps)
                if self.camera.initialize():
                    print("✓ RealSense camera initialized successfully!")
                    self.use_webcam = False
                    return True
                else:
                    print("✗ RealSense camera initialization failed")
            except Exception as e:
                print(f"✗ RealSense camera error: {e}")
        
        # Fallback to webcam
        print("Attempting to initialize webcam...")
        try:
            self.webcam_capture = cv2.VideoCapture(0)
            if self.webcam_capture.isOpened():
                # Set webcam properties
                self.webcam_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
                self.webcam_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
                self.webcam_capture.set(cv2.CAP_PROP_FPS, self.camera_fps)
                
                # Test frame capture
                ret, test_frame = self.webcam_capture.read()
                if ret and test_frame is not None:
                    print("✓ Webcam initialized successfully!")
                    self.use_webcam = True
                    return True
                else:
                    print("✗ Webcam test frame failed")
            else:
                print("✗ Could not open webcam")
        except Exception as e:
            print(f"✗ Webcam error: {e}")
        
        print("✗ Failed to initialize any camera source")
        return False
    
    def process_frame(self, frame):
        """Process a single frame for motion detection and recording."""
        if frame is None:
            return None
            
        # Add frame to circular buffer
        self.frame_buffer.add_frame(frame)
        
        # Detect motion
        motion_value, is_motion, motion_mask = self.motion_detector.detect_motion(frame)
        
        # Check for stillness trigger
        stillness_triggered = self.motion_detector.check_stillness(motion_value)
        
        # Handle recording trigger
        if stillness_triggered and not self.recording_in_progress:
            self.trigger_recording()
        
        # Get motion statistics
        motion_stats = self.motion_detector.get_motion_stats()
        
        return {
            'motion_value': motion_value,
            'is_motion': is_motion,
            'motion_stats': motion_stats,
            'stillness_triggered': stillness_triggered
        }
    
    def trigger_recording(self):
        """Trigger a recording of the last X seconds."""
        if self.recording_in_progress:
            print("Recording already in progress, skipping trigger")
            return
        
        print(f"🎯 STILLNESS DETECTED! Triggering recording of last {self.record_duration} seconds...")
        
        # Start recording in a separate thread to avoid blocking
        recording_thread = threading.Thread(target=self._save_recording)
        recording_thread.daemon = True
        recording_thread.start()
    
    def _save_recording(self):
        """Save the recording (runs in separate thread)."""
        self.recording_in_progress = True
        
        try:
            # Get frames from the buffer
            frames = self.frame_buffer.get_frames_in_duration(self.record_duration)
            
            if not frames:
                print("No frames available for recording")
                return
            
            # Generate filename with timestamp
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stillness_recording_{timestamp_str}.mp4"
            
            # Save the video
            output_path = self.recorder.save_frames_to_video(frames, filename, fps=30)
            
            if output_path:
                self.total_recordings += 1
                self.last_recording_time = time.time()
                print(f"✅ Recording saved: {output_path}")
                print(f"📊 Total recordings: {self.total_recordings}")
            else:
                print("❌ Failed to save recording")
                
        except Exception as e:
            print(f"❌ Error during recording: {e}")
        finally:
            self.recording_in_progress = False
    
    def print_status(self, motion_info):
        """Print status information to console."""
        current_time = time.time()
        
        # Print status every 5 seconds
        if current_time - self.last_status_time >= 5.0:
            motion_stats = motion_info['motion_stats']
            runtime = current_time - self.start_time
            fps = self.frame_count / runtime if runtime > 0 else 0
            
            print(f"\n📊 STATUS UPDATE (Runtime: {runtime:.1f}s)")
            print(f"   Frames processed: {self.frame_count} (FPS: {fps:.1f})")
            print(f"   Motion: {motion_stats['current_motion']:.0f} (Threshold: {self.motion_threshold})")
            print(f"   Still: {motion_stats['is_still']} (Duration: {motion_stats['stillness_duration']:.1f}s)")
            print(f"   Recordings: {self.total_recordings}")
            
            # Buffer stats
            buffer_stats = self.frame_buffer.get_buffer_stats()
            print(f"   Buffer: {buffer_stats['frame_count']} frames ({buffer_stats['buffer_duration']:.1f}s)")
            
            if self.recording_in_progress:
                print("   🔴 SAVING VIDEO...")
            
            self.last_status_time = current_time
    
    def run(self):
        """Main application loop."""
        if not self.initialize():
            return False
        
        print("\n🚀 Headless Stillness Recorder Started!")
        print("The application will automatically record video when stillness is detected.")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        self.running = True
        self.start_time = time.time()
        self.last_status_time = self.start_time
        
        try:
            while self.running:
                # Check max runtime
                if time.time() - self.start_time > self.max_runtime:
                    print(f"\n⏰ Max runtime ({self.max_runtime}s) reached, stopping...")
                    break
                
                # Get frame from camera
                frame = None
                
                if self.use_webcam and self.webcam_capture:
                    ret, frame = self.webcam_capture.read()
                    if not ret:
                        print("Failed to read from webcam")
                        break
                elif self.camera:
                    _, _, _, frame = self.camera.get_frames()
                
                if frame is not None:
                    self.frame_count += 1
                    
                    # Process frame
                    motion_info = self.process_frame(frame)
                    
                    if motion_info:
                        # Print status updates
                        self.print_status(motion_info)
                        
                        # Check for stillness trigger
                        if motion_info['stillness_triggered']:
                            print("🎯 STILLNESS TRIGGER ACTIVATED!")
                else:
                    print("⚠️  No frame received from camera")
                    time.sleep(0.1)  # Brief pause to avoid busy loop
                        
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        self.running = False
        
        # Stop camera
        if self.camera:
            self.camera.stop()
        
        # Release webcam
        if self.webcam_capture:
            self.webcam_capture.release()
        
        # Print final statistics
        if self.start_time:
            runtime = time.time() - self.start_time
            fps = self.frame_count / runtime if runtime > 0 else 0
            print(f"\n📈 FINAL STATISTICS:")
            print(f"   Runtime: {runtime:.1f} seconds")
            print(f"   Frames processed: {self.frame_count}")
            print(f"   Average FPS: {fps:.1f}")
            print(f"   Total recordings: {self.total_recordings}")
            print(f"   Output directory: {self.output_dir}")
            
            if self.total_recordings > 0:
                print(f"🎉 Successfully captured {self.total_recordings} stillness events!")
            else:
                print("ℹ️  No stillness events detected during this session.")

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Headless Stillness Recorder - Motion-triggered video recorder")
    
    parser.add_argument('--record-duration', type=float, default=10.0,
                       help='Duration in seconds to record when stillness is detected (default: 10.0)')
    parser.add_argument('--motion-threshold', type=float, default=1000,
                       help='Motion threshold for stillness detection (default: 1000)')
    parser.add_argument('--stillness-duration', type=float, default=3.0,
                       help='Duration of stillness required to trigger recording (default: 3.0)')
    parser.add_argument('--output-dir', type=str, default='recordings',
                       help='Directory to save recorded videos (default: recordings)')
    parser.add_argument('--max-runtime', type=int, default=300,
                       help='Maximum runtime in seconds (default: 300)')
    parser.add_argument('--camera-width', type=int, default=640,
                       help='Camera frame width (default: 640)')
    parser.add_argument('--camera-height', type=int, default=480,
                       help='Camera frame height (default: 480)')
    parser.add_argument('--camera-fps', type=int, default=30,
                       help='Camera frames per second (default: 30)')
    
    args = parser.parse_args()
    
    # Create and run the recorder
    recorder = StillnessRecorderHeadless(
        record_duration=args.record_duration,
        motion_threshold=args.motion_threshold,
        stillness_duration=args.stillness_duration,
        output_dir=args.output_dir,
        max_runtime=args.max_runtime,
        camera_width=args.camera_width,
        camera_height=args.camera_height,
        camera_fps=args.camera_fps
    )
    
    success = recorder.run()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())