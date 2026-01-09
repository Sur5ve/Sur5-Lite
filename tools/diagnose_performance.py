#!/usr/bin/env python3
"""
Sur5 Performance Diagnostic Tool
================================
This script launches Sur5, captures ALL terminal output in real-time,
and generates a comprehensive diagnostic report after you close the app.

Usage:
    python diagnose_performance.py

Workflow:
    1. Script launches Sur5 and captures all terminal output
    2. You interact with the app - send a test prompt like "Hello"
    3. Wait for the response to complete
    4. Close the app (click X or Ctrl+C in terminal)
    5. Report is automatically generated with all captured data

Output:
    PERFORMANCE_DIAGNOSIS_[hostname].md
"""

import os
import sys
import platform
import socket
import re
import json
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty

# Global buffer for captured output
CAPTURED_OUTPUT = []
OUTPUT_LOCK = threading.Lock()


# ============================================================================
# REAL-TIME OUTPUT CAPTURE
# ============================================================================

def capture_output_stream(stream, prefix=""):
    """Capture output from a stream in real-time."""
    global CAPTURED_OUTPUT
    try:
        for line in iter(stream.readline, ''):
            if line:
                line = line.rstrip()
                with OUTPUT_LOCK:
                    CAPTURED_OUTPUT.append(line)
                # Print to console in real-time
                print(f"{prefix}{line}")
    except:
        pass


def launch_sur5_with_capture():
    """Launch Sur5 and capture all terminal output."""
    global CAPTURED_OUTPUT
    CAPTURED_OUTPUT = []
    
    script_dir = Path(__file__).parent
    launch_script = script_dir / "launch_sur5.py"
    
    if not launch_script.exists():
        print(f"[ERROR] launch_sur5.py not found at: {launch_script}")
        return False
    
    print("=" * 70)
    print("  Sur5 Performance Diagnostic Tool - REAL-TIME CAPTURE MODE")
    print("=" * 70)
    print()
    print("  INSTRUCTIONS:")
    print("  1. Sur5 will launch in a moment")
    print("  2. Send a test prompt like 'Hello, how are you?'")
    print("  3. Wait for the FULL response to complete")
    print("  4. Close the app (click X) or press Ctrl+C here")
    print("  5. A diagnostic report will be generated automatically")
    print()
    print("=" * 70)
    print("  [LAUNCHING SUR5 - All output will be captured below]")
    print("=" * 70)
    print()
    
    # Find Python executable
    python_exe = sys.executable
    
    # Launch Sur5 as subprocess with output capture
    try:
        process = subprocess.Popen(
            [python_exe, str(launch_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(script_dir),
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        
        # Capture output in real-time
        stdout_thread = threading.Thread(
            target=capture_output_stream,
            args=(process.stdout, ""),
            daemon=True
        )
        stdout_thread.start()
        
        # Wait for process to complete
        process.wait()
        
        # Give threads time to finish capturing
        time.sleep(0.5)
        
        print()
        print("=" * 70)
        print("  [SUR5 CLOSED - Generating diagnostic report...]")
        print("=" * 70)
        print()
        
        return True
        
    except KeyboardInterrupt:
        print()
        print("[Interrupted by user - generating report with captured data...]")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch Sur5: {e}")
        return False


# ============================================================================
# SYSTEM INFORMATION
# ============================================================================

def get_system_info():
    """Collect comprehensive system information."""
    info = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable,
    }
    
    # CPU info
    try:
        import multiprocessing
        info["cpu_count"] = multiprocessing.cpu_count()
    except:
        info["cpu_count"] = "Unknown"
    
    # RAM info
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 2)
        info["ram_available_gb"] = round(mem.available / (1024**3), 2)
        info["ram_used_percent"] = mem.percent
    except ImportError:
        info["ram_total_gb"] = "psutil not installed"
        info["ram_available_gb"] = "Unknown"
        info["ram_used_percent"] = "Unknown"
    
    # GPU info
    info["gpu_info"] = detect_gpu()
    
    return info


def detect_gpu():
    """Detect GPU availability."""
    gpu_info = {
        "has_gpu": False,
        "gpu_type": "none",
        "gpu_name": "Unknown",
        "detection_method": None,
    }
    
    # Try CUDA (NVIDIA)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info["has_gpu"] = True
            gpu_info["gpu_type"] = "cuda"
            gpu_info["gpu_name"] = torch.cuda.get_device_name(0)
            gpu_info["detection_method"] = "torch.cuda"
            return gpu_info
    except ImportError:
        pass
    
    # Try Metal (macOS)
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5
            )
            if "Metal" in result.stdout:
                gpu_info["has_gpu"] = True
                gpu_info["gpu_type"] = "metal"
                gpu_info["detection_method"] = "system_profiler"
                # Extract GPU name
                for line in result.stdout.split('\n'):
                    if "Chipset Model:" in line:
                        gpu_info["gpu_name"] = line.split(":")[-1].strip()
                        break
                return gpu_info
        except:
            pass
    
    # Try llama-cpp-python GPU check
    try:
        from llama_cpp import llama_supports_gpu_offload
        if llama_supports_gpu_offload():
            gpu_info["has_gpu"] = True
            gpu_info["gpu_type"] = "llama_cpp_detected"
            gpu_info["detection_method"] = "llama_supports_gpu_offload"
            return gpu_info
    except:
        pass
    
    gpu_info["detection_method"] = "none_found"
    return gpu_info


