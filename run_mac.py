#!/usr/bin/env python3
"""
HinglishCaps - Auto Captions for Hindi/English Videos (macOS Version)

Usage for macOS:
1. Install FFmpeg: brew install ffmpeg
2. Install Python dependencies: pip install -r requirements.txt
3. Run: python run_mac.py --video path/to/video.mp4

For batch processing:
python run_mac.py --folder path/to/videos --output path/to/output
"""

import os
import sys
import argparse
import subprocess
import platform

def check_ffmpeg():
    """Check if FFmpeg is installed on macOS."""
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

def install_ffmpeg_mac():
    """Install FFmpeg on macOS using Homebrew."""
    print("\n📦 Installing FFmpeg using Homebrew...")
    print("If you don't have Homebrew installed, visit: https://brew.sh")
    print("\nRun these commands in Terminal:")
    print("1. Install Homebrew (if not installed):")
    print('   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
    print("\n2. Install FFmpeg:")
    print("   brew install ffmpeg")
    print("\n3. Verify installation:")
    print("   ffmpeg -version")
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
    print("\nRun this command in Terminal:")
    print("   pip install -r requirements.txt")
    print("\nOr install individually:")
    print("   pip install torch transformers openai-whisper whisper-timestamped ffmpeg-python")
    return False

def main():
    print("=" * 60)
    print("HinglishCaps - Auto Captions for Hindi/English Videos")
    print("macOS Version")
    print("=" * 60)
    
    # Check system
    system = platform.system()
    if system != 'Darwin':
        print(f"⚠️  Warning: This script is for macOS, but you're running on {system}")
        print("Consider using the appropriate script for your platform.")
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    ffmpeg_ok = check_ffmpeg()
    deps_ok = check_python_deps()
    
    if not ffmpeg_ok:
        install_ffmpeg_mac()
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
    parser.add_argument('--format', choices=['srt', 'pr-srt', 'pr-text'], 
                       default='srt', help='Output format (default: srt)')
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
            # We need to adapt batch.py for single file processing
            # For now, just show instructions
            print("\n📝 For single video processing, use:")
            print(f"   python batch.py --video \"{args.video}\" --output \"{args.output}\"")
            print(f"   --format {args.format}")
            if args.word_level:
                print(f"   --word-level --words-per-line {args.words_per_line}")
        
        elif args.folder:
            # Batch processing
            print(f"Processing folder: {args.folder}")
            print("\n📝 For batch processing, use:")
            print(f"   python batch.py --folder \"{args.folder}\" --output \"{args.output}\"")
            print(f"   --format {args.format}")
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