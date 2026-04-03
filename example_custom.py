#!/usr/bin/env python3
# Example: Custom processing
import subprocess

# Process specific videos with custom settings
subprocess.run([
    '/Users/apple/Downloads/toolazytoaddcaptions/venv/bin/python', 'simple_caps.py',
    'video1.mp4', 'video2.mov', 'video3.avi',
    '--output', './custom_output',
    '--format', 'pr-text',  # Premiere Pro text format
    '--word-level',
    '--words', '3'  # 3 words per line
])
