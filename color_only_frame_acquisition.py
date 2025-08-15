import pyrealsense2 as rs
import numpy as np
import cv2

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
        
    def initialize(self):
        """
        Initialize the RealSense pipeline for COLOR ONLY.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            print("Initializing RealSense for COLOR ONLY mode...")
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # Enable ONLY color stream (no depth to avoid bandwidth issues)
            self.config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            
            print(f"Starting color stream: {self.width}x{self.height} @ {self.fps}fps")
            profile = self.pipeline.start(self.config)
            
            print("RealSense COLOR ONLY mode initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Error initializing RealSense COLOR ONLY mode: {e}")
            self.pipeline = None
            return False
    
    def get_frames(self):
        """
        Get color frame from RealSense camera.
        
        Returns:
            tuple: (None, color_frame, None, color_image) - maintaining compatibility with original interface
        """
        if self.pipeline is None:
            print("Pipeline not initialized. Call initialize() first.")
            return None, None, None, None
        
        try:
            # Wait for frames (color only)
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            
            color_frame = frames.get_color_frame()
            
            if not color_frame:
                print("No color frame received")
                return None, None, None, None
            
            # Convert to numpy array
            color_image = np.asanyarray(color_frame.get_data())
            
            # Return in format compatible with original FrameAcquisition
            # (depth_frame, color_frame, depth_image, color_image)
            return None, color_frame, None, color_image
            
        except RuntimeError as e:
            print(f"Error getting frames: {e}")
            return None, None, None, None
        except Exception as e:
            print(f"Unexpected error getting frames: {e}")
            return None, None, None, None
    
    def stop(self):
        """Stop the RealSense pipeline."""
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