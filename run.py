#!/usr/bin/env python3
"""
JugVid2 Simple Launcher
======================

A simple launcher script that provides quick access to the main JugVid2 applications.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Simple launcher with quick shortcuts."""
    
    if len(sys.argv) < 2:
        print("🎯 JugVid2 Simple Launcher")
        print("=" * 30)
        print()
        print("Quick Commands:")
        print("  python run.py juggling    # Juggling Tracker")
        print("  python run.py face        # Face Balance Timer")
        print("  python run.py stillness   # Stillness Recorder")
        print("  python run.py menu        # Full Interactive Menu")
        print("  python run.py deps        # Check Dependencies")
        print("  python run.py help        # Show Help")
        print()
        print("For full options, use: python launcher.py")
        return
    
    command = sys.argv[1].lower()
    
    # Map simple commands to launcher commands
    command_map = {
        'juggling': 'juggling',
        'tracker': 'juggling', 
        'face': 'face',
        'balance': 'face',
        'stillness': 'stillness',
        'recorder': 'stillness',
        'pose': 'pose',
        'debug': 'debug',
        'setup': 'setup',
        'test': 'test',
        'deps': 'deps',
        'info': 'info',
        'menu': None,  # Interactive menu
        'help': None   # Show help
    }
    
    if command == 'help':
        subprocess.run([sys.executable, 'launcher.py', '--help'])
    elif command == 'menu':
        subprocess.run([sys.executable, 'launcher.py'])
    elif command in command_map:
        launcher_cmd = command_map[command]
        if launcher_cmd:
            subprocess.run([sys.executable, 'launcher.py', launcher_cmd])
        else:
            subprocess.run([sys.executable, 'launcher.py'])
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: juggling, face, stillness, pose, debug, setup, test, deps, info, menu, help")
        print("Use 'python run.py' to see all options")

if __name__ == '__main__':
    main()