#!/usr/bin/env python3
"""
Linux AppImage Creator for W.AI.TLIST
Creates an AppImage for Linux distribution.
"""

import os
import subprocess
import shutil
import urllib.request
from pathlib import Path

def download_appimage_tool():
    """Download appimagetool if not present."""
    tool_path = Path("appimagetool-x86_64.AppImage")
    
    if tool_path.exists():
        return str(tool_path)
    
    print("📥 Downloading appimagetool...")
    url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    
    try:
        urllib.request.urlretrieve(url, tool_path)
        tool_path.chmod(0o755)
        print("✅ appimagetool downloaded")
        return str(tool_path)
    except Exception as e:
        print(f"❌ Failed to download appimagetool: {e}")
        return None

def create_linux_appimage():
    """Create an AppImage for Linux."""
    print("🐧 Creating Linux AppImage...")
    
    # Paths
    app_name = "Waitlyst"
    appdir_name = "Waitlyst.AppDir"
    appimage_name = "waitlyst-installer-linux.AppImage"
    
    # Create AppDir structure
    appdir = Path(appdir_name)
    if appdir.exists():
        shutil.rmtree(appdir)
    
    # Create directory structure
    appdir.mkdir()
    (appdir / "usr" / "bin").mkdir(parents=True)
    (appdir / "usr" / "share" / "applications").mkdir(parents=True)
    (appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True)
    
    # Copy the executable
    if not os.path.exists(f"dist/{app_name}"):
        print(f"❌ Error: {app_name} not found in dist/")
        return False
    
    print(f"📦 Copying {app_name} to AppDir...")
    shutil.copy2(f"dist/{app_name}", appdir / "usr" / "bin" / app_name)
    
    # Copy _internal directory if it exists
    internal_dir = Path("dist") / "_internal"
    if internal_dir.exists():
        shutil.copytree(internal_dir, appdir / "usr" / "bin" / "_internal")
        print("📁 Copied _internal directory")
    
    # Create desktop entry
    desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=W.AI.TLIST
Comment=Dental Appointment Optimization
Exec=usr/bin/{app_name}
Icon=waitlyst
Terminal=true
Categories=Office;Medical;
Keywords=dental;appointment;medical;clinic;
StartupNotify=true
"""
    
    desktop_file = appdir / "usr" / "share" / "applications" / "waitlyst.desktop"
    desktop_file.write_text(desktop_entry)
    print("📄 Created desktop entry")
    
    # Create AppRun script
    apprun_script = f"""#!/bin/bash
# AppRun script for W.AI.TLIST

# Get the directory where this script is located
APPDIR="$(dirname "$(readlink -f "${{BASH_SOURCE[0]}}")")"

# Set up environment
export PATH="${{APPDIR}}/usr/bin:${{PATH}}"
export LD_LIBRARY_PATH="${{APPDIR}}/usr/lib:${{LD_LIBRARY_PATH}}"

# Change to the app directory
cd "${{APPDIR}}/usr/bin"

# Launch the application
exec "./{app_name}" "$@"
"""
    
    apprun_file = appdir / "AppRun"
    apprun_file.write_text(apprun_script)
    apprun_file.chmod(0o755)
    print("📄 Created AppRun script")
    
    # Create symlink to desktop file
    (appdir / "waitlyst.desktop").symlink_to("usr/share/applications/waitlyst.desktop")
    
    # Create a simple icon (text-based placeholder)
    icon_content = """P3
# Simple icon for W.AI.TLIST
64 64
255
# This is a placeholder icon - replace with actual icon
"""
    
    # Add simple colored blocks to make it recognizable
    for i in range(64):
        for j in range(64):
            if i < 20 and j < 20:
                icon_content += "70 130 180 "  # Blue
            elif i < 20 and j >= 44:
                icon_content += "70 130 180 "  # Blue
            elif i >= 44 and j < 20:
                icon_content += "70 130 180 "  # Blue
            elif i >= 44 and j >= 44:
                icon_content += "70 130 180 "  # Blue
            else:
                icon_content += "255 255 255 "  # White
        icon_content += "\\n"
    
    icon_file = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "waitlyst.png"
    
    # Create a simple PNG using convert if available, otherwise skip icon
    try:
        # Try to create a simple icon using ImageMagick
        subprocess.run([
            "convert", "-size", "256x256", "xc:lightblue",
            "-gravity", "center", "-pointsize", "24", 
            "-annotate", "0", "W.AI\\nTLIST",
            str(icon_file)
        ], check=True)
        print("🎨 Created icon")
    except:
        # If ImageMagick not available, create a simple text file as placeholder
        icon_file.with_suffix('.txt').write_text("W.AI.TLIST Icon Placeholder")
        print("⚠️  Created placeholder icon (install ImageMagick for proper icon)")
    
    # Create symlink to icon
    try:
        (appdir / "waitlyst.png").symlink_to("usr/share/icons/hicolor/256x256/apps/waitlyst.png")
    except:
        pass
    
    # Download and use appimagetool
    appimagetool = download_appimage_tool()
    if not appimagetool:
        print("❌ Cannot create AppImage without appimagetool")
        return False
    
    # Create AppImage
    try:
        print("🔨 Building AppImage...")
        
        # Remove existing AppImage
        if os.path.exists(appimage_name):
            os.remove(appimage_name)
        
        # Set ARCH environment variable
        env = os.environ.copy()
        env['ARCH'] = 'x86_64'
        
        # Run appimagetool
        subprocess.run([
            appimagetool, appdir_name, appimage_name
        ], check=True, env=env)
        
        # Make AppImage executable
        Path(appimage_name).chmod(0o755)
        
        # Get file size
        appimage_size = os.path.getsize(appimage_name) / (1024 * 1024)
        
        print("\n" + "="*50)
        print("🎉 Linux AppImage created successfully!")
        print("="*50)
        print(f"📦 File: {appimage_name}")
        print(f"📊 Size: {appimage_size:.1f}MB")
        print(f"🎯 Instructions:")
        print(f"   1. Download {appimage_name}")
        print(f"   2. Make executable: chmod +x {appimage_name}")
        print(f"   3. Run: ./{appimage_name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ AppImage creation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        if appdir.exists():
            shutil.rmtree(appdir)

if __name__ == "__main__":
    create_linux_appimage() 