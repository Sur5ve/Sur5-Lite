#!/usr/bin/env python3
"""
Display Server Detection Utility
Detects whether running on Wayland, X11, or other display servers.

This is useful for:
- Informing users about feature limitations (e.g., global shortcuts on Wayland)
- Adapting behavior for different display protocols
- Debugging display-related issues

All detection is local-only with zero network activity.
"""

import os
import platform
from enum import Enum
from typing import Optional


class DisplayServer(Enum):
    """Display server types."""
    WAYLAND = "wayland"
    X11 = "x11"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


# Cached display server detection
_display_server_cache: Optional[DisplayServer] = None


def get_display_server() -> DisplayServer:
    """Detect the current display server.
    
    Returns:
        DisplayServer enum value:
        - WAYLAND: Running under Wayland compositor
        - X11: Running under X11/Xorg
        - WINDOWS: Running on Windows
        - MACOS: Running on macOS
        - UNKNOWN: Could not determine display server
    
    Detection methods:
    - Linux: XDG_SESSION_TYPE, WAYLAND_DISPLAY, DISPLAY env vars
    - Windows/macOS: Returns platform-specific constant
    """
    global _display_server_cache
    
    if _display_server_cache is not None:
        return _display_server_cache
    
    system = platform.system()
    
    if system == "Windows":
        _display_server_cache = DisplayServer.WINDOWS
    elif system == "Darwin":
        _display_server_cache = DisplayServer.MACOS
    elif system == "Linux":
        _display_server_cache = _detect_linux_display_server()
    else:
        _display_server_cache = DisplayServer.UNKNOWN
    
    return _display_server_cache


def _detect_linux_display_server() -> DisplayServer:
    """Detect display server on Linux systems."""
    
    # 1. Check XDG_SESSION_TYPE (most reliable, set by session manager)
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return DisplayServer.WAYLAND
    elif session_type == "x11":
        return DisplayServer.X11
    
    # 2. Check for Wayland-specific environment variable
    if os.environ.get("WAYLAND_DISPLAY"):
        return DisplayServer.WAYLAND
    
    # 3. Check for X11-specific environment variable
    if os.environ.get("DISPLAY"):
        return DisplayServer.X11
    
    # 4. Check GDK_BACKEND (GTK apps may set this)
    gdk_backend = os.environ.get("GDK_BACKEND", "").lower()
    if gdk_backend == "wayland":
        return DisplayServer.WAYLAND
    elif gdk_backend == "x11":
        return DisplayServer.X11
    
    # 5. Check QT_QPA_PLATFORM (Qt apps may set this)
    qt_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
    if "wayland" in qt_platform:
        return DisplayServer.WAYLAND
    elif "xcb" in qt_platform or "x11" in qt_platform:
        return DisplayServer.X11
    
    return DisplayServer.UNKNOWN


def is_wayland() -> bool:
    """Check if running under Wayland.
    
    Returns:
        True if running under Wayland compositor
    """
    return get_display_server() == DisplayServer.WAYLAND


def is_x11() -> bool:
    """Check if running under X11/Xorg.
    
    Returns:
        True if running under X11
    """
    return get_display_server() == DisplayServer.X11


def get_display_server_name() -> str:
    """Get human-readable display server name.
    
    Returns:
        String like "Wayland", "X11", "Windows", "macOS", or "Unknown"
    """
    server = get_display_server()
    names = {
        DisplayServer.WAYLAND: "Wayland",
        DisplayServer.X11: "X11",
        DisplayServer.WINDOWS: "Windows",
        DisplayServer.MACOS: "macOS",
        DisplayServer.UNKNOWN: "Unknown",
    }
    return names.get(server, "Unknown")


def get_wayland_limitations() -> list[str]:
    """Get list of known feature limitations on Wayland.
    
    Returns:
        List of limitation descriptions
    """
    if not is_wayland():
        return []
    
    return [
        "Global keyboard shortcuts may not work (Wayland security model)",
        "Window positioning may be restricted",
        "Some clipboard operations may require user interaction",
        "Screen capture may require portal permissions",
    ]


def clear_display_server_cache() -> None:
    """Clear the display server cache to force re-detection."""
    global _display_server_cache
    _display_server_cache = None


def get_session_info() -> dict:
    """Get comprehensive session/display information.
    
    Returns:
        Dictionary with session details for debugging
    """
    return {
        "platform": platform.system(),
        "display_server": get_display_server_name(),
        "xdg_session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "xdg_session_desktop": os.environ.get("XDG_SESSION_DESKTOP", ""),
        "xdg_current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
        "display": os.environ.get("DISPLAY", ""),
        "gdk_backend": os.environ.get("GDK_BACKEND", ""),
        "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM", ""),
        "desktop_session": os.environ.get("DESKTOP_SESSION", ""),
    }


def print_display_info() -> None:
    """Print display server information for debugging."""
    info = get_session_info()
    
    print("\n" + "=" * 50)
    print("DISPLAY SERVER INFORMATION")
    print("=" * 50)
    print(f"Platform:            {info['platform']}")
    print(f"Display Server:      {info['display_server']}")
    
    if platform.system() == "Linux":
        print(f"\nLinux Session Details:")
        print(f"  XDG_SESSION_TYPE:    {info['xdg_session_type'] or '(not set)'}")
        print(f"  XDG_SESSION_DESKTOP: {info['xdg_session_desktop'] or '(not set)'}")
        print(f"  XDG_CURRENT_DESKTOP: {info['xdg_current_desktop'] or '(not set)'}")
        print(f"  WAYLAND_DISPLAY:     {info['wayland_display'] or '(not set)'}")
        print(f"  DISPLAY:             {info['display'] or '(not set)'}")
        print(f"  GDK_BACKEND:         {info['gdk_backend'] or '(not set)'}")
        print(f"  QT_QPA_PLATFORM:     {info['qt_qpa_platform'] or '(not set)'}")
        print(f"  DESKTOP_SESSION:     {info['desktop_session'] or '(not set)'}")
        
        limitations = get_wayland_limitations()
        if limitations:
            print(f"\nWayland Limitations:")
            for lim in limitations:
                print(f"  • {lim}")
    
    print("=" * 50 + "\n")


if __name__ == "__main__":
    print_display_info()






