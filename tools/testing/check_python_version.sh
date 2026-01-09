#!/bin/zsh
# Quick test script to verify Python 3.11 is default

echo "🐍 Python Configuration Check"
echo "=============================="
echo ""

# Check which python3 is being used
PYTHON_PATH=$(which python3)
PYTHON_VERSION=$(python3 --version 2>&1)

echo "Python Location: $PYTHON_PATH"
echo "Python Version: $PYTHON_VERSION"
echo ""

# Check if it's the correct version
if [[ "$PYTHON_VERSION" == *"3.11"* ]]; then
    echo "✅ SUCCESS: Python 3.11 is default!"
    echo "✅ You will never accidentally use Python 3.9"
    echo ""
    echo "Sur5 is ready to launch:"
    echo "  ./launch_sur5.py"
else
    echo "⚠️  WARNING: Not using Python 3.11"
    echo ""
    echo "To fix:"
    echo "  1. Close this terminal window"
    echo "  2. Open a new terminal window"
    echo "  3. Run this test again"
fi

