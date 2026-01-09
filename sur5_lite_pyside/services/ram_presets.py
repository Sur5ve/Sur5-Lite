#!/usr/bin/env python3
"""
RAM Presets Module
Configuration presets for different system memory/VRAM capacities
"""

import logging
from typing import Dict, Any, Tuple

from .gpu_detector import get_gpu_capability

logger = logging.getLogger(__name__)


# Intelligent RAM presets with unified CPU/GPU support
RAM_CONFIGS: Dict[str, Dict[str, Any]] = {
    # User-facing name → runtime parameters
    "Ultra": {
        "n_ctx": 512,
        "n_gpu_layers": 0,  # Force CPU-only for ultra-constrained systems
        "label": "1-2 GB • ~512",
        "description": "Ultra-low-resource (ASUS E410KA, 4GB RAM) • Fastest response",
        "kv_cache_estimate_mb": 112  # estimate_kv_cache_size(512) - very small footprint
    },
    "Minimal": {
        "n_ctx": 2048,
        "n_gpu_layers": "auto",  # Auto-detect GPU
        "label": "2 GB • ~2k",
        "description": "Low-end systems • Essential context only",
        "kv_cache_estimate_mb": 448  # estimate_kv_cache_size(2048) with Qwen3 defaults
    },
    "Fast": {
        "n_ctx": 8192,
        "n_gpu_layers": "auto",  # Auto-detect GPU
        "label": "8 GB • ~8k",
        "description": "Mid-range systems (8+ GB RAM) • Fastest response",
        "kv_cache_estimate_mb": 1792  # estimate_kv_cache_size(8192)
    },
    "Balanced": {
        "n_ctx": 24576,
        "n_gpu_layers": "auto",  # Auto-detect GPU
        "label": "16 GB • ~24k",
        "description": "High-end systems (15+ GB RAM) • Optimal for thinking mode",
        "kv_cache_estimate_mb": 5376  # estimate_kv_cache_size(24576)
    },
    "Power": {
        "n_ctx": 32768,
        "n_gpu_layers": "auto",  # Auto-detect GPU
        "label": "24 GB+ • ~32k",
        "description": "Maximum context • GPU (8+ GB VRAM) or Workstation CPU (24+ GB RAM)",
        "kv_cache_estimate_mb": 7168  # estimate_kv_cache_size(32768)
    }
}


def estimate_kv_cache_size(
    n_ctx: int,
    n_layers: int = 28,
    n_heads: int = 16,
    head_dim: int = 128,
    dtype_bytes: int = 2
) -> float:
    """
    Estimate KV cache VRAM usage in MB.
    
    Default values are for Qwen3-1.7B:
    - 28 layers
    - 16 attention heads
    - 128 dimensions per head
    - FP16 precision (2 bytes per value)
    
    Formula: n_ctx * 2 (K and V) * n_layers * n_heads * head_dim * dtype_bytes / 1024^2
    
    Args:
        n_ctx: Context window size
        n_layers: Number of transformer layers
        n_heads: Number of attention heads
        head_dim: Dimension of each attention head
        dtype_bytes: Bytes per value (2 for FP16, 4 for FP32)
    
    Returns:
        Estimated KV cache size in megabytes
    """
    size_mb = (n_ctx * 2 * n_layers * n_heads * head_dim * dtype_bytes) / (1024 ** 2)
    return size_mb


