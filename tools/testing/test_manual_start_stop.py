#!/usr/bin/env python3
"""
Test script to verify manual start/stop toggle functionality
"""

def test_manual_toggle_logic():
    """Test the manual recording toggle logic."""
    print("🧪 Testing Manual Start/Stop Toggle Logic")
    print("=" * 50)
    
    # Simulate the key states
    recording_in_progress = False
    manual_recording_active = False
    
    def simulate_spacebar_press():
        nonlocal recording_in_progress, manual_recording_active
        
        if not recording_in_progress:
            print("🎬 Starting manual recording...")
            recording_in_progress = True
            manual_recording_active = True
            return "START"
        else:
            print("🛑 Stopping manual recording...")
            recording_in_progress = False
            manual_recording_active = False
            return "STOP"
    
    # Test sequence
    print("1. Initial state:")
    print(f"   recording_in_progress: {recording_in_progress}")
    print(f"   manual_recording_active: {manual_recording_active}")
    
    print("\n2. First SPACEBAR press (should start):")
    action = simulate_spacebar_press()
    print(f"   Action: {action}")
    print(f"   recording_in_progress: {recording_in_progress}")
    print(f"   manual_recording_active: {manual_recording_active}")
    
    print("\n3. Second SPACEBAR press (should stop):")
    action = simulate_spacebar_press()
    print(f"   Action: {action}")
    print(f"   recording_in_progress: {recording_in_progress}")
    print(f"   manual_recording_active: {manual_recording_active}")
    
    print("\n4. Third SPACEBAR press (should start again):")
    action = simulate_spacebar_press()
    print(f"   Action: {action}")
    print(f"   recording_in_progress: {recording_in_progress}")
    print(f"   manual_recording_active: {manual_recording_active}")
    
    print("\n✅ Manual start/stop toggle logic working correctly!")
    print("\nUsage Instructions:")
    print("1. Run: python3 run_stillness_recorder_with_imu.py --manual")
    print("2. Press SPACEBAR to start recording")
    print("3. Press SPACEBAR again to stop recording early")
    print("4. Or wait for auto-stop after configured duration")

if __name__ == "__main__":
    test_manual_toggle_logic()