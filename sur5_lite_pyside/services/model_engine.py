#!/usr/bin/env python3
"""
Model Engine - LLM integration with llama-cpp-python

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

Supports multiple inference backends via the inference_backend module.
"""

import os
import json
import threading
from typing import Dict, Any, Optional, Callable, List, Union
from pathlib import Path

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)

# Import from refactored modules
from .gpu_detector import (
    get_gpu_capability,
    detect_gpu_capability,
    _get_optimal_thread_count,
    _check_macos_metal_support,
)
from .ram_presets import (
    RAM_CONFIGS,
    estimate_kv_cache_size,
    detect_optimal_preset,
    get_safe_preset_for_vram,
    validate_preset_for_vram,
)

# Import portable paths for USB-compatible path resolution
try:
    from ..utils.portable_paths import get_model_settings_file
    PORTABLE_PATHS_AVAILABLE = True
except ImportError:
    PORTABLE_PATHS_AVAILABLE = False

# Try to import llama-cpp libraries
try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

try:
    from llama_cpp_agent import LlamaCppAgent, MessagesFormatterType
    HAS_LLAMA_AGENT = True
except ImportError:
    HAS_LLAMA_AGENT = False

# Global model instance
_model_instance = None
_agent_instance = None
_model_lock = threading.Lock()


# Default model settings
DEFAULT_SETTINGS = {
    "model_path": "",
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "ram_config": "Balanced",
    "thinking_mode": True,
    "dual_mode_preferences": {
        "enable_prompt_templating": True,
        "template_debug_mode": False,
        "remember_last_mode": True,
        "default_thinking_mode": True,
        "model_specific": {}
    }
}

# Settings file path
# Use portable paths if available, otherwise fall back to legacy location
if PORTABLE_PATHS_AVAILABLE:
    SETTINGS_FILE = get_model_settings_file()
else:
    SETTINGS_FILE = Path(__file__).parent.parent / "model_settings.json"


