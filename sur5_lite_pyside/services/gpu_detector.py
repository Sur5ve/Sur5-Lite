#!/usr/bin/env python3
"""
GPU Detection Module
Detects GPU availability and capabilities for llama.cpp inference
"""

import subprocess
import shutil
import platform
import multiprocessing
from typing import Dict, Any, Optional, Tuple

# Logging
from utils.logger import create_module_logger
logger = create_module_logger(__name__)


# Metal detection cache (avoid repeated system_profiler calls)
_METAL_DETECTION_CACHE: Optional[Tuple[bool, int, str]] = None

# Thread count cache (avoid repeated detection)
_OPTIMAL_THREAD_COUNT: Optional[int] = None

# GPU capability cache (run once at startup)
_GPU_CAPABILITY: Optional[Dict[str, Any]] = None


def _get_optimal_thread_count() -> int:
    """
    Get optimal thread count based on CPU cores and platform.
    
    Strategy:
    - Intel Macs: Limited to 4 threads to prevent hanging issues
    - Other platforms: Use up to 8 threads for good performance
    - Caches result to avoid repeated system calls
    
    Returns:
        int: Optimal number of threads for model inference
    """
    global _OPTIMAL_THREAD_COUNT
    
    if _OPTIMAL_THREAD_COUNT is not None:
        return _OPTIMAL_THREAD_COUNT
    
    try:
        cpu_count = multiprocessing.cpu_count()
    except Exception:
        cpu_count = 4  # Safe default
    
    # Intel Macs need lower thread count to prevent hanging
    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        _OPTIMAL_THREAD_COUNT = min(cpu_count, 4)
        logger.debug(f"intel mac: {_OPTIMAL_THREAD_COUNT}/{cpu_count} threads")
    else:
        # Windows, Linux, Apple Silicon - can use more threads
        _OPTIMAL_THREAD_COUNT = min(cpu_count, 8)
        logger.debug(f"threads: {_OPTIMAL_THREAD_COUNT}/{cpu_count}")
    
    return _OPTIMAL_THREAD_COUNT


def _check_macos_metal_support() -> Tuple[bool, int, str]:
    """
    Check if macOS system has Metal GPU support using system_profiler.
    
    Returns:
        tuple: (has_metal: bool, vram_mb: int, gpu_name: str)
    """
    global _METAL_DETECTION_CACHE
    
    # Return cached result if available
    if _METAL_DETECTION_CACHE is not None:
        return _METAL_DETECTION_CACHE
    
    # Default fallback values
    fallback_result = (False, 0, "Unknown")
    
    try:
        # Check if system_profiler command exists
        if not shutil.which("system_profiler"):
            logger.warning("system_profiler command not found")
            _METAL_DETECTION_CACHE = fallback_result
            return fallback_result
        
        # Run system_profiler with timeout
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.warning(f"system_profiler returned error code {result.returncode}")
            _METAL_DETECTION_CACHE = fallback_result
            return fallback_result
        
        output = result.stdout
        
        # Parse output for Metal support
        has_metal = False
        vram_mb = 0
        gpu_name = "Unknown"
        
        # Check for Metal support
        if "Metal Support:" in output or "Metal:" in output:
            has_metal = True
        
        # Extract GPU name (look for "Chipset Model:")
        for line in output.split('\n'):
            if "Chipset Model:" in line:
                gpu_name = line.split("Chipset Model:")[-1].strip()
            elif "VRAM (Dynamic, Max):" in line:
                # Extract VRAM value (e.g., "1536 MB")
                vram_str = line.split(":")[-1].strip()
                try:
                    vram_mb = int(vram_str.split()[0])
                except (ValueError, IndexError):
                    pass
            elif "VRAM:" in line and vram_mb == 0:
                # Alternative VRAM format
                vram_str = line.split(":")[-1].strip()
                try:
                    vram_mb = int(vram_str.split()[0])
                except (ValueError, IndexError):
                    pass
        
        result_tuple = (has_metal, vram_mb, gpu_name)
        _METAL_DETECTION_CACHE = result_tuple
        
        # Log detection results
        if has_metal:
            logger.debug(f"metal: {gpu_name} vram={vram_mb}MB")
        else:
            logger.debug("No Metal support detected")
        
        return result_tuple
        
    except subprocess.TimeoutExpired:
        logger.warning("system_profiler timed out")
        _METAL_DETECTION_CACHE = fallback_result
        return fallback_result
    except Exception as e:
        logger.warning(f"Metal Detection Error: {e}")
        _METAL_DETECTION_CACHE = fallback_result
        return fallback_result


