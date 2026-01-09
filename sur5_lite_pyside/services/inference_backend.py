#!/usr/bin/env python3
"""
Inference Backend Abstraction - Supports multiple LLM inference backends

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

This module provides a unified interface for different inference backends:
- llama.cpp (via llama-cpp-python)
- BitNet.cpp (via bitnet-api when available)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Generator, List, Callable
from enum import Enum
import os

from utils.logger import create_module_logger
logger = create_module_logger(__name__)


class InferenceBackend(Enum):
    """Supported inference backends"""
    LLAMA_CPP = "llama.cpp"
    BITNET = "BitNet.cpp"
    AUTO = "auto"


class BaseModelBackend(ABC):
    """Abstract base class for all inference backends
    
    Provides a unified interface for model loading, generation, and streaming.
    All backends must implement these methods to work with Sur5.
    """
    
    @abstractmethod
    def load_model(self, model_path: str, **kwargs) -> bool:
        """Load a model from path
        
        Args:
            model_path: Path to the model file
            **kwargs: Backend-specific options (n_ctx, n_gpu_layers, etc.)
            
        Returns:
            bool: True if model loaded successfully
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt
        
        Args:
            prompt: The input prompt
            **kwargs: Generation parameters (max_tokens, temperature, etc.)
            
        Returns:
            str: Generated text
        """
        pass
    
    @abstractmethod
    def generate_stream(
        self, 
        prompt: str, 
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Stream generated text token by token
        
        Args:
            prompt: The input prompt
            callback: Function to call with each token (token, metadata)
            **kwargs: Generation parameters
            
        Returns:
            str: Complete generated text
        """
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Chat completion with message history
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            callback: Optional streaming callback
            **kwargs: Generation parameters
            
        Returns:
            str: Assistant's response
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> None:
        """Unload current model and free memory"""
        pass
    
    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        pass
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Get backend identifier"""
        pass
    
    @property
    def model_path(self) -> str:
        """Get current model path"""
        return getattr(self, '_model_path', '')


class LlamaCppBackend(BaseModelBackend):
    """llama.cpp backend using llama-cpp-python
    
    This is the primary backend for standard GGUF models with 2-8 bit quantization.
    Supports GPU acceleration via Metal (macOS) and CUDA (Windows/Linux).
    """
    
    def __init__(self):
        self._model = None
        self._model_path = ""
        self._llama_class = None
    
    def _get_llama_class(self):
        """Lazy import of Llama class"""
        if self._llama_class is None:
            try:
                from llama_cpp import Llama
                self._llama_class = Llama
            except ImportError as e:
                raise RuntimeError(f"llama-cpp-python not installed: {e}")
        return self._llama_class
    
    def load_model(self, model_path: str, **kwargs) -> bool:
        """Load a GGUF model using llama.cpp"""
        try:
            Llama = self._get_llama_class()
            
            # Unload existing model
            self.unload_model()
            
            # Default parameters
            n_ctx = kwargs.get('n_ctx', 4096)
            n_gpu_layers = kwargs.get('n_gpu_layers', -1)  # -1 = auto
            verbose = kwargs.get('verbose', False)
            
            logger.info(f"Loading model with llama.cpp: {os.path.basename(model_path)}")
            
            self._model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=verbose,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['n_ctx', 'n_gpu_layers', 'verbose']}
            )
            
            self._model_path = model_path
            logger.info(f"Model loaded successfully: {os.path.basename(model_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._model = None
            self._model_path = ""
            return False
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        if not self.is_loaded:
            raise RuntimeError("No model loaded")
        
        max_tokens = kwargs.get('max_tokens', 512)
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 0.9)
        stop = kwargs.get('stop', None)
        
        result = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop
        )
        
        return result['choices'][0]['text']
    
    def generate_stream(
        self, 
        prompt: str, 
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Stream generated text token by token"""
        if not self.is_loaded:
            raise RuntimeError("No model loaded")
        
        max_tokens = kwargs.get('max_tokens', 512)
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 0.9)
        stop = kwargs.get('stop', None)
        
        full_response = ""
        
        for chunk in self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
            stream=True
        ):
            token = chunk['choices'][0]['text']
            full_response += token
            
            if callback:
                metadata = {
                    'finish_reason': chunk['choices'][0].get('finish_reason')
                }
                callback(token, metadata)
        
        return full_response
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Chat completion with message history"""
        if not self.is_loaded:
            raise RuntimeError("No model loaded")
        
        max_tokens = kwargs.get('max_tokens', 512)
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 0.9)
        stop = kwargs.get('stop', None)
        stream = callback is not None
        
        if stream:
            full_response = ""
            for chunk in self._model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                stream=True
            ):
                delta = chunk['choices'][0].get('delta', {})
                token = delta.get('content', '')
                if token:
                    full_response += token
                    metadata = {
                        'finish_reason': chunk['choices'][0].get('finish_reason')
                    }
                    callback(token, metadata)
            return full_response
        else:
            result = self._model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop
            )
            return result['choices'][0]['message']['content']
    
    def unload_model(self) -> None:
        """Unload current model and free memory"""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_path = ""
            logger.info("Model unloaded")
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None
    
    @property
    def backend_name(self) -> str:
        """Get backend identifier"""
        return "llama.cpp"
    
    @property
    def model(self):
        """Get the underlying Llama model instance"""
        return self._model


class BitNetBackend(BaseModelBackend):
    """BitNet.cpp backend for 1-bit quantized models
    
    BitNet.cpp provides extremely efficient inference for 1-bit (b1.58) quantized
    models, offering up to 10x smaller models with minimal quality loss.
    
    Note: This backend requires the bitnet-api package or BitNet.cpp installation.
    """
    
    def __init__(self):
        self._model = None
        self._model_path = ""
        self._available = None
    
    def _check_availability(self) -> bool:
        """Check if BitNet backend is available"""
        if self._available is not None:
            return self._available
        
        try:
            # Try to import bitnet-api or similar
            # This is a placeholder - actual import depends on final BitNet Python bindings
            import subprocess
            result = subprocess.run(
                ['python', '-c', 'import bitnet'],
                capture_output=True,
                timeout=5
            )
            self._available = result.returncode == 0
        except Exception:
            self._available = False
        
        if not self._available:
            logger.debug("BitNet backend not available")
        
        return self._available
    
    def load_model(self, model_path: str, **kwargs) -> bool:
        """Load a BitNet model
        
        Note: Implementation depends on final BitNet.cpp Python bindings.
        Currently a placeholder that returns False.
        """
        if not self._check_availability():
            logger.warning("BitNet backend not available - install bitnet-api")
            return False
        
        try:
            # Placeholder for actual BitNet loading
            # When bitnet-api is available, this will be:
            # from bitnet import BitNetModel
            # self._model = BitNetModel(model_path, **kwargs)
            
            logger.info(f"Loading BitNet model: {os.path.basename(model_path)}")
            logger.warning("BitNet loading not yet implemented - use llama.cpp backend")
            return False
            
        except Exception as e:
            logger.error(f"Failed to load BitNet model: {e}")
            return False
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        if not self.is_loaded:
            raise RuntimeError("No BitNet model loaded")
        
        # Placeholder implementation
        raise NotImplementedError("BitNet generation not yet implemented")
    
    def generate_stream(
        self, 
        prompt: str, 
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Stream generated text token by token"""
        if not self.is_loaded:
            raise RuntimeError("No BitNet model loaded")
        
        # Placeholder implementation
        raise NotImplementedError("BitNet streaming not yet implemented")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs
    ) -> str:
        """Chat completion with message history"""
        if not self.is_loaded:
            raise RuntimeError("No BitNet model loaded")
        
        # Placeholder implementation
        raise NotImplementedError("BitNet chat completion not yet implemented")
    
    def unload_model(self) -> None:
        """Unload current model and free memory"""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_path = ""
            logger.info("BitNet model unloaded")
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None
    
    @property
    def backend_name(self) -> str:
        """Get backend identifier"""
        return "BitNet.cpp"


