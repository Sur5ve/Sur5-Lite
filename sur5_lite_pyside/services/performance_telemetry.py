"""
Performance Telemetry Module
Tracks generation performance for diagnostic and optimization purposes.

Features:
- Generation performance logging
- Rolling average tokens/second calculation
- Memory usage snapshots
- GPU utilization tracking (when available)
- Performance analysis and recommendations
"""

import json
import os
import time
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, List, Deque

# Log file path
PERF_LOG_PATH = "logs/perf.log"

# Rolling metrics storage (in-memory)
_ROLLING_METRICS: Dict[str, Deque[float]] = {
    "tokens_per_second": deque(maxlen=50),
    "time_to_first_token": deque(maxlen=50),
    "memory_usage_mb": deque(maxlen=50),
}

# Session statistics
_SESSION_STATS: Dict[str, Any] = {
    "total_generations": 0,
    "total_tokens": 0,
    "total_time": 0.0,
    "session_start": None,
}


def log_generation_performance(
    preset: str,
    n_ctx: int,
    vram_gb: float,
    gpu_type: str,
    success: bool,
    time_to_first_token: Optional[float],
    total_tokens: int,
    total_time: float,
    model_name: str = "Unknown"
):
    """
    Log generation performance metrics to local file.
    
    Args:
        preset: RAM preset used (e.g., "Minimal", "Fast")
        n_ctx: Context window size
        vram_gb: Available VRAM in GB
        gpu_type: GPU type (metal, cuda, cpu)
        success: Whether generation completed successfully
        time_to_first_token: Time in seconds to first token (None if stalled)
        total_tokens: Number of tokens generated
        total_time: Total generation time in seconds
        model_name: Name of the model file
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "preset": preset,
        "n_ctx": n_ctx,
        "vram_gb": vram_gb,
        "gpu_type": gpu_type,
        "success": success,
        "ttft": time_to_first_token,  # Time to first token
        "total_tokens": total_tokens,
        "total_time": total_time,
        "stalled": time_to_first_token is None or time_to_first_token > 30.0
    }
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(PERF_LOG_PATH), exist_ok=True)
    
    # Append to log file
    try:
        with open(PERF_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️  Failed to write performance log: {e}")
    
    # Update rolling metrics
    if total_time > 0 and total_tokens > 0:
        tps = total_tokens / total_time
        _ROLLING_METRICS["tokens_per_second"].append(tps)
    
    if time_to_first_token is not None:
        _ROLLING_METRICS["time_to_first_token"].append(time_to_first_token)
    
    # Update session stats
    if _SESSION_STATS["session_start"] is None:
        _SESSION_STATS["session_start"] = datetime.now().isoformat()
    
    _SESSION_STATS["total_generations"] += 1
    _SESSION_STATS["total_tokens"] += total_tokens
    _SESSION_STATS["total_time"] += total_time


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage statistics.
    
    Returns:
        Dictionary with memory usage in MB.
    """
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),  # Resident Set Size
            "vms_mb": mem_info.vms / (1024 * 1024),  # Virtual Memory Size
            "percent": process.memory_percent(),
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}


def get_gpu_utilization() -> Dict[str, Any]:
    """
    Get GPU utilization if available.
    
    Returns:
        Dictionary with GPU utilization metrics.
    """
    import platform
    
    result: Dict[str, Any] = {
        "available": False,
        "gpu_type": "none",
    }
    
    # Try GPUtil for NVIDIA GPUs
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            result["available"] = True
            result["gpu_type"] = "cuda"
            result["name"] = gpu.name
            result["load_percent"] = gpu.load * 100
            result["memory_used_mb"] = gpu.memoryUsed
            result["memory_total_mb"] = gpu.memoryTotal
            result["memory_percent"] = (gpu.memoryUsed / gpu.memoryTotal * 100) if gpu.memoryTotal > 0 else 0
            result["temperature_c"] = gpu.temperature if hasattr(gpu, 'temperature') else None
            return result
    except ImportError:
        pass
    except Exception:
        pass
    
    # For Metal on macOS, we can only report that it's available
    if platform.system() == "Darwin":
        try:
            from sur5_lite_pyside.services.model_engine import _check_macos_metal_support
            has_metal, vram_mb, gpu_name = _check_macos_metal_support()
            if has_metal:
                result["available"] = True
                result["gpu_type"] = "metal"
                result["name"] = gpu_name
                result["memory_total_mb"] = vram_mb
                # Note: macOS doesn't expose GPU load/utilization via standard APIs
                result["load_percent"] = None  
                return result
        except Exception:
            pass
    
    return result