def load_settings() -> Dict[str, Any]:
    """Load model settings from JSON file.
    
    Returns:
        Dict[str, Any]: Settings dictionary merged with defaults.
    """
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults to add any new keys
                merged = DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
        else:
            return DEFAULT_SETTINGS.copy()
    except Exception as e:
        pass
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """Save model settings to JSON file.
    
    Args:
        settings: Settings dictionary to save.
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        pass


def get_current_settings() -> Dict[str, Any]:
    """Get current model settings.
    
    Returns:
        Dict[str, Any]: Current settings dictionary.
    """
    return load_settings()


class ModelEngine:
    """Manages LLM loading and inference - LAZY LOADING pattern"""
    
    def __init__(self):
        self.model: Optional[Llama] = None
        self.agent = None  # Optional[LlamaCppAgent]
        self.model_path: str = ""
        self._settings_cache: Optional[Dict[str, Any]] = None
        self.is_loaded = False
        # Runtime overrides derived from RAM preset
        self._runtime_n_ctx: Optional[int] = None
        self._runtime_n_gpu_layers: Optional[int] = None

    @property
    def settings(self) -> Dict[str, Any]:
        """Lazily load settings to avoid disk I/O during startup."""
        if self._settings_cache is None:
            self._settings_cache = load_settings()
        return self._settings_cache

    def _ensure_settings_loaded(self) -> None:
        if self._settings_cache is None:
            self._settings_cache = load_settings()
        
    def set_model_path(self, model_path: str) -> None:
        """Set model path for lazy loading (PySide6 pattern)"""
        self.model_path = model_path
        self.is_loaded = False

    def set_runtime_params(self, n_ctx: int, n_gpu_layers: Union[int, str]) -> None:
        """Set runtime params from selected RAM preset before lazy load"""
        self._runtime_n_ctx = int(n_ctx)
        self._runtime_n_gpu_layers = self._resolve_n_gpu_layers(n_gpu_layers)

    def _resolve_n_gpu_layers(self, value: Union[int, str]) -> int:
        """
        Resolve GPU layers with intelligent auto-detection
        
        Args:
            value: int (explicit layer count) or "auto" (auto-detect)
        
        Returns:
            int: Number of GPU layers (-1 = all, 0 = CPU-only)
        """
        if isinstance(value, int):
            return value
        
        if value == "auto":
            gpu_cap = get_gpu_capability()
            layers = gpu_cap["gpu_layers"]
            
            if layers > 0 or layers == -1:
                logger.info(f"GPU offloading enabled: {layers} layers ({gpu_cap['gpu_type']})")
            else:
                logger.info("CPU-only inference (no GPU detected)")
            
            return layers
        
        return 0
        
    def _load_model_deferred(self, model_path: str) -> "Llama":
        """Load (or return cached) GGUF model - Deferred loading pattern.
        
        Args:
            model_path: Path to the GGUF model file.
        
        Returns:
            Llama: The loaded Llama model instance.
        
        Raises:
            FileNotFoundError: If model file doesn't exist.
        """
        global _model_instance
        
        # Thread-safe check: acquire lock before checking global singleton
        with _model_lock:
            if _model_instance and self.model_path == model_path:
                return _model_instance
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            # Get context size and GPU offload from current RAM preset
            current_settings = get_current_settings()
            current_ram_config = current_settings.get("ram_config", "Balanced")
            config = RAM_CONFIGS.get(current_ram_config, RAM_CONFIGS["Balanced"])
            # Allow runtime overrides supplied by service just before load
            context_size = self._runtime_n_ctx or config["n_ctx"]
            n_gpu_layers = (
                self._runtime_n_gpu_layers if self._runtime_n_gpu_layers is not None
                else self._resolve_n_gpu_layers(config.get("n_gpu_layers", 0))
            )
            
            gpu_cap = get_gpu_capability()
            has_gpu = gpu_cap["has_gpu"]
            
            # Adaptive Flash Attention:
            # - Enable on GPU with large contexts (>16k) for 2-3x speedup
            # - Disable on CPU (adds overhead without benefit)
            use_flash_attn = has_gpu and context_size > 16384
            
            # Get optimal thread count based on platform
            optimal_threads = _get_optimal_thread_count()
            
            logger.info(f"Loading model with {current_ram_config} preset: {config['label']}")
            logger.debug(f"ctx={context_size} gpu={has_gpu} flash={use_flash_attn} threads={optimal_threads}")
            
            # Adaptive batch size: Intel Macs need small batches, others can use larger
            import platform as _platform
            is_intel_mac = _platform.system() == "Darwin" and _platform.machine() == "x86_64"
            n_batch = 2 if is_intel_mac else 512  # Intel Mac workaround vs optimal for other platforms
            
            # PySide6 optimized parameters with adaptive thread count
            _model_instance = Llama(
                model_path=model_path,
                flash_attn=use_flash_attn,     # Adaptive: GPU + large context
                n_gpu_layers=n_gpu_layers,     # Auto-detected
                n_batch=n_batch,               # Adaptive: 2 for Intel Mac, 512 for others
                n_ctx=context_size,
                n_threads=optimal_threads,     # Adaptive: based on CPU cores and platform
                n_threads_batch=optimal_threads,
                ctx_shift=True,                # Auto context shifting
                verbose=True
            )
            self.model_path = model_path
            self.model = _model_instance  # Store in instance for access
            return _model_instance
        
    def load_model(self, model_path: str, ram_config: str = "Balanced") -> bool:
        """Load a model with specified RAM configuration"""
        global _model_instance, _agent_instance
        
        if not HAS_LLAMA_CPP or not HAS_LLAMA_AGENT:
            logger.error("Required libraries not available")
            return False
            
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return False
            
        try:
            with _model_lock:
                # Unload existing model
                self.unload_model()
                
                # Get RAM preset
                config = RAM_CONFIGS.get(ram_config, RAM_CONFIGS["Balanced"])
                n_ctx = config["n_ctx"]
                n_gpu_layers = self._resolve_n_gpu_layers(config.get("n_gpu_layers", 0))
                
                logger.info(f"Loading model: {os.path.basename(model_path)}")
                logger.debug(f"preset: {ram_config} ctx={n_ctx}")
                
                # Get GPU capability for this instance too
                gpu_cap = get_gpu_capability()
                has_gpu = gpu_cap["has_gpu"]
                use_flash_attn = has_gpu and n_ctx > 16384
                
                # Get optimal thread count based on platform
                optimal_threads = _get_optimal_thread_count()
                
                # Adaptive batch size: Intel Macs need small batches, others can use larger
                import platform as _platform
                is_intel_mac = _platform.system() == "Darwin" and _platform.machine() == "x86_64"
                n_batch = 2 if is_intel_mac else 512  # Intel Mac workaround vs optimal for other platforms
                
                # Load model with llama-cpp-python
                # Adaptive thread count based on CPU cores and platform
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_batch=n_batch,               # Adaptive: 2 for Intel Mac, 512 for others
                    n_threads=optimal_threads,     # Adaptive: based on CPU cores and platform
                    n_threads_batch=optimal_threads,
                    n_gpu_layers=n_gpu_layers,
                    ctx_shift=True,                # Enable context shifting
                    flash_attn=use_flash_attn,     # Adaptive Flash Attention
                    verbose=True
                )
                
                # Create agent for chat functionality
                self.agent = LlamaCppAgent(
                    self.model,
                    debug_output=False,
                    system_prompt="You are a helpful AI assistant.",
                    predefined_messages_formatter_type=MessagesFormatterType.CHATML
                )
                
                # Update global instances
                _model_instance = self.model
                _agent_instance = self.agent
                
                # Update settings
                self.model_path = model_path
                self.settings["model_path"] = model_path
                self.settings["ram_config"] = ram_config
                save_settings(self.settings)
                
                self.is_loaded = True
                logger.info(f"Model loaded successfully: {os.path.basename(model_path)}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.unload_model()
            return False
            
    def unload_model(self) -> None:
        """Unload the current model"""
        global _model_instance, _agent_instance
        
        with _model_lock:
            if self.model:
                del self.model
                self.model = None
                
            if self.agent:
                del self.agent
                self.agent = None
                
            _model_instance = None
            _agent_instance = None
            
            self.model_path = ""
            self.is_loaded = False
            logger.info("Model unloaded")
            
    def generate_response(
        self, 
        prompt: str, 
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
        top_k: int = None,
        repeat_penalty: float = None,
        stop_sequences: List[str] = None,
        stream_callback: Optional[Callable[[str, Optional[dict]], None]] = None
    ) -> str:
        """Generate a response using the loaded model"""
        if not self.is_loaded or not self.model:
            raise RuntimeError("No model loaded")
            
        # Use settings defaults if not provided
        max_tokens = max_tokens or self.settings.get("max_tokens", 2048)
        temperature = temperature if temperature is not None else self.settings.get("temperature", 0.7)
        top_p = top_p if top_p is not None else self.settings.get("top_p", 0.9)
        top_k = top_k if top_k is not None else self.settings.get("top_k", 40)
        repeat_penalty = repeat_penalty if repeat_penalty is not None else self.settings.get("repeat_penalty", 1.1)
        stop_sequences = stop_sequences or []
        
        try:
            if stream_callback:
                # Streaming generation
                response = ""
                for chunk in self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop=stop_sequences,
                    stream=True
                ):
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        token = chunk['choices'][0].get('text', '')
                        if token:
                            response += token
                            stream_callback(token)
                            
                return response
            else:
                # Non-streaming generation
                result = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop=stop_sequences,
                    stream=False
                )
                
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0].get('text', '').strip()
                    
                return ""
                
        except Exception as e:
            raise RuntimeError(f"Generation error: {e}")
            
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
        stream_callback: Optional[Callable[[str, Optional[dict]], None]] = None
    ) -> str:
        """Generate a chat response using the agent"""
        if not self.is_loaded or not self.agent:
            raise RuntimeError("No model loaded")
            
        # Use settings defaults if not provided
        max_tokens = max_tokens or self.settings.get("max_tokens", 2048)
        temperature = temperature if temperature is not None else self.settings.get("temperature", 0.7)
        repeat_penalty = self.settings.get("repeat_penalty", 1.1)
        
        # Apply Granite-specific optimizations
        if self.model_path:
            model_name = os.path.basename(self.model_path).lower()
            if "granite" in model_name:
                # Granite models need higher repetition penalty to prevent loops
                repeat_penalty = max(repeat_penalty, 1.15)
                logger.debug(f"granite: repeat_penalty={repeat_penalty}")
        
        try:
            if stream_callback:
                # Streaming chat generation
                response = ""
                for chunk in self.agent.get_chat_response(
                    messages,
                    llm_sampling_settings={
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": self.settings.get("top_p", 0.9),
                        "top_k": self.settings.get("top_k", 40),
                        "repeat_penalty": repeat_penalty,
                    },
                    streaming=True
                ):
                    if chunk:
                        response += chunk
                        stream_callback(chunk)
                        
                return response
            else:
                # Non-streaming chat generation
                return self.agent.get_chat_response(
                    messages,
                    llm_sampling_settings={
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": self.settings.get("top_p", 0.9),
                        "top_k": self.settings.get("top_k", 40),
                        "repeat_penalty": repeat_penalty,
                    }
                )
                
        except Exception as e:
            raise RuntimeError(f"Chat generation error: {e}")
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "ram_config": self.settings.get("ram_config", "8GB"),
            "context_size": RAM_CONFIGS.get(self.settings.get("ram_config", "8GB"), {}).get("n_ctx", 4096),
            "settings": self.settings.copy()
        }
        
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """Update model settings"""
        self.settings.update(new_settings)
        save_settings(self.settings)
        
        
# Global engine instance
_engine = None

def get_engine() -> ModelEngine:
    """Get or create the global model engine"""
    global _engine
    if _engine is None:
        _engine = ModelEngine()
    return _engine


def is_model_loaded() -> bool:
    """Check if a model is currently loaded.
    
    Returns:
        bool: True if a model is loaded, False otherwise.
    """
    return _model_instance is not None


def get_model_instance() -> Optional["Llama"]:
    """Get the current model instance.
    
    Returns:
        Optional[Llama]: The loaded Llama model instance, or None.
    """
    return _model_instance


def get_agent_instance() -> Optional["LlamaCppAgent"]:
    """Get the current agent instance.
    
    Returns:
        Optional[LlamaCppAgent]: The loaded agent instance, or None.
    """
    return _agent_instance


def load_model_simple(model_path: str, ram_config: str = "8GB") -> bool:
    """Simple function to load a model.
    
    Args:
        model_path: Path to the GGUF model file.
        ram_config: RAM preset name.
    
    Returns:
        bool: True if model loaded successfully.
    """
    engine = get_engine()
    return engine.load_model(model_path, ram_config)


def generate_simple(prompt: str, **kwargs: Any) -> str:
    """Simple function to generate text.
    
    Args:
        prompt: The input prompt.
        **kwargs: Additional generation parameters.
    
    Returns:
        str: Generated text response.
    """
    engine = get_engine()
    return engine.generate_response(prompt, **kwargs)


def get_thinking_preference(model_path: str) -> bool:
    """Determine if a model supports thinking mode based on its name.
    
    Args:
        model_path: Path to the model file.
    
    Returns:
        bool: True if the model likely supports thinking mode.
    """
    model_name = os.path.basename(model_path).lower()
    
    # Models known to support thinking mode
    thinking_models = [
        "qwen", "llama-3.2", "llama-3.1", "mistral", "deepseek", 
        "reasoning", "thinking", "cot", "chain-of-thought", "smollm",
        "gemma-3-270m", "gemma3-270m"
    ]
    
    return any(keyword in model_name for keyword in thinking_models)


# Expose commonly used functions
__all__ = [
    "ModelEngine", "get_engine", "is_model_loaded", 
    "get_model_instance", "get_agent_instance",
    "load_model_simple", "generate_simple",
    "get_thinking_preference", "RAM_CONFIGS",
    "load_settings", "save_settings", "get_current_settings",
    "detect_optimal_preset", "get_safe_preset_for_vram", "validate_preset_for_vram",
    "detect_gpu_capability", "get_gpu_capability", "estimate_kv_cache_size",
]
