#!/usr/bin/env python3
"""
Beta Version Settings Manager
Handles application settings with Qt integration and model engine sync
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QSettings, QObject, Signal


class SettingsManager(QObject):
    """Manages application settings with Qt integration"""
    
    # Signals
    setting_changed = Signal(str, object)  # setting_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Qt Settings for system integration
        self.qt_settings = QSettings()
        
        # JSON settings file for complex data
        self.settings_file = Path(__file__).parent.parent / "settings.json"
        
        # Default settings
        self.default_settings = {
            # UI Settings
            "current_theme": "sur5_dark",
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
            "model_path": "D:/Models/Qwen3-1.7B-Q4_K_M.gguf",
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9,
            "ram_config": "8GB",
            "thinking_mode": True,
            
            # RAG Settings
            "rag_enabled": True,
            "max_documents": 100,
            "chunk_size": 1000,
            "chunk_overlap": 200,
            
            # Performance Settings
            "enable_virtualization": True,
            "virtualization_threshold": 50,
            "auto_cleanup": True,
        }
        
        # Load model engine settings if available
        self._load_model_engine_settings()
        
        # Load current settings
        self.current_settings = self._load_settings()
        
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
                
            try:
                print("🔗 Settings synced with model engine")
            except Exception:
                print("Settings synced with model engine")
            
        except ImportError:
            print("⚠️ Model engine not available for settings sync")
        except Exception as e:
            try:
                print(f"⚠️ Error syncing with model engine: {e}")
            except Exception:
                print(f"Error syncing with model engine: {e}")
            
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file with fallback to defaults"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    
                # Merge with defaults (add new keys, keep existing values)
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                return settings
            else:
                print(f"📁 Creating new settings file: {self.settings_file}")
                return self.default_settings.copy()
                
        except Exception as e:
            print(f"⚠️ Error loading settings: {e}")
            print("📁 Using default settings")
            return self.default_settings.copy()
            
    def save_settings(self):
        """Save current settings to JSON file and sync with model engine"""
        try:
            # Save to JSON
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2)
                
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
                print("🔄 Settings saved and synced with model engine")
                
            except ImportError:
                print("📁 Settings saved (model engine not available)")
            except Exception as e:
                print(f"⚠️ Error syncing with model engine: {e}")
                print("📁 Settings saved locally")
                
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            
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
        print("🔄 Settings reset to defaults")
        
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
                        
                print("🔄 Settings synced with model engine")
                return True
                
        except Exception as e:
            print(f"⚠️ Error syncing with model engine: {e}")
            
        return False
