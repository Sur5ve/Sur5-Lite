#!/usr/bin/env python3
"""
Configuration Validator for Sur5
Validates settings and configuration files without external dependencies.
"""

from typing import Dict, Any, List, Tuple, Optional
import os


# Valid configuration values
VALID_RAM_CONFIGS = ["Ultra", "Minimal", "Fast", "Balanced", "Power"]
VALID_THEMES = ["sur5ve"]


class ValidationResult:
    """Result of a validation operation with error and warning tracking."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def get_all_messages(self) -> List[str]:
        """Get all error and warning messages."""
        return self.errors + self.warnings
    
    def __bool__(self) -> bool:
        """Return True if validation passed."""
        return self.is_valid

# Settings schema with types and constraints
SETTINGS_SCHEMA = {
    "ram_config": {
        "type": str,
        "valid_values": VALID_RAM_CONFIGS,
        "default": "Balanced",
        "required": False,
    },
    "model_path": {
        "type": str,
        "validator": lambda x: x == "" or os.path.exists(x) or True,  # Allow non-existent for initial setup
        "default": "",
        "required": False,
    },
    "first_time_setup": {
        "type": bool,
        "default": True,
        "required": False,
    },
    "thinking_mode_enabled": {
        "type": bool,
        "default": True,
        "required": False,
    },
    "current_theme": {
        "type": str,
        "valid_values": VALID_THEMES,
        "default": "sur5ve",
        "required": False,
    },
    "font_size": {
        "type": int,
        "min_value": 6,
        "max_value": 24,
        "default": 9,
        "required": False,
    },
}

# Model settings schema
MODEL_SETTINGS_SCHEMA = {
    "model_path": {
        "type": str,
        "default": "",
        "required": False,
    },
    "max_tokens": {
        "type": int,
        "min_value": 64,
        "max_value": 32768,
        "default": 2048,
        "required": False,
    },
    "temperature": {
        "type": (int, float),
        "min_value": 0.0,
        "max_value": 2.0,
        "default": 0.7,
        "required": False,
    },
    "top_p": {
        "type": (int, float),
        "min_value": 0.0,
        "max_value": 1.0,
        "default": 0.9,
        "required": False,
    },
    "top_k": {
        "type": int,
        "min_value": 1,
        "max_value": 200,
        "default": 40,
        "required": False,
    },
    "repeat_penalty": {
        "type": (int, float),
        "min_value": 1.0,
        "max_value": 2.0,
        "default": 1.1,
        "required": False,
    },
    "ram_config": {
        "type": str,
        "valid_values": VALID_RAM_CONFIGS,
        "default": "Balanced",
        "required": False,
    },
    "thinking_mode": {
        "type": bool,
        "default": True,
        "required": False,
    },
}


def validate_value(
    key: str,
    value: Any,
    schema: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate a single value against its schema definition.
    
    Args:
        key: The setting key name.
        value: The value to validate.
        schema: The schema definition for this key.
    
    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.
    """
    # Check type
    expected_type = schema.get("type")
    if expected_type is not None:
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                return False, f"'{key}' must be one of types {expected_type}, got {type(value).__name__}"
        elif not isinstance(value, expected_type):
            return False, f"'{key}' must be {expected_type.__name__}, got {type(value).__name__}"
    
    # Check valid values
    valid_values = schema.get("valid_values")
    if valid_values is not None and value not in valid_values:
        return False, f"'{key}' must be one of {valid_values}, got '{value}'"
    
    # Check min value
    min_value = schema.get("min_value")
    if min_value is not None and value < min_value:
        return False, f"'{key}' must be >= {min_value}, got {value}"
    
    # Check max value
    max_value = schema.get("max_value")
    if max_value is not None and value > max_value:
        return False, f"'{key}' must be <= {max_value}, got {value}"
    
    # Check custom validator
    validator = schema.get("validator")
    if validator is not None and not validator(value):
        return False, f"'{key}' failed custom validation"
    
    return True, None


