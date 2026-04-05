#!/usr/bin/env python3
"""
Simple HinglishCaps - Easy-to-use script for generating captions

Usage:
  python simple_caps.py video.mp4
  python simple_caps.py folder_path
  python simple_caps.py video1.mp4 video2.mp4 video3.mp4

Options:
  --output DIR      Output directory (default: ./captions)
  --format FORMAT   Output format: srt, pr-srt, pr-text, vtt (default: srt)
  --word-level      Generate word-level timestamps
  --words N         Words per line for word-level (default: 2)
  --offset SEC      Shift subtitle timings (+ delays, - starts earlier)
"""

import os
import sys
import argparse
from pathlib import Path
import subprocess

def main():
    print("=" * 60)
    print("HinglishCaps - Simple Video Caption Generator")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(
        description='Generate captions for Hindi/English videos',
        usage='%(prog)s [VIDEO_FILE_OR_FOLDER] [options]'
    )
    
    parser.add_argument('inputs', nargs='+', 
                       help='Video files or folder path')
    parser.add_argument('--output', '-o', default='./captions',
                       help='Output directory (default: ./captions)')
    parser.add_argument('--format', '-f', choices=['srt', 'pr-srt', 'pr-text', 'vtt'],
                       default='srt', help='Output format (default: srt)')
    parser.add_argument('--word-level', '-w', action='store_true',
                       help='Generate word-level timestamps')
    parser.add_argument('--words', type=int, default=2,
                       help='Words per line for word-level (default: 2)')
    parser.add_argument('--offset', type=float, default=0.0,
                       help='Shift subtitle timings in seconds (+ delays, - starts earlier)')
    
    args = parser.parse_args()
    
    # Collect video files
    video_files = []
    
    for input_path in args.inputs:
        path = Path(input_path)
        
        if path.is_dir():
            # Add all video files from directory
            video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', 
                               '.flv', '.m4v', '.ts', '.wmv'}
            for ext in video_extensions:
                video_files.extend(path.glob(f'*{ext}'))
                video_files.extend(path.glob(f'*{ext.upper()}'))
        elif path.is_file():
            # Check if it's a video file
            video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', 
                               '.flv', '.m4v', '.ts', '.wmv'}
            if path.suffix.lower() in video_extensions:
                video_files.append(path)
        else:
            print(f"⚠️  Warning: {input_path} not found, skipping")
    
    if not video_files:
        print("❌ No video files found. Please provide valid video files or folder.")
        sys.exit(1)
    
    print(f"\n📁 Found {len(video_files)} video file(s):")
    for vf in video_files:
        print(f"  • {vf.name}")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📂 Output directory: {output_dir.absolute()}")
    
    # Check if batch.py exists
    if not Path('batch.py').exists():
        print("\n❌ Error: batch.py not found in current directory")
        print("Make sure you're in the HinglishCaps directory.")
        sys.exit(1)
    
    # Build command for batch.py
    cmd = [
        sys.executable, 'batch.py',
        *[str(video_file) for video_file in video_files],
        '--output', str(output_dir),
        '--format', args.format
    ]
    if args.word_level:
        cmd.extend(['--word-level', '--words-per-line', str(args.words)])
    if abs(args.offset) >= 1e-9:
        cmd.extend(['--offset-seconds', str(args.offset)])
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("\n⏳ This may take a while...")
    print("   First run will download the AI model (~1.5 GB)")
    print("   Subsequent runs will be faster")
    
    # Ask for confirmation
    response = input("\n👉 Press Enter to continue, or Ctrl+C to cancel: ")
    
    # Run the command
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\n✅ Done! Check the output directory for caption files.")
        else:
            print(f"\n❌ Process exited with code {result.returncode}")
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
