import gradio as gr
import whisper
import ffmpeg
import os
import tempfile
import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# 1. AUDIO EXTRACTION
# ─────────────────────────────────────────────

def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio from video using FFmpeg."""
    audio_path = os.path.join(output_dir, "audio.wav")
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar="16000", format="wav")  # mono, 16kHz for Whisper
        .overwrite_output()
        .run(quiet=True)
    )
    return audio_path


# ─────────────────────────────────────────────
# 2. TRANSCRIPTION
# ─────────────────────────────────────────────

_model_cache = {}

def load_model(model_size: str):
    """Load and cache Whisper model."""
    if model_size not in _model_cache:
        print(f"Loading Whisper model: {model_size} ...")
        _model_cache[model_size] = whisper.load_model(model_size)
    return _model_cache[model_size]


def transcribe(audio_path: str, model_size: str, language: str) -> list[dict]:
    """
    Transcribe audio and return list of segments.
    Each segment: {"id", "start", "end", "text"}
    """
    model = load_model(model_size)

    options = dict(
        task="transcribe",
        # For Hinglish, setting language="hi" lets Whisper keep Hindi script
        # and transliterate English words naturally.
        # Leave as None for fully automatic detection.
        language=None if language == "auto" else language,
        word_timestamps=False,
        fp16=False,
    )

    result = model.transcribe(audio_path, **options)
    return result["segments"]


# ─────────────────────────────────────────────
# 3. SRT GENERATION
# ─────────────────────────────────────────────

def seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds → HH:MM:SS,mmm (SRT format)."""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours   = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs    = total_seconds % 60
    millis  = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def segments_to_srt(segments: list[dict]) -> str:
    """Convert Whisper segments to SRT string."""
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = seconds_to_srt_time(seg["start"])
        end   = seconds_to_srt_time(seg["end"])
        text  = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 4. MAIN PIPELINE
# ─────────────────────────────────────────────

def generate_captions(video_file, model_size: str, language: str):
    """Full pipeline: video → SRT file."""
    if video_file is None:
        return None, "⚠️ Please upload a video file first."

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1 – extract audio
        yield None, "🎵 Extracting audio from video..."
        audio_path = extract_audio(video_file, tmp)

        # Step 2 – transcribe
        yield None, f"🤖 Transcribing with Whisper ({model_size})... (this may take a minute)"
        segments = transcribe(audio_path, model_size, language)

        # Step 3 – build SRT
        yield None, "📝 Generating SRT file..."
        srt_content = segments_to_srt(segments)

        # Step 4 – save SRT
        srt_path = os.path.join(tmp, "captions.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Copy out of temp dir before it's deleted
        output_path = "/tmp/captions.srt"
        import shutil
        shutil.copy(srt_path, output_path)

        num_lines = len(segments)
        yield output_path, f"✅ Done! Generated {num_lines} caption segments."


# ─────────────────────────────────────────────
# 5. GRADIO UI
# ─────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:ital,wght@0,300;0,400;1,300&display=swap');

body, .gradio-container {
    background: #0a0a0f !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #e8e4dc !important;
}

.gradio-container { max-width: 780px !important; margin: 0 auto !important; }

h1 {
    font-family: 'Syne', sans-serif !important;
    font-size: 2.6rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #ff6b35 0%, #f7c59f 50%, #fffbe6 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    letter-spacing: -1px !important;
    margin-bottom: 0 !important;
}

.subtitle {
    color: #888 !important;
    font-size: 0.95rem !important;
    margin-bottom: 2rem !important;
    font-style: italic !important;
}

.gr-block, .gr-box, .gr-panel { background: #13131a !important; border: 1px solid #2a2a38 !important; border-radius: 12px !important; }
.gr-button-primary { background: #ff6b35 !important; border: none !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; border-radius: 8px !important; transition: all .2s !important; }
.gr-button-primary:hover { background: #e85a24 !important; transform: translateY(-1px) !important; }
label { color: #aaa !important; font-size: 0.85rem !important; letter-spacing: .05em !important; text-transform: uppercase !important; }
"""

def build_ui():
    with gr.Blocks(css=CSS, title="HinglishCaps") as demo:
        gr.HTML("""
            <div style="text-align:center; padding: 2rem 0 0.5rem">
                <h1>HinglishCaps ✦</h1>
                <p class="subtitle">Auto-captions for Hindi · English · Hinglish videos</p>
            </div>
        """)

        with gr.Row():
            with gr.Column(scale=3):
                video_input = gr.Video(label="Upload Video", sources=["upload"])
            with gr.Column(scale=2):
                model_choice = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium", "large"],
                    value="base",
                    label="Whisper Model",
                    info="Larger = more accurate, but slower"
                )
                lang_choice = gr.Dropdown(
                    choices=["auto", "hi", "en"],
                    value="auto",
                    label="Language Hint",
                    info="'hi' works best for Hinglish"
                )
                run_btn = gr.Button("Generate Captions ✦", variant="primary", size="lg")

        status_box = gr.Textbox(label="Status", interactive=False, lines=1, value="Waiting for upload...")
        srt_output = gr.File(label="Download .SRT File", visible=True)

        gr.HTML("""
            <div style="color:#555; font-size:0.8rem; padding:1rem 0; border-top:1px solid #1e1e2a; margin-top:1.5rem">
                <b style="color:#777">How to use your SRT:</b>
                Import into Premiere Pro · DaVinci Resolve · CapCut · Final Cut Pro or any video editor that accepts subtitle files.
            </div>
        """)

        run_btn.click(
            fn=generate_captions,
            inputs=[video_input, model_choice, lang_choice],
            outputs=[srt_output, status_box],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(share=False, server_port=7860)
