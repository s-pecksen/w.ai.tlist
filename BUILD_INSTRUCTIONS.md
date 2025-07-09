# W.AI.TLIST - Build Instructions

This guide explains how to build cross-platform executables for the W.AI.TLIST dental appointment management system.

## Overview

The build process creates a standalone executable that:
- ✅ Runs the Flask web application
- ✅ Automatically opens the app in Chrome browser
- ✅ Works on Windows, Linux, and macOS
- ✅ Requires no Python installation on target machines
- ✅ Includes all dependencies in a single distributable folder

## Prerequisites

### All Platforms
- Python 3.8 or later
- Git (to clone the repository)
- Internet connection (for downloading dependencies)

### Platform-Specific Requirements

#### Windows
- Windows 7 or later
- PowerShell or Command Prompt

#### Linux
- Ubuntu 18.04+ / CentOS 7+ / Fedora 30+ (or equivalent)
- bash shell
- Basic development tools (usually pre-installed)

#### macOS
- macOS 10.14 (Mojave) or later
- Xcode Command Line Tools: `xcode-select --install`

## Quick Start

### Windows
1. Open Command Prompt or PowerShell as Administrator
2. Navigate to the project directory
3. Run: `build_windows.bat`
4. Executable will be created in `dist\Waitlyst.exe`

### Linux
1. Open terminal
2. Navigate to the project directory
3. Run: `./build_linux.sh`
4. Executable will be created in `dist/Waitlyst`

### macOS
1. Open Terminal
2. Navigate to the project directory
3. Run: `./build_macos.sh`
4. Executable will be created in `dist/Waitlyst`

## Manual Build Process

If the automated scripts don't work, you can build manually:

### 1. Setup Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### 3. Build Executable
```bash
pyinstaller waitlyst_launcher.spec --clean --noconfirm
```

## Distribution

After a successful build:

1. **Locate the executable**: 
   - Windows: `dist/Waitlyst.exe`
   - Linux/macOS: `dist/Waitlyst`

2. **Distribution folder**: The entire `dist` folder contains all necessary files

3. **Test the executable**: Run it on the build machine first

4. **Package for distribution**: 
   - Zip the entire `dist` folder
   - Include user instructions (see USER_GUIDE.md)

## Troubleshooting

### Common Issues

#### "Python not found"
- **Windows**: Install Python from python.org, ensure "Add to PATH" is checked
- **Linux**: `sudo apt install python3 python3-pip` (Ubuntu/Debian)
- **macOS**: Install Python from python.org or use Homebrew

#### "Permission denied" (Linux/macOS)
```bash
chmod +x build_linux.sh    # or build_macos.sh
chmod +x dist/Waitlyst      # Make the built executable runnable
```

#### "PyInstaller failed"
1. Try running the build script again
2. Check Python version (must be 3.8+)
3. Ensure all dependencies are installed
4. Check available disk space (build requires ~500MB temporarily)

#### "Module not found" errors
- Delete `venv` folder and rebuild
- Ensure all imports in `src/` directory are properly structured
- Check that all required modules are in `requirements.txt`

### Build Performance

- **First build**: 5-15 minutes (downloads dependencies)
- **Subsequent builds**: 2-5 minutes (uses cached dependencies)
- **Output size**: ~150-300MB (includes Python runtime and all dependencies)

## Advanced Configuration

### Custom Icons
To add a custom icon to the executable:

1. Create an icon file:
   - Windows: `.ico` format
   - Linux: `.png` format  
   - macOS: `.icns` format

2. Update `waitlyst_launcher.spec`:
```python
exe = EXE(
    # ... other parameters ...
    icon='path/to/your/icon.ico',  # Add this line
)
```

### Environment Variables
The application looks for these environment variables:
- `FLASK_APP_ENCRYPTION_KEY`: Required for session encryption
- `FLASK_SESSION_SECRET_KEY`: Required for session management
- `LOCAL_DATABASE_URL`: Optional, defaults to local SQLite

Create a `.env` file in the application directory or set them in the launcher script.

### Build Optimization
To reduce executable size:

1. In `waitlyst_launcher.spec`, set:
```python
upx=True,          # Enable UPX compression
strip=True,        # Strip debug symbols (Linux/macOS)
```

2. Remove unnecessary packages from `requirements.txt`

## Security Considerations

### Code Signing (Optional but Recommended)

#### Windows
```bash
# After building, sign the executable
signtool sign /f certificate.pfx /p password dist/Waitlyst.exe
```

#### macOS
```bash
# Sign the executable
codesign -s "Developer ID Application: Your Name" dist/Waitlyst
```

### Antivirus False Positives
Some antivirus software may flag PyInstaller executables. To minimize this:

1. Build on a clean, updated system
2. Use official Python and PyInstaller versions
3. Consider code signing (see above)
4. Test with Windows Defender and common antivirus tools

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Ensure your system meets the prerequisites
3. Try the manual build process
4. Check the Python and PyInstaller documentation

## File Structure After Build

```
dist/
├── Waitlyst.exe (or Waitlyst on Unix)
├── _internal/
│   ├── templates/
│   ├── static/
│   ├── data/
│   ├── src/
│   └── [Python runtime and dependencies]
```

The entire `dist` folder is portable and can be copied to target machines. 