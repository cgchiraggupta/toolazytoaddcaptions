#!/usr/bin/env python3
"""
HinglishCaps - Auto Captions for Hindi/English Videos (Linux Version)

Usage for Linux:
1. Install FFmpeg: sudo apt install ffmpeg (Ubuntu/Debian)
2. Install Python dependencies: pip install -r requirements.txt
3. Run: python run_linux.py --video path/to/video.mp4

For batch processing:
python run_linux.py --folder path/to/videos --output path/to/output
"""

import os
import sys
import argparse
import subprocess
import platform

def check_ffmpeg():
    """Check if FFmpeg is installed on Linux."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            return True
        else:
            print("❌ FFmpeg is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not in PATH")
        return False

def install_ffmpeg_linux():
    """Install FFmpeg on Linux."""
    print("\n📦 Installing FFmpeg on Linux:")
    
    # Detect distribution
    try:
        with open('/etc/os-release', 'r') as f:
            os_release = f.read()
            if 'ubuntu' in os_release.lower() or 'debian' in os_release.lower():
                print("\nFor Ubuntu/Debian, run:")
                print("   sudo apt update")
                print("   sudo apt install ffmpeg")
            elif 'fedora' in os_release.lower():
                print("\nFor Fedora, run:")
                print("   sudo dnf install ffmpeg")
            elif 'arch' in os_release.lower():
                print("\nFor Arch Linux, run:")
                print("   sudo pacman -S ffmpeg")
            else:
                print("\nPlease install FFmpeg using your package manager.")
                print("Common commands:")
                print("  Debian/Ubuntu: sudo apt install ffmpeg")
                print("  Fedora: sudo dnf install ffmpeg")
                print("  Arch: sudo pacman -S ffmpeg")
    except:
        print("\nPlease install FFmpeg using your package manager.")
    
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
    print("\nRun this command:")
    print("   pip install -r requirements.txt")
    print("\nOr install individually:")
    print(
        "   pip install torch transformers openai-whisper faster-whisper "
        "whisper-timestamped ffmpeg-python"
    )
    
    # Check if pip is installed
    try:
        subprocess.run(['pip', '--version'], capture_output=True)
    except:
        print("\n⚠️  pip might not be installed. Install it with:")
        print("   sudo apt install python3-pip  # Ubuntu/Debian")
        print("   sudo dnf install python3-pip  # Fedora")
        print("   sudo pacman -S python-pip     # Arch")
    
    return False

def main():
    print("=" * 60)
    print("HinglishCaps - Auto Captions for Hindi/English Videos")
    print("Linux Version")
    print("=" * 60)
    
    # Check system
    system = platform.system()
    if system != 'Linux':
        print(f"⚠️  Warning: This script is for Linux, but you're running on {system}")
        print("Consider using the appropriate script for your platform.")
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    ffmpeg_ok = check_ffmpeg()
    deps_ok = check_python_deps()
    
    if not ffmpeg_ok:
        install_ffmpeg_linux()
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