def validate_settings(
    settings: Dict[str, Any],
    schema: Dict[str, Dict[str, Any]] = None
) -> ValidationResult:
    """
    Validate a settings dictionary against a schema.
    
    Args:
        settings: The settings dictionary to validate.
        schema: The schema to validate against (defaults to SETTINGS_SCHEMA).
    
    Returns:
        ValidationResult: Object with is_valid property and error/warning lists.
    """
    if schema is None:
        schema = SETTINGS_SCHEMA
    
    result = ValidationResult()
    
    # Validate each setting
    for key, value in settings.items():
        if key in schema:
            is_valid, error = validate_value(key, value, schema[key])
            if not is_valid:
                result.add_error(error)
        elif not key.startswith("_"):
            # Unknown setting (not a private key), add as warning
            result.add_warning(f"Unknown setting: '{key}'")
    
    # Check for required fields
    for key, field_schema in schema.items():
        if field_schema.get("required", False) and key not in settings:
            result.add_error(f"Missing required field: '{key}'")
    
    return result


def validate_model_settings(settings: Dict[str, Any]) -> ValidationResult:
    """
    Validate model settings dictionary.
    
    Args:
        settings: The model settings dictionary to validate.
    
    Returns:
        ValidationResult: Object with is_valid property and error/warning lists.
    """
    return validate_settings(settings, MODEL_SETTINGS_SCHEMA)


def get_default_value(key: str, schema: Dict[str, Dict[str, Any]] = None) -> Any:
    """
    Get the default value for a setting key.
    
    Args:
        key: The setting key name.
        schema: The schema to use (defaults to SETTINGS_SCHEMA).
    
    Returns:
        The default value for the key, or None if not found.
    """
    if schema is None:
        schema = SETTINGS_SCHEMA
    
    if key in schema:
        return schema[key].get("default")
    return None


def sanitize_settings(
    settings: Dict[str, Any],
    schema: Dict[str, Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sanitize settings by replacing invalid values with defaults.
    
    Args:
        settings: The settings dictionary to sanitize.
        schema: The schema to use (defaults to SETTINGS_SCHEMA).
    
    Returns:
        A new dictionary with invalid values replaced by defaults.
    """
    if schema is None:
        schema = SETTINGS_SCHEMA
    
    result = settings.copy()
    
    for key, value in settings.items():
        if key in schema:
            is_valid, _ = validate_value(key, value, schema[key])
            if not is_valid:
                default = schema[key].get("default")
                if default is not None:
                    result[key] = default
                    print(f"⚠️ Invalid value for '{key}': {value}. Using default: {default}")
    
    return result


def validate_ram_config(ram_config: str) -> bool:
    """
    Validate a RAM configuration name.
    
    Args:
        ram_config: The RAM configuration name to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    return ram_config in VALID_RAM_CONFIGS


def validate_theme(theme: str) -> bool:
    """
    Validate a theme name.
    
    Args:
        theme: The theme name to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    return theme in VALID_THEMES


def validate_temperature(temp: float) -> bool:
    """
    Validate a temperature value.
    
    Args:
        temp: The temperature value to validate.
    
    Returns:
        bool: True if valid (0.0-2.0), False otherwise.
    """
    return isinstance(temp, (int, float)) and 0.0 <= temp <= 2.0


def validate_model_path(path: str) -> Tuple[bool, str]:
    """
    Validate a model path.
    
    Args:
        path: The model file path to validate.
    
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not path:
        return True, ""  # Empty path is valid (no model selected)
    
    if not os.path.exists(path):
        return False, f"Model file not found: {path}"
    
    if not path.lower().endswith(('.gguf', '.bin', '.safetensors')):
        return False, f"Unsupported model format: {path}"
    
    return True, ""


# Export all validation functions
__all__ = [
    "VALID_RAM_CONFIGS",
    "VALID_THEMES",
    "SETTINGS_SCHEMA",
    "MODEL_SETTINGS_SCHEMA",
    "validate_settings",
    "validate_model_settings",
    "validate_value",
    "get_default_value",
    "sanitize_settings",
    "validate_ram_config",
    "validate_theme",
    "validate_temperature",
    "validate_model_path",
]
