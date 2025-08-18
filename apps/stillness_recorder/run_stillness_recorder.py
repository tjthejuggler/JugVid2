#!/usr/bin/env python3
"""
Runner script for the Stillness Recorder application.

This script provides an easy way to launch the stillness recorder with
common configuration options.
"""

import sys
import os
import argparse

def main():
    """Main entry point for the runner script."""
    print("=" * 60)
    print("JugVid2 - Stillness Recorder")
    print("Motion-triggered video recorder using RealSense camera")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(description="Run the Stillness Recorder application")
    
    # Common presets
    parser.add_argument('--preset', choices=['quick', 'normal', 'sensitive', 'custom'], 
                       default='normal',
                       help='Use a preset configuration (default: normal)')
    
    # Custom parameters (override preset)
    parser.add_argument('--record-duration', type=float,
                       help='Duration in seconds to record when stillness is detected')
    parser.add_argument('--motion-threshold', type=float,
                       help='Motion threshold for detecting significant movement')
    parser.add_argument('--stillness-threshold', type=float,
                       help='Stillness threshold for detecting when motion stops')
    parser.add_argument('--stillness-duration', type=float,
                       help='Duration of stillness required to trigger recording')
    parser.add_argument('--output-dir', type=str,
                       help='Directory to save recorded videos')
    
    args = parser.parse_args()
    
    # Define presets
    presets = {
        'quick': {
            'record_duration': 5.0,
            'motion_threshold': 1500,
            'stillness_threshold': 800,
            'stillness_duration': 2.0,
            'output_dir': 'recordings/quick'
        },
        'normal': {
            'record_duration': 10.0,
            'motion_threshold': 1000,
            'stillness_threshold': 500,
            'stillness_duration': 3.0,
            'output_dir': 'recordings/normal'
        },
        'sensitive': {
            'record_duration': 15.0,
            'motion_threshold': 800,
            'stillness_threshold': 300,
            'stillness_duration': 5.0,
            'output_dir': 'recordings/sensitive'
        },
        'custom': {
            'record_duration': 10.0,
            'motion_threshold': 1000,
            'stillness_threshold': 500,
            'stillness_duration': 3.0,
            'output_dir': 'recordings/custom'
        }
    }
    
    # Get preset configuration
    config = presets[args.preset].copy()
    
    # Override with command line arguments
    if args.record_duration is not None:
        config['record_duration'] = args.record_duration
    if args.motion_threshold is not None:
        config['motion_threshold'] = args.motion_threshold
    if args.stillness_threshold is not None:
        config['stillness_threshold'] = args.stillness_threshold
    if args.stillness_duration is not None:
        config['stillness_duration'] = args.stillness_duration
    if args.output_dir is not None:
        config['output_dir'] = args.output_dir
    
    # Display configuration
    print(f"\nUsing preset: {args.preset}")
    print(f"Configuration:")
    print(f"  Record Duration: {config['record_duration']}s")
    print(f"  Motion Threshold (movement): {config['motion_threshold']}")
    print(f"  Stillness Threshold (stop): {config['stillness_threshold']}")
    print(f"  Stillness Duration: {config['stillness_duration']}s")
    print(f"  Output Directory: {config['output_dir']}")
    print()
    
    # Import and run the stillness recorder
    try:
        from stillness_recorder import StillnessRecorder
        
        recorder = StillnessRecorder(
            record_duration=config['record_duration'],
            motion_threshold=config['motion_threshold'],
            stillness_threshold=config['stillness_threshold'],
            stillness_duration=config['stillness_duration'],
            output_dir=config['output_dir']
        )
        
        success = recorder.run()
        return 0 if success else 1
        
    except ImportError as e:
        print(f"Error importing stillness_recorder: {e}")
        print("Make sure all required modules are available.")
        return 1
    except Exception as e:
        print(f"Error running stillness recorder: {e}")
        return 1

if __name__ == "__main__":
    exit(main())