#!/usr/bin/env python3
"""
Health Check Utility - Provides startup diagnostics for Sur5

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

import os
import sys
import platform
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Import portable paths for USB-compatible path resolution
try:
    from .portable_paths import get_models_root, get_embeddings_dir, get_app_root
    PORTABLE_PATHS_AVAILABLE = True
except ImportError:
    PORTABLE_PATHS_AVAILABLE = False


class HealthCheckResult:
    """Result of a health check with status and details."""
    
    def __init__(self, name: str, passed: bool, message: str = "", details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
    
    def __bool__(self) -> bool:
        return self.passed
    
    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"HealthCheckResult({self.name}: {status} - {self.message})"


def check_gpu_availability() -> HealthCheckResult:
    """
    Check Metal/CUDA GPU availability and return detailed status.
    
    Returns:
        HealthCheckResult with GPU detection information.
    """
    details: Dict[str, Any] = {
        "platform": platform.system(),
        "machine": platform.machine(),
        "has_gpu": False,
        "gpu_type": "none",
        "gpu_name": None,
        "vram_mb": 0,
    }
    
    try:
        # Import model engine GPU detection
        from sur5_lite_pyside.services.model_engine import detect_gpu_capability, _check_macos_metal_support
        
        # Check for Metal on macOS
        if platform.system() == "Darwin":
            has_metal, vram_mb, gpu_name = _check_macos_metal_support()
            details["has_gpu"] = has_metal
            details["gpu_type"] = "metal" if has_metal else "none"
            details["gpu_name"] = gpu_name
            details["vram_mb"] = vram_mb
            
            if has_metal:
                if platform.machine() == "arm64":
                    message = f"Apple Silicon detected: {gpu_name} (Metal)"
                else:
                    message = f"Intel Mac Metal: {gpu_name} ({vram_mb}MB VRAM)"
                return HealthCheckResult("GPU", True, message, details)
            else:
                return HealthCheckResult("GPU", False, "No Metal GPU detected", details)
        
        # Check for CUDA on Windows/Linux
        gpu_info = detect_gpu_capability()
        details["has_gpu"] = gpu_info.get("has_gpu", False)
        details["gpu_type"] = gpu_info.get("gpu_type", "none")
        details["vram_mb"] = gpu_info.get("gpu_vram_gb", 0) * 1024
        
        if details["has_gpu"]:
            message = f"{details['gpu_type'].upper()} GPU detected"
            if details["vram_mb"] > 0:
                message += f" ({details['vram_mb']}MB VRAM)"
            return HealthCheckResult("GPU", True, message, details)
        else:
            return HealthCheckResult("GPU", False, "No GPU detected - CPU inference mode", details)
            
    except ImportError as e:
        return HealthCheckResult("GPU", False, f"GPU detection unavailable: {e}", details)
    except Exception as e:
        return HealthCheckResult("GPU", False, f"GPU detection error: {e}", details)


def check_model_path(model_path: Optional[str] = None) -> HealthCheckResult:
    """
    Verify model file exists and has valid format.
    
    Args:
        model_path: Optional path to check. If None, checks configured model.
    
    Returns:
        HealthCheckResult with model path status.
    """
    details: Dict[str, Any] = {
        "path": model_path,
        "exists": False,
        "size_mb": 0,
        "format": None,
    }
    
    # Get model path from settings if not provided
    if model_path is None:
        try:
            from sur5_lite_pyside.services.model_engine import load_settings
            settings = load_settings()
            model_path = settings.get("model_path", "")
            details["path"] = model_path
        except Exception:
            pass
    
    if not model_path:
        return HealthCheckResult("Model", False, "No model path configured", details)
    
    # Check if file exists
    if not os.path.exists(model_path):
        return HealthCheckResult("Model", False, f"Model file not found: {model_path}", details)
    
    details["exists"] = True
    
    # Check file size
    try:
        size_bytes = os.path.getsize(model_path)
        details["size_mb"] = size_bytes / (1024 * 1024)
    except Exception:
        pass
    
    # Check file format
    path_lower = model_path.lower()
    if path_lower.endswith('.gguf'):
        details["format"] = "GGUF"
    elif path_lower.endswith('.bin'):
        details["format"] = "BIN"
    elif path_lower.endswith('.safetensors'):
        details["format"] = "SafeTensors"
    else:
        return HealthCheckResult("Model", False, f"Unknown model format: {model_path}", details)
    
    # Validate GGUF header (basic check)
    if details["format"] == "GGUF":
        try:
            with open(model_path, 'rb') as f:
                magic = f.read(4)
                if magic != b'GGUF':
                    return HealthCheckResult("Model", False, "Invalid GGUF file (bad magic header)", details)
        except Exception as e:
            return HealthCheckResult("Model", False, f"Cannot read model file: {e}", details)
    
    model_name = os.path.basename(model_path)
    message = f"Model OK: {model_name} ({details['size_mb']:.0f}MB, {details['format']})"
    return HealthCheckResult("Model", True, message, details)


def check_dependencies() -> HealthCheckResult:
    """
    Check if critical dependencies are available.
    
    Returns:
        HealthCheckResult with dependency status.
    """
    dependencies: Dict[str, bool] = {}
    missing: List[str] = []
    optional_missing: List[str] = []
    
    # Critical dependencies
    critical = [
        ("PySide6", "pyside6"),
        ("llama_cpp", "llama-cpp-python"),
    ]
    
    # Optional dependencies
    optional = []
    
    for module_name, package_name in critical:
        try:
            __import__(module_name.split('.')[0])
            dependencies[module_name] = True
        except ImportError:
            dependencies[module_name] = False
            missing.append(package_name)
    
    for module_name, package_name in optional:
        try:
            __import__(module_name.split('.')[0])
            dependencies[module_name] = True
        except ImportError:
            dependencies[module_name] = False
            optional_missing.append(package_name)
    
    details = {"dependencies": dependencies}
    
    if missing:
        return HealthCheckResult(
            "Dependencies", 
            False, 
            f"Missing critical packages: {', '.join(missing)}", 
            details
        )
    
    if optional_missing:
        message = f"All critical packages OK. Optional missing: {', '.join(optional_missing)}"
    else:
        message = "All dependencies OK"
    
    return HealthCheckResult("Dependencies", True, message, details)


def check_system_resources() -> HealthCheckResult:
    """
    Check system resources (RAM, disk space).
    
    Returns:
        HealthCheckResult with resource status.
    """
    details: Dict[str, Any] = {
        "ram_total_gb": 0,
        "ram_available_gb": 0,
        "disk_free_gb": 0,
    }
    
    try:
        import psutil
        
        # Check RAM
        mem = psutil.virtual_memory()
        details["ram_total_gb"] = mem.total / (1024**3)
        details["ram_available_gb"] = mem.available / (1024**3)
        
        # Check disk space
        disk = psutil.disk_usage('.')
        details["disk_free_gb"] = disk.free / (1024**3)
        
        warnings = []
        
        if details["ram_available_gb"] < 4:
            warnings.append(f"Low RAM: {details['ram_available_gb']:.1f}GB available")
        
        if details["disk_free_gb"] < 10:
            warnings.append(f"Low disk: {details['disk_free_gb']:.1f}GB free")
        
        if warnings:
            return HealthCheckResult("Resources", True, "; ".join(warnings), details)
        
        message = f"RAM: {details['ram_available_gb']:.1f}GB free, Disk: {details['disk_free_gb']:.1f}GB free"
        return HealthCheckResult("Resources", True, message, details)
        
    except ImportError:
        return HealthCheckResult("Resources", True, "psutil not available, skipping resource check", details)
    except Exception as e:
        return HealthCheckResult("Resources", True, f"Resource check error: {e}", details)


def run_all_checks(model_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run all health checks and return comprehensive summary.
    
    Args:
        model_path: Optional model path to check.
    
    Returns:
        Dictionary with check results and overall status.
    """
    results: List[HealthCheckResult] = [
        check_dependencies(),
        check_system_resources(),
        check_gpu_availability(),
        check_model_path(model_path),
    ]
    
    all_passed = all(r.passed for r in results)
    critical_failed = any(
        not r.passed and r.name in ["Dependencies", "Model"] 
        for r in results
    )
    
    summary = {
        "all_passed": all_passed,
        "critical_failed": critical_failed,
        "checks": {r.name: {"passed": r.passed, "message": r.message, "details": r.details} for r in results},
        "summary_message": "",
    }
    
    if all_passed:
        summary["summary_message"] = "All health checks passed"
    elif critical_failed:
        failed = [r.name for r in results if not r.passed]
        summary["summary_message"] = f"Critical checks failed: {', '.join(failed)}"
    else:
        warnings = [r.name for r in results if not r.passed]
        summary["summary_message"] = f"Non-critical issues: {', '.join(warnings)}"
    
    return summary


def print_health_report(model_path: Optional[str] = None) -> bool:
    """
    Run health checks and print formatted report.
    
    Args:
        model_path: Optional model path to check.
    
    Returns:
        bool: True if all critical checks passed.
    """
    print("\n" + "=" * 60)
    print("Sur5 Health Check Report")
    print("=" * 60)
    
    results = run_all_checks(model_path)
    
    for name, check in results["checks"].items():
        status = "PASS" if check["passed"] else "FAIL"
        icon = "✓" if check["passed"] else "✗"
        print(f"\n{icon} [{status}] {name}")
        print(f"   {check['message']}")
    
    print("\n" + "-" * 60)
    print(f"Summary: {results['summary_message']}")
    print("=" * 60 + "\n")
    
    return not results["critical_failed"]


# Export public API
__all__ = [
    "HealthCheckResult",
    "check_gpu_availability",
    "check_model_path",
    "check_dependencies",
    "check_system_resources",
    "run_all_checks",
    "print_health_report",
]


if __name__ == "__main__":
    # Run health checks when executed directly
    success = print_health_report()
    sys.exit(0 if success else 1)













