#!/usr/bin/env python3
"""
Sur5 Launch Script - Entry point for the Sur5 Lite application

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

Splash screen and initialization are handled internally by run_sur5_app().
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

# Progress file for launcher handoff - write IMMEDIATELY before heavy imports
PROGRESS_FILE = Path(tempfile.gettempdir()) / "sur5_progress.json"


def _write_early_progress(progress: int, message: str):
    """Write progress to temp file for launcher (BEFORE heavy imports)"""
    try:
        # Only write if launcher handoff mode is enabled
        if os.environ.get("SUR5_SKIP_SPLASH", "0") == "1":
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"progress": progress, "message": message, "time": time.time()}, f)
    except Exception:
        pass


# Signal launcher IMMEDIATELY that we've started
_write_early_progress(5, "Python started...")

# Fix Windows console encoding FIRST (before any imports that might print Unicode)
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If encoding fix fails, continue anyway
    
    # Fix Windows taskbar icon - must be set before QApplication is created
    # This tells Windows to treat this as a unique app, not just "python.exe"
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Sur5ve.Sur5Lite')
    except Exception:
        pass

_write_early_progress(10, "Loading Qt framework...")

# Ensure Sur5 package modules resolve their internal absolute imports
# Handle both source mode and frozen mode (PyInstaller)
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running from Python source
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PACKAGE_DIR = os.path.join(BASE_DIR, "sur5_lite_pyside")
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

def main():
    """Launch the Sur5 PySide6 application"""
    try:
        _write_early_progress(15, "Importing Sur5 modules...")
        
        # Import and launch main app
        # run_sur5_app() handles all initialization including:
        # - DPI scaling configuration
        # - QApplication creation
        # - Splash screen display
        # - Main window setup
        from sur5_lite_pyside.core.application import run_sur5_app
        
        _write_early_progress(25, "Starting application...")
        return run_sur5_app()
        
    except ImportError as e:
        message = f"Import Error: {e}"
        try:
            print(message)
        except Exception:
            sys.stdout.write(message + "\n")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except Exception as e:
        message = f"Launch Error: {e}"
        try:
            print(message)
        except Exception:
            sys.stdout.write(message + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
