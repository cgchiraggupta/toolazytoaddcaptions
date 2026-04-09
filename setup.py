#!/usr/bin/env python3
"""
HinglishCaps Setup Script

This script helps you set up HinglishCaps on your system.
Run: python setup.py
"""

import os
import sys
import platform
import subprocess

PYTHON_CMD = sys.executable

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def run_command(cmd, check=True):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"  ❌ Failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def check_python():
    """Check Python version."""
    print_header("Checking Python")
    
    python_version = sys.version_info
    print(f"Python version: {sys.version}")
    
    if python_version.major == 3 and python_version.minor >= 8:
        print("✅ Python 3.8+ is installed")
        return True
    else:
        print("❌ Python 3.8 or higher is required")
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    print_header("Checking FFmpeg")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Extract version from output
            lines = result.stdout.split('\n')
            if lines:
                print(f"✅ FFmpeg is installed: {lines[0]}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ FFmpeg is not installed or not in PATH")
    return False

def install_ffmpeg():
    """Install FFmpeg based on platform."""
    system = platform.system()
    
    print_header(f"Installing FFmpeg on {system}")
    
    if system == 'Darwin':  # macOS
        print("To install FFmpeg on macOS:")
        print("1. Install Homebrew if not installed:")
        print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        print("\n2. Install FFmpeg:")
        print("   brew install ffmpeg")
        
    elif system == 'Windows':
        print("To install FFmpeg on Windows:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Extract to C:\\ffmpeg or similar")
        print("3. Add to PATH:")
        print("   - Press Win+X, select System")
        print("   - Advanced system settings > Environment Variables")
        print("   - Edit Path, add C:\\ffmpeg\\bin")
        
    elif system == 'Linux':
        print("To install FFmpeg on Linux:")
        
        # Try to detect distribution
        distro = "unknown"
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content:
                    distro = 'debian'
                    print("Run: sudo apt install ffmpeg")
                elif 'fedora' in content:
                    distro = 'fedora'
                    print("Run: sudo dnf install ffmpeg")
                elif 'arch' in content:
                    distro = 'arch'
                    print("Run: sudo pacman -S ffmpeg")
                else:
                    print("Use your package manager to install ffmpeg")
        except:
            print("Use your package manager to install ffmpeg")
    
    return False

def check_dependencies():
    """Check Python dependencies."""
    print_header("Checking Python Dependencies")
    
    required = [
        'torch',
        'transformers',
        'whisper',
        'faster_whisper',
        'whisper_timestamped',
        'ffmpeg',
    ]
    missing = []
    
    for dep in required:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep}")
            missing.append(dep)
    
    return len(missing) == 0, missing

def install_dependencies(missing):
    """Install missing dependencies."""
    print_header("Installing Dependencies")
    
    if not missing:
        print("✅ All dependencies are already installed")
        return True
    
    print(f"Missing: {', '.join(missing)}")
    print("\nInstalling dependencies...")
    
    # Try to install from requirements.txt first
    if os.path.exists('requirements.txt'):
        print("\nInstalling from requirements.txt...")
        if run_command(f'"{PYTHON_CMD}" -m pip install -r requirements.txt'):
            print("✅ Dependencies installed from requirements.txt")
            return True
    
    # Fallback: install individually
    print("\nInstalling dependencies individually...")
    
    # Map import names to pip names
    pip_names = {
        'torch': 'torch',
        'transformers': 'transformers',
        'whisper': 'openai-whisper',
        'faster_whisper': 'faster-whisper',
        'whisper_timestamped': 'whisper-timestamped',
        'ffmpeg': 'ffmpeg-python'
    }
    
    for dep in missing:
        pip_name = pip_names.get(dep, dep)
        print(f"Installing {pip_name}...")
        if run_command(f'"{PYTHON_CMD}" -m pip install {pip_name}'):
            print(f"  ✅ {pip_name}")
        else:
            print(f"  ❌ Failed to install {pip_name}")
            return False
    
    return True

def create_example_scripts():
    """Create example usage scripts."""
    print_header("Creating Example Scripts")
    
    examples = {
        'example_single.py': f'''#!/usr/bin/env python3
# Example: Process a single video
import subprocess

# Process one video
subprocess.run([
    {PYTHON_CMD!r}, 'simple_caps.py',
    'your_video.mp4',
    '--output', './captions'
])
''',
        
        'example_batch.py': f'''#!/usr/bin/env python3
# Example: Process multiple videos
import subprocess

# Process all videos in a folder
subprocess.run([
    {PYTHON_CMD!r}, 'simple_caps.py',
    'folder_with_videos/',
    '--output', './batch_captions',
    '--word-level'  # Word-level timestamps
])
''',
        
        'example_custom.py': f'''#!/usr/bin/env python3
# Example: Custom processing
import subprocess

# Process specific videos with custom settings
subprocess.run([
    {PYTHON_CMD!r}, 'simple_caps.py',
    'video1.mp4', 'video2.mov', 'video3.avi',
    '--output', './custom_output',
    '--word-level',
    '--words', '3'  # 3 words per line
])
'''
    }
    
    for filename, content in examples.items():
        with open(filename, 'w') as f:
            f.write(content)
        print(f"Created: {filename}")
    
    return True

def main():
    print_header("HinglishCaps Setup")
    print("This script will help you set up HinglishCaps on your system.")
    
    # Check Python
    if not check_python():
        print("\n❌ Please install Python 3.8 or higher first.")
        return
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    if not ffmpeg_ok:
        install_ffmpeg()
        print("\n⚠️  Please install FFmpeg first, then run setup again.")
        return
    
    # Check dependencies
    deps_ok, missing = check_dependencies()
    if not deps_ok:
        if not install_dependencies(missing):
            print("\n❌ Failed to install some dependencies.")
            print("You can try installing them manually:")
            print(
                "  pip install torch transformers openai-whisper faster-whisper "
                "whisper-timestamped ffmpeg-python"
            )
            return
    
    # Create example scripts
    create_example_scripts()
    
    print_header("Setup Complete! 🎉")
    print("\n✅ HinglishCaps is ready to use!")
    print("\n📖 Quick Start Guide:")
    print("1. Process a single video:")
    print("   python simple_caps.py your_video.mp4")
    print("\n2. Process all videos in a folder:")
    print("   python simple_caps.py folder_path/")
    print("\n3. Process specific videos:")
    print("   python simple_caps.py video1.mp4 video2.mov video3.avi")
    print("\n4. With word-level timestamps:")
    print("   python simple_caps.py video.mp4 --word-level --words 3")
    print("\n5. For Premiere Pro compatibility:")
    print("   python simple_caps.py video.mp4")
    print("\n📚 More examples in example_*.py files")
    print("\n💡 First run will download the AI model (~1.5 GB)")
    print("   Subsequent runs will be faster!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