# ============================================================================
# PACKAGE VERSIONS
# ============================================================================

def get_package_versions():
    """Get versions of key packages."""
    packages = {}
    
    package_list = [
        "llama_cpp",
        "llama_cpp_agent", 
        "PySide6",
        "torch",
        "numpy",
        "faiss",
        "sentence_transformers",
        "psutil",
    ]
    
    for pkg in package_list:
        try:
            mod = __import__(pkg.replace("-", "_"))
            version = getattr(mod, "__version__", "installed (version unknown)")
            packages[pkg] = version
        except ImportError:
            packages[pkg] = "NOT INSTALLED"
    
    return packages


# ============================================================================
# CODE ANALYSIS
# ============================================================================

def analyze_code_settings():
    """Analyze the n_batch and other settings in the code."""
    settings = {
        "n_batch_in_code": [],
        "model_engine_path": None,
        "intel_mac_check_exists": False,
    }
    
    # Find model_engine.py
    script_dir = Path(__file__).parent
    model_engine_paths = [
        script_dir / "sur5_lite_pyside" / "services" / "model_engine.py",
        script_dir / "services" / "model_engine.py",
    ]
    
    for path in model_engine_paths:
        if path.exists():
            settings["model_engine_path"] = str(path)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all n_batch settings
            n_batch_pattern = r'n_batch\s*=\s*(\d+|[a-zA-Z_]+\(\))'
            matches = re.findall(n_batch_pattern, content)
            settings["n_batch_in_code"] = matches
            
            # Check if Intel Mac detection exists
            if "Darwin" in content and "x86_64" in content:
                settings["intel_mac_check_exists"] = True
            
            # Check for _get_optimal_batch_size function
            if "_get_optimal_batch_size" in content:
                settings["has_adaptive_batch"] = True
            else:
                settings["has_adaptive_batch"] = False
                
            break
    
    return settings


# ============================================================================
# PARSE CAPTURED OUTPUT
# ============================================================================

