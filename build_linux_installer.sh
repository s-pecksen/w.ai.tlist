#!/bin/bash

# W.AI.TLIST Linux Installer Builder
# Builds the executable and creates a Linux AppImage installer

echo "==============================================="
echo "    W.AI.TLIST Linux Installer Builder"
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
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
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
echo "✓ Building Linux executable..."
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

# Check if build succeeded
if [ -f "dist/Waitlyst" ]; then
    echo "✅ Executable built successfully!"
    
    # Make executable
    chmod +x dist/Waitlyst
    
    # Create AppImage installer
    echo "✓ Creating Linux AppImage installer..."
    python3 create_linux_appimage.py
    
    if [ -f "waitlyst-installer-linux.AppImage" ]; then
        echo
        echo "==============================================="
        echo "✅ Linux installer created successfully!"
        echo "==============================================="
        echo
        echo "📦 AppImage: waitlyst-installer-linux.AppImage"
        echo "🚀 Executable: dist/Waitlyst"
        echo
        echo "🎯 Distribution options:"
        echo "   • Share the AppImage for easy installation"
        echo "   • Share the executable directly for portable use"
        echo
        echo "📱 Installation instructions:"
        echo "   AppImage:"
        echo "     1. Download the AppImage"
        echo "     2. Make executable: chmod +x waitlyst-installer-linux.AppImage"
        echo "     3. Run: ./waitlyst-installer-linux.AppImage"
        echo
        echo "   Direct executable:"
        echo "     1. Download and extract the dist/ folder"
        echo "     2. Run: ./dist/Waitlyst"
        echo
        
        # Get file sizes
        if command_exists du; then
            echo "📊 File sizes:"
            du -h "waitlyst-installer-linux.AppImage" | cut -f1 | sed 's/^/   AppImage: /'
            du -h "dist/Waitlyst" | cut -f1 | sed 's/^/   Executable: /'
        fi
        
        # Make AppImage executable
        chmod +x "waitlyst-installer-linux.AppImage"
        echo "✓ AppImage permissions set"
        
    else
        echo "⚠️  AppImage creation failed, but executable is available"
        echo
        echo "==============================================="
        echo "✅ Linux executable created successfully!"
        echo "==============================================="
        echo
        echo "📦 Executable: dist/Waitlyst"
        echo
        echo "🎯 To distribute:"
        echo "   • Share the entire dist/ folder"
        echo "   • Users can run: ./dist/Waitlyst"
        echo
        echo "📱 Make sure to set executable permissions:"
        echo "   chmod +x dist/Waitlyst"
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