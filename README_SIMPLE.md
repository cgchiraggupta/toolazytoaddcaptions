# HinglishCaps - Quick Local Setup

This tool is meant to run locally on your computer.

## macOS

1. Install Python from [python.org](https://www.python.org/downloads/macos/) if needed
2. Install Homebrew if needed, then run:

```bash
brew install ffmpeg
```

3. Open Terminal in the project folder
4. Run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_full.txt
python app_full.py
```

5. Open:

```text
http://localhost:7860
```

## Windows

1. Install Python from [python.org](https://www.python.org/downloads/windows/) and check `Add Python to PATH`
2. Install FFmpeg and add it to `Path`
3. Open Command Prompt or PowerShell in the project folder
4. Run:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements_full.txt
python app_full.py
```

5. Open:

```text
http://localhost:7860
```

## If you only want command-line mode

```bash
python simple_caps.py your_video.mp4
```

## First run

The first run downloads the transcription model, so it takes longer.

## Help

See the full setup guide in [`README.md`](README.md).
