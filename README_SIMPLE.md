# HinglishCaps - Simple Installation

## 🚀 Quick Start (For Everyone)

### **For Mac Users:**
1. **Download** the HinglishCaps folder
2. **Double-click** `install-mac.sh`
3. **Follow the instructions** in Terminal
4. **That's it!** The web interface opens automatically

### **For Windows Users:**
1. **Download** the HinglishCaps folder  
2. **Double-click** `install-windows.bat`
3. **Follow the instructions** in Command Prompt
4. **That's it!** The web interface opens automatically

## 📱 What Happens After Installation

### **Web Interface (Recommended for most users):**
- Opens at `http://localhost:7860`
- Upload videos, get SRT files
- User-friendly interface

### **Batch Processing (For multiple videos):**
```bash
# After installation, open Terminal/Command Prompt:
cd /path/to/hinglishcaps

# Mac:
source venv/bin/activate
python batch.py video1.mp4 video2.mov

# Windows:
venv\Scripts\activate
python batch.py video1.mp4 video2.mov
```

## 🛠️ Manual Installation (If scripts don't work)

### **1. Install Python 3.9+**
- **Mac:** Already installed or get from [python.org](https://python.org)
- **Windows:** Download from [python.org](https://python.org) - **CHECK "Add Python to PATH"**

### **2. Install FFmpeg**
- **Mac:** `brew install ffmpeg` in Terminal
- **Windows:** Download from [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/)

### **3. Run HinglishCaps**
```bash
# Navigate to HinglishCaps folder
cd /path/to/hinglishcaps

# Create virtual environment
python -m venv venv

# Activate it
# Mac: source venv/bin/activate
# Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Run web interface
python app.py

# Or run batch processing
python batch.py your-video.mp4
```

## ❓ Need Help?

### **Common Issues:**

**"Python not found"**
- Windows: Reinstall Python, check "Add to PATH"
- Mac: Install Python from python.org

**"FFmpeg not found"**
- Follow FFmpeg installation instructions above
- Restart computer after adding to PATH

**Script closes immediately**
- Open Terminal/Command Prompt first
- Navigate to folder: `cd /path/to/hinglishcaps`
- Run script: `./install-mac.sh` or `install-windows.bat`

## 🌐 Online Version

Don't want to install anything? Use the online version:
**https://huggingface.co/spaces/Ppreyy/hinglishcaptions**

## 📞 Support

- **GitHub Issues:** Report problems
- **Email:** cg077593@gmail.com
- **Response time:** 24-48 hours

---

**That's all!** Double-click the installer for your system and start creating captions in minutes. 🎬