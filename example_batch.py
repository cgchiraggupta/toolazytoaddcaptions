#!/usr/bin/env python3
# Example: Process multiple videos
import subprocess

# Process all videos in a folder
subprocess.run([
    '/Users/apple/Downloads/toolazytoaddcaptions/venv/bin/python', 'simple_caps.py',
    'folder_with_videos/',
    '--output', './batch_captions',
    '--format', 'pr-srt',  # Premiere Pro format
    '--word-level'  # Word-level timestamps
])
