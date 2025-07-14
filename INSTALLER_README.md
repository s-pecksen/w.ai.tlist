# W.AI.TLIST - Cross-Platform Installer Guide

🏥 **W.AI.TLIST** is now available as native installers for Windows (.exe), macOS (.dmg), and Linux (.AppImage). This guide explains how to create and use these installers.

## 🎯 Quick Start

### For Developers (Creating Installers)

**Option 1: Universal Build Script (Recommended)**
```bash
python create_all_installers.py
```

**Option 2: Platform-Specific Build Scripts**
- **Windows**: `build_windows_installer.bat`
- **macOS**: `bash build_macos_installer.sh`  
- **Linux**: `bash build_linux_installer.sh`

### For End Users (Installing the App)

| Platform | File Type | Instructions |
|----------|-----------|--------------|
| 🪟 **Windows** | `.exe` installer | Double-click → Follow wizard → Launch from Start Menu |
| 🍎 **macOS** | `.dmg` package | Double-click → Drag to Applications → Launch from Applications |
| 🐧 **Linux** | `.AppImage` | Download → `chmod +x` → Double-click or `./file.AppImage` |

## 📦 Installer Types

### Windows Installer (.exe)
- **File**: `waitlyst-installer-windows.exe`
- **Features**: 
  - ✅ Professional installation wizard
  - ✅ Start Menu integration
  - ✅ Desktop shortcut (optional)
  - ✅ Automatic uninstaller
  - ✅ Registry integration
  - ✅ Auto-launch option
- **Requirements**: Windows 7+
- **Tools**: Inno Setup (for building)

### macOS Installer (.dmg)
- **File**: `waitlyst-installer-macos.dmg`
- **Features**:
  - ✅ Professional DMG with drag-to-install
  - ✅ Applications folder integration
  - ✅ Proper app bundle structure
  - ✅ Native macOS experience
  - ✅ Launchpad integration
- **Requirements**: macOS 10.14+
- **Tools**: Built-in hdiutil

### Linux Installer (.AppImage)
- **File**: `waitlyst-installer-linux.AppImage`
- **Features**:
  - ✅ Portable executable
  - ✅ No installation required
  - ✅ Works on most Linux distributions
  - ✅ Desktop integration available
  - ✅ Self-contained dependencies
- **Requirements**: Most Linux distributions
- **Tools**: appimagetool (auto-downloaded)

## 🛠️ Building Installers

### Prerequisites

**All Platforms:**
- Python 3.8+
- Git
- Internet connection

**Platform-Specific:**
- **Windows**: Optional - Inno Setup for .exe installer
- **macOS**: Xcode Command Line Tools
- **Linux**: Standard development tools

### Method 1: Universal Builder (Easiest)

```bash
# Clone and navigate to the repository
git clone <repository-url>
cd waitlyst

# Run the universal builder
python create_all_installers.py
```

The script will:
1. Detect your platform
2. Ask what you want to build
3. Create virtual environment
4. Install dependencies
5. Build executable with PyInstaller
6. Create platform-specific installer
7. Show summary of created files

### Method 2: Platform-Specific Builds

#### Windows
```cmd
# Run the Windows builder
build_windows_installer.bat
```

**What it does:**
- Creates virtual environment
- Installs dependencies + PyInstaller
- Builds `dist/Waitlyst.exe`
- Creates `installers/waitlyst-installer-windows.exe` (if Inno Setup available)

#### macOS
```bash
# Run the macOS builder
bash build_macos_installer.sh
```

**What it does:**
- Creates virtual environment
- Installs dependencies + PyInstaller
- Builds `dist/Waitlyst.app`
- Creates `waitlyst-installer-macos.dmg`

#### Linux
```bash
# Run the Linux builder
bash build_linux_installer.sh
```

**What it does:**
- Creates virtual environment
- Installs dependencies + PyInstaller
- Builds `dist/Waitlyst`
- Downloads appimagetool
- Creates `waitlyst-installer-linux.AppImage`

### Method 3: Manual Build

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 4. Build executable
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

# 5. Create installer (platform-specific)
# Windows (requires Inno Setup):
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows_installer.iss

# macOS:
python create_macos_dmg.py

# Linux:
python create_linux_appimage.py
```

## 🎯 Distribution Guide

### For Software Publishers

**File Organization:**
```
releases/
├── waitlyst-installer-windows.exe    # Windows installer
├── waitlyst-installer-macos.dmg      # macOS installer  
├── waitlyst-installer-linux.AppImage # Linux installer
└── portable/
    ├── dist-windows/                 # Windows portable
    ├── dist-macos/                   # macOS portable
    └── dist-linux/                   # Linux portable
