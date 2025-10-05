#!/usr/bin/env python3
"""
Model Service
High-level service for AI model management with Qt integration
"""

import os
import threading
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer

from .model_engine import get_engine, get_thinking_preference, RAM_CONFIGS
from .dual_mode_utils import (
    DualModeConfig, 
    get_model_capabilities,
    should_show_thinking_toggle,
    is_dual_mode_model
)


class ModelService(QObject):
    """Service for managing AI models and inference"""
    
    # Signals
    model_loaded = Signal(str, str)  # model_name, model_path
    model_error = Signal(str)  # error_message  
    loading_progress = Signal(str, int)  # message, progress
    generation_started = Signal()
    generation_finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get model engine instance
        self.engine = get_engine()
        
        # Model state (like Tkinter's self.model_path)
        self.current_model_path = ""
        self.current_model_name = ""
        self.is_loaded = False
        
        # Dual mode configuration
        self.dual_mode_config = DualModeConfig()
        
        # Performance tracking
        self.generation_stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "average_tokens_per_second": 0.0
        }
        
        # Lazy loading like Tkinter (no background workers!)
        
        print("🤖 Model Service initialized")

        # Default RAM preset selection
        self._ram_preset: str = "Balanced"
        
    def set_model_path(self, model_path: str):
        """Set model path without loading (like Tkinter pattern)"""
        self.current_model_path = model_path
        self.current_model_name = os.path.basename(model_path)
        # Store in engine for lazy loading
        self.engine.set_model_path(model_path)
        # Ensure state reflects not-yet-loaded
        self.is_loaded = False
        print(f"🤖 Model path set: {self.current_model_name}")
        
    def load_model(self, model_path: str, ram_config: str = "8GB") -> bool:
        """Load a model with specified RAM configuration"""
        try:
            if not os.path.exists(model_path):
                error_msg = f"Model file not found: {model_path}"
                self.model_error.emit(error_msg)
                return False
                
            # Emit loading progress
            model_name = os.path.basename(model_path)
            self.loading_progress.emit(f"Loading {model_name}...", 10)
            
            # Load model using engine
            self.loading_progress.emit("Initializing model...", 50)
            success = self.engine.load_model(model_path, ram_config)
            
            if success:
                self.current_model_path = model_path
                self.current_model_name = model_name
                self.is_loaded = True
                
                # Configure thinking mode based on model
                thinking_enabled = get_thinking_preference(model_path)
                self.dual_mode_config.thinking_enabled = thinking_enabled
                
                self.loading_progress.emit("Model loaded successfully!", 100)
                self.model_loaded.emit(model_name, model_path)
                
                print(f"✅ Model loaded: {model_name} (Thinking: {thinking_enabled})")
                return True
            else:
                error_msg = f"Failed to load model: {model_name}"
                self.model_error.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            self.model_error.emit(error_msg)
            print(f"❌ {error_msg}")
            return False
            
    def unload_model(self):
        """Unload the current model"""
        try:
            self.engine.unload_model()
            self.current_model_path = ""
            self.current_model_name = ""
            self.is_loaded = False
            
            print("🗑️ Model unloaded")
            
        except Exception as e:
            error_msg = f"Error unloading model: {str(e)}"
            self.model_error.emit(error_msg)
            print(f"❌ {error_msg}")
            
    def generate_response(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """Generate a response using the loaded model"""
        if not self.is_loaded:
            raise RuntimeError("No model loaded")
            
        try:
            self.generation_started.emit()
            
            # Generate response
            response = self.engine.generate_response(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stream_callback=stream_callback,
                **kwargs
            )
            
            # Update stats
            self.generation_stats["total_generations"] += 1
            if response:
                self.generation_stats["total_tokens"] += len(response.split())
                
            self.generation_finished.emit()
            return response
            
        except Exception as e:
            self.generation_finished.emit()
            raise e
            
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Generate a chat response using SYNCHRONOUS lazy loading (like Tkinter, inside background thread)"""
        if not self.current_model_path:
            raise RuntimeError("No model path set")

        # Lazy-load the llama.cpp model using the exact Tkinter parameters.
        # This is executed from a background thread started by ConversationService.
        if not self.is_loaded:
            try:
                # Apply RAM preset before loading
                preset = RAM_CONFIGS.get(self._ram_preset, RAM_CONFIGS["Balanced"])
                self.engine.set_runtime_params(
                    n_ctx=preset["n_ctx"],
                    n_gpu_layers=preset.get("n_gpu_layers", 0)
                )
                print(f"🚀 Lazy-loading model: {os.path.basename(self.current_model_path)} (will print llama.cpp verbose logs)")
                _ = self.engine._lazy_load_model(self.current_model_path)
                self.is_loaded = True
                self.model_loaded.emit(self.current_model_name, self.current_model_path)
                print("✅ Model loaded successfully")
            except Exception as e:
                error_msg = f"Failed to load model: {str(e)}"
                self.model_error.emit(error_msg)
                raise RuntimeError(error_msg)
            
        try:
            self.generation_started.emit()
            
            # Generate response using EXACT Tkinter pattern (create fresh agent each time)
            from llama_cpp_agent import LlamaCppAgent
            from llama_cpp_agent.providers import LlamaCppPythonProvider
            from llama_cpp_agent.chat_history import BasicChatHistory
            from llama_cpp_agent.chat_history.messages import Roles
            
            # Get the loaded model (like Tkinter's llm = _lazy_load_model())
            llm = self.engine.model
            if not llm:
                raise RuntimeError("Model not loaded")
            
            # Create provider and agent exactly like Tkinter
            provider = LlamaCppPythonProvider(llm)
            agent = LlamaCppAgent(
                provider,
                system_prompt="You are a helpful AI assistant.",
                debug_output=False,
            )
            
            # Configure settings like Tkinter
            settings = provider.get_provider_default_settings()
            settings.temperature = temperature or 0.7
            settings.max_tokens = max_tokens or 2048
            settings.stream = True
            
            # Create chat history like Tkinter
            chat_hist = BasicChatHistory()
            for msg in messages[:-1]:  # All except the last message
                # Map string roles to Roles enum like Tkinter
                role = Roles.user if msg["role"] == "user" else Roles.assistant
                chat_hist.add_message({"role": role, "content": msg["content"]})
            
            # Get the user message (last message)
            user_message = messages[-1]["content"] if messages else ""
            
            # Generate response like Tkinter
            stream = agent.get_chat_response(
                user_message,
                llm_sampling_settings=settings,
                chat_history=chat_hist,
                returns_streaming_generator=True,
                print_output=False,
            )
            
            # Collect streaming response
            response_parts = []
            try:
                for chunk in stream:
                    if chunk:
                        response_parts.append(chunk)
                        if stream_callback:
                            stream_callback(chunk)
            except Exception as e:
                print(f"⚠️ Streaming error: {e}")
            
            response = "".join(response_parts)
            
            # Update stats
            self.generation_stats["total_generations"] += 1
            if response:
                self.generation_stats["total_tokens"] += len(response.split())
                
            self.generation_finished.emit()
            return response
            
        except Exception as e:
            self.generation_finished.emit()
            print(f"❌ Generation error: {e}")
            raise e
            
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        base_info = self.engine.get_model_info()
        
        return {
            **base_info,
            "model_name": self.current_model_name,
            "thinking_enabled": self.dual_mode_config.thinking_enabled,
            "dual_mode_config": self.dual_mode_config.to_dict(),
            "generation_stats": self.generation_stats.copy()
        }
        
    def get_ram_configurations(self) -> Dict[str, Dict]:
        """Get available RAM configurations"""
        return RAM_CONFIGS

    def set_ram_preset(self, preset_name: str):
        """Select RAM preset and defer reload until next use"""
        if preset_name not in RAM_CONFIGS:
            self.model_error.emit(f"Invalid RAM preset: {preset_name}")
            return
        # No-op if unchanged to avoid redundant resets
        if self._ram_preset == preset_name:
            return
        if self._ram_preset != preset_name:
            self._ram_preset = preset_name
            # Force lazy reload on next generation
            self.is_loaded = False
            print(
                f"🔧 RAM preset set to {preset_name} • Context ~{RAM_CONFIGS[preset_name]['n_ctx']} (applies on next use)"
            )

    def get_ram_preset(self) -> str:
        return self._ram_preset
        
    def get_thinking_mode(self) -> bool:
        """Get current thinking mode setting"""
        return self.dual_mode_config.thinking_enabled
        
    def set_thinking_mode(self, enabled: bool):
        """Set thinking mode enabled/disabled"""
        if self.dual_mode_config.thinking_enabled != enabled:
            self.dual_mode_config.thinking_enabled = enabled
            print(f"🧠 Thinking mode: {'enabled' if enabled else 'disabled'}")
            
    def get_dual_mode_config(self) -> DualModeConfig:
        """Get dual mode configuration"""
        return self.dual_mode_config
        
    def set_dual_mode_config(self, config: DualModeConfig):
        """Set dual mode configuration"""
        self.dual_mode_config = config
        print("🔧 Dual mode configuration updated")
        
    def update_model_settings(self, settings: Dict[str, Any]):
        """Update model settings"""
        try:
            self.engine.update_settings(settings)
            print("⚙️ Model settings updated")
        except Exception as e:
            error_msg = f"Error updating settings: {str(e)}"
            self.model_error.emit(error_msg)
            print(f"❌ {error_msg}")
            
    def set_ram_config(self, ram_config: str):
        """Set RAM configuration and reload if model is loaded"""
        if ram_config in RAM_CONFIGS:
            current_settings = self.engine.get_model_info().get("settings", {})
            current_settings["ram_config"] = ram_config
            self.engine.update_settings(current_settings)
            
            # If model is loaded, suggest reload
            if self.is_loaded:
                print(f"🔄 RAM config changed to {ram_config}. Consider reloading model for changes to take effect.")
        else:
            error_msg = f"Invalid RAM configuration: {ram_config}"
            self.model_error.emit(error_msg)
            
    def force_reload_current_model(self) -> bool:
        """Force reload the current model with current settings"""
        if not self.current_model_path:
            return False
            
        current_settings = self.engine.get_model_info().get("settings", {})
        ram_config = current_settings.get("ram_config", "8GB")
        
        return self.load_model(self.current_model_path, ram_config)
        
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        return self.generation_stats.copy()
        
    def reset_generation_stats(self):
        """Reset generation statistics"""
        self.generation_stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "average_tokens_per_second": 0.0
        }
        print("📊 Generation stats reset")
        
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded"""
        return self.is_loaded
        
    def get_current_model_name(self) -> str:
        """Get the name of the currently loaded model"""
        return self.current_model_name
        
    def get_current_model_path(self) -> str:
        """Get the path of the currently loaded model"""
        return self.current_model_path
        
    def get_supported_formats(self) -> List[str]:
        """Get list of supported model formats"""
        return [".gguf", ".bin", ".safetensors"]
        
    def get_model_capabilities(self) -> Dict[str, Any]:
        """Get capabilities and optimal settings for current model"""
        if not self.current_model_path:
            return {}
        return get_model_capabilities(self.current_model_path)
    
    def should_show_thinking_toggle(self) -> bool:
        """Check if thinking toggle should be shown for current model"""
        if not self.current_model_path:
            return False
        return should_show_thinking_toggle(self.current_model_path)
    
    def is_dual_mode_model(self) -> bool:
        """Check if current model supports dual-mode operation"""
        if not self.current_model_path:
            return False
        return is_dual_mode_model(self.current_model_path)
        
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.is_loaded:
                self.unload_model()
            print("🧹 Model service cleanup completed")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
            
    def get_model_thinking_preference(self, model_path: str) -> bool:
        """Get thinking mode preference for a model"""
        try:
            from .model_engine import get_thinking_preference as engine_get_thinking_pref
            return engine_get_thinking_pref(model_path)
        except Exception as e:
            print(f"❌ Error getting thinking preference: {e}")
            return False
