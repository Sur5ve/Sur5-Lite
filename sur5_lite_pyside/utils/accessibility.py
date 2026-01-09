#!/usr/bin/env python3
"""
Accessibility Detection Utility
Detects system accessibility settings to adapt UI behavior.

All detection is local-only with zero network activity.
Results are cached after first detection for minimal resource impact.
"""

import os
import platform
from dataclasses import dataclass
from typing import Optional


@dataclass
class AccessibilitySettings:
    """Container for detected accessibility settings."""
    
    prefers_reduced_motion: bool = False
    high_contrast_mode: bool = False
    screen_reader_active: bool = False
    text_scale_factor: float = 1.0
    
    def should_reduce_animations(self) -> bool:
        """Return True if animations should be reduced or disabled."""
        return self.prefers_reduced_motion or self.high_contrast_mode
    
    def should_increase_contrast(self) -> bool:
        """Return True if UI should use higher contrast colors."""
        return self.high_contrast_mode
    
    def get_adjusted_font_scale(self) -> float:
        """Return recommended font scale multiplier."""
        return max(1.0, self.text_scale_factor)


# Cached accessibility settings (detected once at startup)
_accessibility_cache: Optional[AccessibilitySettings] = None


def get_accessibility_settings() -> AccessibilitySettings:
    """Get current system accessibility settings.
    
    Results are cached after first detection to minimize overhead.
    Call clear_accessibility_cache() to force re-detection.
    
    Returns:
        AccessibilitySettings with detected preferences
    """
    global _accessibility_cache
    
    if _accessibility_cache is not None:
        return _accessibility_cache
    
    settings = AccessibilitySettings()
    
    # Import reduced motion detection from processing_header
    try:
        from widgets.chat.processing_header import prefers_reduced_motion
        settings.prefers_reduced_motion = prefers_reduced_motion()
    except ImportError:
        settings.prefers_reduced_motion = _detect_reduced_motion_fallback()
    
    # Detect other accessibility settings based on platform
    system = platform.system()
    
    if system == "Windows":
        settings.high_contrast_mode = _detect_high_contrast_windows()
        settings.screen_reader_active = _detect_screen_reader_windows()
        settings.text_scale_factor = _detect_text_scale_windows()
    elif system == "Darwin":  # macOS
        settings.high_contrast_mode = _detect_high_contrast_macos()
        settings.screen_reader_active = _detect_screen_reader_macos()
        settings.text_scale_factor = _detect_text_scale_macos()
    elif system == "Linux":
        settings.high_contrast_mode = _detect_high_contrast_linux()
        settings.screen_reader_active = _detect_screen_reader_linux()
        settings.text_scale_factor = _detect_text_scale_linux()
    
    _accessibility_cache = settings
    return settings


def clear_accessibility_cache() -> None:
    """Clear the accessibility cache to force re-detection.
    
    Also clears the reduced motion cache if available.
    """
    global _accessibility_cache
    _accessibility_cache = None
    
    # Also clear reduced motion cache
    try:
        from widgets.chat.processing_header import clear_reduced_motion_cache
        clear_reduced_motion_cache()
    except ImportError:
        pass


def _detect_reduced_motion_fallback() -> bool:
    """Fallback reduced motion detection if main function unavailable."""
    # Check environment variables
    env_reduce = os.environ.get("REDUCE_MOTION", "").lower()
    if env_reduce in ("1", "true", "yes"):
        return True
    
    gtk_animations = os.environ.get("GTK_ENABLE_ANIMATIONS", "").lower()
    if gtk_animations in ("0", "false", "no"):
        return True
    
    return False


# =============================================================================
# Windows Accessibility Detection
# =============================================================================

def _detect_high_contrast_windows() -> bool:
    """Detect Windows high contrast mode."""
    try:
        import ctypes
        
        SPI_GETHIGHCONTRAST = 0x0042
        HCF_HIGHCONTRASTON = 0x00000001
        
        class HIGHCONTRAST(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("dwFlags", ctypes.c_uint),
                ("lpszDefaultScheme", ctypes.c_wchar_p)
            ]
        
        hc = HIGHCONTRAST()
        hc.cbSize = ctypes.sizeof(HIGHCONTRAST)
        
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETHIGHCONTRAST, hc.cbSize, ctypes.byref(hc), 0
        )
        
        if result:
            return bool(hc.dwFlags & HCF_HIGHCONTRASTON)
    except Exception:
        pass
    
    return False


def _detect_screen_reader_windows() -> bool:
    """Detect if a screen reader is active on Windows."""
    try:
        import ctypes
        
        # Check if screen reader is running via SystemParametersInfo
        SPI_GETSCREENREADER = 0x0046
        
        screen_reader = ctypes.c_int(0)
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETSCREENREADER, 0, ctypes.byref(screen_reader), 0
        )
        
        if result and screen_reader.value:
            return True
    except Exception:
        pass
    
    # Fallback: Check for common screen reader processes
    try:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq nvda.exe"],
            capture_output=True, text=True, timeout=2
        )
        if "nvda.exe" in result.stdout.lower():
            return True
        
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq narrator.exe"],
            capture_output=True, text=True, timeout=2
        )
        if "narrator.exe" in result.stdout.lower():
            return True
    except Exception:
        pass
    
    return False


def _detect_text_scale_windows() -> float:
    """Detect Windows text scaling factor."""
    try:
        import ctypes
        
        # Get the DPI for the primary monitor
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        
        # Get DPI
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        
        # Standard DPI is 96, calculate scale factor
        if dpi > 0:
            return dpi / 96.0
    except Exception:
        pass
    
    return 1.0