def detect_backend_for_model(model_path: str) -> InferenceBackend:
    """Auto-detect appropriate backend based on model file
    
    Args:
        model_path: Path to the model file
        
    Returns:
        InferenceBackend: Recommended backend for this model
    """
    if not model_path:
        return InferenceBackend.LLAMA_CPP
    
    name = os.path.basename(model_path).lower()
    ext = os.path.splitext(model_path)[1].lower()
    
    # BitNet models typically have specific naming conventions
    if "bitnet" in name or "b1.58" in name or ext == ".bitnet":
        return InferenceBackend.BITNET
    
    # Default to llama.cpp for GGUF and other standard formats
    return InferenceBackend.LLAMA_CPP


def create_backend(
    backend: InferenceBackend = InferenceBackend.AUTO, 
    model_path: str = None
) -> BaseModelBackend:
    """Factory function to create appropriate backend
    
    Args:
        backend: Requested backend (or AUTO to detect)
        model_path: Model path for auto-detection
        
    Returns:
        BaseModelBackend: Configured backend instance
    """
    if backend == InferenceBackend.AUTO and model_path:
        backend = detect_backend_for_model(model_path)
        logger.debug(f"backend: {backend.value}")
    
    if backend == InferenceBackend.BITNET:
        bitnet_backend = BitNetBackend()
        if bitnet_backend._check_availability():
            return bitnet_backend
        else:
            logger.warning("BitNet not available, falling back to llama.cpp")
            return LlamaCppBackend()
    else:
        return LlamaCppBackend()


def get_available_backends() -> List[InferenceBackend]:
    """Get list of available backends on this system
    
    Returns:
        List of available InferenceBackend values
    """
    available = [InferenceBackend.AUTO]
    
    # llama.cpp is always available (required dependency)
    try:
        from llama_cpp import Llama
        available.append(InferenceBackend.LLAMA_CPP)
    except ImportError:
        pass
    
    # Check BitNet availability
    bitnet = BitNetBackend()
    if bitnet._check_availability():
        available.append(InferenceBackend.BITNET)
    
    return available


# Export public API
__all__ = [
    "InferenceBackend",
    "BaseModelBackend",
    "LlamaCppBackend",
    "BitNetBackend",
    "detect_backend_for_model",
    "create_backend",
    "get_available_backends",
]
