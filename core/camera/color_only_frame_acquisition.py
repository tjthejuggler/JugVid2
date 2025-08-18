import pyrealsense2 as rs
import numpy as np
import cv2
import time
import threading
from collections import deque

class ColorOnlyFrameAcquisition:
    """
    Handles RealSense camera setup for COLOR STREAM ONLY.
    
    This is a simplified version that only captures color frames,
    avoiding the bandwidth issues with depth+color streams.
    """
    
    def __init__(self, width=640, height=480, fps=30):
        """
        Initialize the ColorOnlyFrameAcquisition module.
        
        Args:
            width (int): Width of the camera frames
            height (int): Height of the camera frames
            fps (int): Frames per second for camera configuration
        """
        self.width = width
        self.height = height
        self.fps = fps
        
        self.pipeline = None
        self.config = None
        
        # Thread-safe frame buffering for recording
        self._frame_buffer = deque(maxlen=10)  # Keep last 10 frames
        self._buffer_lock = threading.Lock()
        self._frame_thread = None
        self._stop_thread = False
        self._last_frame = None
        self._last_frame_time = 0
        
    def initialize(self):
        """
        Initialize the RealSense pipeline with multiple fallback strategies.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        print("🔧 Attempting RealSense initialization with multiple strategies...")
        
        # Strategy 1: Reset and reinitialize context
        try:
            print("Strategy 1: Fresh context initialization...")
            ctx = rs.context()
            devices = ctx.query_devices()
            print(f"Found {len(devices)} RealSense devices")
            
            if len(devices) == 0:
                print("❌ No RealSense devices found")
                return False
            
            device = devices[0]
            print(f"Device: {device.get_info(rs.camera_info.name)} - Serial: {device.get_info(rs.camera_info.serial_number)}")
            
            # Try to reset the device
            try:
                device.hardware_reset()
                print("🔄 Device hardware reset successful")
                time.sleep(2)  # Wait for device to reinitialize
                
                # Re-query devices after reset
                ctx = rs.context()
                devices = ctx.query_devices()
                if len(devices) == 0:
                    print("❌ Device not found after reset")
                    return False
                device = devices[0]
            except Exception as reset_error:
                print(f"⚠️  Hardware reset failed: {reset_error}")
            
            # Try multiple resolution configurations
            configs_to_try = [
                (640, 480, 30),
                (640, 480, 15),
                (320, 240, 30),
                (1280, 720, 30),
                (1280, 720, 15)
            ]
            
            for width, height, fps in configs_to_try:
                try:
                    print(f"🎯 Trying configuration: {width}x{height} @ {fps}fps")
                    
                    self.pipeline = rs.pipeline(ctx)
                    self.config = rs.config()
                    
                    # Enable color stream with current config
                    self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
                    
                    # Start pipeline
                    profile = self.pipeline.start(self.config)
                    
                    # Verify stream is active
                    color_profile = profile.get_stream(rs.stream.color).as_video_stream_profile()
                    actual_width = color_profile.width()
                    actual_height = color_profile.height()
                    actual_fps = color_profile.fps()
                    
                    print(f"✅ Pipeline started successfully!")
                    print(f"   Actual resolution: {actual_width}x{actual_height} @ {actual_fps}fps")
                    
                    # Update our settings to match actual
                    self.width, self.height, self.fps = actual_width, actual_height, actual_fps
                    
                    # Try to get a test frame to verify it's really working
                    print("🧪 Testing frame acquisition...")
                    for attempt in range(10):
                        try:
                            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                            color_frame = frames.get_color_frame()
                            if color_frame:
                                color_image = np.asanyarray(color_frame.get_data())
                                if color_image is not None and color_image.size > 0:
                                    print(f"✅ Test frame acquired successfully! Shape: {color_image.shape}")
                                    
                                    # Start background frame acquisition thread
                                    self._start_frame_thread()
                                    return True
                                else:
                                    print(f"⚠️  Test frame {attempt+1}: Invalid data")
                            else:
                                print(f"⚠️  Test frame {attempt+1}: No color frame")
                        except Exception as frame_error:
                            print(f"⚠️  Test frame {attempt+1}: {frame_error}")
                        
                        time.sleep(0.1)
                    
                    print("❌ Failed to acquire test frames, trying next configuration...")
                    self.pipeline.stop()
                    self.pipeline = None
                    
                except Exception as config_error:
                    print(f"❌ Configuration {width}x{height}@{fps} failed: {config_error}")
                    if self.pipeline:
                        try:
                            self.pipeline.stop()
                        except:
                            pass
                        self.pipeline = None
                    continue
            
            print("❌ All configurations failed")
            return False
            
        except Exception as e:
            print(f"❌ Strategy 1 failed completely: {e}")
            import traceback
            traceback.print_exc()
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except:
                    pass
                self.pipeline = None
            return False
    
    def _start_frame_thread(self):
        """Start background thread for continuous frame acquisition."""
        if self._frame_thread is None or not self._frame_thread.is_alive():
            self._stop_thread = False
            self._frame_thread = threading.Thread(target=self._frame_acquisition_loop, daemon=True)
            self._frame_thread.start()
            print("✅ Started background frame acquisition thread")
    
    def _frame_acquisition_loop(self):
        """Background thread that continuously acquires frames from RealSense."""
        consecutive_errors = 0
        max_consecutive_errors = 100
        
        while not self._stop_thread and self.pipeline is not None:
            try:
                # Get frames with reasonable timeout
                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                color_frame = frames.get_color_frame()
                
                if color_frame:
                    color_image = np.asanyarray(color_frame.get_data())
                    if color_image is not None and color_image.size > 0:
                        current_time = time.time()
                        
                        # Store frame in thread-safe buffer
                        with self._buffer_lock:
                            self._frame_buffer.append((current_time, color_frame, color_image.copy()))
                            self._last_frame = color_image.copy()
                            self._last_frame_time = current_time
                        
                        consecutive_errors = 0
                        
                        # Occasionally log successful acquisition
                        if hasattr(self, '_frame_count'):
                            self._frame_count += 1
                        else:
                            self._frame_count = 1
                            
                        if self._frame_count % 1000 == 0:
                            print(f"Background thread: {self._frame_count} frames acquired")
                    else:
                        consecutive_errors += 1
                else:
                    consecutive_errors += 1
                    
            except RuntimeError as e:
                consecutive_errors += 1
                if consecutive_errors % 50 == 1:
                    print(f"Background thread: {consecutive_errors} consecutive errors")
                    
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print(f"Background thread error: {e}")
            
            # If too many consecutive errors, stop the thread
            if consecutive_errors > max_consecutive_errors:
                print("Background thread: Too many errors, stopping")
                break
                
            # Small delay to prevent excessive CPU usage
            time.sleep(0.001)
        
        print("Background frame acquisition thread stopped")
    
    def get_frames(self, recording_mode=False):
        """
        Get color frame from RealSense camera using thread-safe buffered approach.
        
        Args:
            recording_mode (bool): If True, prioritize getting fresh frames for recording
        
        Returns:
            tuple: (None, color_frame, None, color_image) - maintaining compatibility with original interface
        """
        if self.pipeline is None:
            print("Pipeline not initialized. Call initialize() first.")
            return None, None, None, None
        
        # Ensure background thread is running
        if self._frame_thread is None or not self._frame_thread.is_alive():
            self._start_frame_thread()
            time.sleep(0.1)  # Give thread time to start
        
        try:
            with self._buffer_lock:
                if recording_mode:
                    # During recording, try to get the most recent frame from buffer
                    if self._frame_buffer:
                        timestamp, color_frame, color_image = self._frame_buffer[-1]
                        # Check if frame is recent (within last 200ms)
                        if time.time() - timestamp < 0.2:
                            return None, color_frame, None, color_image
                
                # Fallback to last known good frame
                if self._last_frame is not None:
                    # Check if frame is reasonably recent (within last 1 second)
                    if time.time() - self._last_frame_time < 1.0:
                        return None, None, None, self._last_frame.copy()
            
            # If no recent frames available, return None
            return None, None, None, None
                
        except Exception as e:
            print(f"Error getting buffered frame: {e}")
            return None, None, None, None
    
    def stop(self):
        """Stop the RealSense pipeline and background thread."""
        # Stop background thread first
        self._stop_thread = True
        if self._frame_thread and self._frame_thread.is_alive():
            self._frame_thread.join(timeout=2.0)
            print("Background frame thread stopped.")
        
        # Clear buffers
        with self._buffer_lock:
            self._frame_buffer.clear()
            self._last_frame = None
        
        # Stop pipeline
        if self.pipeline:
            try:
                self.pipeline.stop()
                print("RealSense COLOR ONLY pipeline stopped.")
            except RuntimeError as e:
                print(f"Error stopping pipeline: {e}")
            finally:
                self.pipeline = None

def main():
    """Test the color-only frame acquisition."""
    acquisition = ColorOnlyFrameAcquisition(width=640, height=480, fps=30)
    
    if not acquisition.initialize():
        print("Failed to initialize!")
        return
    
    print("Testing color-only frame acquisition...")
    print("Press 'q' to quit")
    
    try:
        frame_count = 0
        while True:
            depth_frame, color_frame, depth_image, color_image = acquisition.get_frames()
            
            if color_image is not None:
                frame_count += 1
                cv2.putText(color_image, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow('RealSense Color Only', color_image)
                
                if frame_count % 30 == 0:  # Print every 30 frames
                    print(f"Frames received: {frame_count}")
            else:
                print("No frame received")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        acquisition.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()