def snapshot_memory() -> None:
    """
    Take a memory usage snapshot and store in rolling metrics.
    """
    mem = get_memory_usage()
    if "rss_mb" in mem:
        _ROLLING_METRICS["memory_usage_mb"].append(mem["rss_mb"])


def get_rolling_average_tps() -> Optional[float]:
    """
    Get rolling average tokens per second.
    
    Returns:
        Average tokens/second over recent generations, or None if no data.
    """
    tps_data = _ROLLING_METRICS["tokens_per_second"]
    if not tps_data:
        return None
    return sum(tps_data) / len(tps_data)


def get_rolling_average_ttft() -> Optional[float]:
    """
    Get rolling average time to first token.
    
    Returns:
        Average TTFT in seconds, or None if no data.
    """
    ttft_data = _ROLLING_METRICS["time_to_first_token"]
    if not ttft_data:
        return None
    return sum(ttft_data) / len(ttft_data)


def get_session_stats() -> Dict[str, Any]:
    """
    Get statistics for the current session.
    
    Returns:
        Dictionary with session statistics.
    """
    stats = _SESSION_STATS.copy()
    
    # Calculate session duration
    if stats["session_start"]:
        try:
            start = datetime.fromisoformat(stats["session_start"])
            duration = (datetime.now() - start).total_seconds()
            stats["session_duration_seconds"] = duration
        except Exception:
            stats["session_duration_seconds"] = 0
    
    # Calculate averages
    if stats["total_generations"] > 0:
        stats["avg_tokens_per_generation"] = stats["total_tokens"] / stats["total_generations"]
        stats["avg_time_per_generation"] = stats["total_time"] / stats["total_generations"]
    else:
        stats["avg_tokens_per_generation"] = 0
        stats["avg_time_per_generation"] = 0
    
    # Add rolling averages
    stats["rolling_avg_tps"] = get_rolling_average_tps()
    stats["rolling_avg_ttft"] = get_rolling_average_ttft()
    
    return stats


def get_comprehensive_metrics() -> Dict[str, Any]:
    """
    Get comprehensive system and performance metrics.
    
    Returns:
        Dictionary with all available metrics.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "session": get_session_stats(),
        "memory": get_memory_usage(),
        "gpu": get_gpu_utilization(),
        "rolling_metrics": {
            "tokens_per_second": list(_ROLLING_METRICS["tokens_per_second"]),
            "time_to_first_token": list(_ROLLING_METRICS["time_to_first_token"]),
            "memory_usage_mb": list(_ROLLING_METRICS["memory_usage_mb"]),
        }
    }


def export_metrics_to_file(filepath: str = "logs/metrics_export.json") -> bool:
    """
    Export comprehensive metrics to a JSON file.
    
    Args:
        filepath: Path to export file.
    
    Returns:
        True if export succeeded, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        metrics = get_comprehensive_metrics()
        
        with open(filepath, "w") as f:
            json.dump(metrics, f, indent=2)
        
        print(f"✓ Metrics exported to: {filepath}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to export metrics: {e}")
        return False


def reset_session_stats() -> None:
    """Reset session statistics."""
    global _SESSION_STATS
    _SESSION_STATS = {
        "total_generations": 0,
        "total_tokens": 0,
        "total_time": 0.0,
        "session_start": None,
    }
    
    # Clear rolling metrics
    for key in _ROLLING_METRICS:
        _ROLLING_METRICS[key].clear()
    
    print("📊 Session statistics reset")


