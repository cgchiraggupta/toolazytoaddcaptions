#!/usr/bin/env python3
"""
HinglishCaps - Auto Captions for Hindi/English Videos (Windows Version)

Usage for Windows:
1. Install FFmpeg: Download from https://ffmpeg.org/download.html
2. Add FFmpeg to PATH
3. Install Python dependencies: pip install -r requirements.txt
4. Run: python run_windows.py --video "path\\to\\video.mp4"

For batch processing:
python run_windows.py --folder "path\\to\\videos" --output "path\\to\\output"
"""

import os
import sys
import argparse
import subprocess
import platform

def check_ffmpeg():
    """Check if FFmpeg is installed on Windows."""
    try:
        # Try running ffmpeg command
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True,
                              shell=True)
        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            return True
        else:
            print("❌ FFmpeg is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not in PATH")
        return False

def install_ffmpeg_windows():
    """Instructions for installing FFmpeg on Windows."""
    print("\n📦 Installing FFmpeg on Windows:")
    print("\n1. Download FFmpeg from: https://ffmpeg.org/download.html")
    print("   - Go to the Windows builds section")
    print("   - Download the 'release essentials' build")
    print("\n2. Extract the ZIP file to a folder, e.g., C:\\ffmpeg")
    print("\n3. Add FFmpeg to PATH:")
    print("   a. Press Windows key + X, select 'System'")
    print("   b. Click 'Advanced system settings'")
    print("   c. Click 'Environment Variables'")
    print("   d. Under 'System variables', find 'Path' and click 'Edit'")
    print("   e. Click 'New' and add the path to the bin folder, e.g., C:\\ffmpeg\\bin")
    print("   f. Click OK to close all dialogs")
    print("\n4. Open a new Command Prompt and run: ffmpeg -version")
    return False

def check_python_deps():
    """Check if Python dependencies are installed."""
    try:
        import torch
        import transformers
        import whisper
        import whisper_timestamped
        import ffmpeg
        print("✅ Python dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        return False

def install_python_deps():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    print("\nRun this command in Command Prompt or PowerShell:")
    print("   pip install -r requirements.txt")
    print("\nOr install individually:")
    print(
        "   pip install torch transformers openai-whisper faster-whisper "
        "whisper-timestamped ffmpeg-python"
    )
    return False

def check_python():
    """Check if Python is installed and accessible."""
    try:
        result = subprocess.run(['python', '--version'], 
                              capture_output=True, text=True,
                              shell=True)
        if result.returncode == 0:
            print(f"✅ Python is installed: {result.stdout.strip()}")
            return True
    except:
        pass
    
    # Try python3
    try:
        result = subprocess.run(['python3', '--version'], 
                              capture_output=True, text=True,
                              shell=True)
        if result.returncode == 0:
            print(f"✅ Python3 is installed: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("❌ Python is not installed or not in PATH")
    return False

def install_python_windows():
    """Instructions for installing Python on Windows."""
    print("\n🐍 Installing Python on Windows:")
    print("\n1. Download Python from: https://www.python.org/downloads/")
    print("2. Run the installer")
    print("3. IMPORTANT: Check 'Add Python to PATH' during installation")
    print("4. Complete the installation")
    print("5. Open a new Command Prompt and run: python --version")
    return False

def main():
    print("=" * 60)
    print("HinglishCaps - Auto Captions for Hindi/English Videos")
    print("Windows Version")
    print("=" * 60)
    
    # Check system
    system = platform.system()
    if system != 'Windows':
        print(f"⚠️  Warning: This script is for Windows, but you're running on {system}")
        print("Consider using the appropriate script for your platform.")
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    python_ok = check_python()
    if not python_ok:
        install_python_windows()
        print("\n⚠️  Please install Python first, then run this script again.")
        return
    
    ffmpeg_ok = check_ffmpeg()
    deps_ok = check_python_deps()
    
    if not ffmpeg_ok:
        install_ffmpeg_windows()
        print("\n⚠️  Please install FFmpeg first, then run this script again.")
        return
    
    if not deps_ok:
        install_python_deps()
        print("\n⚠️  Please install Python dependencies first, then run this script again.")
        return
    
    print("\n✅ All prerequisites are met!")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Generate captions for Hindi/English videos')
    parser.add_argument('--video', help='Path to a single video file')
    parser.add_argument('--folder', help='Path to folder containing videos')
    parser.add_argument('--output', help='Output directory for caption files', default='./captions')
    parser.add_argument('--word-level', action='store_true', 
                       help='Generate word-level timestamps')
    parser.add_argument('--words-per-line', type=int, default=2,
                       help='Words per line for word-level timestamps (default: 2)')
    
    args = parser.parse_args()

    if not args.video and not args.folder:
        print("\n❌ Please specify either --video or --folder")
        parser.print_help()
        return
    
    # Import and run the actual batch processor
    print("\n🚀 Starting caption generation...")
    
    try:
        # Import the batch processor
        import batch
        
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        if args.video:
            # Single video processing
            print(f"Processing single video: {args.video}")
            print("\n📝 For single video processing, use:")
            print(f'   python batch.py --video "{args.video}" --output "{args.output}"')
            if args.word_level:
                print(f"   --word-level --words-per-line {args.words_per_line}")
        
        elif args.folder:
            # Batch processing
            print(f"Processing folder: {args.folder}")
            print("\n📝 For batch processing, use:")
            print(f'   python batch.py --folder "{args.folder}" --output "{args.output}"')
            if args.word_level:
                print(f"   --word-level --words-per-line {args.words_per_line}")
        
        print("\n💡 Tip: Run 'python batch.py --help' for all available options")
        
    except ImportError:
        print("\n❌ Could not import batch processor")
        print("Make sure you're in the correct directory and all dependencies are installed.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