# =============================================================================
# macOS Accessibility Detection
# =============================================================================

def _detect_high_contrast_macos() -> bool:
    """Detect macOS high contrast / increased contrast mode."""
    try:
        import subprocess
        
        # Check increaseContrast setting
        result = subprocess.run(
            ["defaults", "read", "com.apple.universalaccess", "increaseContrast"],
            capture_output=True, text=True, timeout=2
        )
        if result.stdout.strip() == "1":
            return True
    except Exception:
        pass
    
    return False


def _detect_screen_reader_macos() -> bool:
    """Detect if VoiceOver is active on macOS."""
    try:
        import subprocess
        
        # Check VoiceOver status
        result = subprocess.run(
            ["defaults", "read", "com.apple.universalaccess", "voiceOverOnOffKey"],
            capture_output=True, text=True, timeout=2
        )
        if result.stdout.strip() == "1":
            return True
        
        # Alternative: Check if VoiceOver process is running
        result = subprocess.run(
            ["pgrep", "-x", "VoiceOver"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except Exception:
        pass
    
    return False


def _detect_text_scale_macos() -> float:
    """Detect macOS text scaling factor."""
    try:
        import subprocess
        
        # Get the display scale factor from system_profiler
        result = subprocess.run(
            ["defaults", "read", "NSGlobalDomain", "AppleInterfaceStyle"],
            capture_output=True, text=True, timeout=2
        )
        # macOS doesn't have a simple text scale setting like Windows
        # The Retina scaling is handled automatically
    except Exception:
        pass
    
    return 1.0


# =============================================================================
# Linux Accessibility Detection
# =============================================================================

def _detect_high_contrast_linux() -> bool:
    """Detect Linux high contrast mode (GNOME, KDE, etc.)."""
    import subprocess
    
    # 1. GNOME: Check high-contrast theme
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "high-contrast"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            return True
    except Exception:
        pass
    
    # 2. GNOME: Check if using high contrast GTK theme
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'\"").lower()
            if "highcontrast" in theme or "high-contrast" in theme:
                return True
    except Exception:
        pass
    
    # 3. KDE: Check color scheme name
    for kread_cmd in ["kreadconfig6", "kreadconfig5"]:
        try:
            result = subprocess.run(
                [kread_cmd, "--file", "kdeglobals", "--group", "General", 
                 "--key", "ColorScheme"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                scheme = result.stdout.strip().lower()
                if "highcontrast" in scheme or "high-contrast" in scheme:
                    return True
        except Exception:
            pass
    
    # 4. Check GTK_THEME environment variable
    gtk_theme = os.environ.get("GTK_THEME", "").lower()
    if "highcontrast" in gtk_theme or "high-contrast" in gtk_theme:
        return True
    
    return False


def _detect_screen_reader_linux() -> bool:
    """Detect if Orca or other screen reader is active on Linux."""
    import subprocess
    
    # Check for Orca screen reader process
    try:
        result = subprocess.run(
            ["pgrep", "-x", "orca"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except Exception:
        pass
    
    # Check for screen reader via AT-SPI
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.a11y.applications", "screen-reader-enabled"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            return True
    except Exception:
        pass
    
    # Check GNOME accessibility toolkit
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "toolkit-accessibility"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            return True
    except Exception:
        pass
    
    return False


def _detect_text_scale_linux() -> float:
    """Detect Linux text scaling factor (GNOME, KDE, etc.)."""
    import subprocess
    
    # 1. GNOME: Check text-scaling-factor
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            factor = float(result.stdout.strip())
            if factor > 0:
                return factor
    except Exception:
        pass
    
    # 2. KDE: Check font DPI or scaling
    for kread_cmd in ["kreadconfig6", "kreadconfig5"]:
        try:
            result = subprocess.run(
                [kread_cmd, "--file", "kcmfonts", "--group", "General", 
                 "--key", "forceFontDPI"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                dpi_str = result.stdout.strip()
                if dpi_str and dpi_str != "0":
                    dpi = int(dpi_str)
                    # Standard DPI is 96
                    if dpi > 0:
                        return dpi / 96.0
        except Exception:
            pass
    
    # 3. Check GDK_SCALE environment variable
    gdk_scale = os.environ.get("GDK_SCALE", "")
    if gdk_scale:
        try:
            return float(gdk_scale)
        except ValueError:
            pass
    
    # 4. Check QT_SCALE_FACTOR environment variable
    qt_scale = os.environ.get("QT_SCALE_FACTOR", "")
    if qt_scale:
        try:
            return float(qt_scale)
        except ValueError:
            pass
    
    return 1.0


def print_accessibility_info() -> None:
    """Print detected accessibility settings for debugging."""
    settings = get_accessibility_settings()
    
    print("\n" + "=" * 50)
    print("ACCESSIBILITY SETTINGS")
    print("=" * 50)
    print(f"Platform:              {platform.system()}")
    print(f"Reduced Motion:        {settings.prefers_reduced_motion}")
    print(f"High Contrast:         {settings.high_contrast_mode}")
    print(f"Screen Reader Active:  {settings.screen_reader_active}")
    print(f"Text Scale Factor:     {settings.text_scale_factor:.2f}x")
    print(f"Should Reduce Anims:   {settings.should_reduce_animations()}")
    print(f"Adjusted Font Scale:   {settings.get_adjusted_font_scale():.2f}x")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    print_accessibility_info()






