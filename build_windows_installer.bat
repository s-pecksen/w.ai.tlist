@echo off
REM W.AI.TLIST Windows Installer Builder
REM Builds the executable and creates a Windows installer

echo ===============================================
echo    W.AI.TLIST Windows Installer Builder
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

REM Create virtual environment if it doesn't exist
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
pip install pyinstaller

REM Clean previous builds
echo ✓ Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "installers" rmdir /s /q installers

REM Build the executable
echo ✓ Building Windows executable...
python -m PyInstaller waitlyst_launcher.spec --clean --noconfirm

REM Check if build succeeded
if exist "dist\Waitlyst.exe" (
    echo ✅ Executable built successfully!
    
    REM Create installers directory
    mkdir installers
    
    REM Check if Inno Setup is available
    set "INNO_SETUP_PATH="
    for %%i in ("C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Program Files\Inno Setup 6\ISCC.exe") do (
        if exist "%%i" set "INNO_SETUP_PATH=%%i"
    )
    
    if defined INNO_SETUP_PATH (
        echo ✓ Creating Windows installer with Inno Setup...
        "%INNO_SETUP_PATH%" windows_installer.iss
        
        if exist "installers\waitlyst-installer-windows.exe" (
            echo.
            echo ===============================================
            echo ✅ Windows installer created successfully!
            echo ===============================================
            echo.
            echo 📦 Installer: installers\waitlyst-installer-windows.exe
            echo 🚀 Executable: dist\Waitlyst.exe
            echo.
            echo 🎯 Distribution options:
            echo   • Share the installer (.exe) for easy installation
            echo   • Share the executable directly for portable use
            echo.
        ) else (
            echo ❌ Installer creation failed
        )
    ) else (
        echo ⚠️  Inno Setup not found. Creating portable executable only.
        echo 📥 To create installer, install Inno Setup from: https://jrsoftware.org/isinfo.php
        echo.
        echo ===============================================
        echo ✅ Windows executable created successfully!
        echo ===============================================
        echo.
        echo 📦 Executable: dist\Waitlyst.exe
        echo 📁 Size: 
        for %%I in (dist\Waitlyst.exe) do echo    %%~zI bytes
        echo.
        echo 🎯 To distribute:
        echo   • Share the entire dist\ folder
        echo   • Users can run Waitlyst.exe directly
        echo.
    )
) else (
    echo.
    echo ===============================================
    echo ❌ Build failed!
    echo ===============================================
    echo.
    echo Please check the error messages above.
)

echo.
echo Press any key to exit...
pause >nul 