def detect_optimal_preset() -> Tuple[str, str]:
    """
    Intelligently detect the optimal RAM preset based on comprehensive hardware analysis.
    
    Returns:
        tuple: (preset_name, reasoning)
    """
    # Import HardwareDetector for CPU/RAM detection
    try:
        from sur5_lite_pyside.utils.hardware_detector import HardwareDetector
        has_hardware_detector = True
    except ImportError:
        has_hardware_detector = False
        logger.debug("HardwareDetector not available - using basic detection")
    
    # Get hardware info
    gpu_info = get_gpu_capability()
    has_gpu = gpu_info.get("has_gpu", False)
    gpu_type = gpu_info.get("gpu_type", "none")
    vram_gb = gpu_info.get("gpu_vram_gb", 0)
    
    # System RAM and CPU info
    if has_hardware_detector:
        cpu_info = HardwareDetector.get_cpu_info()
        ram_info = HardwareDetector.get_ram_info()
        cpu_count = cpu_info.get("cores_logical", 0)
        cpu_freq_mhz = cpu_info.get("frequency_mhz", 0)
        cpu_ghz = cpu_freq_mhz / 1000 if cpu_freq_mhz else 0
        total_ram_gb = ram_info.get("total_gb", 0)
    else:
        # Fallback to basic detection
        import psutil
        cpu_count = psutil.cpu_count(logical=True) or 0
        cpu_freq = psutil.cpu_freq()
        cpu_ghz = cpu_freq.current / 1000 if cpu_freq else 0
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
    
    reasoning = []
    reasoning.append("Hardware Analysis:")
    reasoning.append(f"  CPU: {cpu_count} cores @ {cpu_ghz:.1f} GHz")
    reasoning.append(f"  RAM: {total_ram_gb:.1f} GB")
    reasoning.append(f"  GPU: {gpu_type} ({vram_gb:.1f} GB VRAM)" if has_gpu else "  GPU: None (CPU-only)")
    
    # Decision logic with unified CPU/GPU Power preset support
    
    # TIER 1: Power preset (32k context) - GPU or high-end CPU
    if has_gpu and vram_gb >= 8:
        # High-end GPU (RTX 3060 12GB+, M1 Pro/Max, etc.)
        preset = "Power"
        reasoning.append(f"✅ High VRAM GPU ({vram_gb:.1f}GB) → Power preset (32k context, GPU-accelerated)")
    
    elif not has_gpu and total_ram_gb >= 24 and cpu_count >= 12:
        # Workstation-class CPU system (32+ GB RAM preferred)
        preset = "Power"
        reasoning.append(f"✅ Workstation CPU ({cpu_count} cores, {total_ram_gb:.1f}GB RAM) → Power preset (32k context)")
        reasoning.append(f"   Note: CPU-only inference is slower but handles maximum context")
    
    # TIER 2: Balanced preset (24k context) - Mid-high systems
    elif has_gpu and vram_gb >= 4:
        # Mid-range GPU (RTX 3050, M1 base, etc.)
        preset = "Balanced"
        reasoning.append(f"✅ Mid-range GPU ({vram_gb:.1f}GB VRAM) → Balanced preset (24k context)")
    
    elif not has_gpu and total_ram_gb >= 15 and cpu_count >= 8:
        # High-end CPU system (16 GB RAM shows as ~15.7 GB after hardware reservation)
        preset = "Balanced"
        reasoning.append(f"✅ High-end CPU ({cpu_count} cores, {total_ram_gb:.1f}GB RAM) → Balanced preset (24k context)")
    
    # TIER 3: Fast preset (8k context) - Mid-range systems
    elif has_gpu and vram_gb >= 2:
        # Entry-level GPU
        preset = "Fast"
        reasoning.append(f"⚠️ Entry-level GPU ({vram_gb:.1f}GB VRAM) → Fast preset (8k context)")
    
    elif not has_gpu and total_ram_gb >= 8 and cpu_count >= 4:
        # Mid-range CPU system
        preset = "Fast"
        reasoning.append(f"✅ Mid-range CPU ({cpu_count} cores, {total_ram_gb:.1f}GB RAM) → Fast preset (8k context)")
    
    # TIER 4: Minimal preset (2k context) - Low-end systems or very low VRAM
    elif has_gpu and vram_gb > 0 and vram_gb < 2:
        # Very low VRAM (Intel Iris Plus range: 1-2GB)
        preset = "Minimal"
        reasoning.append(f"⚠️ Very low VRAM ({vram_gb:.1f}GB) → Minimal preset (2k context)")
        reasoning.append(f"   Reason: GPU offload enabled but VRAM insufficient for large KV cache")
    
    elif has_gpu and vram_gb < 0.5:
        # Tiny GPU VRAM (<512MB Intel UHD) - treat as CPU-only
        if total_ram_gb >= 8 and cpu_count >= 4:
            preset = "Fast"
            reasoning.append(f"✅ CPU-only mode (GPU VRAM too low: {vram_gb*1024:.0f}MB)")
            reasoning.append(f"   {cpu_count} cores, {total_ram_gb:.1f}GB RAM → Fast preset")
        elif total_ram_gb < 5:
            preset = "Ultra"
            reasoning.append(f"⚠️ Ultra-constrained (GPU VRAM: {vram_gb*1024:.0f}MB, RAM: {total_ram_gb:.1f}GB)")
            reasoning.append(f"   → Ultra preset (512 context) for maximum speed")
        else:
            preset = "Minimal"
            reasoning.append(f"⚠️ CPU-only mode (GPU VRAM too low: {vram_gb*1024:.0f}MB)")
            reasoning.append(f"   Limited resources → Minimal preset")
    
    elif total_ram_gb < 5:
        # Ultra-constrained system (4GB RAM or less) - ASUS E410KA, etc.
        preset = "Ultra"
        reasoning.append(f"⚠️ Very limited RAM ({total_ram_gb:.1f}GB) → Ultra preset (512 context)")
        reasoning.append(f"   Optimized for maximum speed on constrained devices")
    
    else:
        # Low-end or constrained system
        preset = "Minimal"
        reasoning.append(f"⚠️ Limited resources ({cpu_count} cores, {total_ram_gb:.1f}GB RAM) → Minimal preset (2k context)")
    
    reasoning_text = "\n".join(reasoning)
    return preset, reasoning_text


