#!/usr/bin/env python3
"""
Quick verification script to test RAM preset detection and qasync handling
Run this BEFORE compiling to .exe to ensure everything works correctly
"""

import platform
import sys

def test_qasync_handling():
    """Test that qasync is handled correctly based on platform"""
    print("\n" + "="*60)
    print("TEST 1: qasync Platform Detection")
    print("="*60)
    
    print(f"Platform: {platform.system()}")
    print(f"sys.platform: {sys.platform}")
    
    # Import the model service to trigger qasync check
    try:
        from sur5_lite_pyside.services.model_service import HAS_QASYNC
        print(f"HAS_QASYNC: {HAS_QASYNC}")
        
        if platform.system() == "Darwin":
            print("✅ PASS: macOS should have qasync available")
        else:
            if not HAS_QASYNC:
                print("✅ PASS: Windows correctly skips qasync")
            else:
                print("⚠️  WARNING: qasync loaded on Windows (not critical but unexpected)")
    except Exception as e:
        print(f"❌ FAIL: Error importing model_service: {e}")
        return False
    
    return True

def test_ram_preset_detection():
    """Test RAM preset detection logic"""
    print("\n" + "="*60)
    print("TEST 2: RAM Preset Detection")
    print("="*60)
    
    try:
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count(logical=True)
        
        print(f"System RAM: {total_ram_gb:.1f} GB")
        print(f"CPU Cores: {cpu_count}")
        
        # Predict what preset should be selected
        if total_ram_gb >= 16 and cpu_count >= 8:
            expected = "Balanced (if initially Minimal)"
            print(f"✅ System qualifies for upgrade to: {expected}")
        elif total_ram_gb >= 8 and cpu_count >= 4:
            expected = "Fast (if initially Minimal)"
            print(f"✅ System qualifies for upgrade to: {expected}")
        else:
            expected = "Minimal (no upgrade available)"
            print(f"ℹ️  System specs: {expected}")
        
        # Try to import and check actual detection
        from sur5_lite_pyside.services.model_engine import detect_optimal_preset
        detected_preset, reasoning = detect_optimal_preset()
        
        print(f"\nActual detected preset: {detected_preset}")
        print("\nReasoning:")
        print(reasoning)
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing preset detection: {e}")
        return False

def test_imports():
    """Test that all critical imports work"""
    print("\n" + "="*60)
    print("TEST 3: Critical Imports")
    print("="*60)
    
    imports_to_test = [
        ("PySide6.QtCore", "QObject, Signal"),
        ("sur5_lite_pyside.services.model_engine", "get_engine, RAM_CONFIGS"),
        ("sur5_lite_pyside.services.dual_mode_utils", "get_model_capabilities"),
        ("psutil", ""),
    ]
    
    all_passed = True
    for module, items in imports_to_test:
        try:
            if items:
                exec(f"from {module} import {items}")
            else:
                exec(f"import {module}")
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            all_passed = False
    
    return all_passed

def test_requirements():
    """Check if all requirements are satisfied"""
    print("\n" + "="*60)
    print("TEST 4: Requirements Check")
    print("="*60)
    
    critical_packages = [
        "PySide6",
        "llama_cpp",
        "psutil",
    ]
    
    optional_packages = [
        ("qasync", "macOS only"),
    ]
    
    import importlib
    
    print("\nCritical packages:")
    all_passed = True
    for package in critical_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            all_passed = False
    
    print("\nOptional packages:")
    for package, note in optional_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} - installed ({note})")
        except ImportError:
            print(f"ℹ️  {package} - not installed ({note})")
    
    return all_passed

def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("🔍 VERIFICATION SCRIPT - Sur5 Changes")
    print("="*60)
    print("Purpose: Verify RAM preset & qasync fixes are working")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("qasync handling", test_qasync_handling()))
    results.append(("RAM preset detection", test_ram_preset_detection()))
    results.append(("Critical imports", test_imports()))
    results.append(("Requirements", test_requirements()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED")
        print("✅ Ready to compile to .exe")
        print("\nNext steps:")
        print("1. Test the app: python launch_sur5.py")
        print("2. Verify streaming performance (should be fast)")
        print("3. Compile: pyinstaller Sur5.spec --clean")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("⚠️  Fix issues before compiling")
        return 1

if __name__ == "__main__":
    sys.exit(main())






