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

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate
python app.py
```

Then open your browser at `http://localhost:7860`

---

## Usage

1. Open the app in your browser
2. Upload a video file using the upload area
3. Click **Generate Captions**
4. The progress bar will appear — wait for it to complete
5. Download the `.srt` file once it shows up

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

The first time you click Generate Captions, the model (~1.5 GB) downloads automatically from HuggingFace. This happens once. After that it is cached permanently at `~/.cache/huggingface/` and is never downloaded again.

During the download the progress bar will sit at 30% and the status will read "Transcribing". That is normal — the download and transcription both happen inside the same blocking call with no intermediate progress updates. Do not close the tab or kill the process.

On a decent connection the download takes 3 to 8 minutes. Transcription starts immediately after.

---

## Project structure

```
toolazytoaddcaptions/
├── app.py              # everything — audio extraction, transcription, SRT generation, Gradio UI
├── requirements.txt    # Python dependencies
└── README.md
```

The old openai-whisper based implementation is preserved inside `app.py` as commented-out code. Each replaced section is clearly marked with `── OLD` and `── END OLD` so you can find and restore it if needed.

---

## How it works

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

---

## Model

**Oriserve/Whisper-Hindi2Hinglish-Apex**
HuggingFace: https://huggingface.co/Oriserve/Whisper-Hindi2Hinglish-Apex

A Whisper medium checkpoint fine-tuned on Hinglish speech data. The base Whisper model can get confused by code-switching — it may randomly switch between Hindi script and English script mid-sentence, or transliterate instead of transcribe. Apex is trained to handle this natively and keeps output consistent.

- File size: ~1.5 GB
- Downloaded automatically on first run
- Cached at `~/.cache/huggingface/hub/`

---

## Performance

All numbers are approximate and depend on video length and background load.

| Machine | Time per minute of video |
|---|---|
| Apple M1 8 GB (CPU) | 1 to 2 minutes |
| Apple M2 / M3 (CPU) | 45 to 90 seconds |
| Modern Intel / AMD (CPU) | 2 to 4 minutes |

There is no GPU acceleration in the current setup. If you have an NVIDIA GPU, change `device = "cpu"` to `device = "cuda"` in `load_model()` inside `app.py` and transcription will be significantly faster.

---

## Dependencies

| Package | Purpose |
|---|---|
| `gradio` | Web UI |
| `torch` | Model runtime |
| `transformers` | HuggingFace model loading and pipeline |
| `accelerate` | Optimized model loading |
| `ffmpeg-python` | Audio extraction from video |

---

## Notes

- The app auto-selects a free port starting from 7860. If 7860 is occupied it moves to 7861, and so on.
- Output `.srt` files are written to your system's temp directory and served through Gradio's file cache.
- Tested on macOS with Python 3.14 and Gradio 6.