def get_safe_preset_for_vram() -> str:
    """
    Auto-select appropriate preset based on available VRAM.
    
    DEPRECATED: Use detect_optimal_preset() for comprehensive detection.
    This function is kept for backward compatibility.
    
    Returns:
        Recommended preset name
    """
    preset, _ = detect_optimal_preset()
    return preset


def validate_preset_for_vram(preset_name: str) -> Tuple[bool, str]:
    """
    Check if a preset will fit in available VRAM.
    
    Args:
        preset_name: Name of the preset to validate
    
    Returns:
        Tuple of (is_safe, warning_message)
        is_safe: True if preset should work, False if it may stall
        warning_message: Empty if safe, otherwise contains warning text
    """
    if preset_name not in RAM_CONFIGS:
        return False, f"Unknown preset: {preset_name}"
    
    gpu_info = get_gpu_capability()
    available_vram_gb = gpu_info.get("gpu_vram_gb", 0)
    
    # If no GPU, all presets are safe (CPU mode)
    if not gpu_info.get("has_gpu", False):
        return True, ""
    
    preset = RAM_CONFIGS[preset_name]
    kv_cache_mb = preset.get("kv_cache_estimate_mb", 0)
    
    # Rough estimate: model weights (~1GB for Qwen3-1.7B) + KV cache + 20% overhead
    model_size_mb = 1024  # ~1GB for typical small models
    overhead_factor = 1.2
    required_vram_mb = (model_size_mb + kv_cache_mb) * overhead_factor
    required_vram_gb = required_vram_mb / 1024
    
    if available_vram_gb < required_vram_gb:
        return False, f"Preset requires ~{required_vram_gb:.1f}GB, available: {available_vram_gb:.1f}GB"
    
    return True, ""


def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific preset.
    
    Args:
        preset_name: Name of the preset
    
    Returns:
        Preset configuration dictionary, or Balanced preset if not found
    """
    return RAM_CONFIGS.get(preset_name, RAM_CONFIGS["Balanced"])


# Expose commonly used items
__all__ = [
    "RAM_CONFIGS",
    "estimate_kv_cache_size",
    "detect_optimal_preset",
    "get_safe_preset_for_vram",
    "validate_preset_for_vram",
    "get_preset_config",
]

