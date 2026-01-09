#!/usr/bin/env python3
"""
Settings Schema and Validation
Provides typed schema validation and version-aware migration for application settings.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

# Current settings schema version
SETTINGS_VERSION = 2

# Schema definition with types, defaults, and constraints
SETTINGS_SCHEMA = {
    # UI Settings
    "current_theme": {
        "type": str,
        "default": "sur5ve",
        "choices": ["sur5ve"],
        "description": "Current color theme"
    },
    "font_size": {
        "type": int,
        "default": 9,
        "min": 8,
        "max": 24,
        "description": "UI font size in points"
    },
    "show_in_system_tray": {
        "type": bool,
        "default": False,
        "description": "Show Sur5 in system tray"
    },
    "minimize_to_tray": {
        "type": bool,
        "default": False,
        "description": "Minimize to tray instead of closing"
    },
    "show_performance_monitor": {
        "type": bool,
        "default": False,
        "description": "Show performance monitor in status bar"
    },
    "enable_virtualization": {
        "type": bool,
        "default": False,
        "description": "Enable message virtualization for long conversations"
    },
    "splitter_sizes": {
        "type": list,
        "default": None,
        "description": "Saved splitter sizes for layout persistence"
    },
    
    # Model Settings
    "model_path": {
        "type": str,
        "default": "",
        "description": "Path to current GGUF model"
    },
    "ram_preset": {
        "type": str,
        "default": "Balanced",
        "choices": ["Minimal", "Fast", "Balanced", "Power"],
        "description": "RAM/VRAM preset for model loading"
    },
    "temperature": {
        "type": float,
        "default": 0.7,
        "min": 0.0,
        "max": 2.0,
        "description": "Model temperature (creativity)"
    },
    "top_p": {
        "type": float,
        "default": 0.9,
        "min": 0.0,
        "max": 1.0,
        "description": "Top-p (nucleus) sampling"
    },
    "max_tokens": {
        "type": int,
        "default": 2048,
        "min": 64,
        "max": 32768,
        "description": "Maximum tokens to generate"
    },
    
    # Thinking Mode Settings
    "thinking_mode_enabled": {
        "type": bool,
        "default": True,
        "description": "Enable thinking/reasoning mode"
    },
    "show_thinking": {
        "type": bool,
        "default": True,
        "description": "Show thinking process in UI"
    },
    
    # Notifications
    "notify_generation_complete": {
        "type": bool,
        "default": False,
        "description": "Notify when generation completes"
    },
    "notify_only_minimized": {
        "type": bool,
        "default": True,
        "description": "Only notify when window is minimized"
    },
    
    # First Run
    "first_run_complete": {
        "type": bool,
        "default": False,
        "description": "Whether first run experience is complete"
    },
    
    # Meta
    "settings_version": {
        "type": int,
        "default": SETTINGS_VERSION,
        "description": "Settings schema version for migration"
    }
}


def validate_value(key: str, value: Any) -> Tuple[bool, Any, Optional[str]]:
    """
    Validate a single setting value against its schema.
    
    Args:
        key: Setting key
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, sanitized_value, error_message)
    """
    if key not in SETTINGS_SCHEMA:
        # Unknown key - allow but don't validate
        return True, value, None
    
    schema = SETTINGS_SCHEMA[key]
    expected_type = schema["type"]
    default = schema.get("default")
    
    # Handle None values
    if value is None:
        return True, default, None
    
    # Type validation
    if expected_type == int:
        if isinstance(value, float):
            value = int(value)
        elif not isinstance(value, int):
            return False, default, f"Expected int, got {type(value).__name__}"
    elif expected_type == float:
        if isinstance(value, int):
            value = float(value)
        elif not isinstance(value, float):
            return False, default, f"Expected float, got {type(value).__name__}"
    elif expected_type == bool:
        if not isinstance(value, bool):
            # Try to coerce common representations
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            elif isinstance(value, int):
                value = bool(value)
            else:
                return False, default, f"Expected bool, got {type(value).__name__}"
    elif expected_type == str:
        if not isinstance(value, str):
            value = str(value)
    elif expected_type == list:
        if value is not None and not isinstance(value, list):
            return False, default, f"Expected list, got {type(value).__name__}"
    
    # Constraint validation
    if "choices" in schema and value not in schema["choices"]:
        return False, default, f"Value '{value}' not in choices: {schema['choices']}"
    
    if "min" in schema and value < schema["min"]:
        return False, schema["min"], f"Value {value} below minimum {schema['min']}"
    
    if "max" in schema and value > schema["max"]:
        return False, schema["max"], f"Value {value} above maximum {schema['max']}"
    
    return True, value, None


def validate_settings(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and sanitize all settings.
    
    Args:
        data: Settings dictionary to validate
        
    Returns:
        Tuple of (sanitized_settings, list_of_warnings)
    """
    sanitized = {}
    warnings = []
    
    for key, value in data.items():
        is_valid, clean_value, error = validate_value(key, value)
        sanitized[key] = clean_value
        
        if not is_valid and error:
            warnings.append(f"{key}: {error}")
    
    # Add defaults for missing required keys
    for key, schema in SETTINGS_SCHEMA.items():
        if key not in sanitized:
            sanitized[key] = schema.get("default")
    
    return sanitized, warnings


def migrate_settings(data: Dict[str, Any], from_version: int) -> Dict[str, Any]:
    """
    Migrate settings from older versions.
    
    Args:
        data: Settings dictionary to migrate
        from_version: Source version number
        
    Returns:
        Migrated settings dictionary
    """
    migrated = data.copy()
    
    # Version 1 -> 2: Added thinking_mode_enabled, show_thinking
    if from_version < 2:
        # Migrate old thinking_enabled to new name
        if "thinking_enabled" in migrated:
            migrated["thinking_mode_enabled"] = migrated.pop("thinking_enabled")
        
        # Add default for show_thinking if missing
        if "show_thinking" not in migrated:
            migrated["show_thinking"] = True
        
        # Add settings_version
        migrated["settings_version"] = 2
    
    # Future migrations would be added here:
    # if from_version < 3:
    #     ...
    
    return migrated


def get_default_settings() -> Dict[str, Any]:
    """
    Get a dictionary of all default settings.
    
    Returns:
        Dictionary with all default values
    """
    return {key: schema.get("default") for key, schema in SETTINGS_SCHEMA.items()}


def get_setting_info(key: str) -> Optional[Dict[str, Any]]:
    """
    Get schema information for a setting.
    
    Args:
        key: Setting key
        
    Returns:
        Schema dictionary or None if not found
    """
    return SETTINGS_SCHEMA.get(key)


def is_valid_setting(key: str) -> bool:
    """Check if a key is a known setting."""
    return key in SETTINGS_SCHEMA


# Export public interface
__all__ = [
    "SETTINGS_VERSION",
    "SETTINGS_SCHEMA",
    "validate_value",
    "validate_settings",
    "migrate_settings",
    "get_default_settings",
    "get_setting_info",
    "is_valid_setting",
]

