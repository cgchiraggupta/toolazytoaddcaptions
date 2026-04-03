#!/usr/bin/env python3
# Example: Process a single video
import subprocess

# Process one video
subprocess.run([
    '/Users/apple/Downloads/toolazytoaddcaptions/venv/bin/python', 'simple_caps.py',
    'your_video.mp4',
    '--output', './captions',
    '--format', 'srt'
])
