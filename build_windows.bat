@echo off
REM WAITLYST Windows Build Script
REM This script builds the Windows executable for WAITLYST

echo ===============================================
echo    WAITLYST Windows Build Script
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://python.org
    pause
    exit /b 1
)

echo ✓ Python found
echo.

REM Check if we're in a virtual environment or create one
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ✓ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo ✓ Installing dependencies...
pip install -r requirements.txt

REM Install PyInstaller
echo ✓ Installing PyInstaller...
pip install pyinstaller

REM Clean previous builds
if exist "dist" (
    echo ✓ Cleaning previous builds...
    rmdir /s /q dist
)
if exist "build" (
    rmdir /s /q build
)

REM Build the executable
echo ✓ Building Windows executable...
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

REM Check if build succeeded
if exist "dist\Waitlyst.exe" (
    echo.
    echo ===============================================
    echo ✅ Build completed successfully!
    echo ===============================================
    echo.
    echo Executable location: dist\Waitlyst.exe
    echo.
    echo You can now distribute the 'dist' folder to users.
    echo Users can run Waitlyst.exe to start the application.
    echo.
) else (
    echo.
    echo ===============================================
    echo ❌ Build failed!
    echo ===============================================
    echo.
    echo Please check the error messages above.
)

pause 