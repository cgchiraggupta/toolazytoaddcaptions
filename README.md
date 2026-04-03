# HinglishCaps

HinglishCaps is a local-first captioning tool for Hindi, English, and Hinglish videos.

It generates subtitle files you can import into editors like CapCut, DaVinci Resolve, Premiere Pro, and Final Cut Pro.

The app is designed to run on your own machine because the transcription model is heavy and works best with local CPU/RAM access.

## What it does

- Generate captions for a single video
- Process multiple videos in one batch
- Export standard `.srt` files
- Export Premiere Pro-friendly subtitle formats
- Optionally generate shorter word-level subtitle chunks

Powered by [Oriserve/Whisper-Hindi2Hinglish-Apex](https://huggingface.co/Oriserve/Whisper-Hindi2Hinglish-Apex), a Whisper checkpoint fine-tuned for Hinglish and Indian speech patterns.

## Recommended way to use it

Run the local web app:

```bash
python app_full.py
```

Then open:

```text
http://localhost:7860
```

This is the best experience for most users.

## System requirements

- Python 3.9 or newer
- FFmpeg installed and available in `PATH`
- 8 GB RAM minimum
- Internet connection on first run to download the model

## macOS setup

### 1. Install Python

If you do not already have a recent Python:

- Download from [python.org](https://www.python.org/downloads/macos/)

Check it:

```bash
python3 --version
```

### 2. Install FFmpeg

Using Homebrew:

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
python3 -m venv venv
source venv/bin/activate
```

### 5. Install dependencies

For the web app:

```bash
pip install -r requirements_full.txt
```

For command-line only usage:

```bash
pip install -r requirements.txt
```

### 6. Launch the app

```bash
python app_full.py
```

Open:

```text
http://localhost:7860
```

## Windows setup

### 1. Install Python

- Download from [python.org](https://www.python.org/downloads/windows/)
- During installation, make sure you check `Add Python to PATH`

Check it in Command Prompt or PowerShell:

```powershell
python --version
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
python -m venv venv
venv\Scripts\activate
```

### 5. Install dependencies

For the web app:

```powershell
pip install -r requirements_full.txt
```

For command-line only usage:

```powershell
pip install -r requirements.txt
```

### 6. Launch the app

```powershell
python app_full.py
```

Open:

```text
http://localhost:7860
```

## Easier installers

This repo also includes:

- macOS: [`install-mac.sh`](install-mac.sh)
- Windows: [`install-windows.bat`](install-windows.bat)

These are meant to help users set things up faster, but the manual instructions above are the most reliable reference.

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

### `ffmpeg not found`

- Make sure FFmpeg is installed
- Make sure it is added to `PATH`
- Restart Terminal, Command Prompt, or PowerShell after installing it

### `python not found`

- Reinstall Python and ensure it is added to `PATH`
- On macOS, try `python3` if `python` is not available

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

MIT. See [`LICENSE`](LICENSE).
