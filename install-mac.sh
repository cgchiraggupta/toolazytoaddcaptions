#!/bin/bash

# HinglishCaps - Mac Installer
# Double-click this file to install and run HinglishCaps

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                          HINGLISHCAPS INSTALLER"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "This will install HinglishCaps on your Mac. It will:"
echo "1. Check for Python 3.9+"
echo "2. Create a virtual environment"
echo "3. Install required packages"
echo "4. Check for FFmpeg"
echo "5. Launch the web interface"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python version
echo "🔍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "Please install Python 3.9 or later from: https://www.python.org/downloads/"
    echo "Then run this script again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Found Python $PYTHON_VERSION"

# Check if Python 3.9 or higher
if [[ $(python3 -c 'import sys; print(sys.version_info >= (3, 9))') != "True" ]]; then
    echo "❌ Python 3.9 or higher is required. You have Python $PYTHON_VERSION"
    echo "Please upgrade Python from: https://www.python.org/downloads/"
    exit 1
fi

# Check for FFmpeg
echo "🔍 Checking for FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Installing via Homebrew..."

    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not installed. FFmpeg is required for audio extraction."
        echo ""
        echo "To install Homebrew, run this command in Terminal:"
        echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        echo ""
        echo "Then run this installer again."
        exit 1
    fi

    echo "📦 Installing FFmpeg via Homebrew (this may take a minute)..."
    brew install ffmpeg
    echo "✅ FFmpeg installed successfully"
else
    echo "✅ FFmpeg is already installed"
fi

# Create virtual environment
echo "🔧 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install packages
echo "📦 Installing Python packages..."
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python packages installed"
else
    echo "❌ requirements.txt not found in $SCRIPT_DIR"
    echo "Please make sure you're running this script from the HinglishCaps folder."
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "🎉 INSTALLATION COMPLETE!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "HinglishCaps is now ready to use!"
echo ""
echo "The web interface will open in your browser automatically."
echo "You can also run it manually anytime by:"
echo "1. Opening Terminal"
echo "2. Navigating to this folder: cd \"$SCRIPT_DIR\""
echo "3. Running: source venv/bin/activate && python app.py"
echo ""
echo "For batch processing (multiple videos), use:"
echo "source venv/bin/activate && python batch.py your-video.mp4"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"

# Launch the application
echo "🚀 Launching HinglishCaps..."
echo "Opening browser at http://localhost:7860"
echo "Press Ctrl+C in Terminal to stop the application"
echo ""

# Wait a moment for user to read
sleep 2

# Run the application
python app.py
