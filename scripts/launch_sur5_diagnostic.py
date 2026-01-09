#!/usr/bin/env python3.11
"""
Sur5 Diagnostic Launcher
Provides detailed logging for GPU offload and token generation troubleshooting
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{title.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

def print_info(label, value):
    """Print labeled information"""
    print(f"{Colors.OKBLUE}{label}:{Colors.ENDC} {value}")

def print_success(message):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def get_system_info():
    """Collect system information for diagnostics"""
    import platform
    import subprocess
    
    info = {
        "os": platform.system(),
        "os_version": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }
    
    # Get macOS GPU info if on Darwin
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout
                # Parse GPU name and VRAM
                for line in output.split('\n'):
                    if "Chipset Model:" in line:
                        info["gpu_name"] = line.split("Chipset Model:")[-1].strip()
                    elif "VRAM (Dynamic, Max):" in line or "VRAM:" in line:
                        info["vram"] = line.split(":")[-1].strip()
        except Exception as e:
            info["gpu_error"] = str(e)
    
    return info

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Dependency Check")
    
    dependencies = {
        "PySide6": "PySide6",
        "llama-cpp-python": "llama_cpp",
        "llama-cpp-agent": "llama_cpp_agent",
    }
    
    all_ok = True
    for name, module in dependencies.items():
        try:
            __import__(module)
            print_success(f"{name} installed")
        except ImportError:
            print_error(f"{name} NOT installed")
            all_ok = False
    
    return all_ok

def detect_gpu_diagnostic():
    """Run GPU detection diagnostics"""
    print_section("GPU Detection Diagnostic")
    
    try:
        # Import the model engine to test GPU detection
        sys.path.insert(0, str(Path(__file__).parent))
        from sur5_lite_pyside.services.model_engine import detect_gpu_capability
        
        gpu_info = detect_gpu_capability()
        
        print_info("Has GPU", gpu_info.get("has_gpu", False))
        print_info("GPU Type", gpu_info.get("gpu_type", "none"))
        print_info("GPU Layers", gpu_info.get("gpu_layers", 0))
        print_info("VRAM (GB)", gpu_info.get("gpu_vram_gb", 0))
        
        # Interpret the results
        layers = gpu_info.get("gpu_layers", 0)
        vram_gb = gpu_info.get("gpu_vram_gb", 0)
        
        print("\n" + Colors.BOLD + "Layer Offload Strategy:" + Colors.ENDC)
        if layers == 0:
            print_warning(f"CPU-only mode (0 layers offloaded)")
            print("  Reason: No GPU detected or VRAM < 1GB")
        elif layers == 6:
            print_success(f"HYBRID mode (6 layers offloaded to GPU)")
            print(f"  {Colors.OKGREEN}This is the NEW Intel Mac fix!{Colors.ENDC}")
            print(f"  VRAM: {vram_gb} GB (1-2 GB range)")
            print("  Expected: 6/29 layers on GPU, 22/29 on CPU")
        elif layers == -1:
            print_success(f"FULL offload mode (all layers to GPU)")
            print(f"  VRAM: {vram_gb} GB (≥2 GB)")
            print("  Expected: Auto-offload all available layers")
        else:
            print_info("Custom layer count", layers)
        
        return gpu_info
        
    except Exception as e:
        print_error(f"GPU detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_log_file():
    """Create a timestamped log file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"sur5_diagnostic_{timestamp}.log"
    return log_file

