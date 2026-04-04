# HinglishCaps - Quick Local Setup

HinglishCaps is meant to run locally on your computer.

## Recommended Python version

Use **Python 3.12**.

Avoid Python 3.13 or 3.14 for now. Some dependencies in the current stack can fail on those newer versions.

## Fastest setup for most people

### macOS

1. Install Python 3.12
   - Download from [python.org](https://www.python.org/downloads/macos/)
   - or install with Homebrew: `brew install python@3.12`
2. Install FFmpeg:

```bash
brew install ffmpeg
```

3. Open Terminal in the project folder and run:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_full.txt
python app_full.py
```

4. Open:

```text
http://127.0.0.1:7860
```

### Windows

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/windows/)
   - check `Add Python to PATH`
2. Install FFmpeg and add it to `Path`
3. Open Command Prompt or PowerShell in the project folder and run:

```powershell
py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements_full.txt
python app_full.py
```

4. Open:

```text
http://127.0.0.1:7860
```

## First run

The first run downloads the transcription model, so startup and the first processing job will take longer.

## Help

See the full guide in `README.md`.