```

**Release Checklist:**
- [ ] Test on target platforms
- [ ] Verify auto-launch functionality
- [ ] Check installer/uninstaller
- [ ] Validate browser opening
- [ ] Test with antivirus software
- [ ] Sign executables (optional but recommended)

### For End Users

**Installation Instructions:**

#### Windows Users
1. Download `waitlyst-installer-windows.exe`
2. Right-click → "Run as administrator" (if prompted)
3. Follow the installation wizard
4. Launch from Start Menu or desktop shortcut
5. The app will start and open in your browser automatically

#### macOS Users
1. Download `waitlyst-installer-macos.dmg`
2. Double-click the DMG file
3. Drag "W.AI.TLIST" to the Applications folder
4. Launch from Applications folder or Spotlight
5. If security warning appears: Right-click → Open → Confirm

#### Linux Users
1. Download `waitlyst-installer-linux.AppImage`
2. Make executable: `chmod +x waitlyst-installer-linux.AppImage`
3. Run: `./waitlyst-installer-linux.AppImage`
4. Or double-click in file manager
5. The app will start and open in your browser automatically

## 🔧 Advanced Configuration

### Custom Icons
To add custom icons to installers:

1. **Windows**: Add icon file and update `windows_installer.iss`:
   ```ini
   SetupIconFile=path\to\icon.ico
   ```

2. **macOS**: Add icon and update `waitlyst_launcher.spec`:
   ```python
   icon='path/to/icon.icns'
   ```

3. **Linux**: Replace icon creation in `create_linux_appimage.py`

### Code Signing

#### Windows (Optional)
```cmd
# Sign the executable
signtool sign /f certificate.pfx /p password dist/Waitlyst.exe

# Sign the installer
signtool sign /f certificate.pfx /p password installers/waitlyst-installer-windows.exe
```

#### macOS (Optional)
```bash
# Sign the app
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/Waitlyst.app

# Notarize (requires Apple Developer account)
xcrun notarytool submit waitlyst-installer-macos.dmg --keychain-profile "AC_PASSWORD" --wait
```

### Environment Variables

The application looks for these environment variables:
- `FLASK_APP_ENCRYPTION_KEY`: Required for session encryption
- `FLASK_SESSION_SECRET_KEY`: Required for session management  
- `LOCAL_DATABASE_URL`: Optional, defaults to local SQLite

Create a `.env` file in the application directory:
```env
FLASK_APP_ENCRYPTION_KEY=your-encryption-key
FLASK_SESSION_SECRET_KEY=your-session-key
```

## 🚨 Troubleshooting

### Build Issues

**"Python not found"**
- Install Python 3.8+ from python.org
- Ensure Python is in PATH

**"PyInstaller failed"**
- Check available disk space (need ~500MB)
- Try deleting `venv` and rebuilding
- Check antivirus isn't blocking files

**Windows: "Inno Setup not found"**
- Install from: https://jrsoftware.org/isinfo.php
- Or use portable executable instead

**macOS: "Command not found"**
- Install Xcode Command Line Tools: `xcode-select --install`

**Linux: "AppImage creation failed"**
- Install missing dependencies
- Check internet connection (downloads appimagetool)

### Runtime Issues

**App won't start**
- Check port 7860 isn't in use
- Run as administrator/sudo if needed
- Check firewall settings

**Browser doesn't open**
- Manually navigate to http://127.0.0.1:7860
- Try different browser

**Security warnings**
- **Windows**: Click "More info" → "Run anyway"
- **macOS**: Right-click → "Open" → Confirm
- **Linux**: Add executable permissions

## 📊 File Sizes

Typical installer sizes:
- **Windows .exe**: ~25-30MB
- **macOS .dmg**: ~25-30MB  
- **Linux .AppImage**: ~25-30MB

Includes:
- Python runtime
- Flask and all dependencies
- Application code and assets
- Stripe payment integration
- Web browser launching logic

## 🔄 Updates

For future updates:
1. Increment version in `waitlyst_launcher.spec`
2. Update `windows_installer.iss` version info
3. Rebuild all installers
4. Test on target platforms
5. Distribute new installer files

## 📞 Support

**For Build Issues:**
- Check Python version: `python --version`
- Verify file permissions
- Check available disk space
- Review error messages

**For Runtime Issues:**
- Check system requirements
- Verify network connectivity
- Review firewall settings
- Test with different browsers

**Platform-Specific Help:**
- **Windows**: Check Windows Defender exclusions
- **macOS**: Review Gatekeeper settings
- **Linux**: Verify executable permissions

---

## 🎉 Summary

You now have three professional installer formats:

| Platform | Installer Type | User Experience |
|----------|----------------|-----------------|
| Windows | `.exe` installer | Enterprise-grade installation wizard |
| macOS | `.dmg` package | Native drag-to-install experience |
| Linux | `.AppImage` | Portable, no-install-needed executable |

All installers:
- ✅ Include the universal launcher with browser auto-opening
- ✅ Bundle all dependencies (no Python required)
- ✅ Provide one-click installation
- ✅ Auto-launch the application post-install
- ✅ Create appropriate system shortcuts
- ✅ Support all W.AI.TLIST features including Stripe integration

**🚀 Ready for professional distribution!** 