def main():
    """Main diagnostic launcher"""
    print_section("Sur5 Diagnostic Launcher")
    print_info("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print_info("Working Directory", os.getcwd())
    print_info("Script Location", str(Path(__file__).parent))
    
    # System information
    print_section("System Information")
    sys_info = get_system_info()
    for key, value in sys_info.items():
        print_info(key.replace("_", " ").title(), value)
    
    # Check dependencies
    if not check_dependencies():
        print_error("\nMissing dependencies. Install with:")
        print("  pip install PySide6 llama-cpp-python llama-cpp-agent")
        return 1
    
    # GPU diagnostics
    gpu_info = detect_gpu_diagnostic()
    
    # Create log file
    log_file = create_log_file()
    print_section("Logging Configuration")
    print_info("Log File", str(log_file))
    print_info("Console Output", "Enabled (real-time)")
    
    # Set environment variables for verbose llama.cpp output
    env = os.environ.copy()
    env["LLAMA_CPP_VERBOSE"] = "1"
    env["GGML_METAL_DEBUG"] = "1"  # Metal-specific debug output
    
    print_section("Launching Sur5 with Verbose Logging")
    print(f"{Colors.WARNING}Note: llama.cpp will print detailed layer offloading information{Colors.ENDC}")
    print(f"{Colors.WARNING}Look for: 'llm_load_tensors: offloaded X/Y layers to GPU'{Colors.ENDC}")
    print(f"\n{Colors.OKBLUE}Press Ctrl+C to stop Sur5 and view summary{Colors.ENDC}\n")
    
    # Brief pause before launch
    time.sleep(2)
    
    # Launch Sur5 with output capture
    launch_script = Path(__file__).parent / "launch_sur5.py"
    
    try:
        # Use Popen to capture output in real-time
        with open(log_file, 'w', encoding='utf-8') as log:
            # Write header to log
            log.write("="*70 + "\n")
            log.write("Sur5 Diagnostic Log\n")
            log.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write("="*70 + "\n\n")
            
            # Write system info to log
            log.write("System Information:\n")
            for key, value in sys_info.items():
                log.write(f"  {key}: {value}\n")
            log.write("\n")
            
            # Write GPU info to log
            if gpu_info:
                log.write("GPU Detection Results:\n")
                for key, value in gpu_info.items():
                    log.write(f"  {key}: {value}\n")
                log.write("\n")
            
            log.write("="*70 + "\n")
            log.write("Application Output:\n")
            log.write("="*70 + "\n\n")
            log.flush()
            
            # Launch process
            process = subprocess.Popen(
                [sys.executable, str(launch_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1
            )
            
            # Read output line by line
            for line in process.stdout:
                # Print to console
                print(line, end='')
                # Write to log file
                log.write(line)
                log.flush()
            
            # Wait for process to complete
            return_code = process.wait()
            
            print_section("Sur5 Terminated")
            print_info("Exit Code", return_code)
            print_info("Log File", str(log_file))
            
            # Write footer to log
            log.write("\n" + "="*70 + "\n")
            log.write(f"Process terminated with exit code: {return_code}\n")
            log.write(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write("="*70 + "\n")
        
        print_success(f"\nDiagnostic log saved to: {log_file}")
        
        # Summary
        print_section("Diagnostic Summary")
        if gpu_info:
            layers = gpu_info.get("gpu_layers", 0)
            if layers == 6:
                print_success("Hybrid GPU offload mode activated (6 layers)")
                print(f"\n{Colors.BOLD}What to look for in the logs:{Colors.ENDC}")
                print("  1. 'llm_load_tensors: offloaded 6/29 layers to GPU'")
                print("  2. Model loading without errors")
                print("  3. Token generation produces coherent text (not garbage)")
                print(f"\n{Colors.BOLD}If tokens are still garbage:{Colors.ENDC}")
                print("  • Check log file for Metal errors")
                print("  • Try reducing to 3 layers (edit model_engine.py line 177)")
                print("  • Or fall back to CPU-only (0 layers)")
            elif layers == 0:
                print_info("Running in CPU-only mode", "No GPU offloading")
            elif layers == -1:
                print_info("Running in full GPU offload mode", "All layers on GPU")
        
        return return_code
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
        print_info("Log File", str(log_file))
        return 130
    except Exception as e:
        print_error(f"Launch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

