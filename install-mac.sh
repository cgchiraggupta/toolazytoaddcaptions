#!/bin/bash

set -e

echo "=========================================================================="
echo "                         HINGLISHCAPS MAC INSTALLER"
echo "=========================================================================="
echo ""
echo "Recommended Python version: 3.12"
echo "This installer will:"
echo "1. Check for Python 3.12"
echo "2. Check for FFmpeg"
echo "3. Create a virtual environment"
echo "4. Install web app dependencies"
echo "5. Launch HinglishCaps locally"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Checking Python..."
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
elif command -v python3 >/dev/null 2>&1; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PY_MINOR" -ge 10 ] && [ "$PY_MINOR" -le 12 ]; then
        PYTHON_BIN="$(command -v python3)"
    else
        echo "Python $(python3 --version 2>&1) found, but HinglishCaps currently supports Python 3.10 to 3.12 best."
        echo "Please install Python 3.12 and run again."
        echo "Homebrew: brew install python@3.12"
        echo "python.org: https://www.python.org/downloads/macos/"
        exit 1
    fi
else
    echo "Python 3.12 was not found."
    echo "Install it with one of these options:"
    echo "- brew install python@3.12"
    echo "- https://www.python.org/downloads/macos/"
    exit 1
fi

echo "Using $($PYTHON_BIN --version 2>&1)"

echo "Checking FFmpeg..."
if ! command -v ffmpeg >/dev/null 2>&1; then
    if ! command -v brew >/dev/null 2>&1; then
        echo "FFmpeg is required, and Homebrew was not found."
        echo "Install Homebrew first: https://brew.sh"
        exit 1
    fi
    echo "Installing FFmpeg with Homebrew..."
    brew install ffmpeg
fi

echo "Creating virtual environment..."
rm -rf venv
"$PYTHON_BIN" -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements_full.txt

echo ""
echo "Installation complete."
echo "Opening HinglishCaps at http://127.0.0.1:7860"
echo "Press Ctrl+C in this terminal to stop the app."
echo ""

python app_full.py
