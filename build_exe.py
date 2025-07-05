import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully.")

def create_spec_file():
    """Create a PyInstaller spec file for the Flask app."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('data', 'data'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'flask',
        'flask_login',
        'flask_sqlalchemy',
        'flask_session',
        'sqlalchemy',
        'jinja2',
        'werkzeug',
        'blinker',
        'click',
        'itsdangerous',
        'markupsafe',
        'cryptography',
        'cffi',
        'pycparser',
        'greenlet',
        'keyring',
        'jaraco.classes',
        'jaraco.context',
        'jaraco.functools',
        'more_itertools',
        'typing_extensions',
        'dotenv',
        'supabase',
        'psycopg2',
        'pywin32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wai_tlist_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('wai_tlist_app.spec', 'w') as f:
        f.write(spec_content)
    print("Created PyInstaller spec file: wai_tlist_app.spec")

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable...")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build using the spec file
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "wai_tlist_app.spec"
    ])
    
    print("Build completed successfully!")
    print("Executable location: dist/wai_tlist_app.exe")

def create_launcher_script():
    """Create a simple launcher script for the executable."""
    launcher_content = '''@echo off
echo Starting WAI TList Application...
echo.
echo The application will open in your default web browser.
echo Please wait a moment...
echo.
start "" "http://localhost:7860"
"%~dp0wai_tlist_app.exe"
pause
'''
    
    with open('dist/launch_app.bat', 'w') as f:
        f.write(launcher_content)
    print("Created launcher script: dist/launch_app.bat")

def create_readme():
    """Create a README file for the packaged application."""
    readme_content = '''# WAI TList Application - Offline Version

## Installation Instructions

1. Extract all files from this package to a folder on your computer
2. Double-click `launch_app.bat` to start the application
3. The application will automatically open in your default web browser
4. If the browser doesn't open automatically, manually navigate to: http://localhost:7860

## System Requirements

- Windows 10 or later
- No internet connection required (fully offline)
- No Python installation required

## Troubleshooting

- If the application doesn't start, try running `wai_tlist_app.exe` directly
- Make sure no other application is using port 7860
- Check that your antivirus software isn't blocking the executable

## Data Storage

All data is stored locally in the `data` folder within the application directory.
Your data will persist between application sessions.

## Support

For technical support, contact your system administrator.
'''
    
    with open('dist/README.txt', 'w') as f:
        f.write(readme_content)
    print("Created README file: dist/README.txt")

def main():
    """Main build process."""
    print("Starting build process for WAI TList Application...")
    print("=" * 50)
    
    # Install PyInstaller
    install_pyinstaller()
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    build_executable()
    
    # Create additional files
    create_launcher_script()
    create_readme()
    
    print("=" * 50)
    print("Build process completed!")
    print("Your executable is ready in the 'dist' folder.")
    print("You can now distribute the entire 'dist' folder to your clients.")

if __name__ == "__main__":
    main() 