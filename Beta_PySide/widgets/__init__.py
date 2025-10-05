#!/usr/bin/env python3
"""
Beta Version Widgets Module
UI components for the Beta Version application
"""

# Export main widget categories
from . import chat
from . import sidebar
from . import common

__all__ = [
    "chat",
    "sidebar", 
    "common"
]
