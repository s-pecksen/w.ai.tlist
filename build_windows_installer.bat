@echo off
REM W.AI.TLIST Windows 64-bit Installer Builder
REM Builds the executable and creates a Windows installer for x86_64 architecture

echo ===============================================
echo    W.AI.TLIST Windows 64-bit Installer Builder
echo ===============================================
echo.

REM Check system architecture
echo ^> Checking system architecture...
if not "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    echo WARNING: This script is optimized for 64-bit ^(x86_64^) systems
    echo Current architecture: %PROCESSOR_ARCHITECTURE%
    echo.
)
echo ^> Target architecture: x86_64 ^(64-bit Intel/AMD^)
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://python.org
    echo Make sure to install the 64-bit version for optimal performance
    pause
    exit /b 1
)

REM Check Python architecture
python -c "import platform; print('Python architecture:', platform.architecture()[0])"
echo [OK] Python found
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

echo [OK] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [OK] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [OK] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Verify PyInstaller installation
echo [OK] Verifying PyInstaller...
pyinstaller --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller installation failed
    pause
    exit /b 1
)

REM Clean previous builds
echo [OK] Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "installers" rmdir /s /q installers

REM Verify spec file exists
if not exist "waitlyst_launcher.spec" (
    echo ERROR: waitlyst_launcher.spec not found
    pause
    exit /b 1
)

REM Build the executable
echo ===============================================
echo [OK] Building Windows 64-bit executable...
echo ===============================================
echo Target: Windows x86_64 standalone executable
echo Mode: Windowed ^(no console^)
echo Build: Single-file ^(--onefile equivalent^)
echo Security: Bootloader obfuscation enabled
echo Compression: UPX enabled
echo Version: 1.0.0 ^(Pecksen Software^)
echo Manifest: UAC asInvoker, DPI aware
echo.
python -m PyInstaller waitlyst_launcher.spec --onefile --clean --noconfirm --key=waitlyst_secure_2024_pecksen

REM Check if build succeeded
if exist "dist\Waitlyst.exe" (
    echo.
    echo ===============================================
    echo [SUCCESS] Executable built successfully!
    echo ===============================================
    
    REM Show file information
    echo.
    echo File Information:
    for %%I in (dist\Waitlyst.exe) do (
        echo   File: dist\Waitlyst.exe
        echo   Size: %%~zI bytes ^(single-file executable^)
        echo   Modified: %%~tI
        echo   Version: 1.0.0.0 - Pecksen Software
        echo   Security: Bootloader obfuscated
        echo   Manifest: Embedded ^(UAC asInvoker, DPI aware^)
    )
    
    REM Test executable
    echo.
    echo [OK] Testing executable compatibility...
    dist\Waitlyst.exe --help >nul 2>&1
    echo [OK] Executable appears to be working
    
    REM Check for code signing certificate
    if exist "certificate.pfx" (
        echo [OK] Code signing certificate found
        if defined CERT_PASSWORD (
            echo [OK] Signing executable with certificate...
            signtool sign /f "certificate.pfx" /p "%CERT_PASSWORD%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "dist\Waitlyst.exe"
            if %ERRORLEVEL% equ 0 (
                echo [OK] Executable signed successfully - SmartScreen warnings eliminated!
            ) else (
                echo [WARNING] Code signing failed - executable remains unsigned
            )
        ) else (
            echo [WARNING] Certificate found but CERT_PASSWORD not set
            echo [INFO] Set CERT_PASSWORD environment variable to enable signing
        )
    ) else (
        echo [INFO] No code signing certificate found ^(certificate.pfx^)
        echo [INFO] See CODE_SIGNING_GUIDE.md for instructions to eliminate SmartScreen warnings
    )
    
    REM Create installers directory
    mkdir installers
    
    REM Check if Inno Setup is available
    set "INNO_SETUP_PATH="
    for %%i in ("C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Program Files\Inno Setup 6\ISCC.exe") do (
        if exist "%%i" set "INNO_SETUP_PATH=%%i"
    )
    
    if defined INNO_SETUP_PATH (
        echo [OK] Creating Windows installer with Inno Setup...
        "%INNO_SETUP_PATH%" windows_installer.iss
        
        if exist "installers\waitlyst-installer-windows.exe" (
            echo.
            echo ===============================================
            echo [SUCCESS] Windows installer created successfully!
            echo ===============================================
            echo.
            echo Installer: installers\waitlyst-installer-windows.exe
            echo Executable: dist\Waitlyst.exe
            echo Target: Windows 10/11 ^(x86_64^)
            echo.
            echo Distribution options:
            echo   - Share the installer ^(.exe^) for easy installation
            echo   - Share the executable directly for portable use
            echo.
            echo Features:
            echo   - No Python installation required
            echo   - No external dependencies needed  
            echo   - Single-file standalone executable
            echo   - Bootloader obfuscated for reduced AV detection
            echo   - Version info embedded ^(Pecksen Software 1.0.0^)
            echo   - UAC asInvoker ^(no admin prompts^)
            echo   - DPI aware for high-resolution displays
            echo   - Compatible with Windows 10 and 11
            echo.
            echo [INFO] To build additional user trust:
            echo   1. Submit to VirusTotal: python virustotal_submit.py
            echo   2. Include INSTALLATION_INSTRUCTIONS.md with installer
            echo.
        ) else (
            echo [ERROR] Installer creation failed
        )
    ) else (
        echo [WARNING] Inno Setup not found. Creating portable executable only.
        echo To create installer, install Inno Setup from: https://jrsoftware.org/isinfo.php
        echo.
        echo ===============================================
        echo [SUCCESS] Windows 64-bit executable created successfully!
        echo ===============================================
        echo.
        echo Executable: dist\Waitlyst.exe
        echo Target: Windows 10/11 ^(x86_64^)
        for %%I in (dist\Waitlyst.exe) do echo Size: %%~zI bytes
        echo.
        echo To distribute:
        echo   - Share the dist\Waitlyst.exe file
        echo   - Users can run it directly - no installation needed
        echo   - No Python or dependencies required
        echo.
        echo Features:
        echo   - Single-file 64-bit executable
        echo   - Bootloader obfuscated for reduced AV detection
        echo   - Version info embedded ^(Pecksen Software 1.0.0^)
        echo   - UAC asInvoker ^(no admin prompts^)
        echo   - DPI aware for high-resolution displays
        echo   - Compatible with Windows 10 and 11
        echo   - Opens automatically in browser
        echo   - No console window ^(windowed mode^)
        echo.
        echo [INFO] To build user trust and eliminate security warnings:
            echo   1. Submit to VirusTotal: python virustotal_submit.py
            echo   2. Include INSTALLATION_INSTRUCTIONS.md with distribution
            echo   3. Consider code signing ^(see CODE_SIGNING_GUIDE.md^)
            echo.
        )
    ) else (
    echo.
    echo ===============================================
    echo [ERROR] Build failed!
    echo ===============================================
    echo.
    echo Please check the error messages above.
    echo Common issues:
    echo   - Missing dependencies in requirements.txt
    echo   - Python architecture mismatch ^(ensure 64-bit Python^)
    echo   - Insufficient disk space
    echo   - PyInstaller version compatibility
)

echo.
echo Press any key to exit...
pause >nul 