def analyze_performance_logs() -> Dict[str, Any]:
    """
    Analyze performance logs and return summary statistics.
    
    Returns:
        Dictionary with performance statistics per preset
    """
    if not os.path.exists(PERF_LOG_PATH):
        return {"error": "No performance logs found"}
    
    # Read all log entries
    entries = []
    try:
        with open(PERF_LOG_PATH, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"error": f"Failed to read logs: {e}"}
    
    if not entries:
        return {"error": "No valid log entries found"}
    
    # Organize by preset
    preset_stats = {}
    
    for entry in entries:
        preset = entry.get("preset", "Unknown")
        
        if preset not in preset_stats:
            preset_stats[preset] = {
                "total_runs": 0,
                "successful_runs": 0,
                "stalled_runs": 0,
                "ttft_sum": 0,
                "ttft_count": 0,
                "total_tokens_sum": 0
            }
        
        stats = preset_stats[preset]
        stats["total_runs"] += 1
        
        if entry.get("success"):
            stats["successful_runs"] += 1
        
        if entry.get("stalled"):
            stats["stalled_runs"] += 1
        
        ttft = entry.get("ttft")
        if ttft is not None and ttft < 30:
            stats["ttft_sum"] += ttft
            stats["ttft_count"] += 1
        
        stats["total_tokens_sum"] += entry.get("total_tokens", 0)
    
    # Calculate averages
    summary = {}
    for preset, stats in preset_stats.items():
        avg_ttft = stats["ttft_sum"] / stats["ttft_count"] if stats["ttft_count"] > 0 else None
        success_rate = stats["successful_runs"] / stats["total_runs"] * 100 if stats["total_runs"] > 0 else 0
        
        summary[preset] = {
            "total_runs": stats["total_runs"],
            "success_rate": success_rate,
            "stall_rate": stats["stalled_runs"] / stats["total_runs"] * 100 if stats["total_runs"] > 0 else 0,
            "avg_ttft": avg_ttft,
            "total_tokens": stats["total_tokens_sum"]
        }
    
    # Get hardware info from latest entry
    latest = entries[-1] if entries else {}
    
    return {
        "hardware": {
            "gpu_type": latest.get("gpu_type", "Unknown"),
            "vram_gb": latest.get("vram_gb", 0)
        },
        "presets": summary
    }


def print_performance_summary():
    """Print a human-readable performance summary"""
    analysis = analyze_performance_logs()
    
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return
    
    print("=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    
    hardware = analysis.get("hardware", {})
    print(f"\nHardware: {hardware.get('gpu_type', 'Unknown')} ({hardware.get('vram_gb', 0):.1f} GB VRAM)")
    
    presets = analysis.get("presets", {})
    
    if not presets:
        print("\nNo preset data available")
        return
    
    print("\nPreset Performance:")
    for preset, stats in sorted(presets.items()):
        success_rate = stats["success_rate"]
        stall_rate = stats["stall_rate"]
        avg_ttft = stats.get("avg_ttft")
        
        # Status emoji
        if success_rate == 100 and stall_rate == 0 and avg_ttft and avg_ttft < 5:
            status = "✅"
        elif success_rate >= 50:
            status = "⚠️ "
        else:
            status = "❌"
        
        print(f"  {status} {preset:12s} - ", end="")
        print(f"Success: {success_rate:.0f}% ", end="")
        
        if avg_ttft:
            print(f"• Avg TTFT: {avg_ttft:.2f}s ", end="")
        
        if stall_rate > 0:
            print(f"• Stalls: {stall_rate:.0f}%", end="")
        
        print()
    
    # Recommendation
    print("\nRecommendation:")
    best_preset = None
    best_score = -1
    
    for preset, stats in presets.items():
        # Score based on success rate and speed
        score = stats["success_rate"]
        if stats.get("avg_ttft") and stats["avg_ttft"] < 10:
            score += 20  # Bonus for fast response
        
        if score > best_score:
            best_score = score
            best_preset = preset
    
    if best_preset:
        print(f"  Use '{best_preset}' for best results")
    
    print("=" * 80)


if __name__ == "__main__":
    print_performance_summary()

