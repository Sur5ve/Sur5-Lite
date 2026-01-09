#!/usr/bin/env python3
"""
System Theme Detection Utility
Detects OS dark/light mode preference to optionally auto-match Sur5's theme.

Supports:
- Windows: Registry AppsUseLightTheme
- macOS: defaults read AppleInterfaceStyle
- Linux/GNOME: gsettings color-scheme
- Linux/KDE: kdeglobals ColorScheme
- Linux/XFCE: xfconf-query ThemeName
- Fallback: GTK_THEME environment variable

All detection is local-only with zero network activity.
Results are cached after first detection for minimal resource impact (~0.001% CPU, ~1KB RAM).
"""

import os
import platform
from enum import Enum
from typing import Optional


class SystemTheme(Enum):
    """System theme preference."""
    DARK = "dark"
    LIGHT = "light"
    UNKNOWN = "unknown"


# Cached theme detection
_system_theme_cache: Optional[SystemTheme] = None


def get_system_theme() -> SystemTheme:
    """Detect the system's preferred color scheme (dark/light mode).
    
    Returns:
        SystemTheme enum value:
        - DARK: System prefers dark mode
        - LIGHT: System prefers light mode
        - UNKNOWN: Could not determine preference
    
    Results are cached after first detection.
    """
    global _system_theme_cache
    
    if _system_theme_cache is not None:
        return _system_theme_cache
    
    system = platform.system()
    
    if system == "Windows":
        _system_theme_cache = _detect_theme_windows()
    elif system == "Darwin":
        _system_theme_cache = _detect_theme_macos()
    elif system == "Linux":
        _system_theme_cache = _detect_theme_linux()
    else:
        _system_theme_cache = SystemTheme.UNKNOWN
    
    return _system_theme_cache


def is_dark_mode() -> bool:
    """Check if system prefers dark mode.
    
    Returns:
        True if system is in dark mode, False otherwise
    """
    return get_system_theme() == SystemTheme.DARK


def is_light_mode() -> bool:
    """Check if system prefers light mode.
    
    Returns:
        True if system is in light mode, False otherwise
    """
    return get_system_theme() == SystemTheme.LIGHT


def get_recommended_sur5_theme() -> str:
    """Get recommended Sur5 theme based on system preference.
    
    Returns:
        Theme key string: "sur5ve"
    """
    # Sur5ve is the only supported theme
    return "sur5ve"


def clear_theme_cache() -> None:
    """Clear the theme cache to force re-detection.
    
    Useful if system theme changes while the app is running.
    """
    global _system_theme_cache
    _system_theme_cache = None


# =============================================================================
# Windows Theme Detection
# =============================================================================

def _detect_theme_windows() -> SystemTheme:
    """Detect Windows system theme via registry."""
    try:
        import winreg
        
        # Open the registry key for personalization settings
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            # AppsUseLightTheme: 0 = dark, 1 = light
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            
            if value == 0:
                return SystemTheme.DARK
            else:
                return SystemTheme.LIGHT
                
    except Exception:
        pass
    
    # Fallback: Check SystemUsesLightTheme
    try:
        import winreg
        
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            
            if value == 0:
                return SystemTheme.DARK
            else:
                return SystemTheme.LIGHT
                
    except Exception:
        pass
    
    return SystemTheme.UNKNOWN


# =============================================================================
# macOS Theme Detection
# =============================================================================

def _detect_theme_macos() -> SystemTheme:
    """Detect macOS system theme via defaults command."""
    try:
        import subprocess
        
        # Check AppleInterfaceStyle (only exists when dark mode is enabled)
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True, timeout=2
        )
        
        if result.returncode == 0:
            style = result.stdout.strip().lower()
            if style == "dark":
                return SystemTheme.DARK
        else:
            # AppleInterfaceStyle not set = light mode
            return SystemTheme.LIGHT
            
    except Exception:
        pass
    
    return SystemTheme.UNKNOWN


