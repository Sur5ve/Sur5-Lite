#!/usr/bin/env python3
"""
Model Service - High-level service for AI model management with Qt integration

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

Supports async model loading via qasync.
"""

import os
import time
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer, QThread

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)

# Try to import qasync for async operations
# qasync can cause issues with PyInstaller on Windows
# We gracefully fall back if it's not available or fails to load
import sys
import platform

HAS_QASYNC = False
try:
    # Enable qasync on macOS and Linux (not Windows due to PyInstaller issues)
    if platform.system() in ("Darwin", "Linux"):
        from qasync import asyncSlot
        HAS_QASYNC = True
        logger.debug(f"qasync on {platform.system()}")
    else:
        # Windows: Skip qasync to avoid PyInstaller complications
        logger.debug("qasync disabled (not needed on Windows - QThread is sufficient)")
        raise ImportError("Intentionally skipped for Windows compatibility")
except ImportError:
    # Fallback decorator that does nothing
    def asyncSlot(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator

from .model_engine import get_engine, get_thinking_preference, RAM_CONFIGS
from .dual_mode_utils import (
    DualModeConfig, 
    get_model_capabilities,
    should_show_thinking_toggle,
    is_dual_mode_model
)


class ModelLoadWorker(QThread):
    """
    Background worker for non-blocking model loading on Windows.
    
    Since qasync is disabled on Windows for PyInstaller compatibility,
    this QThread-based worker provides async model loading without
    freezing the UI.
    
    Signals:
        finished: Emitted when loading completes (success: bool, message: str)
        progress: Emitted during loading (percent: int, status: str)
        error: Emitted if loading fails (error_message: str)
    """
    finished = Signal(bool, str)  # success, message
    progress = Signal(int, str)   # percent, status
    error = Signal(str)           # error_message
    
    def __init__(self, engine, model_path: str, ram_config: str, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.model_path = model_path
        self.ram_config = ram_config
        self._is_cancelled = False
    
    def cancel(self) -> None:
        """Request cancellation of the loading operation."""
        self._is_cancelled = True
    
    def run(self) -> None:
        """
        Perform model loading in background thread.
        
        This runs the blocking Llama model initialization off the main thread,
        preventing UI freezes during the 10-30 second loading process.
        """
        try:
            model_name = os.path.basename(self.model_path)
            
            # Check for cancellation
            if self._is_cancelled:
                self.finished.emit(False, "Loading cancelled")
                return
            
            self.progress.emit(10, f"Loading {model_name}...")
            
            # Validate model path
            if not os.path.exists(self.model_path):
                self.error.emit(f"Model file not found: {self.model_path}")
                self.finished.emit(False, "Model not found")
                return
            
            if self._is_cancelled:
                self.finished.emit(False, "Loading cancelled")
                return
            
            self.progress.emit(30, "Initializing model parameters...")
            
            # Get RAM preset configuration
            from .model_engine import RAM_CONFIGS
            preset = RAM_CONFIGS.get(self.ram_config, RAM_CONFIGS["Balanced"])
            
            # Set runtime parameters
            self.engine.set_runtime_params(
                n_ctx=preset["n_ctx"],
                n_gpu_layers=preset.get("n_gpu_layers", 0)
            )
            
            if self._is_cancelled:
                self.finished.emit(False, "Loading cancelled")
                return
            
            self.progress.emit(50, "Loading model weights...")
            
            # Perform the actual model loading (blocking operation)
            # Note: Once _load_model_deferred starts, it cannot be interrupted
            # Cancellation only works before/after this call
            try:
                _ = self.engine._load_model_deferred(self.model_path)
            except Exception as e:
                self.error.emit(f"Failed to load model: {str(e)}")
                self.finished.emit(False, str(e))
                return
            
            # Check cancellation after loading (cleanup partial state)
            if self._is_cancelled:
                # Unload the model that was just loaded
                try:
                    self.engine.unload_model()
                except Exception:
                    pass
                self.finished.emit(False, "Loading cancelled")
                return
            
            self.progress.emit(90, "Finalizing...")
            
            self.progress.emit(100, "Model loaded successfully!")
            self.finished.emit(True, model_name)
            
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            self.error.emit(error_msg)
            self.finished.emit(False, error_msg)


class ModelService(QObject):
    """Service for managing AI models and inference"""
    
    # Signals
    model_loaded = Signal(str, str)  # model_name, model_path
    model_error = Signal(str)  # error_message  
    model_cancelled = Signal()  # Emitted when model loading is cancelled
    loading_progress = Signal(str, int)  # message, progress
    generation_started = Signal()
    generation_finished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get model engine instance
        self.engine = get_engine()
        
        # Model state
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
        
        # Stop flag for skip button
        self._stop_requested = False
        
        # Background worker for Windows async loading
        self._load_worker: Optional[ModelLoadWorker] = None
        
        # Lazy loading pattern
        
        logger.info("Model Service initialized")

        # SMART DEFAULT RAM PRESET SELECTION WITH AUTO-UPGRADE
        # Always detect optimal preset and upgrade if better than saved setting
        from sur5_lite_pyside.services.model_engine import load_settings, detect_optimal_preset, save_settings
        
        current_settings = load_settings()
        user_preset = current_settings.get("ram_config")
        
        # Always run auto-detection to find optimal preset
        detected_preset, reasoning = detect_optimal_preset()
        
        # Define preset priority (lower numbers = more restrictive)
        preset_priority = {
            "Ultra": 0,    # Most restrictive (512 context, for 4GB RAM devices)
            "Minimal": 1,
            "Fast": 2,
            "Balanced": 3,
            "Power": 4
        }
        
        current_priority = preset_priority.get(user_preset, 0)
        detected_priority = preset_priority.get(detected_preset, 0)
        
        # Decide which preset to use
        if not user_preset or user_preset == "Balanced":
            # No preset saved or using old default - use detected
            final_preset = detected_preset
            reason = "Auto-detected optimal preset for your hardware"
            
        elif detected_priority > current_priority:
            # Hardware can handle better preset - auto-upgrade
            final_preset = detected_preset
            reason = f"Auto-upgraded from {user_preset} → {detected_preset}"
            
        else:
            # User's saved preset is same or better - keep it
            final_preset = user_preset
            reason = f"Using saved preset (hardware supports {detected_preset})"
        
        logger.info("RAM PRESET SELECTION")
        logger.debug(reasoning)
        logger.info(f"Saved preset: {user_preset or 'None'}, Detected optimal: {detected_preset}")
        logger.info(f"Selected: {final_preset} - Reason: {reason}")
        
        self._ram_preset = final_preset
        
        # Save to settings if changed
        if final_preset != user_preset:
            current_settings["ram_config"] = final_preset
            save_settings(current_settings)
        
    def set_model_path(self, model_path: str) -> None:
        """Set model path without loading (PySide6 pattern)"""
        self.current_model_path = model_path
        self.current_model_name = os.path.basename(model_path)
        # Store in engine for lazy loading
        self.engine.set_model_path(model_path)
        # Ensure state reflects not-yet-loaded
        self.is_loaded = False
        logger.info(f"Model path set: {self.current_model_name}")
        
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
                
                # thinking mode: respect user pref if exists
                thinking_enabled = False  # Default
                try:
                    from PySide6.QtWidgets import QApplication
                    from .dual_mode_utils import get_model_capabilities
                    
                    app = QApplication.instance()
                    capabilities = get_model_capabilities(model_path)
                    is_thinking_model = capabilities.get("supports_thinking", False)
                    
                    if app and hasattr(app, 'settings_manager'):
                        # Get user's saved preference for this model category
                        thinking_enabled = app.settings_manager.get_thinking_mode_for_category(is_thinking_model)
                        logger.debug(f"saved think pref: {thinking_enabled}")
                    else:
                        # Fallback: auto-detect from model name
                        thinking_enabled = get_thinking_preference(model_path)
                        logger.debug(f"auto think: {thinking_enabled}")
                except Exception as e:
                    logger.warning(f"Could not load thinking preference: {e}")
                    # FIX BUG 3: Only set fallback inside except block, not after it
                    thinking_enabled = get_thinking_preference(model_path)
                    
                self.dual_mode_config.thinking_enabled = thinking_enabled
                
                self.loading_progress.emit("Model loaded successfully!", 100)
                self.model_loaded.emit(model_name, model_path)
                
                logger.info(f"Model loaded: {model_name} (Thinking: {thinking_enabled})")
                return True
            else:
                error_msg = f"Failed to load model: {model_name}"
                self.model_error.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            self.model_error.emit(error_msg)
            logger.error(error_msg)
            return False
    
    async def load_model_async(self, model_path: str, ram_config: str = "8GB") -> bool:
        """
        Async version of load_model - runs blocking operation in executor
        This prevents UI freezing during model loading
        
        Usage:
            await model_service.load_model_async(path, config)
        """
        if not HAS_QASYNC:
            # Fallback to sync version if qasync not available
            return self.load_model(model_path, ram_config)
        
        logger.debug("Using async model loading (non-blocking UI)")
        
        # Run the blocking load_model in an executor to avoid blocking the event loop
        # FIX BUG 7: Use get_running_loop() instead of deprecated get_event_loop()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,  # Use default ThreadPoolExecutor
            self.load_model,
            model_path,
            ram_config
        )
    
    def load_model_background(self, model_path: str, ram_config: str = "Balanced") -> bool:
        """
        Load model in background using QThread (Windows-compatible async loading).
        
        This method is designed for Windows where qasync is not available.
        It starts a background worker thread that performs the blocking model
        load while keeping the UI responsive.
        
        Args:
            model_path: Path to the GGUF model file
            ram_config: RAM preset name (Minimal, Fast, Balanced, Power)
        
        Returns:
            bool: True if loading was started successfully, False otherwise
        
        The actual loading result is communicated via signals:
            - model_loaded: Emitted on success with (model_name, model_path)
            - model_error: Emitted on failure with error message
            - loading_progress: Emitted during loading with (message, percent)
        """
        # Cancel any existing loading operation
        if self._load_worker is not None and self._load_worker.isRunning():
            logger.warning("Cancelling previous model load operation")
            self._load_worker.cancel()
            self._load_worker.wait(2000)  # Wait up to 2 seconds
        
        # Validate model path first
        if not os.path.exists(model_path):
            error_msg = f"Model file not found: {model_path}"
            self.model_error.emit(error_msg)
            return False
        
        # Store model info
        self.current_model_path = model_path
        self.current_model_name = os.path.basename(model_path)
        
        # Create and configure worker
        self._load_worker = ModelLoadWorker(
            engine=self.engine,
            model_path=model_path,
            ram_config=ram_config,
            parent=self
        )
        
        # Connect worker signals
        self._load_worker.finished.connect(self._on_load_worker_finished)
        self._load_worker.progress.connect(self._on_load_worker_progress)
        self._load_worker.error.connect(self._on_load_worker_error)
        
        # Start background loading
        logger.info(f"Starting background model load: {self.current_model_name}")
        self._load_worker.start()
        
        return True
    
    def _on_load_worker_finished(self, success: bool, message: str) -> None:
        """Handle completion of background model loading."""
        if success:
            self.is_loaded = True
            self.model_loaded.emit(self.current_model_name, self.current_model_path)
            logger.info(f"Background load complete: {message}")
            
            # cfg thinking mode
            try:
                thinking_enabled = get_thinking_preference(self.current_model_path)
                self.dual_mode_config.thinking_enabled = thinking_enabled
            except Exception:
                pass
        else:
            self.is_loaded = False
            if message != "Loading cancelled":
                self.model_error.emit(message)
            logger.error(f"Background load failed: {message}")
        
        # Clean up worker reference
        self._load_worker = None
    
    def _on_load_worker_progress(self, percent: int, status: str) -> None:
        """Handle progress updates from background loading."""
        self.loading_progress.emit(status, percent)
    
    def _on_load_worker_error(self, error_message: str) -> None:
        """Handle errors from background loading."""
        self.model_error.emit(error_message)
        logger.error(f"Background load error: {error_message}")
    
    def cancel_background_load(self) -> bool:
        """
        Cancel any in-progress background model loading.
        
        Returns:
            True if cancellation was initiated, False if no load in progress
        """
        if self._load_worker is not None and self._load_worker.isRunning():
            logger.info("Cancelling background model load")
            self._load_worker.cancel()
            
            # Clean up any partial model state
            self._cleanup_partial_load()
            
            # Emit cancellation signal for UI feedback
            self.model_cancelled.emit()
            
            return True
        return False
    
    def _cleanup_partial_load(self) -> None:
        """Clean up any partial state from a cancelled load."""
        try:
            # Reset loading flags
            self.is_loaded = False
            
            # If engine has partial state, unload it
            if self.engine and hasattr(self.engine, 'unload_model'):
                try:
                    self.engine.unload_model()
                except Exception:
                    pass
            
            logger.debug("Partial load state cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")
            
    def unload_model(self) -> None:
        """Unload the current model"""
        try:
            self.engine.unload_model()
            self.current_model_path = ""
            self.current_model_name = ""
            self.is_loaded = False
            
            logger.info("Model unloaded")
            
        except Exception as e:
            error_msg = f"Error unloading model: {str(e)}"
            self.model_error.emit(error_msg)
            logger.error(error_msg)
            
    def generate_response(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        stream_callback: Optional[Callable[[str, Optional[dict]], None]] = None,
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
            
    def stop_generation(self) -> None:
        """Request generation to stop (for skip button)"""
        logger.info("Stop generation requested")
        self._stop_requested = True
    
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
        stream_callback: Optional[Callable[[str, Optional[dict]], None]] = None
    ) -> str:
        """Generate a chat response using DIRECT llama-cpp-python (bypass llama-cpp-agent)"""
        # Reset stop flag at start of generation
        self._stop_requested = False
        
        # Telemetry tracking
        generation_start_time = None
        first_chunk_time = None
        chunk_count = 0
        
        if not self.current_model_path:
            raise RuntimeError("No model path set")

        # Lazy-load the llama.cpp model using optimized parameters.
        # This is executed from a background thread started by ConversationService.
        if not self.is_loaded:
            try:
                # Apply RAM preset before loading
                preset = RAM_CONFIGS.get(self._ram_preset, RAM_CONFIGS["Balanced"])
                
                # Validate preset for available VRAM
                from sur5_lite_pyside.services.model_engine import validate_preset_for_vram, get_safe_preset_for_vram
                is_safe, warning = validate_preset_for_vram(self._ram_preset)
                
                if not is_safe:
                    recommended = get_safe_preset_for_vram()
                    logger.warning(f"VRAM WARNING: {warning}. Recommended: Switch to '{recommended}' preset. Proceeding with '{self._ram_preset}' anyway.")
                
                self.engine.set_runtime_params(
                    n_ctx=preset["n_ctx"],
                    n_gpu_layers=preset.get("n_gpu_layers", 0)
                )
                logger.info(f"Lazy-loading model: {os.path.basename(self.current_model_path)}")
                _ = self.engine._load_model_deferred(self.current_model_path)
                self.is_loaded = True
                self.model_loaded.emit(self.current_model_name, self.current_model_path)
                logger.info("Model loaded successfully")
            except Exception as e:
                error_msg = f"Failed to load model: {str(e)}"
                self.model_error.emit(error_msg)
                raise RuntimeError(error_msg)
            
        try:
            self.generation_started.emit()
            generation_start_time = time.time()
            
            # Get the loaded model
            llm = self.engine.model
            if not llm:
                raise RuntimeError("Model not loaded")
            
            # reset KV cache before generation
            # This prevents "llama_decode returned -1" errors on multi-turn conversations
            # by ensuring a clean slate for the new message sequence
            if hasattr(llm, 'reset'):
                llm.reset()
                logger.debug("Model KV cache reset for new generation")
            
            # Use DIRECT llama-cpp-python chat completion (bypass agent)
            logger.debug("Using direct llama-cpp-python create_chat_completion")
            
            # Get model-specific stop sequences
            from sur5_lite_pyside.services.dual_mode_utils import get_default_stop_sequences, get_model_capabilities
            model_capabilities = get_model_capabilities(self.current_model_path) if self.current_model_path else {}
            stop_sequences = get_default_stop_sequences(
                model_capabilities=model_capabilities,
                model_path=self.current_model_path
            )
            # Filter to just the key stop tokens for reliable stopping
            primary_stops = ["<|im_end|>", "<|endoftext|>", "<|im_start|>user"]
            active_stops = [s for s in stop_sequences if s in primary_stops][:3]  # llama-cpp limits stop sequences
            
            # Create chat completion with streaming
            response_stream = llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens or 2048,
                temperature=temperature or 0.7,
                stream=True,
                stop=active_stops if active_stops else None
            )
            
            # Collect streaming response
            response_parts = []
            chunk_iter_count = 0
            try:
                for chunk in response_stream:
                    chunk_iter_count += 1
                    # Check stop flag (for skip button)
                    if self._stop_requested:
                        logger.info("Generation stopped by request")
                        break
                    
                    # Extract content from chunk
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        finish_reason = chunk['choices'][0].get('finish_reason')
                        
                        if content:
                            # Track first chunk timing
                            if first_chunk_time is None:
                                first_chunk_time = time.time()
                            
                            chunk_count += 1
                            response_parts.append(content)
                            
                            # Stream to callback
                            if stream_callback:
                                stream_callback(content)
            except Exception as e:
                logger.warning(f"Streaming error: {e}")
            
            response = "".join(response_parts)
            generation_end_time = time.time()
            
            # Log performance telemetry
            try:
                from sur5_lite_pyside.services.performance_telemetry import log_generation_performance
                from sur5_lite_pyside.services.model_engine import get_gpu_capability
                
                gpu_info = get_gpu_capability()
                preset = RAM_CONFIGS.get(self._ram_preset, RAM_CONFIGS["Balanced"])
                
                time_to_first_token = (first_chunk_time - generation_start_time) if first_chunk_time else None
                total_time = generation_end_time - generation_start_time
                
                log_generation_performance(
                    preset=self._ram_preset,
                    n_ctx=preset.get("n_ctx", 0),
                    vram_gb=gpu_info.get("gpu_vram_gb", 0),
                    gpu_type=gpu_info.get("gpu_type", "unknown"),
                    success=len(response) > 0,
                    time_to_first_token=time_to_first_token,
                    total_tokens=len(response.split()),
                    total_time=total_time,
                    model_name=os.path.basename(self.current_model_path) if self.current_model_path else "Unknown"
                )
            except Exception as e:
                logger.warning(f"Failed to log telemetry: {e}")
            
            # Update stats
            self.generation_stats["total_generations"] += 1
            if response:
                self.generation_stats["total_tokens"] += len(response.split())
                
            self.generation_finished.emit()
            return response
            
        except Exception as e:
            self.generation_finished.emit()
            logger.error(f"Generation error: {e}")
            raise e
            
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        base_info = self.engine.get_model_info()
        
        # Override with current runtime preset (not saved settings)
        current_preset = self._ram_preset
        current_config = RAM_CONFIGS.get(current_preset, {})
        
        return {
            **base_info,
            "ram_config": current_preset,  # Use runtime preset
            "context_size": current_config.get("n_ctx", 4096),  # Use runtime context size
            "model_name": self.current_model_name,
            "thinking_enabled": self.dual_mode_config.thinking_enabled,
            "dual_mode_config": self.dual_mode_config.to_dict(),
            "generation_stats": self.generation_stats.copy()
        }
        
    def get_ram_configurations(self) -> Dict[str, Dict]:
        """Get available RAM configurations"""
        return RAM_CONFIGS

    def set_ram_preset(self, preset_name: str) -> None:
        """Select RAM preset and defer reload until next use.
        
        Args:
            preset_name: The preset name (Minimal, Fast, Balanced, or Power).
        """
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
            logger.info(f"RAM preset set to {preset_name} • Context ~{RAM_CONFIGS[preset_name]['n_ctx']} (applies on next use)")

    def get_ram_preset(self) -> str:
        """Get the currently selected RAM preset name.
        
        Returns:
            str: The preset name (Minimal, Fast, Balanced, or Power).
        """
        return self._ram_preset
        
    def get_thinking_mode(self) -> bool:
        """Get current thinking mode setting based on model category
        
        Returns thinking mode preference for the current model category
        (thinking models vs non-thinking models)
        """
        # Try to get per-category preference from settings manager
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and hasattr(app, 'settings_manager'):
                # Check if current model supports thinking
                if self.current_model_path:
                    capabilities = get_model_capabilities(self.current_model_path)
                    is_thinking_model = capabilities.get("supports_thinking", False)
                    
                    # Get preference for this category
                    category_preference = app.settings_manager.get_thinking_mode_for_category(is_thinking_model)
                    return category_preference
        except Exception as e:
            logger.warning(f"Could not load per-category preference: {e}")
        
        # Fallback to current dual mode config
        return self.dual_mode_config.thinking_enabled
        
    def set_thinking_mode(self, enabled: bool) -> None:
        """Set thinking mode for current model category.
        
        Saves the preference separately for thinking models vs non-thinking models.
        
        Args:
            enabled: Whether to enable thinking mode.
        """
        if self.dual_mode_config.thinking_enabled != enabled:
            self.dual_mode_config.thinking_enabled = enabled
            
            # Save per-category preference to settings manager
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app and hasattr(app, 'settings_manager') and self.current_model_path:
                    # Check if current model supports thinking
                    capabilities = get_model_capabilities(self.current_model_path)
                    is_thinking_model = capabilities.get("supports_thinking", False)
                    
                    # Save preference for this category
                    app.settings_manager.set_thinking_mode_for_category(is_thinking_model, enabled)
            except Exception as e:
                logger.warning(f"Could not save per-category preference: {e}")
            
            logger.info(f"Thinking mode: {'enabled' if enabled else 'disabled'}")
            
    def get_dual_mode_config(self) -> DualModeConfig:
        """Get dual mode configuration"""
        return self.dual_mode_config
        
    def set_dual_mode_config(self, config: DualModeConfig) -> None:
        """Set dual mode configuration.
        
        Args:
            config: The new dual mode configuration.
        """
        self.dual_mode_config = config
        logger.debug("Dual mode configuration updated")
        
    def update_model_settings(self, settings: Dict[str, Any]) -> None:
        """Update model settings.
        
        Args:
            settings: Dictionary of settings to update.
        """
        try:
            self.engine.update_settings(settings)
            logger.debug("Model settings updated")
        except Exception as e:
            error_msg = f"Error updating settings: {str(e)}"
            self.model_error.emit(error_msg)
            logger.error(error_msg)
            
    def set_ram_config(self, ram_config: str) -> None:
        """Set RAM configuration and reload if model is loaded.
        
        Args:
            ram_config: The RAM configuration name.
        """
        if ram_config in RAM_CONFIGS:
            current_settings = self.engine.get_model_info().get("settings", {})
            current_settings["ram_config"] = ram_config
            self.engine.update_settings(current_settings)
            
            # If model is loaded, suggest reload
            if self.is_loaded:
                logger.info(f"RAM config changed to {ram_config}. Consider reloading model for changes to take effect.")
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
        
    def reset_generation_stats(self) -> None:
        """Reset generation statistics."""
        self.generation_stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "average_tokens_per_second": 0.0
        }
        logger.debug("Generation stats reset")
        
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
        
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.is_loaded:
                self.unload_model()
            logger.info("Model service cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            
    def get_model_thinking_preference(self, model_path: str) -> bool:
        """Get thinking mode preference for a model"""
        try:
            from .model_engine import get_thinking_preference as engine_get_thinking_pref
            return engine_get_thinking_pref(model_path)
        except Exception as e:
            logger.error(f"Error getting thinking preference: {e}")
            return False
