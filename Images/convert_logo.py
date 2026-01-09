#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Sur5 Lite Logo to .ico format for Windows application icon
Generates multi-resolution .ico file for optimal display at all sizes
"""

from PIL import Image
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

def convert_logo_to_icon():
    """Convert the Sur5 Lite shield logo to multi-resolution Windows .ico file"""
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "sur5_logo.png")
    output_path = os.path.join(script_dir, "sur5_icon.ico")
    
    print("=" * 60)
    print("Sur5 Lite Logo to Icon Converter")
    print("=" * 60)
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        return False
    
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print()
    
    try:
        # Load the logo
        print("Loading logo image...")
        img = Image.open(input_path)
        print(f"  Original size: {img.size[0]}x{img.size[1]} pixels")
        print(f"  Mode: {img.mode}")
        
        # Convert to RGBA for transparency support
        if img.mode != 'RGBA':
            print("  Converting to RGBA mode...")
            img = img.convert('RGBA')
        
        # Ensure square aspect ratio (center crop if needed)
        width, height = img.size
        if width != height:
            print(f"  Cropping to square aspect ratio...")
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            img = img.crop((left, top, left + size, top + size))
            print(f"  Cropped size: {img.size[0]}x{img.size[1]} pixels")
        
        # Generate multi-resolution .ico file
        # Windows icon sizes: 16, 32, 48, 64, 128, 256
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        print()
        print("Generating multi-resolution .ico file...")
        for size in icon_sizes:
            print(f"  - {size[0]}x{size[1]} pixels")
        
        # Save as .ico with all resolutions
        img.save(output_path, format='ICO', sizes=icon_sizes)
        
        # Verify output file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print()
            print("=" * 60)
            print(f"✓ SUCCESS: Icon created successfully!")
            print("=" * 60)
            print(f"Output file: {output_path}")
            print(f"File size: {file_size:,} bytes")
            print(f"Resolutions: {', '.join([f'{s[0]}x{s[1]}' for s in icon_sizes])}")
            print()
            print("The icon is ready to use for:")
            print("  - Windows executable (.exe) icon")
            print("  - Application window title bar")
            print("  - Windows taskbar icon")
            print("  - Qt application icon")
            return True
        else:
            print()
            print("ERROR: Output file was not created")
            return False
            
    except Exception as e:
        print()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = convert_logo_to_icon()
    
    if not success:
        print()
        print("Conversion failed. Please check the error messages above.")
        exit(1)
    
    print()
    print("Next steps:")
    print("  1. Update sur5_lite_pyside/core/application.py to set window icon")
    print("  2. Update sur5_lite_pyside/widgets/splash_screen.py to display logo")
    print("  3. Update build scripts to embed icon in executable")
    print()

