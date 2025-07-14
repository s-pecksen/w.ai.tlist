#!/usr/bin/env python3
"""
macOS DMG Creator for W.AI.TLIST
Creates a DMG installer for macOS distribution.
"""

import os
import subprocess
import shutil
from pathlib import Path

def create_macos_dmg():
    """Create a DMG installer for macOS."""
    print("🍎 Creating macOS DMG installer...")
    
    # Paths
    app_name = "Waitlyst.app"
    dmg_name = "waitlyst-installer-macos.dmg"
    temp_dmg = "temp.dmg"
    volume_name = "W.AI.TLIST Installer"
    
    # Create temporary directory structure
    temp_dir = Path("dmg_temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    # Copy the app bundle
    if not os.path.exists(f"dist/{app_name}"):
        print(f"❌ Error: {app_name} not found in dist/")
        return False
    
    print(f"📦 Copying {app_name} to DMG...")
    shutil.copytree(f"dist/{app_name}", temp_dir / app_name)
    
    # Copy additional files
    additional_files = ["README.md", "LICENSE"]
    for file in additional_files:
        if os.path.exists(file):
            shutil.copy2(file, temp_dir)
            print(f"📄 Added {file}")
    
    # Create Applications alias
    print("🔗 Creating Applications alias...")
    apps_alias = temp_dir / "Applications"
    if apps_alias.exists():
        apps_alias.unlink()
    
    try:
        subprocess.run([
            "ln", "-sf", "/Applications", str(apps_alias)
        ], check=True)
    except subprocess.CalledProcessError:
        print("⚠️  Could not create Applications alias")
    
    # Calculate size needed
    try:
        result = subprocess.run([
            "du", "-sm", str(temp_dir)
        ], capture_output=True, text=True, check=True)
        size_mb = int(result.stdout.split()[0]) + 50  # Add 50MB buffer
    except:
        size_mb = 200  # Default size
    
    print(f"💾 DMG size: {size_mb}MB")
    
    # Create DMG
    try:
        # Remove existing DMG files
        for dmg_file in [temp_dmg, dmg_name]:
            if os.path.exists(dmg_file):
                os.remove(dmg_file)
        
        # Create temporary DMG
        print("🔨 Creating temporary DMG...")
        subprocess.run([
            "hdiutil", "create",
            "-srcfolder", str(temp_dir),
            "-volname", volume_name,
            "-fs", "HFS+",
            "-fsargs", "-c c=64,a=16,e=16",
            "-format", "UDRW",
            "-size", f"{size_mb}m",
            temp_dmg
        ], check=True)
        
        # Mount the DMG
        print("📀 Mounting DMG...")
        mount_result = subprocess.run([
            "hdiutil", "attach", "-readwrite", "-noverify", "-noautoopen",
            temp_dmg
        ], capture_output=True, text=True, check=True)
        
        device = mount_result.stdout.split()[0]
        mount_point = f"/Volumes/{volume_name}"
        
        try:
            # Set up DMG appearance (if possible)
            print("🎨 Setting up DMG appearance...")
            
            # Create .DS_Store for layout
            ds_store_script = f'''
tell application "Finder"
    tell disk "{volume_name}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {{100, 100, 600, 400}}
        set arrangement of icon view options of container window to not arranged
        set icon size of icon view options of container window to 72
        set position of item "{app_name}" of container window to {{150, 200}}
        set position of item "Applications" of container window to {{350, 200}}
        update without registering applications
        delay 2
        close
    end tell
end tell
'''
            
            # Try to apply appearance settings
            try:
                subprocess.run([
                    "osascript", "-e", ds_store_script
                ], check=False, timeout=30)
            except:
                print("⚠️  Could not set DMG appearance")
            
            # Sync
            subprocess.run(["sync"], check=True)
            
        finally:
            # Unmount the DMG
            print("📤 Unmounting DMG...")
            subprocess.run([
                "hdiutil", "detach", device
            ], check=True)
        
        # Convert to final DMG
        print("🗜️  Converting to final DMG...")
        subprocess.run([
            "hdiutil", "convert", temp_dmg,
            "-format", "UDZO",
            "-imagekey", "zlib-level=9",
            "-o", dmg_name
        ], check=True)
        
        # Cleanup
        os.remove(temp_dmg)
        shutil.rmtree(temp_dir)
        
        # Get final size
        dmg_size = os.path.getsize(dmg_name) / (1024 * 1024)
        
        print("\n" + "="*50)
        print("🎉 macOS DMG created successfully!")
        print("="*50)
        print(f"📦 File: {dmg_name}")
        print(f"📊 Size: {dmg_size:.1f}MB")
        print(f"🎯 Instructions:")
        print(f"   1. Double-click {dmg_name}")
        print(f"   2. Drag {app_name} to Applications")
        print(f"   3. Launch from Applications folder")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ DMG creation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if os.path.exists(temp_dmg):
            os.remove(temp_dmg)

if __name__ == "__main__":
    create_macos_dmg() 