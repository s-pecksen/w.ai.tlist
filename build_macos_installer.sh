#!/bin/bash

# W.AI.TLIST macOS Installer Builder
# Builds the executable and creates a macOS DMG installer

echo "==============================================="
echo "    W.AI.TLIST macOS Installer Builder"
echo "==============================================="
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python is installed
if ! command_exists python3; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or later:"
    echo "  Option 1: Download from https://python.org"
    echo "  Option 2: Install via Homebrew: brew install python"
    exit 1
fi

echo "✓ Python 3 found"
echo

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to create virtual environment"
        exit 1
    fi
fi

echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Clean previous builds
echo "✓ Cleaning previous builds..."
rm -rf dist build

# Build the executable
echo "✓ Building macOS executable..."
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

# Check if build succeeded
if [ -d "dist/Waitlyst.app" ]; then
    echo "✅ App bundle built successfully!"
    
    # Create DMG installer
    echo "✓ Creating macOS DMG installer..."
    python3 create_macos_dmg.py
    
    if [ -f "waitlyst-installer-macos.dmg" ]; then
        echo
        echo "==============================================="
        echo "✅ macOS installer created successfully!"
        echo "==============================================="
        echo
        echo "📦 DMG Installer: waitlyst-installer-macos.dmg"
        echo "🚀 App Bundle: dist/Waitlyst.app"
        echo
        echo "🎯 Distribution options:"
        echo "   • Share the DMG for easy installation"
        echo "   • Share the .app bundle directly"
        echo
        echo "📱 Installation instructions:"
        echo "   1. Double-click the DMG file"
        echo "   2. Drag W.AI.TLIST to Applications folder"
        echo "   3. Launch from Applications"
        echo
        
        # Get file sizes
        if command_exists du; then
            echo "📊 File sizes:"
            du -h "waitlyst-installer-macos.dmg" | cut -f1 | sed 's/^/   DMG: /'
            du -h "dist/Waitlyst.app" | cut -f1 | sed 's/^/   App: /'
        fi
    else
        echo "⚠️  DMG creation failed, but app bundle is available"
        echo
        echo "==============================================="
        echo "✅ macOS app bundle created successfully!"
        echo "==============================================="
        echo
        echo "📦 App Bundle: dist/Waitlyst.app"
        echo
        echo "🎯 To distribute:"
        echo "   • Share the Waitlyst.app bundle"
        echo "   • Users can drag it to Applications folder"
        echo
    fi
else
    echo
    echo "==============================================="
    echo "❌ Build failed!"
    echo "==============================================="
    echo
    echo "Please check the error messages above."
    exit 1
fi 