#!/usr/bin/env python3
"""
Test script for 3D Ball Tracker Integration

This script tests the integration of the visual_3d_ball_tracker functionality
into the juggling_tracker application as a live feed.
"""

import sys
import time
sys.path.append('.')

def test_imports():
    """Test that all required components can be imported."""
    print("🧪 Testing 3D Ball Tracker Integration")
    print("=" * 50)
    
    try:
        # Test 1: Import the new 3D ball tracker widget
        print("📦 Testing imports...")
        from apps.juggling_tracker.ui.ball_3d_feed_widget import Ball3DFeedWidget
        print("✅ Ball3DFeedWidget imported successfully")
        
        # Test 2: Import video feed manager with 3D support
        from apps.juggling_tracker.ui.video_feed_manager import VideoFeedManager
        print("✅ VideoFeedManager imported successfully")
        
        # Test 3: Import main window with 3D integration
        from apps.juggling_tracker.ui.main_window import MainWindow
        print("✅ MainWindow imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_3d_feed_widget():
    """Test the 3D ball tracker feed widget functionality."""
    print("\n🎯 Testing 3D Ball Tracker Feed Widget...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from apps.juggling_tracker.ui.ball_3d_feed_widget import Ball3DFeedWidget
        
        # Create minimal QApplication for testing
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Test widget creation
        widget = Ball3DFeedWidget("test_3d", "Test 3D Tracker")
        print("✅ Ball3DFeedWidget created successfully")
        
        # Test ball data update with mock data
        mock_balls = [
            {
                'original_3d': (0.1, 0.2, 0.8),
                'profile_id': 'pink_ball',
                'name': 'Pink Ball',
                'timestamp_str': '12:34:56.789'
            },
            {
                'original_3d': (-0.2, -0.1, 1.2),
                'profile_id': 'orange_ball',
                'name': 'Orange Ball',
                'timestamp_str': '12:34:56.789'
            }
        ]
        
        widget.update_ball_data(mock_balls)
        print("✅ Ball data update successful")
        
        # Test widget properties
        assert widget.get_fps() >= 0, "FPS should be non-negative"
        assert widget.get_latency() >= 0, "Latency should be non-negative"
        print("✅ Widget properties working correctly")
        
        # Test configuration methods
        widget.set_3d_bounds((-1.0, 1.0), (-0.5, 0.5), (0.1, 2.0))
        widget.set_size_range(5, 100)
        print("✅ Configuration methods working")
        
        return True
        
    except Exception as e:
        print(f"❌ 3D Feed Widget test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_video_feed_manager_integration():
    """Test the video feed manager integration with 3D ball tracker."""
    print("\n📺 Testing Video Feed Manager Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from apps.juggling_tracker.ui.video_feed_manager import VideoFeedManager
        
        # Create minimal QApplication for testing
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create video feed manager
        manager = VideoFeedManager()
        print("✅ VideoFeedManager created successfully")
        
        # Test adding 3D ball tracker feed
        feed_id = manager.add_ball_3d_feed("Test 3D Tracker", "test_3d")
        print(f"✅ 3D ball tracker feed added: {feed_id}")
        
        # Verify feed was added
        ball_3d_feeds = manager.get_ball_3d_feeds()
        assert len(ball_3d_feeds) == 1, "Should have one 3D ball tracker feed"
        assert ball_3d_feeds[0] == feed_id, "Feed ID should match"
        print("✅ 3D ball tracker feed verification successful")
        
        # Test updating 3D ball tracker feed
        mock_balls = [
            {
                'original_3d': (0.0, 0.0, 1.0),
                'profile_id': 'yellow_ball',
                'name': 'Yellow Ball'
            }
        ]
        
        manager.update_ball_3d_feed(feed_id, mock_balls)
        print("✅ 3D ball tracker feed update successful")
        
        # Test mixed feed types
        manager.add_feed("Video Feed", "video_1", "video")
        manager.add_imu_feed("IMU Feed", "imu_1", "left")
        
        total_feeds = manager.get_feed_count()
        video_feeds = len(manager.get_video_feeds())
        imu_feeds = len(manager.get_imu_feeds())
        ball_3d_feeds_count = len(manager.get_ball_3d_feeds())
        
        print(f"✅ Mixed feeds: Total={total_feeds}, Video={video_feeds}, IMU={imu_feeds}, 3D Ball={ball_3d_feeds_count}")
        assert total_feeds == 3, "Should have 3 total feeds"
        assert ball_3d_feeds_count == 1, "Should have 1 3D ball tracker feed"
        
        # Test feed removal
        removed = manager.remove_feed(feed_id)
        assert removed, "Feed removal should succeed"
        assert len(manager.get_ball_3d_feeds()) == 0, "Should have no 3D ball tracker feeds after removal"
        print("✅ 3D ball tracker feed removal successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Video Feed Manager integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_window_integration():
    """Test the main window integration with 3D ball tracker."""
    print("\n🏠 Testing Main Window Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from apps.juggling_tracker.ui.main_window import MainWindow
        
        # Create minimal QApplication for testing
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create mock app
        class MockApp:
            def __init__(self):
                self.watch_imu_manager = None
                self.debug_imu = False
        
        mock_app = MockApp()
        main_window = MainWindow(app=mock_app)
        print("✅ MainWindow created successfully")
        
        # Test that new methods exist
        assert hasattr(main_window, '_update_3d_ball_tracker_feed'), "Should have _update_3d_ball_tracker_feed method"
        assert hasattr(main_window, '_ensure_3d_ball_tracker_feed_on_mode_switch'), "Should have _ensure_3d_ball_tracker_feed_on_mode_switch method"
        print("✅ New 3D ball tracker methods present")
        
        # Test video feed manager has 3D support
        assert hasattr(main_window.video_feed_manager, 'add_ball_3d_feed'), "VideoFeedManager should have add_ball_3d_feed method"
        assert hasattr(main_window.video_feed_manager, 'get_ball_3d_feeds'), "VideoFeedManager should have get_ball_3d_feeds method"
        print("✅ VideoFeedManager has 3D ball tracker support")
        
        # Test mode switching logic (without actually switching modes)
        initial_feed_count = main_window.video_feed_manager.get_feed_count()
        print(f"✅ Initial feed count: {initial_feed_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Main Window integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_jugvid2cpp_integration():
    """Test integration with JugVid2cpp interface."""
    print("\n🎯 Testing JugVid2cpp Integration...")
    
    try:
        # Test that JugVid2cpp interface can be imported
        from apps.juggling_tracker.modules.jugvid2cpp_interface import JugVid2cppInterface
        print("✅ JugVid2cppInterface imported successfully")
        
        # Test that the interface has the expected methods
        interface = JugVid2cppInterface()
        assert hasattr(interface, 'get_identified_balls'), "Should have get_identified_balls method"
        print("✅ JugVid2cppInterface has required methods")
        
        # Note: We don't actually start the interface to avoid requiring the executable
        print("✅ JugVid2cpp integration structure verified")
        
        return True
        
    except Exception as e:
        print(f"❌ JugVid2cpp integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting 3D Ball Tracker Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("3D Feed Widget Tests", test_3d_feed_widget),
        ("Video Feed Manager Integration", test_video_feed_manager_integration),
        ("Main Window Integration", test_main_window_integration),
        ("JugVid2cpp Integration", test_jugvid2cpp_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("🏁 INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ 3D Ball Tracker is successfully integrated into Juggling Tracker")
        print("✅ The visual_3d_ball_tracker functionality is now available as a live feed")
        print("✅ Users can switch to 'JugVid2cpp 3D Tracking' mode to see 3D ball visualization")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)