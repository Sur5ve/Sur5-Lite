#!/usr/bin/env python3
"""
Portable Paths Manager - Centralized path resolution for USB portable mode

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

Includes XDG Base Directory compliance for Linux systems.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict

# Logging - use lazy import to avoid circular dependency
def _get_logger():
    try:
        from utils.logger import create_module_logger
        return create_module_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


# =============================================================================
# XDG Base Directory Specification (Linux)
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
# =============================================================================

def get_xdg_data_home() -> Path:
    """Get XDG_DATA_HOME directory.
    
    Returns the base directory for user-specific data files.
    On non-Linux systems, returns a platform-appropriate equivalent.
    
    Returns:
        Path: XDG_DATA_HOME or platform equivalent
        - Linux: $XDG_DATA_HOME or ~/.local/share
        - macOS: ~/Library/Application Support
        - Windows: %LOCALAPPDATA% or ~/AppData/Local
    """
    system = platform.system()
    
    if system == "Linux":
        xdg_data = os.environ.get("XDG_DATA_HOME", "")
        if xdg_data:
            return Path(xdg_data)
        return Path.home() / ".local" / "share"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support"
    else:  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data)
        return Path.home() / "AppData" / "Local"


def get_xdg_config_home() -> Path:
    """Get XDG_CONFIG_HOME directory.
    
    Returns the base directory for user-specific configuration files.
    On non-Linux systems, returns a platform-appropriate equivalent.
    
    Returns:
        Path: XDG_CONFIG_HOME or platform equivalent
        - Linux: $XDG_CONFIG_HOME or ~/.config
        - macOS: ~/Library/Preferences
        - Windows: %APPDATA% or ~/AppData/Roaming
    """
    system = platform.system()
    
    if system == "Linux":
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            return Path(xdg_config)
        return Path.home() / ".config"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Preferences"
    else:  # Windows
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            return Path(app_data)
        return Path.home() / "AppData" / "Roaming"


def get_xdg_cache_home() -> Path:
    """Get XDG_CACHE_HOME directory.
    
    Returns the base directory for user-specific non-essential (cached) data.
    On non-Linux systems, returns a platform-appropriate equivalent.
    
    Returns:
        Path: XDG_CACHE_HOME or platform equivalent
        - Linux: $XDG_CACHE_HOME or ~/.cache
        - macOS: ~/Library/Caches
        - Windows: %LOCALAPPDATA%/Temp or ~/AppData/Local/Temp
    """
    system = platform.system()
    
    if system == "Linux":
        xdg_cache = os.environ.get("XDG_CACHE_HOME", "")
        if xdg_cache:
            return Path(xdg_cache)
        return Path.home() / ".cache"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Caches"
    else:  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data) / "Temp"
        return Path.home() / "AppData" / "Local" / "Temp"


def get_xdg_state_home() -> Path:
    """Get XDG_STATE_HOME directory.
    
    Returns the base directory for user-specific state data that should persist
    between (application) restarts, but is not important enough for backup.
    
    Returns:
        Path: XDG_STATE_HOME or platform equivalent
        - Linux: $XDG_STATE_HOME or ~/.local/state
        - macOS: ~/Library/Application Support (same as data)
        - Windows: %LOCALAPPDATA% (same as data)
    """
    system = platform.system()
    
    if system == "Linux":
        xdg_state = os.environ.get("XDG_STATE_HOME", "")
        if xdg_state:
            return Path(xdg_state)
        return Path.home() / ".local" / "state"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support"
    else:  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data)
        return Path.home() / "AppData" / "Local"


def get_sur5_data_dir() -> Path:
    """Get Sur5-specific data directory (XDG-compliant on Linux).
    
    For non-portable installations, this returns the XDG-compliant path.
    In portable mode, returns the portable UserData directory instead.
    
    Returns:
        Path: Sur5 data directory
    """
    if is_portable_mode():
        return get_userdata_root()
    
    data_home = get_xdg_data_home()
    sur5_dir = data_home / "Sur5"
    sur5_dir.mkdir(parents=True, exist_ok=True)
    return sur5_dir


def get_sur5_config_dir() -> Path:
    """Get Sur5-specific configuration directory (XDG-compliant on Linux).
    
    For non-portable installations, this returns the XDG-compliant path.
    In portable mode, returns the portable UserData directory instead.
    
    Returns:
        Path: Sur5 config directory
    """
    if is_portable_mode():
        return get_userdata_root()
    
    config_home = get_xdg_config_home()
    sur5_dir = config_home / "Sur5"
    sur5_dir.mkdir(parents=True, exist_ok=True)
    return sur5_dir


def get_sur5_cache_dir() -> Path:
    """Get Sur5-specific cache directory (XDG-compliant on Linux).
    
    For non-portable installations, this returns the XDG-compliant path.
    In portable mode, returns a cache subdirectory in UserData.
    
    Returns:
        Path: Sur5 cache directory
    """
    if is_portable_mode():
        cache_dir = get_userdata_root() / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    cache_home = get_xdg_cache_home()
    sur5_dir = cache_home / "Sur5"
    sur5_dir.mkdir(parents=True, exist_ok=True)
    return sur5_dir


# =============================================================================
# Helper Functions
# =============================================================================

def get_path_or_fallback(portable_func, fallback_path: Path) -> Path:
    """Get portable path or fallback to legacy path.
    
    This helper consolidates the common pattern:
        if PORTABLE_PATHS_AVAILABLE:
            return portable_func()
        return fallback_path
    
    Args:
        portable_func: Function that returns the portable path (e.g., get_settings_file)
        fallback_path: Fallback Path to use if portable_func fails
    
    Returns:
        Path: The portable path if available, otherwise the fallback
    """
    try:
        return portable_func()
    except Exception:
        return fallback_path


# =============================================================================
# Core Path Functions
# =============================================================================

def is_portable_mode() -> bool:
    """
    Detect if running in portable USB mode.
    
    Portable mode is indicated by:
    1. Running as frozen executable (PyInstaller)
    2. Presence of PORTABLE_MODE marker file next to executable
    
    Returns:
        bool: True if in portable mode, False otherwise
    """
    if not getattr(sys, 'frozen', False):
        # Running from source - not portable mode
        return False
    
    # Running as executable - check for PORTABLE_MODE marker
    app_root = get_app_root()
    marker_file = app_root / "PORTABLE_MODE"
    
    return marker_file.exists()


def get_app_root() -> Path:
    """
    Get application root directory.
    
    Returns:
        Path: Application root directory
        - Frozen: Directory containing the executable
        - Source: Project root (3 levels up from this file)
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (.exe or .app)
        # sys.executable points to Sur5.exe or Sur5.app/Contents/MacOS/Sur5
        if platform.system() == "Darwin" and sys.executable.endswith("/MacOS/Sur5"):
            # macOS .app bundle: go up to .app directory
            return Path(sys.executable).parent.parent.parent
        else:
            # Windows .exe: parent directory
            return Path(sys.executable).parent
    else:
        # Running from Python source
        # This file is at: sur5_lite_pyside/utils/portable_paths.py
        # App root is 2 levels up
        return Path(__file__).parent.parent.parent


