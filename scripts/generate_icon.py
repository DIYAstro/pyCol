#!/usr/bin/env python3
"""
Convert PNG icon to ICO format for Inno Setup and PyInstaller.
Creates a multi-resolution ICO with all standard Windows icon sizes.
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    exit(1)


def main():
    project_root = Path(__file__).parent.parent
    png_path = project_root / 'src' / 'icon.png'
    ico_path = project_root / 'build' / 'icon.ico'
    
    if not png_path.exists():
        print(f"ERROR: {png_path} not found!")
        exit(1)
    
    # Create build directory if needed
    ico_path.parent.mkdir(exist_ok=True)
    
    # Open PNG 
    img = Image.open(png_path)
    
    # Ensure RGBA mode for transparency
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Windows ICO standard sizes (must include 256x256 for best quality on modern Windows)
    sizes = [256, 128, 64, 48, 32, 16]
    
    # Save as ICO with multiple sizes embedded
    # Pillow's save with sizes parameter handles this properly
    img.save(
        ico_path, 
        format='ICO',
        sizes=[(s, s) for s in sizes]
    )
    
    print(f"Generated: {ico_path} (sizes: {sizes})")


if __name__ == '__main__':
    main()
