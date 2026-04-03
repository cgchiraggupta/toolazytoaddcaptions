#!/usr/bin/env python3
"""
Test script to verify HinglishCaps installation.
Run: python test_installation.py
"""

import sys
import os
import subprocess

def test_import(module_name):
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        return True, f"✅ {module_name}"
    except ImportError as e:
        return False, f"❌ {module_name}: {e}"

def test_command(cmd):
    """Test if a command runs successfully."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, f"✅ {cmd}"
        else:
            return False, f"❌ {cmd}: {result.stderr[:100]}"
    except Exception as e:
        return False, f"❌ {cmd}: {e}"

def main():
    print("=" * 60)
    print("HinglishCaps Installation Test")
    print("=" * 60)
    
    print("\n🔍 Testing Python imports...")
    
    # Test core imports
    imports = [
        'torch',
        'transformers',
        'whisper',
        'whisper_timestamped',
        'ffmpeg',
    ]
    
    all_ok = True
    for module in imports:
        ok, msg = test_import(module)
        print(f"  {msg}")
        if not ok:
            all_ok = False
    
    print("\n🔍 Testing system commands...")
    
    # Test FFmpeg
    ok, msg = test_command('ffmpeg -version')
    print(f"  {msg}")
    if not ok:
        all_ok = False
    
    # Test Python version
    ok, msg = test_command(f'"{sys.executable}" --version')
    print(f"  {msg}")
    
    print("\n🔍 Testing script files...")
    
    # Check if required scripts exist
    scripts = ['batch.py', 'simple_caps.py', 'setup.py']
    for script in scripts:
        if os.path.exists(script):
            print(f"  ✅ {script} exists")
        else:
            print(f"  ❌ {script} missing")
            all_ok = False
    
    print("\n" + "=" * 60)
    
    if all_ok:
        print("🎉 All tests passed! HinglishCaps is ready to use.")
        print("\n📖 Quick start:")
        print(f"  {sys.executable} simple_caps.py --help")
        print(f"  {sys.executable} setup.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\n💡 Try running:")
        print(f"  {sys.executable} setup.py")
        print("  pip install -r requirements.txt")

if __name__ == "__main__":
    main()
