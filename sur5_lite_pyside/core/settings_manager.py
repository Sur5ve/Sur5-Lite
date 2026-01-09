#!/usr/bin/env python3
"""
Sur5ve Settings Manager - Protected Core Module
Handles application settings with portable path support and model engine sync

Sur5ve LLC - Proprietary Code
Licensed under MIT License
"""

import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QSettings, QObject, Signal

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)

# Import portable paths for USB-compatible path resolution
try:
    from utils.portable_paths import (
        get_settings_file, 
        get_models_root,
        is_portable_mode,
        get_app_root
    )
    PORTABLE_PATHS_AVAILABLE = True
except ImportError:
    PORTABLE_PATHS_AVAILABLE = False
    logger.warning("Portable paths not available - using legacy paths")

# Import config validator for settings validation
try:
    from utils.config_validator import validate_settings, sanitize_settings
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False
    logger.warning("Config validator not available - skipping validation")


def get_default_model_path() -> str:
    """Get platform-appropriate default model path for Granite 4.0-350m
    
    Priority order:
    1. SUR5_MODELS_PATH environment variable (for demo USB launcher)
    2. USB/portable structure relative to app
    3. Platform-specific system locations
    
    Returns:
        str: Path to model file (existing if found, or first default location)
    """
    import sys
    
    # FIX BUG 6: Preferred model filename (but will scan for any .gguf if not found)
    model_filename = "gemma-3-270m-it-Q4_K_M.gguf"
    
    # Check environment variable first (set by USB launcher for demo)
    env_models_path = os.environ.get('SUR5_MODELS_PATH')
    if env_models_path:
        env_model_file = Path(env_models_path) / model_filename
        if env_model_file.exists():
            logger.info(f"Found model via SUR5_MODELS_PATH: {env_model_file}")
            return str(env_model_file)
        # Also check for other .gguf files in the env path
        env_models_dir = Path(env_models_path)
        if env_models_dir.exists():
            gguf_files = list(env_models_dir.glob("*.gguf"))
            if gguf_files:
                # Return first found .gguf file
                logger.info(f"Found model via SUR5_MODELS_PATH: {gguf_files[0]}")
                return str(gguf_files[0])
    
    # Use portable paths if available
    if PORTABLE_PATHS_AVAILABLE:
        app_root = get_app_root()
        models_root = get_models_root()
    else:
        # Fallback: determine application root directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (.exe or .app)
            app_root = Path(sys.executable).parent
        else:
            # Running from Python source
            # This file is at: App/sur5_lite_pyside/core/settings_manager.py
            # App root is 3 levels up
            app_root = Path(__file__).parent.parent.parent
        
        models_root = app_root / "Models"
    
    # Define relative paths (for USB/portable structure)
    # Priority: Models/ next to .exe (USB structure)
    relative_paths = [
        models_root / model_filename,                 # Models/ (USB structure - PRIORITY)
        app_root / "models" / model_filename,         # App/models/ (lowercase, bundled)
        app_root.parent / "Models" / model_filename,  # Demo structure: ../Models/ (sibling to App)
    ]
    
    # Define platform-specific system paths as fallback
    if platform.system() == "Darwin":  # macOS
        home = Path.home()
        system_paths = [
            home / "Models" / model_filename,
            home / "Documents" / "Models" / model_filename,
            home / "Desktop" / model_filename,
            Path("/Applications/Sur5.app/Contents/Resources/models") / model_filename,
        ]
    elif platform.system() == "Linux":  # Linux
        home = Path.home()
        system_paths = [
            home / "Models" / model_filename,
            home / ".local" / "share" / "Sur5" / "models" / model_filename,  # XDG_DATA_HOME
            home / "Documents" / "Models" / model_filename,
            Path("/opt/Sur5/models") / model_filename,
        ]
    else:  # Windows
        # Simplified for USB distribution - prioritize user locations
        system_paths = [
            Path.home() / "Models" / model_filename,
            Path.home() / "Documents" / "Models" / model_filename,
            Path.home() / "Desktop" / model_filename,
        ]
    
    # Combine: check relative paths first, then system paths
    all_paths = relative_paths + system_paths
    
    # Return first existing path with preferred filename
    for path in all_paths:
        if path.exists():
            resolved_path = path.resolve()  # Get absolute path for display
            logger.info(f"Found model at: {resolved_path}")
            return str(resolved_path)
    
    # FIX BUG 6: If preferred model not found, scan directories for ANY .gguf file
    scan_dirs = [models_root, app_root / "models", app_root.parent / "Models"]
    for scan_dir in scan_dirs:
        if scan_dir.exists():
            gguf_files = sorted(scan_dir.glob("*.gguf"), key=lambda f: f.stat().st_size, reverse=True)
            if gguf_files:
                # Return the largest .gguf file (likely the best model)
                resolved_path = gguf_files[0].resolve()
                logger.info(f"Found model via directory scan: {resolved_path}")
                return str(resolved_path)
    
    # No existing model found, return first relative path as default
    default_path = relative_paths[0].resolve()
    logger.warning(f"No model found. Will look for: {default_path}")
    logger.info(f"Please place {model_filename} in the Models folder.")
    return str(default_path)


