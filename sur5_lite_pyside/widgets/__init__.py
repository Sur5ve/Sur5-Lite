#!/usr/bin/env python3
"""
Sur5 Widgets Module
UI components for the Sur5 application
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