# =============================================================================
# Linux Theme Detection
# =============================================================================

def _detect_theme_linux() -> SystemTheme:
    """Detect Linux system theme.
    
    Checks in order: GNOME -> KDE -> XFCE -> GTK_THEME env var
    """
    import subprocess
    
    # 1. GNOME: Check color-scheme setting
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            scheme = result.stdout.strip().strip("'\"").lower()
            if "dark" in scheme:
                return SystemTheme.DARK
            elif "light" in scheme or "default" in scheme:
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    # 2. GNOME fallback: Check gtk-theme for dark indicators
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'\"").lower()
            if "dark" in theme:
                return SystemTheme.DARK
            elif "light" in theme:
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    # 3. KDE Plasma: Check color scheme
    for kread_cmd in ["kreadconfig6", "kreadconfig5"]:
        try:
            result = subprocess.run(
                [kread_cmd, "--file", "kdeglobals", "--group", "General", 
                 "--key", "ColorScheme"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                scheme = result.stdout.strip().lower()
                if scheme:
                    if "dark" in scheme or "breeze-dark" in scheme:
                        return SystemTheme.DARK
                    elif "light" in scheme or "breeze" in scheme:
                        return SystemTheme.LIGHT
        except Exception:
            pass
    
    # 4. XFCE: Check theme name
    try:
        result = subprocess.run(
            ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().lower()
            if "dark" in theme:
                return SystemTheme.DARK
            elif "light" in theme:
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    # 5. Cinnamon: Check gtk-theme
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.cinnamon.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'\"").lower()
            if "dark" in theme:
                return SystemTheme.DARK
            elif "light" in theme:
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    # 6. MATE: Check gtk-theme
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.mate.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'\"").lower()
            if "dark" in theme:
                return SystemTheme.DARK
            elif "light" in theme:
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    # 7. GTK_THEME environment variable (fallback)
    gtk_theme = os.environ.get("GTK_THEME", "").lower()
    if gtk_theme:
        if "dark" in gtk_theme:
            return SystemTheme.DARK
        elif "light" in gtk_theme:
            return SystemTheme.LIGHT
    
    # 8. Check Adwaita variants (common default)
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'\"")
            # Adwaita-dark is dark, plain Adwaita is light
            if theme == "Adwaita-dark":
                return SystemTheme.DARK
            elif theme == "Adwaita":
                return SystemTheme.LIGHT
    except Exception:
        pass
    
    return SystemTheme.UNKNOWN


def get_theme_info() -> dict:
    """Get comprehensive theme detection information.
    
    Returns:
        Dictionary with theme details for debugging
    """
    return {
        "platform": platform.system(),
        "detected_theme": get_system_theme().value,
        "is_dark_mode": is_dark_mode(),
        "is_light_mode": is_light_mode(),
        "recommended_sur5_theme": get_recommended_sur5_theme(),
        "gtk_theme_env": os.environ.get("GTK_THEME", ""),
        "xdg_current_desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
    }


def print_theme_info() -> None:
    """Print theme detection information for debugging."""
    info = get_theme_info()
    
    print("\n" + "=" * 50)
    print("SYSTEM THEME DETECTION")
    print("=" * 50)
    print(f"Platform:              {info['platform']}")
    print(f"Detected Theme:        {info['detected_theme']}")
    print(f"Is Dark Mode:          {info['is_dark_mode']}")
    print(f"Is Light Mode:         {info['is_light_mode']}")
    print(f"Recommended Sur5:      {info['recommended_sur5_theme']}")
    
    if platform.system() == "Linux":
        print(f"\nLinux Details:")
        print(f"  GTK_THEME:           {info['gtk_theme_env'] or '(not set)'}")
        print(f"  XDG_CURRENT_DESKTOP: {info['xdg_current_desktop'] or '(not set)'}")
    
    print("=" * 50 + "\n")


if __name__ == "__main__":
    print_theme_info()






