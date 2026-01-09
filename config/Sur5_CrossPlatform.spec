# -*- mode: python ; coding: utf-8 -*-
"""
Sur5 Cross-Platform PyInstaller Spec File
Builds native executables for Windows and macOS from the same codebase.

Usage:
    Windows (single exe):   pyinstaller Sur5_CrossPlatform.spec
    Windows (portable):     set SUR5_ONEDIR=1 && pyinstaller Sur5_CrossPlatform.spec
    macOS:                  pyinstaller Sur5_CrossPlatform.spec

Environment Variables:
    SUR5_CONSOLE_MODE=1     Enable console window for debugging
    SUR5_ONEDIR=1           Build portable folder distribution (Windows)
                            Recommended for LGPL compliance - allows easy
                            replacement of PySide6/Qt libraries.

================================================================================
TRADEMARK NOTICE
================================================================================
The "Sur5", "Sur5ve", and "Sur5 Lite" names, as well as all associated logos,
are trademarks of Sur5ve LLC and are NOT covered by the MIT License.

This build configuration includes Sur5ve trademarks. If you fork this project,
you MUST modify this spec file to use your own branding before building.
See TRADEMARK.md for complete policy.
================================================================================

LGPL COMPLIANCE NOTE
================================================================================
Sur5 Lite uses PySide6 (LGPL v3). The --onedir build mode creates a portable
distribution where PySide6 libraries are visible and replaceable, making it
easier for users to exercise their LGPL rights. See docs/LGPL_COMPLIANCE.md.
================================================================================
"""

import os
import platform
import sys
from pathlib import Path

# Detect platform
IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

# Check for console mode override (useful for macOS debugging)
# Read from environment variable since --console can't be passed with .spec files
CONSOLE_MODE = os.environ.get('SUR5_CONSOLE_MODE', '0') == '1'

# Check for onedir mode (Windows only) - creates portable distribution for LGPL compliance
# When enabled, builds a folder with separate DLLs instead of single .exe
ONEDIR_MODE = os.environ.get('SUR5_ONEDIR', '0') == '1'

block_cipher = None

# Application metadata
APP_NAME = 'Sur5'
APP_VERSION = '2.0.0'
BUNDLE_IDENTIFIER = 'com.sur5ve.sur5'

# Source files
ENTRY_POINT = 'launch_sur5.py'

# Data files to include (cross-platform paths)
datas = [
    ('sur5_lite_pyside', 'sur5_lite_pyside'),
    ('models/all-MiniLM-L6-v2', 'models/all-MiniLM-L6-v2'),  # Embedding model for RAG (~90MB)
    ('models/docling/granite-docling-258M', 'models/docling/granite-docling-258M'),  # Docling model (~509MB)
    ('README.md', '.'),
    ('TRADEMARK.md', '.'),  # Trademark notice - MUST be included in all distributions
    ('LICENSE', '.'),  # License file
]

# Hidden imports (dependencies that PyInstaller might miss)
hiddenimports = [
    # Core ML/AI
    'sentence_transformers',
    'faiss',
    'llama_cpp',
    'llama_cpp_agent',
    
    # Document parsing
    'pypdf',
    'docx',
    'python_docx',
    'beautifulsoup4',
    'bs4',
    'markdown',
    
    # Document AI (Docling)
    'docling',
    'docling.document_converter',
    'PIL',
    'Pillow',
    
    # Text processing
    'nltk',
    'rank_bm25',
    
    # System monitoring
    'psutil',
    'GPUtil',
    
    # PySide6 extras
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    
    # ONNX runtime
    'onnxruntime',
]

# Analysis step
a = Analysis(
    [ENTRY_POINT],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific executable configuration
if IS_MACOS:
    print(f"\n{'='*60}")
    print(f"Building for macOS (Apple Silicon / Intel)")
    print(f"Console mode: {'ENABLED (debug)' if CONSOLE_MODE else 'DISABLED (release)'}")
    print(f"{'='*60}\n")
    
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=CONSOLE_MODE,  # Enable console for debugging, disable for release
        disable_windowed_traceback=False,
        argv_emulation=False,  # Important for macOS
        target_arch=None,  # Auto-detect (supports both Intel and Apple Silicon)
        codesign_identity=None,  # Set this when you have a signing certificate
        entitlements_file=None,  # Set this for notarization
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=APP_NAME,
    )
    
    # Create macOS .app bundle
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=None,  # Add icon path here when available
        bundle_identifier=BUNDLE_IDENTIFIER,
        version=APP_VERSION,
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': 'Sur5 - AI Assistant',
            'CFBundlePackageType': 'APPL',
            'NSRequiresAquaSystemAppearance': 'False',  # Support Dark Mode
            'LSMinimumSystemVersion': '10.15.0',  # macOS Catalina or later
            # Add these when ready for distribution:
            # 'NSAppleEventsUsageDescription': 'Sur5 needs to process documents.',
            # 'NSCameraUsageDescription': 'Sur5 needs camera access for OCR.',
        },
    )
    
elif IS_WINDOWS:
    build_mode = "PORTABLE (onedir)" if ONEDIR_MODE else "SINGLE EXE (onefile)"
    print(f"\n{'='*60}")
    print(f"Building for Windows (10/11)")
    print(f"Build mode: {build_mode}")
    print(f"Console mode: {'ENABLED (debug)' if CONSOLE_MODE else 'DISABLED (release)'}")
    if ONEDIR_MODE:
        print(f"LGPL Note: Portable mode allows easy PySide6 replacement")
    print(f"{'='*60}\n")
    
    if ONEDIR_MODE:
        # PORTABLE BUILD (--onedir equivalent)
        # Creates a folder with separate DLLs for better LGPL compliance
        # Users can easily replace PySide6/Qt libraries
        exe = EXE(
            pyz,
            a.scripts,
            [],
            exclude_binaries=True,  # Separate binaries for onedir
            name=APP_NAME,
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            console=CONSOLE_MODE,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,
            entitlements_file=None,
            icon=None,
            version_file=None,
            uac_admin=False,
            uac_uiaccess=False,
        )
        
        coll = COLLECT(
            exe,
            a.binaries,
            a.zipfiles,
            a.datas,
            strip=False,
            upx=True,
            upx_exclude=[],
            name=f'{APP_NAME}_Portable',  # Folder name
        )
    else:
        # SINGLE EXE BUILD (--onefile equivalent)
        # More convenient but DLLs are extracted to temp at runtime
        exe = EXE(
            pyz,
            a.scripts,
            a.binaries,
            a.zipfiles,
            a.datas,
            [],
            name=APP_NAME,
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            upx_exclude=[],
            runtime_tmpdir=None,
            console=CONSOLE_MODE,  # Enable console for debugging, disable for release
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,  # Set this when you have a signing certificate
            entitlements_file=None,
            icon=None,  # Add icon path here when available (.ico file)
            version_file=None,  # Add version info file when available
            uac_admin=False,  # Don't require admin rights
            uac_uiaccess=False,
        )
    
else:
    print(f"\nWarning: Building for {platform.system()} - not officially supported")
    print("Using generic Linux/Unix configuration\n")
    
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=CONSOLE_MODE,
        disable_windowed_traceback=False,
    )

