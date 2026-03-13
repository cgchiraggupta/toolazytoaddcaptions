# HinglishCaps ✦
Auto-generate subtitles for Hindi · English · Hinglish videos using OpenAI Whisper.
Outputs a standard `.SRT` file you can import into any video editor.

---

## Setup (one-time)

### Prerequisites
- Python 3.9+
- **FFmpeg** installed on your system (required for audio extraction)

Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows — download from https://ffmpeg.org/download.html and add to PATH
```

### Install Python dependencies
```bash
cd hinglish-captions
pip install -r requirements.txt
```

> **Apple Silicon (M1/M2/M3)?** PyTorch works natively. No extra steps needed.
> **NVIDIA GPU?** Replace `torch` in requirements.txt with the CUDA build from https://pytorch.org/get-started/locally/ for 5-10× faster transcription.

---

## Run
```bash
python app.py
```
Open your browser at **http://localhost:7860**

---

## How it works

```
Video File
    │
    ▼
[FFmpeg] ──► Extracts mono 16kHz WAV audio
    │
    ▼
[Whisper] ──► AI transcription with timestamps
    │           (set language hint to "hi" for Hinglish)
    ▼
[Python] ──► Converts segments → SRT format
    │
    ▼
  captions.srt  ──► Import into your video editor ✓
```

## Model Size Guide

| Model  | Size   | Speed  | Accuracy | Best for                         |
|--------|--------|--------|----------|----------------------------------|
| tiny   | 39MB   | ⚡⚡⚡⚡ | ★★☆☆☆    | Quick tests                      |
| base   | 74MB   | ⚡⚡⚡   | ★★★☆☆    | Short clips, good starting point |
| small  | 244MB  | ⚡⚡     | ★★★★☆    | Most Hinglish content ← sweet spot |
| medium | 769MB  | ⚡       | ★★★★★    | Long videos, heavy code-switching |
| large  | 1.5GB  | 🐢      | ★★★★★+   | Maximum accuracy                 |

**Recommendation:** Start with `small` for Hinglish. It handles code-switching very well.

## Language Hint

- `auto` — Whisper detects language automatically. Can get confused with Hinglish.
- `hi` — Forces Hindi mode. Whisper will preserve Hindi script AND keep English words
  in English script. **Best for Hinglish** reels/videos.
- `en` — Forces English mode. English only.

## Importing SRT into Video Editors

- **CapCut** → Text → Auto Captions → Import → choose `.srt`
- **DaVinci Resolve** → Timeline → Import Subtitle
- **Premiere Pro** → File → Import → select `.srt`
- **Final Cut Pro** → File → Import → Captions
- **iMovie** → Doesn't support SRT natively (use CapCut instead)

## Want even better Hinglish accuracy?

Swap the Whisper model for a fine-tuned Hindi version from Hugging Face.
Search for: `whisper-hindi` or `vasista22/whisper-hindi-large-v2`

Replace the `transcribe()` function in `app.py` with the 🤗 `transformers` pipeline:

```python
from transformers import pipeline

pipe = pipeline(
    "automatic-speech-recognition",
    model="vasista22/whisper-hindi-large-v2",
    chunk_length_s=30,
    device="cpu",  # or "cuda" for GPU
)
result = pipe(audio_path, return_timestamps=True)
```
# toolazytoaddcaptions
