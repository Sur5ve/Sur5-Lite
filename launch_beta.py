#!/usr/bin/env python3
"""
Beta Version PySide6 Launch Script
"""

import sys
import os

# Add the Beta_PySide directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Beta_PySide'))

def main():
    """Launch the Beta Version PySide6 application"""
    try:
        from core.application import run_beta_app
        return run_beta_app()
    except ImportError as e:
        try:
            print(f"❌ Import Error: {e}")
        except Exception:
            print(f"Import Error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except Exception as e:
        try:
            print(f"❌ Launch Error: {e}")
        except Exception:
            print(f"Launch Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