def get_userdata_root() -> Path:
    """
    Get UserData directory root.
    
    In portable mode: {app_root}/UserData/
    In development mode: {app_root}/UserData/ (for testing portable behavior)
    
    Creates the directory structure if it doesn't exist.
    
    Returns:
        Path: UserData directory path
    """
    app_root = get_app_root()
    userdata_dir = app_root / "UserData"
    
    # Create base UserData directory
    userdata_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    subdirs = [
        "Conversations",
    ]
    
    for subdir in subdirs:
        (userdata_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    return userdata_dir


def get_models_root() -> Path:
    """
    Get Models directory root for GGUF files.
    
    Priority order:
    1. SUR5_MODELS_PATH environment variable (for demo USB launcher)
    2. Portable mode: {app_root}/Models/
    3. XDG-compliant: $XDG_DATA_HOME/Sur5/models/ (Linux)
    4. Platform-specific: ~/Library/Application Support/Sur5/models/ (macOS)
    5. Platform-specific: %LOCALAPPDATA%/Sur5/models/ (Windows)
    6. Fallback: {app_root}/Models/
    
    Returns:
        Path: Models directory path
    """
    # Check environment variable first (set by USB launcher for demo)
    env_models_path = os.environ.get('SUR5_MODELS_PATH')
    if env_models_path:
        models_dir = Path(env_models_path)
        if models_dir.exists():
            _get_logger().debug(f"Using models from SUR5_MODELS_PATH: {models_dir}")
            return models_dir
        else:
            _get_logger().warning(f"SUR5_MODELS_PATH set but not found: {models_dir}")
    
    app_root = get_app_root()
    
    # In portable mode, always use app-relative Models directory
    if is_portable_mode():
        models_dir = app_root / "Models"
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir
    
    # Check for Models directory next to app (development/bundled)
    app_models_dir = app_root / "Models"
    if app_models_dir.exists() and any(app_models_dir.glob("*.gguf")):
        return app_models_dir
    
    # Check for Models directory as sibling to App (USB structure)
    # Structure: Sur5 Lite/Models/ and Sur5 Lite/App/
    parent_models_dir = app_root.parent / "Models"
    if parent_models_dir.exists() and any(parent_models_dir.glob("*.gguf")):
        return parent_models_dir
    
    # Use XDG-compliant path for system installation
    xdg_models_dir = get_xdg_data_home() / "Sur5" / "models"
    if xdg_models_dir.exists() and any(xdg_models_dir.glob("*.gguf")):
        return xdg_models_dir
    
    # Default to app-relative Models directory
    models_dir = app_root / "Models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    return models_dir


def get_settings_file() -> Path:
    """
    Get settings.json file path.
    
    Returns:
        Path: Full path to settings.json in UserData
    """
    return get_userdata_root() / "settings.json"


def get_model_settings_file() -> Path:
    """
    Get model_settings.json file path.
    
    Returns:
        Path: Full path to model_settings.json in UserData
    """
    return get_userdata_root() / "model_settings.json"


def get_user_patterns_file() -> Path:
    """
    Get user_patterns.json file path.
    
    Returns:
        Path: Full path to user_patterns.json in UserData
    """
    return get_userdata_root() / "user_patterns.json"


def get_conversations_dir() -> Path:
    """
    Get conversations directory.
    
    Returns:
        Path: Full path to Conversations directory
    """
    return get_userdata_root() / "Conversations"


def get_user_data_dir() -> Path:
    """
    Alias for get_userdata_root() for backward compatibility.
    
    Returns:
        Path: Full path to UserData directory
    """
    return get_userdata_root()


def get_models_dir() -> Path:
    """
    Alias for get_models_root() for backward compatibility.
    
    Returns:
        Path: Full path to Models directory
    """
    return get_models_root()


def get_logs_dir() -> Path:
    """
    Get logs directory.
    
    Returns:
        Path: Full path to logs directory
    """
    logs_dir = get_userdata_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_usb_identifier() -> Optional[str]:
    """
    Get unique USB drive identifier for DRM validation.
    
    Windows: Returns volume serial number
    macOS: Returns volume UUID
    Linux: Returns device UUID
    
    This is a foundation for future USB-locking DRM integration.
    Will be integrated with custom DRM/compiler (kakasoft/VMProtect style).
    
    Returns:
        str: Volume identifier, or None if not on removable drive or error
    """
    try:
        if not is_portable_mode():
            # Not in portable mode - return None
            return None
        
        app_root = get_app_root()
        
        if platform.system() == "Windows":
            # Windows: Get volume serial number
            import ctypes
            
            # Get drive letter from app root (validate it exists)
            drive = str(app_root.drive)
            if not drive:
                # Non-standard path (UNC, subst, etc.) - can't determine USB ID
                return None
            drive = drive + "\\"
            
            # Get volume serial number
            volumeNameBuffer = ctypes.create_unicode_buffer(1024)
            fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)
            serial_number = ctypes.c_ulong(0)
            max_component_length = ctypes.c_ulong(0)
            file_system_flags = ctypes.c_ulong(0)
            
            result = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drive),
                volumeNameBuffer,
                ctypes.sizeof(volumeNameBuffer),
                ctypes.byref(serial_number),
                ctypes.byref(max_component_length),
                ctypes.byref(file_system_flags),
                fileSystemNameBuffer,
                ctypes.sizeof(fileSystemNameBuffer)
            )
            
            if result:
                # Format as hex string
                return f"{serial_number.value:08X}"
            else:
                return None
                
        elif platform.system() == "Darwin":
            # macOS: Check if on external volume
            import subprocess
            
            # Check if path is on /Volumes/ (external drive)
            if not str(app_root).startswith("/Volumes/"):
                return None
            
            # Get volume UUID using diskutil
            try:
                result = subprocess.run(
                    ["diskutil", "info", str(app_root)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Parse output for Volume UUID
                for line in result.stdout.split('\n'):
                    if "Volume UUID:" in line:
                        uuid = line.split(":")[-1].strip()
                        return uuid
                        
            except subprocess.CalledProcessError:
                return None
                
        elif platform.system() == "Linux":
            # Linux: Get device UUID using lsblk
            import subprocess
            
            try:
                # Use df to get the device for the app root
                df_result = subprocess.run(
                    ["df", str(app_root)],
                    capture_output=True, text=True, timeout=5
                )
                if df_result.returncode == 0:
                    # Parse device from df output (second line, first column)
                    lines = df_result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        device = lines[1].split()[0]
                        
                        # Get UUID using lsblk
                        lsblk_result = subprocess.run(
                            ["lsblk", "-no", "UUID", device],
                            capture_output=True, text=True, timeout=5
                        )
                        if lsblk_result.returncode == 0:
                            uuid = lsblk_result.stdout.strip()
                            if uuid:
                                return uuid
            except Exception:
                pass
            return None
            
        else:
            # Other platforms - not implemented
            return None
            
    except Exception as e:
        _get_logger().warning(f"Error getting USB identifier: {e}")
        return None


def get_drive_info() -> Dict[str, str]:
    """
    Get information about the drive where the application is running.
    
    Returns:
        dict: Drive information including type, serial, label, etc.
    """
    info = {
        "portable_mode": is_portable_mode(),
        "app_root": str(get_app_root()),
        "platform": platform.system(),
        "usb_id": get_usb_identifier(),
    }
    
    try:
        if platform.system() == "Windows":
            import ctypes
            
            app_root = get_app_root()
            drive = str(app_root.drive) + "\\"
            
            # Get drive type
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
            drive_types = {
                0: "Unknown",
                1: "No Root Directory",
                2: "Removable",
                3: "Fixed",
                4: "Remote",
                5: "CD-ROM",
                6: "RAM Disk"
            }
            info["drive_type"] = drive_types.get(drive_type, "Unknown")
            
            # Get volume label
            volumeNameBuffer = ctypes.create_unicode_buffer(1024)
            fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)
            serial_number = ctypes.c_ulong(0)
            max_component_length = ctypes.c_ulong(0)
            file_system_flags = ctypes.c_ulong(0)
            
            result = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drive),
                volumeNameBuffer,
                ctypes.sizeof(volumeNameBuffer),
                ctypes.byref(serial_number),
                ctypes.byref(max_component_length),
                ctypes.byref(file_system_flags),
                fileSystemNameBuffer,
                ctypes.sizeof(fileSystemNameBuffer)
            )
            
            if result:
                info["volume_label"] = volumeNameBuffer.value
                info["file_system"] = fileSystemNameBuffer.value
                
    except Exception as e:
        info["error"] = str(e)
    
    return info


