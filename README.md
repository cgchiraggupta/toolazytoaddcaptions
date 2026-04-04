# HinglishCaps

HinglishCaps is a local-first captioning tool for Hindi, English, and Hinglish videos.

It generates subtitle files you can import into editors like CapCut, DaVinci Resolve, Premiere Pro, and Final Cut Pro.

This project is designed to run on your own machine. The transcription model is large, so local use is the most reliable path.

## What it does

- Generate captions for a single video
- Process multiple videos in one batch
- Export standard `.srt` files
- Export Premiere Pro-friendly subtitle formats
- Optionally generate shorter word-level subtitle chunks

Powered by [Oriserve/Whisper-Hindi2Hinglish-Apex](https://huggingface.co/Oriserve/Whisper-Hindi2Hinglish-Apex), a Whisper checkpoint fine-tuned for Hinglish and Indian speech patterns.

## Important: use Python 3.12

For the current dependency stack, the recommended version is **Python 3.12**.

Please avoid:
- Python 3.13
- Python 3.14

Those newer versions can fail during dependency installation or app startup.

## Easiest way to use HinglishCaps

Run the local web app:

```bash
python app_full.py
```

Then open:

```text
http://127.0.0.1:7860
```

## System requirements

- Python 3.12
- FFmpeg installed and available in `PATH`
- 8 GB RAM minimum
- Internet connection on first run to download the model

## macOS setup

### 1. Install Python 3.12

Option A: python.org
- Download Python 3.12 from [python.org](https://www.python.org/downloads/macos/)

Option B: Homebrew

```bash
brew install python@3.12
```

Check it:

```bash
python3.12 --version
```

### 2. Install FFmpeg

```bash
brew install ffmpeg
```

Check it:

```bash
ffmpeg -version
```

### 3. Download this project

```bash
git clone https://github.com/cgchiraggupta/toolazytoaddcaptions.git
cd toolazytoaddcaptions
```

### 4. Create a virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 5. Install dependencies

For the web app:

```bash
pip install --upgrade pip
pip install -r requirements_full.txt
```

For command-line only usage:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Launch the app

```bash
python app_full.py
```

Open:

```text
http://127.0.0.1:7860
```

## Windows setup

### 1. Install Python 3.12

- Download **Python 3.12** from [python.org](https://www.python.org/downloads/windows/)
- During installation, check `Add Python to PATH`

Check it:

```powershell
py -3.12 --version
```

### 2. Install FFmpeg

Option A: manual install

- Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) or [Gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/)
- Extract it to something like `C:\ffmpeg`
- Add `C:\ffmpeg\bin` to your system `Path`

Check it:

```powershell
ffmpeg -version
```

### 3. Download this project

```powershell
git clone https://github.com/cgchiraggupta/toolazytoaddcaptions.git
cd toolazytoaddcaptions
```

### 4. Create a virtual environment

```powershell
py -3.12 -m venv venv
venv\Scripts\activate
```

### 5. Install dependencies

For the web app:

```powershell
python -m pip install --upgrade pip
pip install -r requirements_full.txt
```

For command-line only usage:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Launch the app

```powershell
python app_full.py
```

Open:

```text
http://127.0.0.1:7860
```

## Installers

This repo also includes:

- `install-mac.sh`
- `install-windows.bat`

These are intended to guide users into the correct setup path, but the manual instructions above are the main reference.

## How to use the web app

### Single video

1. Open the `Single Video` tab
2. Upload one video
3. Choose whether you want word-level timestamps
4. Pick the output format
5. Click `Generate Captions`
6. Download the generated subtitle file

### Batch processing

1. Open the `Batch Processing` tab
2. Upload multiple videos
3. Choose your caption settings
4. Click `Process All Videos`
5. Download the ZIP file with all caption outputs

## Output formats

- `srt`: Standard subtitle format, works in most editors
- `pr-srt`: Premiere Pro-friendly SRT output
- `pr-text`: Text export for Premiere workflows

## Command-line usage

If you prefer terminal usage:

```bash
python simple_caps.py your_video.mp4
```

Multiple files:

```bash
python simple_caps.py video1.mp4 video2.mov video3.avi
```

A whole folder:

```bash
python simple_caps.py ./videos
```

With custom options:

```bash
python simple_caps.py video.mp4 --output ./captions --format pr-srt --word-level --words 2
```

## First run note

The first run downloads the model, which is roughly 1.5 GB. That run will be slower.

After that, the model is cached and future runs are faster.

## Troubleshooting

### `tokenizers` build error or strange install failures

This usually means you are using the wrong Python version.

Use **Python 3.12** and recreate the virtual environment.

### `ffmpeg not found`

- Make sure FFmpeg is installed
- Make sure it is added to `PATH`
- Restart Terminal, Command Prompt, or PowerShell after installing it

### `python not found`

- Reinstall Python 3.12 and ensure it is added to `PATH`
- On macOS, use `python3.12`
- On Windows, use `py -3.12`

### `ModuleNotFoundError`

Install dependencies inside the active virtual environment:

```bash
pip install -r requirements_full.txt
```

### App is slow on first run

This is expected because the model downloads and initializes the first time.

### Out of memory or crashes

- Close other heavy apps
- Process fewer files at once
- Make sure the machine has enough available RAM

## Supported editors

- CapCut
- DaVinci Resolve
- Adobe Premiere Pro
- Final Cut Pro
- Any editor that can import `.srt`

## License

MIT. See `LICENSE`.
