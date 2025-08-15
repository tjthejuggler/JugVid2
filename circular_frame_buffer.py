import numpy as np
import cv2
import time
from collections import deque
import threading

class CircularFrameBuffer:
    """
    A circular buffer that stores video frames with timestamps.
    
    This buffer maintains a rolling window of the most recent frames,
    automatically discarding old frames when the buffer reaches capacity.
    Thread-safe for concurrent read/write operations.
    """
    
    def __init__(self, max_duration_seconds=10.0, fps=30):
        """
        Initialize the circular frame buffer.
        
        Args:
            max_duration_seconds (float): Maximum duration of frames to store
            fps (int): Expected frames per second (used to calculate buffer size)
        """
        self.max_duration = max_duration_seconds
        self.fps = fps
        self.max_frames = int(max_duration_seconds * fps * 1.2)  # 20% buffer for safety
        
        # Thread-safe deque for storing frames with timestamps
        self.frames = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
        
        # Statistics
        self.total_frames_added = 0
        self.buffer_start_time = None
        
    def add_frame(self, frame, timestamp=None):
        """
        Add a frame to the buffer.
        
        Args:
            frame (numpy.ndarray): Video frame to add
            timestamp (float, optional): Frame timestamp. If None, uses current time.
        """
        if frame is None:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        # Make a copy of the frame to avoid reference issues
        frame_copy = frame.copy()
        
        with self.lock:
            self.frames.append((timestamp, frame_copy))
            self.total_frames_added += 1
            
            if self.buffer_start_time is None:
                self.buffer_start_time = timestamp
                
            # Clean up old frames that exceed the duration limit
            self._cleanup_old_frames(timestamp)
    
    def _cleanup_old_frames(self, current_timestamp):
        """
        Remove frames older than max_duration from the buffer.
        
        Args:
            current_timestamp (float): Current timestamp for comparison
        """
        cutoff_time = current_timestamp - self.max_duration
        
        # Remove frames from the left (oldest) that are too old
        while self.frames and self.frames[0][0] < cutoff_time:
            self.frames.popleft()
    
    def get_frames_in_duration(self, duration_seconds):
        """
        Get all frames from the last N seconds.
        
        Args:
            duration_seconds (float): Duration in seconds to retrieve
            
        Returns:
            list: List of (timestamp, frame) tuples in chronological order
        """
        if duration_seconds <= 0:
            return []
            
        current_time = time.time()
        cutoff_time = current_time - duration_seconds
        
        with self.lock:
            # Get frames newer than cutoff_time
            recent_frames = []
            for timestamp, frame in self.frames:
                if timestamp >= cutoff_time:
                    recent_frames.append((timestamp, frame))
            
            return recent_frames
    
    def get_all_frames(self):
        """
        Get all frames currently in the buffer.
        
        Returns:
            list: List of (timestamp, frame) tuples in chronological order
        """
        with self.lock:
            return list(self.frames)
    
    def get_frame_count(self):
        """
        Get the current number of frames in the buffer.
        
        Returns:
            int: Number of frames currently stored
        """
        with self.lock:
            return len(self.frames)
    
    def get_duration_range(self):
        """
        Get the time range of frames currently in the buffer.
        
        Returns:
            tuple: (oldest_timestamp, newest_timestamp, duration_seconds)
        """
        with self.lock:
            if not self.frames:
                return None, None, 0.0
                
            oldest_timestamp = self.frames[0][0]
            newest_timestamp = self.frames[-1][0]
            duration = newest_timestamp - oldest_timestamp
            
            return oldest_timestamp, newest_timestamp, duration
    
    def get_buffer_stats(self):
        """
        Get buffer statistics.
        
        Returns:
            dict: Buffer statistics including size, duration, fps, etc.
        """
        with self.lock:
            frame_count = len(self.frames)
            oldest_ts, newest_ts, duration = self.get_duration_range()
            
            # Calculate actual FPS based on buffer contents
            actual_fps = 0.0
            if duration > 0 and frame_count > 1:
                actual_fps = (frame_count - 1) / duration
            
            return {
                'frame_count': frame_count,
                'max_frames': self.max_frames,
                'buffer_duration': duration,
                'max_duration': self.max_duration,
                'actual_fps': actual_fps,
                'expected_fps': self.fps,
                'total_frames_added': self.total_frames_added,
                'buffer_utilization': frame_count / self.max_frames if self.max_frames > 0 else 0.0
            }
    
    def clear(self):
        """Clear all frames from the buffer."""
        with self.lock:
            self.frames.clear()
            self.buffer_start_time = None
    
    def update_max_duration(self, new_duration_seconds):
        """
        Update the maximum duration and adjust buffer size accordingly.
        
        Args:
            new_duration_seconds (float): New maximum duration in seconds
        """
        self.max_duration = new_duration_seconds
        self.max_frames = int(new_duration_seconds * self.fps * 1.2)
        
        with self.lock:
            # Create new deque with updated max length
            old_frames = list(self.frames)
            self.frames = deque(old_frames, maxlen=self.max_frames)
            
            # Clean up frames that are now too old
            if old_frames:
                current_time = old_frames[-1][0]  # Use timestamp of most recent frame
                self._cleanup_old_frames(current_time)