def parse_captured_output():
    """Parse the captured terminal output for performance data."""
    global CAPTURED_OUTPUT
    
    perf_data = {
        "llama_context_info": {},
        "performance_stats": {},
        "model_loaded": None,
        "raw_llama_output": [],
        "captured_lines": len(CAPTURED_OUTPUT),
    }
    
    all_content = "\n".join(CAPTURED_OUTPUT)
    
    # Parse llama_context info
    context_patterns = {
        "n_ctx": r"n_ctx\s*=\s*(\d+)",
        "n_batch": r"n_batch\s*=\s*(\d+)",
        "n_ubatch": r"n_ubatch\s*=\s*(\d+)",
        "flash_attn": r"flash_attn\s*=\s*(\d+)",
        "n_threads": r"n_threads\s*=\s*(\d+)",
        "n_gpu_layers": r"n_gpu_layers\s*=\s*(\d+)",
    }
    
    for key, pattern in context_patterns.items():
        matches = re.findall(pattern, all_content)
        if matches:
            # Get the last match (most recent)
            perf_data["llama_context_info"][key] = matches[-1]
    
    # Parse performance stats (tokens per second, timing, etc.)
    perf_patterns = {
        "load_time_ms": r"load time\s*=\s*([\d.]+)\s*ms",
        "prompt_eval_time_ms": r"prompt eval time\s*=\s*([\d.]+)\s*ms",
        "prompt_tokens": r"prompt eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*tokens",
        "prompt_tokens_per_sec": r"prompt eval.*?([\d.]+)\s*tokens per second",
        "eval_time_ms": r"eval time\s*=\s*([\d.]+)\s*ms",
        "eval_tokens": r"eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*(?:runs|tokens)",
        "eval_tokens_per_sec": r"eval time.*?([\d.]+)\s*tokens per second",
        "total_time_ms": r"total time\s*=\s*([\d.]+)\s*ms",
        "total_tokens": r"total time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*tokens",
    }
    
    for key, pattern in perf_patterns.items():
        matches = re.findall(pattern, all_content)
        if matches:
            perf_data["performance_stats"][key] = matches[-1]
    
    # Find model name
    model_patterns = [
        r"Model loaded.*?:\s*(\S+\.gguf)",
        r"loading model from[:\s]+(\S+\.gguf)",
        r"llama_model_load:\s*(\S+\.gguf)",
        r"(\w+[-\w]*\.gguf)",
    ]
    
    for pattern in model_patterns:
        match = re.search(pattern, all_content, re.IGNORECASE)
        if match:
            perf_data["model_loaded"] = match.group(1)
            break
    
    # Extract relevant llama.cpp output lines
    llama_lines = []
    keywords = [
        'llama_', 'load_tensors', 'print_info', 'graph_reserve',
        'n_ctx', 'n_batch', 'n_ubatch', 'n_threads', 'n_gpu',
        'eval time', 'prompt eval', 'total time', 'tokens per second',
        'Memory tier', 'Model loaded', 'flash_attn', 'VRAM', 'RAM'
    ]
    
    for line in CAPTURED_OUTPUT:
        if any(kw.lower() in line.lower() for kw in keywords):
            llama_lines.append(line.strip())
    
    perf_data["raw_llama_output"] = llama_lines
    
    return perf_data


# ============================================================================
# GENERATE REPORT
# ============================================================================

