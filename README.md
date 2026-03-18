# HinglishCaps

Auto-generate subtitles for Hindi, English, and Hinglish videos.
Outputs a standard `.srt` file you can import into any video editor.

Powered by [Oriserve/Whisper-Hindi2Hinglish-Apex](https://huggingface.co/Oriserve/Whisper-Hindi2Hinglish-Apex) — a Whisper checkpoint fine-tuned specifically for Hinglish (Hindi-English code-switching).

---

## What it does

Upload a video, click a button, get an `.srt` caption file back.

Under the hood it strips the audio with FFmpeg, runs it through the Apex model, converts the timestamped output to SRT format, and hands you the file. Works well with content that switches between Hindi and English — reels, vlogs, interviews, podcasts.

---

## Requirements

**System dependencies**

- Python 3.9 or higher
- FFmpeg installed and available in your PATH

Install FFmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html and add the bin folder to PATH
```

**Hardware**

- 4 GB RAM minimum (model loads to ~3 GB)
- No GPU required — runs entirely on CPU
- Apple Silicon (M1 / M2 / M3) works natively with no extra steps

---

## Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/cgchiraggupta/toolazytoaddcaptions.git
cd toolazytoaddcaptions

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Running the app

### Web Interface (app.py)

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate
python app.py
```

Then open your browser at `http://localhost:7860`

### Batch Processing CLI (batch.py)

For processing multiple videos at once:

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate

# Single video
python batch.py video.mp4

# Multiple videos
python batch.py clip1.mp4 clip2.mov clip3.mkv

# Entire folder of videos
python batch.py /path/to/videos/

# Mix of files and folders
python batch.py intro.mp4 /path/to/more/videos/

# Custom output folder
python batch.py /videos/ --output /subtitles/
```

---

## Usage

### Web Interface

1. Open the app in your browser at `http://localhost:7860`
2. Upload a video file using the upload area
3. Click **Generate Captions**
4. The progress bar will appear — wait for it to complete
5. Download the `.srt` file once it shows up

### Batch Processing CLI

The batch processing script (`batch.py`) provides a command-line interface for processing multiple videos efficiently:

**Features:**
- Process individual video files or entire folders
- Shared model caching (loads once for entire batch)
- Progress tracking with timing information
- Success/failure reporting
- Custom output directory support

**Supported video formats:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.m4v`, `.ts`, `.wmv`

**Output:**
- Generates `.srt` files with the same name as input videos
- Saves to same directory as input videos by default
- Can specify custom output directory with `--output` flag

**Importing the SRT into your editor**

| Editor | How to import |
|---|---|
| CapCut | Text > Auto Captions > Import |
| DaVinci Resolve | Timeline > Import Subtitle |
| Premiere Pro | File > Import |
| Final Cut Pro | File > Import > Captions |
| iMovie | Not supported — use CapCut instead |

---

## First run

The first time you run the app (either web interface or batch CLI), the model (~1.5 GB) downloads automatically from HuggingFace. This happens once. After that it is cached permanently at `~/.cache/huggingface/` and is never downloaded again.

During the download the progress bar will sit at 30% and the status will read "Transcribing". That is normal — the download and transcription both happen inside the same blocking call with no intermediate progress updates. Do not close the tab or kill the process.

On a decent connection the download takes 3 to 8 minutes. Transcription starts immediately after.

---

## Project structure

```
toolazytoaddcaptions/
├── app.py              # Web interface — audio extraction, transcription, SRT generation, Gradio UI
├── batch.py            # Batch processing CLI for multiple videos
├── requirements.txt    # Python dependencies
└── README.md
```

The old openai-whisper based implementation is preserved inside `app.py` as commented-out code. Each replaced section is clearly marked with `── OLD` and `── END OLD` so you can find and restore it if needed.

---

## How it works

### Web Interface Flow
```
Video file
    |
    v
FFmpeg  -->  extracts mono 16 kHz WAV audio
    |
    v
Apex model  -->  transcribes audio with word-level timestamps
    |
    v
Python  -->  converts segments to SRT format
    |
    v
captions.srt  -->  ready to import into your editor
```

### Batch Processing Flow
```
Multiple video files/folders
    |
    v
Collect all videos  -->  filter by supported formats
    |
    v
For each video:
    ├── Extract audio with FFmpeg
    ├── Transcribe with cached Apex model
    ├── Generate SRT with timestamps
    └── Save to output directory
    |
    v
Summary report with success/failure count
```

---

## Model

**Oriserve/Whisper-Hindi2Hinglish-Apex**
HuggingFace: https://huggingface.co/Oriserve/Whisper-Hindi2Hinglish-Apex

A Whisper medium checkpoint fine-tuned on Hinglish speech data. The base Whisper model can get confused by code-switching — it may randomly switch between Hindi script and English script mid-sentence, or transliterate instead of transcribe. Apex is trained to handle this natively and keeps output consistent.

- File size: ~1.5 GB
- Downloaded automatically on first run
- Cached at `~/.cache/huggingface/hub/`
- Shared cache between web interface and batch CLI

---

## Performance

All numbers are approximate and depend on video length and background load.

| Machine | Time per minute of video |
|---|---|
| Apple M1 8 GB (CPU) | 1 to 2 minutes |
| Apple M2 / M3 (CPU) | 45 to 90 seconds |
| Modern Intel / AMD (CPU) | 2 to 4 minutes |

**Batch Processing Notes:**
- Model loads once and stays cached in memory for entire batch
- Each video is processed sequentially
- Total time = sum of individual video processing times
- Memory usage remains constant after initial model load

There is no GPU acceleration in the current setup. If you have an NVIDIA GPU, change `device = "cpu"` to `device = "cuda"` in `load_model()` inside both `app.py` and `batch.py` and transcription will be significantly faster.

---

## Dependencies

| Package | Purpose |
|---|---|
| `gradio` | Web UI (app.py only) |
| `torch` | Model runtime |
| `transformers` | HuggingFace model loading and pipeline |
| `accelerate` | Optimized model loading |
| `ffmpeg-python` | Audio extraction from video |
| `argparse` | CLI argument parsing (batch.py only) |

---

## Code Architecture

### app.py
- Single-file Gradio web application
- Real-time progress updates
- File upload/download handling
- Automatic port selection (7860+)

### batch.py
- Command-line interface with comprehensive help
- Modular functions for audio extraction, transcription, SRT generation
- Error handling with detailed error messages
- Progress reporting with emoji indicators
- Shared model caching system

**Key Functions in batch.py:**
- `load_model()`: Cached model loader (shared with app.py)
- `extract_audio()`: FFmpeg-based audio extraction
- `transcribe()`: Transcription with timestamp estimation
- `process_video()`: Complete pipeline for single video
- `run_batch()`: Batch coordinator with statistics
- `collect_videos()`: File/folder collection with format filtering

---

## Notes

- The web app auto-selects a free port starting from 7860. If 7860 is occupied it moves to 7861, and so on.
- Output `.srt` files are written to your system's temp directory (web) or specified output directory (batch) and served through Gradio's file cache.
- Batch processing uses the same model cache as the web interface — if you've already downloaded the model via the web app, batch processing will use the cached version.
- Tested on macOS with Python 3.14 and Gradio 6.
- The batch CLI includes emoji indicators for better visual feedback during long-running processes.

---

## Troubleshooting

**Common Issues:**

1. **"ModuleNotFoundError: No module named 'ffmpeg'"**
   - Make sure you've activated the virtual environment: `source venv/bin/activate`
   - Install requirements: `pip install -r requirements.txt`

2. **"FFmpeg not found"**
   - Install FFmpeg system-wide (see Requirements section)
   - Ensure FFmpeg is in your PATH

3. **Batch processing is slow**
   - First run downloads the model (~1.5 GB)
   - Subsequent runs use cached model
   - Consider using GPU if available (change `device = "cpu"` to `device = "cuda"`)

4. **No speech detected**
   - Check if your video has audible dialogue
   - Model is optimized for Hindi, English, and Hinglish speech

5. **Port already in use**
   - The web app will automatically try the next port (7861, 7862, etc.)
   - Check console output for the actual port being used

---

## License

This project is open source and available for personal and commercial use.