def detect_gpu_capability() -> Dict[str, Any]:
    """
    Detect GPU availability and capabilities for llama.cpp
    
    Returns:
        dict with keys:
            - has_gpu: bool
            - gpu_layers: int (-1 for auto, 0 for CPU-only)
            - gpu_type: str (cuda/metal/none)
            - gpu_vram_gb: int (estimated VRAM)
    """
    detection_result = {
        "has_gpu": False,
        "gpu_layers": 0,
        "gpu_type": "none",
        "gpu_vram_gb": 0
    }
    
    try:
        # Check for Metal FIRST on macOS (both Intel and Apple Silicon)
        # This must run before generic GPU detection to get accurate VRAM info
        if platform.system() == "Darwin":
            has_metal, vram_mb, gpu_name = _check_macos_metal_support()
            
            if has_metal:
                detection_result["has_gpu"] = True
                detection_result["gpu_type"] = "metal"
                detection_result["gpu_vram_gb"] = vram_mb // 1024 if vram_mb > 0 else 0
                
                # Handle low VRAM scenarios
                if vram_mb < 1024:
                    detection_result["gpu_layers"] = 0
                    logger.warning(f"Metal GPU detected but VRAM too low ({vram_mb}MB) - using CPU inference")
                elif vram_mb < 2048:
                    # Hybrid mode for low-VRAM Intel Macs (1-2GB range)
                    detection_result["gpu_layers"] = 6  # Light GPU offload
                    logger.info(f"Intel Mac hybrid mode: 6 GPU layers + 22 CPU layers ({vram_mb}MB VRAM)")
                    logger.debug(f"gpu: {gpu_name}")
                else:
                    # Full offload for high-VRAM systems (Apple Silicon M1/M2/M3)
                    detection_result["gpu_layers"] = -1  # Auto-offload all layers
                    
                    # Architecture-aware logging
                    if platform.machine() == "arm64":
                        logger.info("Apple Silicon detected - Metal GPU acceleration available")
                    elif platform.machine() == "x86_64":
                        logger.info(f"Intel Mac detected - Metal GPU acceleration available (GPU: {gpu_name}, VRAM: {vram_mb}MB)")
                    else:
                        logger.info("macOS detected - Metal GPU acceleration available")
                
                return detection_result
            
        # Try to detect CUDA GPU (NVIDIA) - for Windows/Linux
        try:
            import torch
            if torch.cuda.is_available():
                detection_result["has_gpu"] = True
                detection_result["gpu_layers"] = -1  # Auto-offload all layers
                detection_result["gpu_type"] = "cuda"
                detection_result["gpu_vram_gb"] = torch.cuda.get_device_properties(0).total_memory // (1024**3)
                logger.info(f"NVIDIA GPU detected: {torch.cuda.get_device_name(0)} ({detection_result['gpu_vram_gb']} GB VRAM)")
                return detection_result
        except ImportError:
            pass
        
        # Try alternative: check if llama-cpp-python was built with GPU support (generic fallback)
        try:
            from llama_cpp import llama_supports_gpu_offload
            if llama_supports_gpu_offload():
                detection_result["has_gpu"] = True
                detection_result["gpu_layers"] = -1
                detection_result["gpu_type"] = "detected"
                logger.info("GPU support detected in llama-cpp-python build")
                return detection_result
        except (ImportError, AttributeError):
            pass
        
        # Fallback: CPU-only
        logger.info("No GPU detected - using CPU inference")
        
    except Exception as e:
        logger.warning(f"GPU detection error: {e} - defaulting to CPU")
    
    return detection_result


def get_gpu_capability() -> Dict[str, Any]:
    """Get cached GPU capability detection"""
    global _GPU_CAPABILITY
    if _GPU_CAPABILITY is None:
        _GPU_CAPABILITY = detect_gpu_capability()
    return _GPU_CAPABILITY


def clear_gpu_cache() -> None:
    """Clear all GPU detection caches (useful for testing)"""
    global _GPU_CAPABILITY, _METAL_DETECTION_CACHE, _OPTIMAL_THREAD_COUNT
    _GPU_CAPABILITY = None
    _METAL_DETECTION_CACHE = None
    _OPTIMAL_THREAD_COUNT = None


# Expose commonly used functions
__all__ = [
    "detect_gpu_capability",
    "get_gpu_capability",
    "_get_optimal_thread_count",
    "_check_macos_metal_support",
    "clear_gpu_cache",
]

