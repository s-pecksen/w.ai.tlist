#!/usr/bin/env python3
"""
W.AI.TLIST Universal Installer Creator
Master script to create installers for all platforms.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              W.AI.TLIST INSTALLER CREATOR                   ║
║              Cross-Platform Installer Builder               ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_requirements():
    """Check if basic requirements are met."""
    print("🔧 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check if required files exist
    required_files = [
        'app.py',
        'universal_launcher.py',
        'requirements.txt',
        'waitlyst_launcher.spec'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def clean_build_artifacts():
    """Clean previous build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    artifacts = ['venv', 'build', 'dist', 'installers']
    for artifact in artifacts:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                shutil.rmtree(artifact)
            else:
                os.remove(artifact)
    
    # Clean platform-specific installer files
    installer_files = [
        'waitlyst-installer-windows.exe',
        'waitlyst-installer-macos.dmg',
        'waitlyst-installer-linux.AppImage',
        'appimagetool-x86_64.AppImage'
    ]
    
    for file in installer_files:
        if os.path.exists(file):
            os.remove(file)
    
    print("✅ Build artifacts cleaned")

def build_executable():
    """Build the executable using PyInstaller."""
    print("🔨 Building executable...")
    
    try:
        # Create virtual environment
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        
        # Determine pip and python commands
        system = platform.system().lower()
        if system == 'windows':
            pip_cmd = ['venv\\Scripts\\pip.exe']
            python_cmd = ['venv\\Scripts\\python.exe']
        else:
            pip_cmd = ['venv/bin/pip']
            python_cmd = ['venv/bin/python']
        
        # Install dependencies
        print("📥 Installing dependencies...")
        subprocess.run(pip_cmd + ['install', '--upgrade', 'pip'], check=True)
        subprocess.run(pip_cmd + ['install', '-r', 'requirements.txt'], check=True)
        subprocess.run(pip_cmd + ['install', 'pyinstaller'], check=True)
        
        # Build executable
        print("⚙️ Running PyInstaller...")
        subprocess.run(python_cmd + ['-m', 'PyInstaller', 'waitlyst_launcher.spec', '--clean', '--noconfirm'], check=True)
        
        # Check if executable was created
        system = platform.system().lower()
        if system == 'windows':
            executable_path = Path('dist') / 'Waitlyst.exe'
        elif system == 'darwin':
            executable_path = Path('dist') / 'Waitlyst.app'
        else:
            executable_path = Path('dist') / 'Waitlyst'
        
        if executable_path.exists():
            print(f"✅ Executable created: {executable_path}")
            return True
        else:
            print("❌ Executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def create_windows_installer():
    """Create Windows installer."""
    print("🪟 Creating Windows installer...")
    
    if not os.path.exists('dist/Waitlyst.exe'):
        print("❌ Windows executable not found")
        return False
    
    # Create installers directory
    os.makedirs('installers', exist_ok=True)
    
    # Check for Inno Setup
    inno_setup_paths = [
        'C:/Program Files (x86)/Inno Setup 6/ISCC.exe',
        'C:/Program Files/Inno Setup 6/ISCC.exe'
    ]
    
    inno_setup_path = None
    for path in inno_setup_paths:
        if os.path.exists(path):
            inno_setup_path = path
            break
    
    if inno_setup_path:
        try:
            subprocess.run([inno_setup_path, 'windows_installer.iss'], check=True)
            if os.path.exists('installers/waitlyst-installer-windows.exe'):
                print("✅ Windows installer created: installers/waitlyst-installer-windows.exe")
                return True
            else:
                print("❌ Installer file not found after build")
                return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Inno Setup failed: {e}")
            return False
    else:
        print("⚠️  Inno Setup not found. Skipping Windows installer.")
        print("📥 Install Inno Setup from: https://jrsoftware.org/isinfo.php")
        return False

def create_macos_installer():
    """Create macOS DMG installer."""
    print("🍎 Creating macOS installer...")
    
    if not os.path.exists('dist/Waitlyst.app'):
        print("❌ macOS app bundle not found")
        return False
    
    try:
        # Import and run the DMG creator
        from create_macos_dmg import create_macos_dmg
        return create_macos_dmg()
    except Exception as e:
        print(f"❌ DMG creation failed: {e}")
        return False

def create_linux_installer():
    """Create Linux AppImage installer."""
    print("🐧 Creating Linux installer...")
    
    if not os.path.exists('dist/Waitlyst'):
        print("❌ Linux executable not found")
        return False
    
    try:
        # Import and run the AppImage creator
        from create_linux_appimage import create_linux_appimage
        return create_linux_appimage()
    except Exception as e:
        print(f"❌ AppImage creation failed: {e}")
        return False

def main():
    """Main execution function."""
    print_banner()
    
    # Check what platform we're on
    current_platform = platform.system().lower()
    print(f"🔍 Current platform: {platform.system()}")
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements not met. Exiting.")
        return False
    
    # Ask user what to build
    print("\n🎯 What would you like to build?")
    print("1. Current platform only")
    print("2. All platforms (if possible)")
    print("3. Custom selection")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return False
    
    # Determine what to build
    build_windows = False
    build_macos = False
    build_linux = False
    
    if choice == "1":
        if current_platform == 'windows':
            build_windows = True
        elif current_platform == 'darwin':
            build_macos = True
        else:
            build_linux = True
    elif choice == "2":
        build_windows = True
        build_macos = True
        build_linux = True
    elif choice == "3":
        try:
            if input("Build Windows installer? (y/n): ").lower().startswith('y'):
                build_windows = True
            if input("Build macOS installer? (y/n): ").lower().startswith('y'):
                build_macos = True
            if input("Build Linux installer? (y/n): ").lower().startswith('y'):
                build_linux = True
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return False
    else:
        print("❌ Invalid choice")
        return False
    
    if not (build_windows or build_macos or build_linux):
        print("❌ Nothing selected to build")
        return False
    
    # Clean previous builds
    clean_build_artifacts()
    
    # Build executable
    if not build_executable():
        print("❌ Failed to build executable")
        return False
    
    # Create installers
    results = []
    
    if build_windows:
        if current_platform == 'windows':
            success = create_windows_installer()
            results.append(("Windows", success))
        else:
            print("⚠️  Cannot build Windows installer on non-Windows platform")
            results.append(("Windows", False))
    
    if build_macos:
        if current_platform == 'darwin':
            success = create_macos_installer()
            results.append(("macOS", success))
        else:
            print("⚠️  Cannot build macOS installer on non-macOS platform")
            results.append(("macOS", False))
    
    if build_linux:
        if current_platform == 'linux':
            success = create_linux_installer()
            results.append(("Linux", success))
        else:
            print("⚠️  Cannot build Linux installer on non-Linux platform")
            results.append(("Linux", False))
    
    # Print summary
    print("\n" + "="*60)
    print("🎉 BUILD SUMMARY")
    print("="*60)
    
    for platform_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{platform_name}: {status}")
    
    # List created files
    print("\n📦 Created files:")
    
    installer_files = [
        ('installers/waitlyst-installer-windows.exe', 'Windows Installer'),
        ('waitlyst-installer-macos.dmg', 'macOS DMG'),
        ('waitlyst-installer-linux.AppImage', 'Linux AppImage'),
        ('dist/Waitlyst.exe', 'Windows Executable'),
        ('dist/Waitlyst.app', 'macOS App Bundle'),
        ('dist/Waitlyst', 'Linux Executable')
    ]
    
    for file_path, description in installer_files:
        if os.path.exists(file_path):
            try:
                size = os.path.getsize(file_path) / (1024 * 1024)
                print(f"   {description}: {file_path} ({size:.1f}MB)")
            except:
                print(f"   {description}: {file_path}")
    
    print("\n🚀 Ready for distribution!")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 