class SettingsManager(QObject):
    """Manages application settings with portable JSON storage"""
    
    # Signals
    setting_changed = Signal(str, object)  # setting_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Determine settings file location
        # Priority 1: SUR5_SETTINGS_FILE environment variable (for demo mode)
        env_settings_file = os.environ.get('SUR5_SETTINGS_FILE')
        if env_settings_file and Path(env_settings_file).exists():
            self.settings_file = Path(env_settings_file)
            self.portable_mode = True  # Treat as portable when using custom settings
            logger.info(f"Using demo settings file: {self.settings_file}")
        elif PORTABLE_PATHS_AVAILABLE:
            # Portable mode: use UserData/settings.json
            self.settings_file = get_settings_file()
            self.portable_mode = is_portable_mode()
        else:
            # Fallback: legacy location
            self.settings_file = Path(__file__).parent.parent / "settings.json"
            self.portable_mode = False
        
        # Qt Settings reference (for migration only)
        self._qt_settings_migrated = False
        try:
            self.qt_settings = QSettings()
        except Exception as e:
            logger.warning(f"Could not initialize QSettings (will use JSON only): {e}")
            self.qt_settings = None
        
        # Default settings - Sur5ve Protected Configuration
        self.default_settings = {
            # UI Settings - Sur5ve Theme Engine
            "current_theme": "sur5ve",
            "window_geometry": None,
            "window_state": None,
            "font_size": 9,
            "font_family": "Segoe UI",
            
            # Chat Settings  
            "max_chat_history": 1000,
            "auto_save_conversations": True,
            "show_timestamps": True,
            "enable_markdown": True,
            
            # Model Settings (will be synced with model engine)
            "model_path": get_default_model_path(),  # Cross-platform model path detection
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9,
            "ram_config": "8GB",
            "thinking_mode": True,  # Legacy setting (kept for backward compatibility)
            
            # Per-category thinking mode preferences
            "thinking_mode_preferences": {
                "thinking_models": True,      # Default ON for dual-mode models (Qwen, GPT-OSS, etc.)
                "non_thinking_models": False  # Default OFF for standard models (Gemma, Granite, etc.)
            },
            
            # Performance Settings
            "enable_virtualization": True,
            "virtualization_threshold": 50,
            "auto_cleanup": True,
            
            # Interface Settings (Cross-Platform Enhancements)
            "match_system_theme": False,      # Auto-switch dark/light based on OS
            "show_in_system_tray": False,     # Enable system tray icon
            "minimize_to_tray": False,        # Minimize to tray on close
            "show_performance_monitor": False, # Show CPU/RAM/GPU monitor
            
            # Notification Settings
            "notify_generation_complete": False,  # Notify when generation completes
            "notify_only_minimized": True,        # Only notify when minimized
        }
        
        # Load model engine settings if available
        self._load_model_engine_settings()
        
        # Load current settings (includes migration from QSettings)
        self.current_settings = self._load_settings()
        
        # Migrate from QSettings/Registry if needed (first portable run)
        if self.portable_mode and not self._qt_settings_migrated:
            self._migrate_from_qsettings()
        
    def _load_model_engine_settings(self):
        """Load settings from model engine if available"""
        try:
            from services.model_engine import load_settings, get_current_settings, RAM_CONFIGS
            
            # Get model engine settings
            model_settings = get_current_settings()
            
            # Update defaults with model engine values
            if model_settings:
                self.default_settings.update({
                    "model_path": model_settings.get("model_path", self.default_settings["model_path"]),
                    "max_tokens": model_settings.get("max_tokens", self.default_settings["max_tokens"]),
                    "temperature": model_settings.get("temperature", self.default_settings["temperature"]),
                    "top_p": model_settings.get("top_p", self.default_settings["top_p"]),
                    "ram_config": model_settings.get("ram_config", self.default_settings["ram_config"]),
                })
                
            logger.debug("Settings synced with model engine")
            
        except ImportError:
            logger.debug("Model engine not available for settings sync")
        except Exception as e:
            try:
                logger.warning(f"Error syncing with model engine: {e}")
            except Exception:
                logger.warning(f"Error syncing with model engine: {e}")
            
    def _migrate_from_qsettings(self):
        """Migrate settings from QSettings/Registry to portable JSON (first run only)"""
        if not self.qt_settings:
            return
        
        try:
            migrated_any = False
            
            # Check if QSettings has any values
            all_keys = self.qt_settings.allKeys()
            
            if all_keys:
                logger.info("Migrating settings from Registry to portable JSON...")
                
                # Migrate each setting
                for key in all_keys:
                    value = self.qt_settings.value(key)
                    
                    # Try to map QSettings keys to our settings
                    # QSettings might use different key names
                    if key == "window_geometry" or key == "geometry":
                        # Convert QByteArray to something JSON-serializable
                        # For now, we'll skip geometry (will be recreated)
                        continue
                    elif key == "window_state" or key == "state":
                        continue
                    elif key in self.current_settings:
                        self.current_settings[key] = value
                        migrated_any = True
                
                if migrated_any:
                    # Save migrated settings
                    self.save_settings()
                    logger.info(f"Migrated {len(all_keys)} settings from Registry to portable storage")
                    
                    # Mark migration as complete
                    self._qt_settings_migrated = True
                    
        except Exception as e:
            logger.warning(f"Error migrating from QSettings: {e}")
            logger.info("Continuing with default settings")
            
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file with validation and fallback to defaults"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    
                # Check if migration marker exists
                if loaded_settings.get("_qt_settings_migrated"):
                    self._qt_settings_migrated = True
                    
                # Merge with defaults (add new keys, keep existing values)
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                
                # Validate and sanitize settings if validator available
                if HAS_VALIDATOR:
                    validation_result = validate_settings(settings)
                    if not validation_result.is_valid:
                        logger.warning("Settings validation issues found:")
                        for msg in validation_result.get_all_messages():
                            logger.warning(f"  {msg}")
                        # Sanitize to fix invalid values
                        settings = sanitize_settings(settings)
                        logger.info("Settings sanitized")
                    elif validation_result.warnings:
                        for msg in validation_result.warnings:
                            logger.warning(msg)
                
                return settings
            else:
                if self.portable_mode:
                    logger.info(f"Creating new portable settings file: {self.settings_file}")
                else:
                    logger.info(f"Creating new settings file: {self.settings_file}")
                return self.default_settings.copy()
                
        except Exception as e:
            logger.warning(f"Error loading settings: {e}")
            logger.info("Using default settings")
            return self.default_settings.copy()
            
    def save_settings(self):
        """Save current settings to JSON file with atomic write and sync with model engine"""
        try:
            # Add migration marker to prevent re-migration
            save_data = self.current_settings.copy()
            if self.portable_mode and self._qt_settings_migrated:
                save_data["_qt_settings_migrated"] = True
            
            # Atomic write: write to temp file, then rename
            # This prevents corruption if app crashes during save
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.settings_file.parent,
                prefix='.settings_',
                suffix='.json.tmp'
            )
            
            fd_consumed = False  # Track if os.fdopen took ownership
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    fd_consumed = True  # os.fdopen succeeded, it owns the fd now
                    json.dump(save_data, f, indent=2)
                
                # Atomic rename
                os.replace(temp_path, self.settings_file)
                
            except Exception as save_ex:
                # Clean up temp file on error
                # BUG: If os.fdopen succeeded, it already closed the fd. Calling os.close again is a double-close!
                if not fd_consumed:
                    try:
                        os.close(temp_fd)
                    except Exception:
                        pass
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
                
            # Sync model-related settings with model engine
            try:
                from services.model_engine import save_settings as save_model_settings
                
                # Extract model-related settings
                model_settings = {
                    "model_path": self.current_settings.get("model_path", ""),
                    "max_tokens": self.current_settings.get("max_tokens", 2048),
                    "temperature": self.current_settings.get("temperature", 0.7),
                    "top_p": self.current_settings.get("top_p", 0.9),
                    "ram_config": self.current_settings.get("ram_config", "8GB"),
                }
                
                save_model_settings(model_settings)
                if self.portable_mode:
                    logger.debug("Portable settings saved and synced with model engine")
                else:
                    logger.debug("Settings saved and synced with model engine")
                
            except ImportError:
                if self.portable_mode:
                    logger.debug("Portable settings saved (model engine not available)")
                else:
                    logger.debug("Settings saved (model engine not available)")
            except Exception as e:
                logger.warning(f"Error syncing with model engine: {e}")
                if self.portable_mode:
                    logger.debug("Portable settings saved locally")
                else:
                    logger.debug("Settings saved locally")
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value with optional default"""
        return self.current_settings.get(key, default)
        
    def set_setting(self, key: str, value: Any):
        """Set a setting value and emit change signal"""
        if self.current_settings.get(key) != value:
            self.current_settings[key] = value
            self.setting_changed.emit(key, value)
            
            # Auto-save for critical settings
            if key in ["model_path", "current_theme", "ram_config"]:
                self.save_settings()
                
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.current_settings.copy()
        
    def reset_settings(self):
        """Reset all settings to defaults"""
        self.current_settings = self.default_settings.copy()
        self.save_settings()
        logger.info("Settings reset to defaults")
    
    def get_thinking_mode_for_category(self, is_thinking_model: bool) -> bool:
        """Get thinking mode preference for a specific model category
        
        Args:
            is_thinking_model: True if model supports thinking mode, False otherwise
            
        Returns:
            bool: Thinking mode preference for that category
        """
        prefs = self.current_settings.get("thinking_mode_preferences", {})
        
        if is_thinking_model:
            return prefs.get("thinking_models", True)
        else:
            return prefs.get("non_thinking_models", False)
    
    def set_thinking_mode_for_category(self, is_thinking_model: bool, enabled: bool):
        """Set thinking mode preference for a specific model category
        
        Args:
            is_thinking_model: True if model supports thinking mode, False otherwise
            enabled: Whether thinking mode should be enabled for this category
        """
        if "thinking_mode_preferences" not in self.current_settings:
            self.current_settings["thinking_mode_preferences"] = {
                "thinking_models": True,
                "non_thinking_models": False
            }
        
        category = "thinking_models" if is_thinking_model else "non_thinking_models"
        self.current_settings["thinking_mode_preferences"][category] = enabled
        
        # Also update legacy thinking_mode for backward compatibility
        self.current_settings["thinking_mode"] = enabled
        
        self.save_settings()
        logger.debug(f"think mode {category}: {enabled}")
        
    def get_ram_configurations(self) -> Dict[str, Dict]:
        """Get available RAM configurations from model engine"""
        try:
            from services.model_engine import RAM_CONFIGS
            return RAM_CONFIGS
        except ImportError:
            # Fallback configurations
            return {
                "4GB": {"n_ctx": 2048, "n_batch": 128, "n_threads": 4},
                "8GB": {"n_ctx": 4096, "n_batch": 256, "n_threads": 6}, 
                "16GB": {"n_ctx": 8192, "n_batch": 512, "n_threads": 8},
                "32GB": {"n_ctx": 16384, "n_batch": 1024, "n_threads": 12}
            }
            
    def is_model_engine_available(self) -> bool:
        """Check if model engine is available"""
        try:
            import services.model_engine
            return True
        except ImportError:
            return False
            
    def sync_with_model_engine(self):
        """Manually sync settings with model engine"""
        try:
            from services.model_engine import get_current_settings
            
            model_settings = get_current_settings()
            if model_settings:
                # Update current settings with model engine values
                for key, value in model_settings.items():
                    if key in self.current_settings:
                        self.set_setting(key, value)
                        
                logger.debug("Settings synced with model engine")
                return True
                
        except Exception as e:
            logger.warning(f"Error syncing with model engine: {e}")
            
        return False
    
    # =========================================================================
    # First-Run Detection
    # =========================================================================
    
    def is_first_run(self) -> bool:
        """Check if this is the first time the app is running.
        
        Returns:
            bool: True if this is the first run, False otherwise
        """
        return not self.get_setting("has_completed_first_run", False)
    
    def mark_first_run_complete(self):
        """Mark that first-run setup has been completed.
        
        Call this after the user has completed initial setup or
        after showing the welcome experience.
        """
        self.set_setting("has_completed_first_run", True)
        self.save_settings()
        logger.info("First-run setup complete")
    
    def get_first_run_tip(self, tip_index: int = 0) -> str:
        """Get a first-run tip for display during loading.
        
        Args:
            tip_index: Index of the tip to show (wraps around)
        
        Returns:
            str: A helpful tip for new users
        """
        # Sur5ve Protected Tips Array
        tips = [
            "💡 Sur5ve runs 100% offline - no internet required",
            "⌨️ Use Ctrl+S to send messages, Ctrl+Z to stop generation",
            "🔄 Switch models anytime using the Control Hub",
            "🎯 Enable 'Thinking Mode' for more thorough responses",
            "💾 Your conversations are saved locally and privately",
            "🚀 For faster responses, try the 'Fast' RAM preset",
            "🔍 Use Ctrl+F to search within your chat history",
            "⚡ Sur5ve is optimized for your hardware automatically",
        ]
        return tips[tip_index % len(tips)]
    
    def get_random_tip(self) -> str:
        """Get a random tip for display.
        
        Returns:
            str: A randomly selected tip
        """
        import random
        return self.get_first_run_tip(random.randint(0, 7))