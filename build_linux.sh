#!/bin/bash

# WAITLYST Linux Build Script
# This script builds the Linux executable for WAITLYST

echo "==============================================="
echo "    WAITLYST Linux Build Script"
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

# Install PyInstaller
echo "✓ Installing PyInstaller..."
pip install pyinstaller

# Clean previous builds
if [ -d "dist" ]; then
    echo "✓ Cleaning previous builds..."
    rm -rf dist
fi
if [ -d "build" ]; then
    rm -rf build
fi

# Build the executable
echo "✓ Building Linux executable..."
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

# Check if build succeeded
if [ -f "dist/Waitlyst" ]; then
    echo
    echo "==============================================="
    echo "✅ Build completed successfully!"
    echo "==============================================="
    echo
    echo "Executable location: dist/Waitlyst"
    echo
    echo "You can now distribute the 'dist' folder to users."
    echo "Users can run ./Waitlyst to start the application."
    echo "Make sure the executable has proper permissions:"
    echo "  chmod +x dist/Waitlyst"
    echo
    
    # Make executable
    chmod +x dist/Waitlyst
    echo "✓ Executable permissions set"
else
    echo
    echo "==============================================="
    echo "❌ Build failed!"
    echo "==============================================="
    echo
    echo "Please check the error messages above."
    exit 1
fi 