class FrameBufferRecorder:
    """
    Helper class to record frames from the circular buffer to video files.
    """
    
    def __init__(self, output_dir="recordings"):
        """
        Initialize the frame buffer recorder.
        
        Args:
            output_dir (str): Directory to save recorded videos
        """
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def save_frames_to_video(self, frames, filename=None, fps=30):
        """
        Save a list of frames to a video file.
        
        Args:
            frames (list): List of (timestamp, frame) tuples
            filename (str, optional): Output filename. If None, generates timestamp-based name.
            fps (int): Output video FPS
            
        Returns:
            str: Path to the saved video file, or None if failed
        """
        if not frames:
            print("No frames to save")
            return None
        
        # Generate filename if not provided
        if filename is None:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(frames[0][0]))
            filename = f"stillness_recording_{timestamp_str}.mp4"
        
        # Ensure filename has correct extension
        if not filename.endswith(('.mp4', '.avi', '.mov')):
            filename += '.mp4'
        
        import os
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            # Get frame dimensions from first frame
            first_frame = frames[0][1]
            height, width = first_frame.shape[:2]
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not video_writer.isOpened():
                print(f"Error: Could not open video writer for {output_path}")
                return None
            
            # Write frames to video
            frames_written = 0
            for timestamp, frame in frames:
                video_writer.write(frame)
                frames_written += 1
            
            video_writer.release()
            
            duration = frames[-1][0] - frames[0][0]
            print(f"Saved {frames_written} frames ({duration:.2f}s) to {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"Error saving video to {output_path}: {e}")
            return None

def test_circular_buffer():
    """Test the circular frame buffer with simulated frames."""
    print("Testing Circular Frame Buffer...")
    
    # Create buffer for 5 seconds at 10 FPS
    buffer = CircularFrameBuffer(max_duration_seconds=5.0, fps=10)
    
    # Create some test frames
    frame_width, frame_height = 320, 240
    
    print("Adding frames to buffer...")
    start_time = time.time()
    
    for i in range(60):  # Add 60 frames over 6 seconds
        # Create a test frame with frame number
        frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Add frame with simulated timestamp
        timestamp = start_time + (i * 0.1)  # 10 FPS
        buffer.add_frame(frame, timestamp)
        
        # Print stats every 10 frames
        if i % 10 == 0:
            stats = buffer.get_buffer_stats()
            print(f"Frame {i}: Buffer has {stats['frame_count']} frames, "
                  f"duration: {stats['buffer_duration']:.2f}s, "
                  f"utilization: {stats['buffer_utilization']:.1%}")
    
    # Test getting frames from last 3 seconds
    print("\nTesting frame retrieval...")
    recent_frames = buffer.get_frames_in_duration(3.0)
    print(f"Retrieved {len(recent_frames)} frames from last 3 seconds")
    
    # Test recording to video
    print("\nTesting video recording...")
    recorder = FrameBufferRecorder()
    output_path = recorder.save_frames_to_video(recent_frames, "test_recording.mp4", fps=10)
    
    if output_path:
        print(f"Test video saved to: {output_path}")
    
    # Final stats
    final_stats = buffer.get_buffer_stats()
    print(f"\nFinal buffer stats:")
    for key, value in final_stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_circular_buffer()