#!/usr/bin/env python3
"""
Granite 350M Dense vs Hybrid Benchmark Script
Tests both Granite-4.0-350M and Granite-4.0-H-350M models
with various context sizes to find optimal settings for low-resource systems.

Key difference:
- Granite-4.0-350M: 28 attention layers (standard transformer)
- Granite-4.0-H-350M: 4 attention + 28 Mamba2 layers (MUCH faster inference!)

The H (Hybrid) model uses Mamba2 which has O(n) complexity vs O(n²) for attention,
making it theoretically faster especially at longer context lengths.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Try to import llama-cpp
try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False
    print("ERROR: llama-cpp-python not installed!")
    print("Run: pip install llama-cpp-python")
    sys.exit(1)


# Default model paths - adjust these to your system
DEFAULT_MODELS_DIR = Path(__file__).parent.parent / "models"
GEMMA_MODEL = "gemma-3-270m-it-Q4_K_M.gguf"
GRANITE_DENSE_MODEL = "granite-4.0-350m-Q4_K_M.gguf"
GRANITE_HYBRID_MODEL = "granite-4.0-h-350m-Q4_K_M.gguf"


def get_system_info() -> Dict[str, Any]:
    """Get system information for the benchmark."""
    import platform
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count(logical=True)
    except ImportError:
        ram_gb = 0
        cpu_count = os.cpu_count() or 1
    
    return {
        "platform": platform.system(),
        "processor": platform.processor(),
        "cpu_count": cpu_count,
        "ram_gb": round(ram_gb, 2),
        "python_version": platform.python_version(),
    }


def benchmark_model(
    model_path: str,
    n_ctx: int = 2048,
    n_batch: int = 512,
    n_threads: int = None,
    prompt: str = "What is the capital of France? Answer in one sentence.",
    max_tokens: int = 50,
    warmup_runs: int = 1,
    test_runs: int = 3,
) -> Dict[str, Any]:
    """
    Benchmark a single model configuration.
    
    Returns:
        Dict with timing metrics
    """
    if not os.path.exists(model_path):
        return {"error": f"Model not found: {model_path}"}
    
    model_name = os.path.basename(model_path)
    print(f"\n{'='*60}")
    print(f"Benchmarking: {model_name}")
    print(f"  n_ctx={n_ctx}, n_batch={n_batch}, n_threads={n_threads}")
    print(f"{'='*60}")
    
    # Determine thread count
    if n_threads is None:
        n_threads = min(os.cpu_count() or 4, 8)  # Cap at 8 for efficiency
    
    results = {
        "model": model_name,
        "n_ctx": n_ctx,
        "n_batch": n_batch,
        "n_threads": n_threads,
        "max_tokens": max_tokens,
        "load_times": [],
        "ttft_times": [],  # Time to first token
        "generation_times": [],
        "tokens_generated": [],
        "tokens_per_sec": [],
    }
    
    total_runs = warmup_runs + test_runs
    
    for run in range(total_runs):
        is_warmup = run < warmup_runs
        run_type = "WARMUP" if is_warmup else f"RUN {run - warmup_runs + 1}"
        
        try:
            # Load model
            load_start = time.perf_counter()
            model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_batch=n_batch,
                n_threads=n_threads,
                n_threads_batch=n_threads,
                n_gpu_layers=0,  # CPU-only for fair comparison
                verbose=False,
            )
            load_time = time.perf_counter() - load_start
            
            # Time to first token (prompt processing)
            ttft_start = time.perf_counter()
            
            # Generate
            gen_start = time.perf_counter()
            output = model(
                prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                stop=[".", "!", "?"],  # Stop at sentence end for consistency
            )
            gen_end = time.perf_counter()
            
            # Extract metrics
            gen_time = gen_end - gen_start
            
            # Get actual tokens generated from response
            if "choices" in output and len(output["choices"]) > 0:
                response_text = output["choices"][0].get("text", "")
                # Rough token count (actual tokenization varies)
                tokens_gen = len(response_text.split()) + 1
            else:
                tokens_gen = 0
            
            # Calculate tokens per second
            tps = tokens_gen / gen_time if gen_time > 0 else 0
            
            # Log results
            print(f"  [{run_type}] Load: {load_time:.2f}s | Gen: {gen_time:.2f}s | "
                  f"{tokens_gen} tokens @ {tps:.1f} tok/s")
            
            # Only record test runs
            if not is_warmup:
                results["load_times"].append(load_time)
                results["generation_times"].append(gen_time)
                results["tokens_generated"].append(tokens_gen)
                results["tokens_per_sec"].append(tps)
            
            # Clean up
            del model
            
        except Exception as e:
            print(f"  [{run_type}] ERROR: {e}")
            if not is_warmup:
                results["error"] = str(e)
            break
    
    # Calculate averages
    if results["tokens_per_sec"]:
        results["avg_load_time"] = sum(results["load_times"]) / len(results["load_times"])
        results["avg_gen_time"] = sum(results["generation_times"]) / len(results["generation_times"])
        results["avg_tps"] = sum(results["tokens_per_sec"]) / len(results["tokens_per_sec"])
        print(f"\n  AVERAGE: {results['avg_tps']:.1f} tok/s (gen: {results['avg_gen_time']:.2f}s)")
    
    return results


def run_comparison_benchmark(
    models_dir: str,
    context_sizes: List[int] = [512, 1024, 2048],
    batch_sizes: List[int] = [512],
    include_gemma: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run comprehensive benchmark comparing models.
    """
    models_dir = Path(models_dir)
    all_results = []
    
    # Build list of models to test
    models_to_test = []
    
    # Check for Granite Dense
    granite_dense_path = models_dir / GRANITE_DENSE_MODEL
    if granite_dense_path.exists():
        models_to_test.append(("Granite Dense 350M", str(granite_dense_path)))
    else:
        print(f"⚠️  Granite Dense not found: {granite_dense_path}")
    
    # Check for Granite Hybrid
    granite_hybrid_path = models_dir / GRANITE_HYBRID_MODEL
    if granite_hybrid_path.exists():
        models_to_test.append(("Granite Hybrid (H) 350M", str(granite_hybrid_path)))
    else:
        print(f"⚠️  Granite Hybrid not found: {granite_hybrid_path}")
    
    # Check for Gemma (baseline)
    if include_gemma:
        gemma_path = models_dir / GEMMA_MODEL
        if gemma_path.exists():
            models_to_test.append(("Gemma 270M (baseline)", str(gemma_path)))
        else:
            print(f"⚠️  Gemma not found: {gemma_path}")
    
    if not models_to_test:
        print("\n❌ No models found to benchmark!")
        print(f"   Please place models in: {models_dir}")
        return []
    
    print(f"\n🚀 Found {len(models_to_test)} model(s) to benchmark:")
    for name, path in models_to_test:
        print(f"   • {name}")
    
    # Test each model with each configuration
    test_prompt = "Explain what machine learning is in simple terms."
    
    for n_ctx in context_sizes:
        for n_batch in batch_sizes:
            print(f"\n{'#'*60}")
            print(f"# Testing with n_ctx={n_ctx}, n_batch={n_batch}")
            print(f"{'#'*60}")
            
            for model_name, model_path in models_to_test:
                result = benchmark_model(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_batch=n_batch,
                    prompt=test_prompt,
                    max_tokens=100,
                    warmup_runs=1,
                    test_runs=2,
                )
                result["model_name"] = model_name
                all_results.append(result)
    
    return all_results


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print a summary table of results."""
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    
    # Group by context size
    by_ctx = {}
    for r in results:
        if "error" in r:
            continue
        ctx = r.get("n_ctx", 0)
        if ctx not in by_ctx:
            by_ctx[ctx] = []
        by_ctx[ctx].append(r)
    
    for ctx in sorted(by_ctx.keys()):
        print(f"\n📊 Context Size: {ctx}")
        print("-" * 60)
        print(f"{'Model':<30} {'Avg tok/s':>12} {'Avg Gen Time':>14}")
        print("-" * 60)
        
        for r in sorted(by_ctx[ctx], key=lambda x: x.get("avg_tps", 0), reverse=True):
            model = r.get("model_name", r.get("model", "Unknown"))[:28]
            avg_tps = r.get("avg_tps", 0)
            avg_gen = r.get("avg_gen_time", 0)
            
            # Highlight the fastest
            marker = "🏆" if r == max(by_ctx[ctx], key=lambda x: x.get("avg_tps", 0)) else "  "
            print(f"{marker}{model:<28} {avg_tps:>10.1f} {avg_gen:>12.2f}s")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    # Find best Granite configuration
    granite_results = [r for r in results if "granite" in r.get("model", "").lower() and "error" not in r]
    gemma_results = [r for r in results if "gemma" in r.get("model", "").lower() and "error" not in r]
    
    if granite_results:
        best_granite = max(granite_results, key=lambda x: x.get("avg_tps", 0))
        print(f"\n✅ Best Granite config: n_ctx={best_granite['n_ctx']} @ {best_granite['avg_tps']:.1f} tok/s")
        
        # Check if Hybrid is faster
        hybrid_results = [r for r in granite_results if "-h-" in r.get("model", "").lower()]
        dense_results = [r for r in granite_results if "-h-" not in r.get("model", "").lower()]
        
        if hybrid_results and dense_results:
            best_hybrid = max(hybrid_results, key=lambda x: x.get("avg_tps", 0))
            best_dense = max(dense_results, key=lambda x: x.get("avg_tps", 0))
            
            if best_hybrid["avg_tps"] > best_dense["avg_tps"]:
                speedup = best_hybrid["avg_tps"] / best_dense["avg_tps"]
                print(f"   🚀 Hybrid (Mamba2) is {speedup:.1f}x FASTER than Dense!")
            else:
                speedup = best_dense["avg_tps"] / best_hybrid["avg_tps"]
                print(f"   ⚠️  Dense is {speedup:.1f}x faster than Hybrid on this system")
    
    if gemma_results and granite_results:
        best_gemma = max(gemma_results, key=lambda x: x.get("avg_tps", 0))
        best_granite = max(granite_results, key=lambda x: x.get("avg_tps", 0))
        
        if best_gemma["avg_tps"] > best_granite["avg_tps"]:
            ratio = best_gemma["avg_tps"] / best_granite["avg_tps"]
            print(f"\n⚡ Gemma 270M is {ratio:.1f}x faster than best Granite config")
            print("   Consider using Gemma for speed-critical applications.")
        else:
            ratio = best_granite["avg_tps"] / best_gemma["avg_tps"]
            print(f"\n🎉 Best Granite is {ratio:.1f}x faster than Gemma!")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Granite 350M Dense vs Hybrid models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark_granite.py                    # Run with defaults
  python benchmark_granite.py -d /path/to/models # Specify models directory
  python benchmark_granite.py --ctx 512 1024     # Test specific context sizes
  python benchmark_granite.py --no-gemma         # Skip Gemma baseline
        """
    )
    
    parser.add_argument(
        "-d", "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help=f"Directory containing model files (default: {DEFAULT_MODELS_DIR})"
    )
    parser.add_argument(
        "--ctx",
        type=int,
        nargs="+",
        default=[512, 1024, 2048],
        help="Context sizes to test (default: 512 1024 2048)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        nargs="+",
        default=[512],
        help="Batch sizes to test (default: 512)"
    )
    parser.add_argument(
        "--no-gemma",
        action="store_true",
        help="Skip Gemma baseline comparison"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Save results to JSON file"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("GRANITE 350M BENCHMARK: Dense vs Hybrid (Mamba2)")
    print("="*80)
    
    # Print system info
    sys_info = get_system_info()
    print(f"\n📍 System: {sys_info['platform']} | {sys_info['processor']}")
    print(f"   CPU: {sys_info['cpu_count']} cores | RAM: {sys_info['ram_gb']:.1f} GB")
    print(f"   Python: {sys_info['python_version']}")
    
    # Run benchmarks
    results = run_comparison_benchmark(
        models_dir=args.models_dir,
        context_sizes=args.ctx,
        batch_sizes=args.batch,
        include_gemma=not args.no_gemma,
    )
    
    if results:
        print_summary(results)
        
        # Save results if requested
        if args.output:
            output_data = {
                "system": sys_info,
                "results": results,
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")


if __name__ == "__main__":
    main()