def print_portable_info():
    """Print portable mode information for debugging."""
    logger = _get_logger()
    info = get_drive_info()
    
    logger.info("=" * 60)
    logger.info("PORTABLE MODE INFORMATION")
    logger.info("=" * 60)
    logger.info(f"Portable Mode:    {info['portable_mode']}")
    logger.info(f"Platform:         {info['platform']}")
    logger.info(f"App Root:         {info['app_root']}")
    
    # Show environment variable overrides
    env_models = os.environ.get('SUR5_MODELS_PATH')
    env_usb = os.environ.get('SUR5_USB_DRIVE')
    if env_models or env_usb:
        logger.info("Environment Overrides:")
        if env_models:
            logger.info(f"  SUR5_MODELS_PATH: {env_models}")
        if env_usb:
            logger.info(f"  SUR5_USB_DRIVE:   {env_usb}")
    
    if info.get('drive_type'):
        logger.info(f"Drive Type:       {info['drive_type']}")
    if info.get('volume_label'):
        logger.info(f"Volume Label:     {info['volume_label']}")
    if info.get('file_system'):
        logger.info(f"File System:      {info['file_system']}")
    if info.get('usb_id'):
        logger.info(f"USB ID:           {info['usb_id']}")
    
    logger.info("Paths:")
    logger.info(f"  UserData:       {get_userdata_root()}")
    logger.info(f"  Models:         {get_models_root()}")
    logger.info(f"  Conversations:  {get_conversations_dir()}")
    logger.info("=" * 60)


# dir structure init is lazy (on first access)
# Removed blocking call that ran on import, improving startup time


if __name__ == "__main__":
    # Test the portable paths system
    print_portable_info()

