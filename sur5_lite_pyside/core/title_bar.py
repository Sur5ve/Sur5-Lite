#!/usr/bin/env python3
"""
Title Bar Customization Module
Windows 11 advanced title bar styling for Sur5
"""

import platform
from typing import Dict, Any, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)


def setup_advanced_title_bar(window) -> None:
    """Setup advanced Windows 11 title bar with custom colors
    
    Args:
        window: QMainWindow instance to apply styling to
    """
    try:
        if platform.system() != "Windows":
            return
        
        # Wait for window to be fully created
        QTimer.singleShot(100, lambda: _apply_advanced_title_bar_delayed(window))
        
    except Exception as e:
        logger.debug(f"titlebar n/a: {e}")


def _apply_advanced_title_bar_delayed(window) -> None:
    """Apply title bar styling after window is fully initialized"""
    try:
        if platform.system() != "Windows":
            return
        
        app = QApplication.instance()
        current_theme = "sur5ve"
        if hasattr(app, 'theme_manager') and app.theme_manager.current_theme:
            current_theme = app.theme_manager.current_theme
        
        apply_advanced_title_bar(window, current_theme)
        
    except Exception as e:
        logger.debug(f"titlebar err: {e}")


def apply_advanced_title_bar(window, theme_name: str) -> None:
    """Apply bleeding-edge Windows 11 title bar styling with optimal UI/UX contrast
    
    Args:
        window: QMainWindow instance
        theme_name: Name of the theme to apply
    """
    try:
        if platform.system() != "Windows":
            return
        
        from ctypes import windll, c_int, byref
        hwnd = int(window.winId())
        
        # Get theme colors
        app = QApplication.instance()
        theme_colors = {}
        if hasattr(app, 'theme_manager'):
            theme_colors = app.theme_manager.get_theme_colors(theme_name) or {}
        
        # Determine if dark theme
        is_dark = "light" not in theme_name.lower()
        
        # 1. Enable dark mode base (Windows 10 build 19041+)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(c_int(1 if is_dark else 0)), 4
        )
        
        # 2. Custom caption color with optimal UI/UX (Windows 11 22000+)
        try:
            DWMWA_CAPTION_COLOR = 35
            
            if is_dark:
                # Dark themes: Use deep background for reduced eye strain
                bg_primary = theme_colors.get("bg_primary", "#1a1a1a")
                caption_color = bg_primary
            else:
                # Light theme: Use soft, warm off-white (NOT pure white)
                # Pure white causes eye strain - use warm gray/beige
                caption_color = "#f5f5f3"  # Soft warm gray (same as bg_secondary)
            
            color_bgr = _hex_to_bgr(caption_color)
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR,
                byref(c_int(color_bgr)), 4
            )
        except Exception:
            pass
        
        # 3. Set text color with WCAG AAA contrast (7:1 minimum)
        try:
            DWMWA_TEXT_COLOR = 36
            
            if is_dark:
                # Dark themes: Pure white for maximum readability
                text_color = 0x00FFFFFF
            else:
                # Light theme: Soft black (not pure black) for reduced eye strain
                # Pure black on white is too harsh - use #1a1a1a (26,26,26)
                text_color = 0x001a1a1a  # Soft black (same as text_primary in light theme)
            
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR,
                byref(c_int(text_color)), 4
            )
        except Exception:
            pass
        
        # 4. Set border color with theme-appropriate accent
        try:
            DWMWA_BORDER_COLOR = 34
            
            if is_dark:
                # Dark themes: Use vibrant accent for visual pop
                primary_color = theme_colors.get("primary", "#20B2AA")
                border_color = primary_color
            else:
                # Light theme: Use softer, more subdued border
                # Bright borders on light backgrounds cause eye strain
                border_color = "#d0d0d0"  # Soft gray border
            
            border_bgr = _hex_to_bgr(border_color)
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_BORDER_COLOR,
                byref(c_int(border_bgr)), 4
            )
        except Exception:
            pass
        
        # 5. Ensure rounded corners (Windows 11)
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                byref(c_int(DWMWCP_ROUND)), 4
            )
        except Exception:
            pass
        
        logger.debug(f"titlebar: {theme_name} dark={is_dark}")
        
    except Exception as e:
        # Fail silently - not all Windows versions support this
        pass


def _hex_to_bgr(hex_color: str) -> int:
    """Convert hex color to Windows BGR COLORREF format
    
    Args:
        hex_color: Hex color string (e.g., "#20B2AA")
    
    Returns:
        int: Windows COLORREF in BGR format
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # Windows uses BGR format
    return (b << 16) | (g << 8) | r


def force_foreground_windows(window) -> None:
    """Windows-specific: Force this window to foreground after it's fully rendered
    
    Args:
        window: QMainWindow instance
    """
    try:
        if platform.system() != "Windows":
            return
        
        import ctypes
        hwnd = int(window.winId())
        user32 = ctypes.windll.user32
        
        # Get current foreground window's thread
        foreground = user32.GetForegroundWindow()
        if foreground and foreground != hwnd:
            fg_thread = user32.GetWindowThreadProcessId(foreground, None)
            cur_thread = user32.GetCurrentThreadId()
            
            # Attach our thread to foreground thread to allow focus change
            user32.AttachThreadInput(fg_thread, cur_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fg_thread, cur_thread, False)
        
        # Also activate via Qt
        window.raise_()
        window.activateWindow()
    except Exception:
        pass


# Expose commonly used functions
__all__ = [
    "setup_advanced_title_bar",
    "apply_advanced_title_bar",
    "force_foreground_windows",
]

