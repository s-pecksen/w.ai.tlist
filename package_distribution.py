#!/usr/bin/env python3
"""
W.AI.TLIST Distribution Packager
Creates distributable packages for all platforms.
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

def create_distribution_package():
    """Create a complete distribution package."""
    print("📦 Creating W.AI.TLIST distribution package...")
    
    # Create package directory
    package_name = f"waitlyst-installer-{datetime.now().strftime('%Y%m%d')}"
    package_dir = Path(package_name)
    
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    package_dir.mkdir()
    
    # Files to include in the package
    files_to_include = [
        'app.py',
        'launcher.py',
        'requirements.txt',
        'waitlyst_launcher.spec',
        'install.py',
        'universal_installer.py',
        'build_windows.bat',
        'build_linux.sh',
        'build_macos.sh',
        'BUILD_INSTRUCTIONS.md',
        'USER_GUIDE.md',
        'README_EXECUTABLE.md',
        'LICENSE'
    ]
    
    # Directories to include
    dirs_to_include = [
        'src',
        'templates',
        'static',
        'data'
    ]
    
    # Copy files
    print("📋 Copying files...")
    for file in files_to_include:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
            print(f"  ✅ {file}")
        else:
            print(f"  ⚠️  {file} not found")
    
    # Copy directories
    print("📁 Copying directories...")
    for dir_name in dirs_to_include:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, package_dir / dir_name)
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ⚠️  {dir_name}/ not found")
    
    # Create README for the package
    readme_content = f"""# W.AI.TLIST Distribution Package
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quick Installation (Any Platform)

1. Extract this package
2. Run: `python install.py`
3. Wait for build to complete
4. Launch the application from the dist folder

## Alternative Installation Methods

### Windows
- Run: `build_windows.bat`
- Execute: `dist\\Waitlyst.exe`

### Linux
- Run: `bash build_linux.sh`
- Execute: `./dist/Waitlyst`

### macOS
- Run: `bash build_macos.sh`
- Execute: `./dist/Waitlyst`

## Universal Installer
- Run: `python universal_installer.py`
- Full system installation with shortcuts

## System Requirements
- Python 3.8+
- 1GB RAM
- 500MB disk space
- Modern web browser

## Support
- See BUILD_INSTRUCTIONS.md for detailed build info
- See USER_GUIDE.md for end-user instructions
- See README_EXECUTABLE.md for deployment guide

W.AI.TLIST - Dental Appointment Optimization
"""
    
    (package_dir / 'README.md').write_text(readme_content, encoding='utf-8')
    
    # Create Windows installer batch file
    windows_installer = f"""@echo off
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                W.AI.TLIST INSTALLER                         ║
echo ║              Dental Appointment Optimization                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 🚀 Installing W.AI.TLIST for Windows...
echo.
python install.py
pause
"""
    (package_dir / 'INSTALL_WINDOWS.bat').write_text(windows_installer, encoding='utf-8')
    
    # Create Unix installer script
    unix_installer = f"""#!/bin/bash
echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                W.AI.TLIST INSTALLER                         ║"
echo "║              Dental Appointment Optimization                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo
echo "🚀 Installing W.AI.TLIST for Linux/macOS..."
echo
python3 install.py
read -p "Press Enter to continue..."
"""
    unix_script = package_dir / 'INSTALL_UNIX.sh'
    unix_script.write_text(unix_installer, encoding='utf-8')
    unix_script.chmod(0o755)
    
    # Create ZIP file
    zip_filename = f"{package_name}.zip"
    print(f"🗜️  Creating {zip_filename}...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir.parent)
                zipf.write(file_path, arcname)
    
    # Get package size
    package_size = os.path.getsize(zip_filename) / (1024 * 1024)
    
    print("\n" + "="*60)
    print("🎉 DISTRIBUTION PACKAGE CREATED!")
    print("="*60)
    print(f"📦 Package: {zip_filename}")
    print(f"📊 Size: {package_size:.1f}MB")
    print(f"📁 Contains: {len(files_to_include)} files, {len(dirs_to_include)} directories")
    print("\n🎯 Distribution Instructions:")
    print("1. Share the ZIP file with users")
    print("2. Users extract and run:")
    print("   • Windows: INSTALL_WINDOWS.bat")
    print("   • Linux/macOS: bash INSTALL_UNIX.sh")
    print("   • Any platform: python install.py")
    print("\n✨ Ready for distribution!")
    
    # Cleanup
    shutil.rmtree(package_dir)
    
    return zip_filename

if __name__ == "__main__":
    create_distribution_package() 