#!/bin/bash

# Set PYTHONPATH for librealsense
export PYTHONPATH="/home/twain/Projects/librealsense/build/Release:$PYTHONPATH"

# Run the program
python run_juggling_tracker.py "$@"