#!/usr/bin/env python3
"""
Hardware Detection Utility
Detects system hardware capabilities for model recommendations
"""

import platform
from typing import Dict, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("WARNING: psutil not available - hardware detection limited")

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False
    print("INFO: GPUtil not available - GPU detection disabled")


class HardwareDetector:
    """Detect system hardware capabilities"""
    
    @staticmethod
    def get_cpu_info() -> Dict[str, any]:
        """Get CPU information"""
        info = {
            "architecture": platform.machine(),
            "processor": platform.processor(),
        }
        
        if HAS_PSUTIL:
            try:
                info["cores_physical"] = psutil.cpu_count(logical=False) or 0
                info["cores_logical"] = psutil.cpu_count(logical=True) or 0
                
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    info["frequency_mhz"] = cpu_freq.max if cpu_freq.max else cpu_freq.current
                else:
                    info["frequency_mhz"] = 0
            except Exception as e:
                print(f"WARNING: Error getting CPU info: {e}")
                info["cores_physical"] = 0
                info["cores_logical"] = 0
                info["frequency_mhz"] = 0
        else:
            info["cores_physical"] = 0
            info["cores_logical"] = 0
            info["frequency_mhz"] = 0
        
        return info
    
    @staticmethod
    def get_ram_info() -> Dict[str, any]:
        """Get RAM information"""
        if not HAS_PSUTIL:
            return {
                "total_gb": 0,
                "available_gb": 0,
                "percent_used": 0
            }
        
        try:
            mem = psutil.virtual_memory()
            return {
                "total_gb": mem.total / (1024**3),
                "available_gb": mem.available / (1024**3),
                "percent_used": mem.percent
            }
        except Exception as e:
            print(f"WARNING: Error getting RAM info: {e}")
            return {
                "total_gb": 0,
                "available_gb": 0,
                "percent_used": 0
            }
    
    @staticmethod
    def get_gpu_info() -> Optional[Dict[str, any]]:
        """Get GPU information (if available)"""
        if not HAS_GPUTIL:
            return None
        
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return None
            
            gpu = gpus[0]  # Primary GPU
            return {
                "name": gpu.name,
                "memory_total_mb": gpu.memoryTotal,
                "memory_free_mb": gpu.memoryFree,
                "memory_used_mb": gpu.memoryUsed,
                "gpu_load_percent": gpu.load * 100,
                "temperature_c": gpu.temperature if hasattr(gpu, 'temperature') else None,
                "driver": gpu.driver if hasattr(gpu, 'driver') else None
            }
        except Exception as e:
            print(f"INFO: No GPU detected or error: {e}")
            return None
    
    @staticmethod
    def get_system_summary() -> Dict[str, any]:
        """Get complete system summary"""
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine()
            },
            "cpu": HardwareDetector.get_cpu_info(),
            "ram": HardwareDetector.get_ram_info(),
            "gpu": HardwareDetector.get_gpu_info()
        }
    
    @staticmethod
    def recommend_model_size() -> Dict[str, any]:
        """Recommend model size based on available hardware
        
        Returns:
            Dictionary with recommended model parameters:
            - recommended_model: Model size recommendation (e.g., "7B-Q5_K_M")
            - max_context_length: Recommended max context
            - use_gpu: Whether GPU acceleration is recommended
            - gpu_layers: Number of GPU layers to use (0 = CPU only)
            - reasoning: Why this recommendation was made
        """
        ram_info = HardwareDetector.get_ram_info()
        ram_gb = ram_info.get("total_gb", 0)
        gpu_info = HardwareDetector.get_gpu_info()
        has_gpu = gpu_info is not None
        
        # Model size heuristics based on RAM
        if ram_gb >= 64:
            recommended = "70B-Q4_K_M"
            max_context = 8192
            reasoning = "High RAM (64GB+) - Can handle large 70B models"
        elif ram_gb >= 32:
            recommended = "13B-Q5_K_M"
            max_context = 8192
            reasoning = "Good RAM (32GB) - Optimal for 13B models with quality quantization"
        elif ram_gb >= 14:  # Changed from 16 to 14 to account for 16GB systems
            recommended = "7B-Q5_K_M"
            max_context = 4096
            reasoning = "Moderate RAM (14-32GB) - 7B models provide good balance"
        elif ram_gb >= 7:  # Changed from 8 to 7 to account for 8GB systems
            recommended = "3B-Q4_K_M"
            max_context = 2048
            reasoning = "Limited RAM (7-14GB) - Smaller models recommended"
        else:
            recommended = "1.5B-Q4_K_M"
            max_context = 1024
            reasoning = "Low RAM (<7GB) - Use smallest models for stability"
        
        # GPU recommendations
        if has_gpu:
            gpu_name = gpu_info.get("name", "Unknown")
            gpu_memory_mb = gpu_info.get("memory_total_mb", 0)
            gpu_memory_gb = gpu_memory_mb / 1024
            
            # Adjust GPU layers based on VRAM
            if gpu_memory_gb >= 12:
                gpu_layers = 40  # Full offload for large VRAM
                reasoning += f" | GPU detected ({gpu_name}, {gpu_memory_gb:.1f}GB VRAM) - Full offload"
            elif gpu_memory_gb >= 8:
                gpu_layers = 32  # Partial offload
                reasoning += f" | GPU detected ({gpu_name}, {gpu_memory_gb:.1f}GB VRAM) - Partial offload"
            elif gpu_memory_gb >= 4:
                gpu_layers = 20  # Light offload
                reasoning += f" | GPU detected ({gpu_name}, {gpu_memory_gb:.1f}GB VRAM) - Light offload"
            else:
                gpu_layers = 0  # CPU only for low VRAM
                reasoning += f" | GPU detected but VRAM too low ({gpu_memory_gb:.1f}GB) - CPU only"
        else:
            gpu_layers = 0
            reasoning += " | No GPU detected - CPU only"
        
        return {
            "recommended_model": recommended,
            "max_context_length": max_context,
            "use_gpu": has_gpu and gpu_layers > 0,
            "gpu_layers": gpu_layers,
            "reasoning": reasoning,
            "ram_gb": ram_gb,
            "gpu_detected": has_gpu,
            "gpu_name": gpu_info.get("name") if has_gpu else None
        }
    
    @staticmethod
    def format_system_info() -> str:
        """Format system information as human-readable string"""
        summary = HardwareDetector.get_system_summary()
        
        lines = []
        lines.append("=== System Information ===\n")
        
        # Platform
        platform_info = summary["platform"]
        lines.append(f"OS: {platform_info['system']} {platform_info['release']}")
        lines.append(f"Architecture: {platform_info['machine']}\n")
        
        # CPU
        cpu = summary["cpu"]
        lines.append(f"CPU:")
        if cpu["cores_physical"]:
            lines.append(f"  Cores: {cpu['cores_physical']} physical, {cpu['cores_logical']} logical")
            if cpu["frequency_mhz"]:
                lines.append(f"  Frequency: {cpu['frequency_mhz']:.0f} MHz")
        else:
            lines.append(f"  {cpu['processor']}")
        lines.append("")
        
        # RAM
        ram = summary["ram"]
        if ram["total_gb"]:
            lines.append(f"RAM:")
            lines.append(f"  Total: {ram['total_gb']:.1f} GB")
            lines.append(f"  Available: {ram['available_gb']:.1f} GB")
            lines.append(f"  Used: {ram['percent_used']:.1f}%\n")
        
        # GPU
        gpu = summary["gpu"]
        if gpu:
            lines.append(f"GPU:")
            lines.append(f"  Name: {gpu['name']}")
            lines.append(f"  VRAM: {gpu['memory_total_mb']:.0f} MB total, {gpu['memory_free_mb']:.0f} MB free")
            if gpu['temperature_c']:
                lines.append(f"  Temperature: {gpu['temperature_c']:.0f}°C")
        else:
            lines.append("GPU: Not detected or not available\n")
        
        # Recommendation
        lines.append("\n=== Model Recommendation ===")
        rec = HardwareDetector.recommend_model_size()
        lines.append(f"Recommended: {rec['recommended_model']}")
        lines.append(f"Max Context: {rec['max_context_length']} tokens")
        lines.append(f"GPU Layers: {rec['gpu_layers']}")
        lines.append(f"\nReasoning: {rec['reasoning']}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # Test hardware detection
    print(HardwareDetector.format_system_info())

