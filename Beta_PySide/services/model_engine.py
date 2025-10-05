#!/usr/bin/env python3
"""
Beta Version Model Engine
LLM integration with llama-cpp-python and llama-cpp-agent
"""

import os
import json
import threading
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

# Try to import llama-cpp libraries
try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    print("Warning: llama-cpp-python not installed. Install with: pip install llama-cpp-python")

try:
    from llama_cpp_agent import LlamaCppAgent, MessagesFormatterType
    HAS_LLAMA_AGENT = True
except ImportError:
    HAS_LLAMA_AGENT = False
    print("Warning: llama-cpp-agent not installed. Install with: pip install llama-cpp-agent")

# Global model instance
_model_instance = None
_agent_instance = None
_model_lock = threading.Lock()

# RAM presets aligned with Tkinter profiles
RAM_CONFIGS = {
    # User-facing name → runtime parameters
    "Fast": {
        "n_ctx": 8192,
        "n_gpu_layers": 0,  # CPU-friendly
        "label": "4 GB • ~8k",
        "description": "CPU-friendly • lowest latency"
    },
    "Balanced": {
        "n_ctx": 24576,
        "n_gpu_layers": 0,
        "label": "8 GB • ~24k",
        "description": "General-purpose • steady latency"
    },
    "Power": {
        "n_ctx": 32768,
        "n_gpu_layers": "auto",  # Offload when GPU build available
        "label": "16 GB+ • ~32k",
        "description": "GPU-optimized • longest window"
    }
}

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
SETTINGS_FILE = Path(__file__).parent.parent / "model_settings.json"


def load_settings() -> Dict[str, Any]:
    """Load model settings from JSON file"""
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
        print(f"Error loading model settings: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]):
    """Save model settings to JSON file"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving model settings: {e}")


def get_current_settings() -> Dict[str, Any]:
    """Get current model settings"""
    return load_settings()


class ModelEngine:
    """Manages LLM loading and inference - LAZY LOADING like Tkinter"""
    
    def __init__(self):
        self.model: Optional[Llama] = None
        self.agent: Optional[LlamaCppAgent] = None
        self.model_path: str = ""
        self.settings = load_settings()
        self.is_loaded = False
        # Runtime overrides derived from RAM preset
        self._runtime_n_ctx: Optional[int] = None
        self._runtime_n_gpu_layers: Optional[int] = None
        
    def set_model_path(self, model_path: str):
        """Set model path for lazy loading (like Tkinter)"""
        self.model_path = model_path
        self.is_loaded = False

    def set_runtime_params(self, n_ctx: int, n_gpu_layers: int | str):
        """Set runtime params from selected RAM preset before lazy load"""
        self._runtime_n_ctx = int(n_ctx)
        self._runtime_n_gpu_layers = self._resolve_n_gpu_layers(n_gpu_layers)

    def _resolve_n_gpu_layers(self, value: int | str) -> int:
        if isinstance(value, int):
            return value
        if value == "auto":
            try:
                # If llama.cpp is built with GPU, -1 offloads as much as possible
                return -1
            except Exception:
                return 0
        return 0
        
    def _lazy_load_model(self, model_path: str) -> Llama:
        """Load (or return cached) GGUF model - COPIED FROM TKINTER"""
        global _model_instance
        
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
        
        print(f"🚀 Loading model with {current_ram_config} preset: {config['label']} — {config['description']}")
        
        # EXACT TKINTER PARAMETERS - proven fast
        _model_instance = Llama(
            model_path=model_path,
            flash_attn=False,           # ⚡ Tkinter optimized
            n_gpu_layers=n_gpu_layers,
            n_batch=8,                  # ⚡ TINY batch size (key difference!)
            n_ctx=context_size,
            n_threads=8,                # ⚡ Fixed threads like Tkinter
            n_threads_batch=8,          # ⚡ Batch threading like Tkinter  
            verbose=True                # ⚡ Show progress like Tkinter
        )
        self.model_path = model_path
        self.model = _model_instance  # Store in instance for access
        return _model_instance
        
    def load_model(self, model_path: str, ram_config: str = "Balanced") -> bool:
        """Load a model with specified RAM configuration"""
        global _model_instance, _agent_instance
        
        if not HAS_LLAMA_CPP or not HAS_LLAMA_AGENT:
            print("❌ Required libraries not available")
            return False
            
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return False
            
        try:
            with _model_lock:
                # Unload existing model
                self.unload_model()
                
                # Get RAM preset
                config = RAM_CONFIGS.get(ram_config, RAM_CONFIGS["Balanced"])
                n_ctx = config["n_ctx"]
                n_gpu_layers = self._resolve_n_gpu_layers(config.get("n_gpu_layers", 0))
                
                print(f"🤖 Loading model: {os.path.basename(model_path)}")
                print(f"🔧 RAM Preset: {ram_config} - Context: {n_ctx}")
                
                # Load model with llama-cpp-python
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_batch=8,
                    n_threads=8,
                    n_gpu_layers=n_gpu_layers,
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
                print(f"✅ Model loaded successfully: {os.path.basename(model_path)}")
                return True
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.unload_model()
            return False
            
    def unload_model(self):
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
            print("🗑️ Model unloaded")
            
    def generate_response(
        self, 
        prompt: str, 
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
        top_k: int = None,
        repeat_penalty: float = None,
        stop_sequences: List[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None
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
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Generate a chat response using the agent"""
        if not self.is_loaded or not self.agent:
            raise RuntimeError("No model loaded")
            
        # Use settings defaults if not provided
        max_tokens = max_tokens or self.settings.get("max_tokens", 2048)
        temperature = temperature if temperature is not None else self.settings.get("temperature", 0.7)
        
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
                        "repeat_penalty": self.settings.get("repeat_penalty", 1.1),
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
                        "repeat_penalty": self.settings.get("repeat_penalty", 1.1),
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
        
    def update_settings(self, new_settings: Dict[str, Any]):
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
    """Check if a model is currently loaded"""
    return _model_instance is not None


def get_model_instance() -> Optional[Llama]:
    """Get the current model instance"""
    return _model_instance


def get_agent_instance() -> Optional[LlamaCppAgent]:
    """Get the current agent instance"""
    return _agent_instance


def load_model_simple(model_path: str, ram_config: str = "8GB") -> bool:
    """Simple function to load a model"""
    engine = get_engine()
    return engine.load_model(model_path, ram_config)


def generate_simple(prompt: str, **kwargs) -> str:
    """Simple function to generate text"""
    engine = get_engine()
    return engine.generate_response(prompt, **kwargs)


def get_thinking_preference(model_path: str) -> bool:
    """Determine if a model supports thinking mode based on its name"""
    model_name = os.path.basename(model_path).lower()
    
    # Models known to support thinking mode
    thinking_models = [
        "qwen", "llama-3.2", "llama-3.1", "mistral", "deepseek", 
        "reasoning", "thinking", "cot", "chain-of-thought"
    ]
    
    return any(keyword in model_name for keyword in thinking_models)


# Expose commonly used functions
__all__ = [
    "ModelEngine", "get_engine", "is_model_loaded", 
    "get_model_instance", "get_agent_instance",
    "load_model_simple", "generate_simple",
    "get_thinking_preference", "RAM_CONFIGS",
    "load_settings", "save_settings", "get_current_settings"
]
