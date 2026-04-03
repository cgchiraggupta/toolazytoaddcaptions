#!/usr/bin/env python3
"""
HinglishCaps - Local Web Interface (requires running locally)

Note: This web interface requires more memory than available on
Hugging Face Spaces free tier. Run it on your local machine instead.
"""

print("=" * 60)
print("HinglishCaps - Local Web Interface")
print("=" * 60)
print("\n⚠️  This web interface requires running on your local machine.")
print("   It won't work on Hugging Face Spaces due to memory constraints.")
print("\n📋 To run this locally:")
print("1. Install full dependencies:")
print("   pip install -r requirements_full.txt")
print("\n2. Make sure FFmpeg is installed")
print("\n3. Run the web app:")
print("   python app_full.py")
print("\n💡 For command-line usage (recommended):")
print("   python simple_caps.py --help")
print("   python setup.py")

# Try to import gradio to check if dependencies are installed
try:
    import gradio as gr
    print("\n✅ Gradio is installed. You can run the web app locally.")
except ImportError:
    print("\n❌ Gradio is not installed. Install with:")
    print("   pip install -r requirements_full.txt")