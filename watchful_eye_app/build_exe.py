"""
Build script for Watchful Eye Desktop App
Creates a standalone .EXE using PyInstaller
"""

import subprocess
import sys
import os

def build_exe():
    print("Building Watchful Eye Desktop App...")
    print("This may take a few minutes...")
    print()

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "WatchfulEye",
        "--add-data", "ai;ai",
        "--add-data", "ui;ui",
        "--add-data", "utils;utils",
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "pyaudio",
        "--hidden-import", "psutil",
        "--hidden-import", "mss",
        "--hidden-import", "requests",
        "--collect-all", "customtkinter",
        "main.py"
    ]

    subprocess.check_call(cmd)

    print()
    print("="*50)
    print("Build complete!")
    print("="*50)
    print()
    print("EXE located at:")
    print(f"  {os.path.join(os.getcwd(), 'dist', 'WatchfulEye.exe')}")
    print()
    print("To pin to taskbar:")
    print("  1. Right-click WatchfulEye.exe")
    print("  2. Select 'Pin to taskbar'")
    print()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build_exe()