def generate_report():
    """Generate comprehensive markdown report."""
    
    print("[1/4] Collecting system information...")
    sys_info = get_system_info()
    
    print("[2/4] Checking package versions...")
    packages = get_package_versions()
    
    print("[3/4] Analyzing code settings...")
    code_settings = analyze_code_settings()
    
    print("[4/4] Parsing captured output...")
    perf_data = parse_captured_output()
    
    # Build report
    hostname = sys_info.get("hostname", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# Sur5 Performance Diagnosis Report

**Generated:** {timestamp}  
**Hostname:** {hostname}  
**Purpose:** Compare performance between machines to diagnose n_batch issue

---

## 1. System Information

| Property | Value |
|----------|-------|
| **Hostname** | {sys_info.get('hostname')} |
| **OS** | {sys_info.get('os')} {sys_info.get('os_release')} |
| **OS Version** | {sys_info.get('os_version')} |
| **Architecture** | {sys_info.get('machine')} |
| **Processor** | {sys_info.get('processor')} |
| **CPU Cores** | {sys_info.get('cpu_count')} |
| **RAM Total** | {sys_info.get('ram_total_gb')} GB |
| **RAM Available** | {sys_info.get('ram_available_gb')} GB |
| **RAM Used** | {sys_info.get('ram_used_percent')}% |

### GPU Detection

| Property | Value |
|----------|-------|
| **Has GPU** | {sys_info['gpu_info'].get('has_gpu')} |
| **GPU Type** | {sys_info['gpu_info'].get('gpu_type')} |
| **GPU Name** | {sys_info['gpu_info'].get('gpu_name')} |
| **Detection Method** | {sys_info['gpu_info'].get('detection_method')} |

---

## 2. Python & Package Versions

| Package | Version |
|---------|---------|
| **Python** | {sys_info.get('python_version', '').split()[0]} |
"""
    
    for pkg, ver in packages.items():
        report += f"| {pkg} | {ver} |\n"
    
    report += f"""
---

## 3. Code Analysis (n_batch settings)

| Property | Value |
|----------|-------|
| **model_engine.py location** | {code_settings.get('model_engine_path', 'NOT FOUND')} |
| **n_batch values in code** | {', '.join(code_settings.get('n_batch_in_code', ['None found']))} |
| **Intel Mac check exists** | {code_settings.get('intel_mac_check_exists')} |
| **Has adaptive batch function** | {code_settings.get('has_adaptive_batch', False)} |

---

## 4. Runtime Performance (CAPTURED FROM TERMINAL)

**Lines captured:** {perf_data.get('captured_lines', 0)}

### llama_context Settings (What was ACTUALLY used at runtime)

| Setting | Value |
|---------|-------|
"""
    
    ctx_info = perf_data.get("llama_context_info", {})
    for key in ["n_ctx", "n_batch", "n_ubatch", "n_threads", "n_gpu_layers", "flash_attn"]:
        val = ctx_info.get(key, "Not captured")
        report += f"| **{key}** | {val} |\n"
    
    report += f"""
### Performance Metrics

| Metric | Value |
|--------|-------|
| **Model Loaded** | {perf_data.get('model_loaded', 'Not captured')} |
"""
    
    perf_stats = perf_data.get("performance_stats", {})
    metric_labels = {
        "load_time_ms": "Load Time",
        "prompt_eval_time_ms": "Prompt Eval Time",
        "prompt_tokens": "Prompt Tokens",
        "prompt_tokens_per_sec": "Prompt Speed (tok/s)",
        "eval_time_ms": "Generation Time",
        "eval_tokens": "Generated Tokens",
        "eval_tokens_per_sec": "Generation Speed (tok/s)",
        "total_time_ms": "Total Time",
        "total_tokens": "Total Tokens",
    }
    
    for key, label in metric_labels.items():
        val = perf_stats.get(key, "Not captured")
        if "time_ms" in key and val != "Not captured":
            try:
                val = f"{float(val)/1000:.2f} sec ({val} ms)"
            except:
                pass
        report += f"| **{label}** | {val} |\n"
    
    report += f"""
---

## 5. Key Findings Summary

"""
    
    # Analyze and summarize
    n_ubatch = ctx_info.get("n_ubatch")
    n_batch = ctx_info.get("n_batch")
    tok_per_sec = perf_stats.get("eval_tokens_per_sec")
    
    # n_batch analysis
    if n_ubatch == "2" or n_batch == "2":
        report += ">> WARNING: n_batch/n_ubatch = 2 - This is the Intel Mac workaround!\n"
        report += ">> This causes VERY SLOW performance on Windows and other platforms.\n\n"
    elif n_ubatch or n_batch:
        val = n_ubatch or n_batch
        report += f">> OK: n_batch = {val} - Normal batch size\n\n"
    else:
        report += ">> UNKNOWN: n_batch values not captured - did you send a prompt?\n\n"
    
    # Speed analysis
    if tok_per_sec:
        try:
            speed = float(tok_per_sec)
            if speed < 5:
                report += f">> SLOW: Generation speed: {speed:.1f} tok/s - VERY SLOW (n_batch issue likely)\n\n"
            elif speed < 15:
                report += f">> MODERATE: Generation speed: {speed:.1f} tok/s - Could be faster\n\n"
            else:
                report += f">> FAST: Generation speed: {speed:.1f} tok/s - GOOD performance!\n\n"
        except:
            pass
    else:
        report += ">> Speed not captured - make sure to send a prompt and wait for full response\n\n"
    
    report += f"""
---

## 6. Raw Terminal Output (Relevant Lines)

The following lines were captured from the terminal during Sur5 execution:

```
"""
    
    raw_lines = perf_data.get("raw_llama_output", [])
    if raw_lines:
        for line in raw_lines[-100:]:  # Last 100 relevant lines
            report += line + "\n"
    else:
        report += "(No relevant llama.cpp output captured)\n"
        report += "(Make sure to send a prompt and wait for the response)\n"
    
    report += """```

---

## 7. Full Captured Output (Debug)

<details>
<summary>Click to expand full terminal output</summary>

```
"""
    
    for line in CAPTURED_OUTPUT[-200:]:  # Last 200 lines total
        report += line + "\n"
    
    report += """```

</details>

---

_End of diagnostic report. Share this file with Sur5 Lite for analysis._
"""
    
    # Save report
    output_file = Path(__file__).parent / f"PERFORMANCE_DIAGNOSIS_{hostname}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print()
    print("=" * 70)
    print(f"  [OK] Report saved to:")
    print(f"  {output_file}")
    print("=" * 70)
    print()
    print("  Share this .md file with Sur5 Lite for analysis!")
    print()
    
    return output_file


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    print()
    
    # Check if --no-launch flag is passed (for debugging)
    if "--no-launch" in sys.argv:
        print("[DEBUG MODE] Skipping Sur5 launch, generating report from existing logs...")
        generate_report()
        return
    
    # Launch Sur5 with real-time capture
    success = launch_sur5_with_capture()
    
    if success or len(CAPTURED_OUTPUT) > 0:
        generate_report()
    else:
        print("[ERROR] No output captured. Please run Sur5 manually and use --no-launch flag.")


if __name__ == "__main__":
    main()
