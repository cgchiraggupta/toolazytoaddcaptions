@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: HinglishCaps - Windows Installer
:: Double-click this file to install and run HinglishCaps

echo ════════════════════════════════════════════════════════════════════════════════
echo                           HINGLISHCAPS INSTALLER
echo ════════════════════════════════════════════════════════════════════════════════
echo.
echo This will install HinglishCaps on your Windows PC. It will:
echo 1. Check for Python 3.9+
echo 2. Create a virtual environment
echo 3. Install required packages
echo 4. Check for FFmpeg
echo 5. Launch the web interface
echo.
echo ════════════════════════════════════════════════════════════════════════════════

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check Python version
echo 🔍 Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, CHECK "Add Python to PATH"
    echo Then run this script again.
    echo.
    pause
    exit /b 1
)

:: Check Python 3.9 or higher
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version)"') do set "PYTHON_VERSION=%%i"
echo ✅ Found Python !PYTHON_VERSION!

python -c "import sys; exit(0) if sys.version_info >= (3, 9) else exit(1)" >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.9 or higher is required. You have Python !PYTHON_VERSION!
    echo Please upgrade Python from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Check for FFmpeg
echo 🔍 Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg not found. FFmpeg is required for audio extraction.
    echo.
    echo Please install FFmpeg:
    echo 1. Download from: https://www.gyan.dev/ffmpeg/builds/
    echo 2. Choose "ffmpeg-release-essentials.zip"
    echo 3. Extract to C:\ffmpeg
    echo 4. Add C:\ffmpeg\bin to your PATH
    echo    - Press Windows key, type "environment"
    echo    - Click "Edit environment variables for your account"
    echo    - Edit "Path", add "C:\ffmpeg\bin"
    echo 5. Restart your computer
    echo.
    echo After installing FFmpeg, run this script again.
    echo.
    pause
    exit /b 1
) else (
    echo ✅ FFmpeg is already installed
)

:: Create virtual environment
echo 🔧 Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

:: Activate virtual environment and install packages
echo 📦 Installing Python packages...
call venv\Scripts\activate.bat

:: Upgrade pip first
python -m pip install --upgrade pip

:: Install requirements
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ Python packages installed
) else (
    echo ❌ requirements.txt not found in %SCRIPT_DIR%
    echo Please make sure you're running this script from the HinglishCaps folder.
    echo.
    pause
    exit /b 1
)

echo.
echo ════════════════════════════════════════════════════════════════════════════════
echo 🎉 INSTALLATION COMPLETE!
echo ════════════════════════════════════════════════════════════════════════════════
echo.
echo HinglishCaps is now ready to use!
echo.
echo The web interface will open in your browser automatically.
echo You can also run it manually anytime by:
echo 1. Opening Command Prompt
echo 2. Navigating to this folder: cd "%SCRIPT_DIR%"
echo 3. Running: venv\Scripts\activate ^&^& python app.py
echo.
echo For batch processing (multiple videos), use:
echo venv\Scripts\activate ^&^& python batch.py your-video.mp4
echo.
echo ════════════════════════════════════════════════════════════════════════════════

:: Launch the application
echo 🚀 Launching HinglishCaps...
echo Opening browser at http://localhost:7860
echo Press Ctrl+C in this window to stop the application
echo.
timeout /t 3 /nobreak >nul

:: Run the application
python app.py

:: If app closes, keep window open
if errorlevel 1 (
    echo.
    echo ❌ Application closed with an error.
    echo Please check the error message above.
    echo.
    pause
)
