#!/bin/zsh
# Test script to verify Python 3.11 is default

echo "🔍 Testing Python Configuration"
echo "================================"
echo ""

# Source the updated .zshrc
source ~/.zshrc

echo "Python 3 location:"
which python3

echo ""
echo "Python 3 version:"
python3 --version

echo ""
echo "Pip 3 location:"
which pip3

echo ""
echo "✅ Configuration test complete!"
echo ""
echo "Expected: Python 3.11.14"
echo "If you see Python 3.9.6, close and reopen your terminal."

