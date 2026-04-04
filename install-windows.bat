@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================================================
echo                        HINGLISHCAPS WINDOWS INSTALLER
echo ==========================================================================
echo.
echo Recommended Python version: 3.12
echo This installer will:
echo 1. Check for Python 3.12
echo 2. Check for FFmpeg
echo 3. Create a virtual environment
echo 4. Install web app dependencies
echo 5. Launch HinglishCaps locally
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Checking Python...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 was not found.
    echo Please install Python 3.12 from https://www.python.org/downloads/windows/
    echo During installation, check "Add Python to PATH"
    pause
    exit /b 1
)

echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg is required.
    echo.
    echo Install FFmpeg using one of these steps:
    echo 1. Download from https://www.gyan.dev/ffmpeg/builds/
    echo 2. Extract to C:\ffmpeg
    echo 3. Add C:\ffmpeg\bin to your PATH
    echo 4. Restart Command Prompt and run this installer again
    echo.
    pause
    exit /b 1
)

echo Creating virtual environment...
if exist "venv" rmdir /s /q "venv"
py -3.12 -m venv venv
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements_full.txt

echo.
echo Installation complete.
echo Open http://127.0.0.1:7860 in your browser.
echo Press Ctrl+C in this window to stop the app.
echo.

python app_full.py
