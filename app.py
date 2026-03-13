import datetime
import os

# import shutil  # ← not needed in new pipeline (shutil.copy removed); kept for reference
import tempfile

# from pathlib import Path  # ← not used in current version, kept for reference
import ffmpeg
import gradio as gr

# import whisper  # ← OLD: openai-whisper based transcription
#                 #   commented out — replaced by HuggingFace Apex model below
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from transformers import pipeline as hf_pipeline

# ─────────────────────────────────────────────
# 1. AUDIO EXTRACTION  (unchanged)
# ─────────────────────────────────────────────


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio from video using FFmpeg."""
    audio_path = os.path.join(output_dir, "audio.wav")
    (
        ffmpeg.input(video_path)
        .output(audio_path, ac=1, ar="16000", format="wav")  # mono, 16kHz for Whisper
        .overwrite_output()
        .run(quiet=True)
    )
    return audio_path


# ─────────────────────────────────────────────
# 2. TRANSCRIPTION
# ─────────────────────────────────────────────

# ── OLD: openai-whisper  (multi-size, language-hint dropdown) ────────────────
#
# _model_cache = {}
#
# def load_model(model_size: str):
#     """Load and cache Whisper model."""
#     if model_size not in _model_cache:
#         print(f"Loading Whisper model: {model_size} ...")
#         _model_cache[model_size] = whisper.load_model(model_size)
#     return _model_cache[model_size]
#
#
# def transcribe(audio_path: str, model_size: str, language: str) -> list[dict]:
#     """
#     Transcribe audio and return list of segments.
#     Each segment: {"id", "start", "end", "text"}
#     """
#     model = load_model(model_size)
#
#     options = dict(
#         task="transcribe",
#         # For Hinglish, setting language="hi" lets Whisper keep Hindi script
#         # and transliterate English words naturally.
#         # Leave as None for fully automatic detection.
#         language=None if language == "auto" else language,
#         word_timestamps=False,
#         fp16=False,
#     )
#
#     result = model.transcribe(audio_path, **options)
#     return result["segments"]
#
# ── END OLD ──────────────────────────────────────────────────────────────────


# ── NEW: Oriserve Whisper-Hindi2Hinglish-Apex  (HuggingFace) ─────────────────

_model_cache = {}


def load_model():
    """Load and cache the Apex model. Downloads automatically on first run (~1.5 GB)."""
    if "apex" not in _model_cache:
        print(
            "Loading Whisper-Hindi2Hinglish-Apex... (first run will download ~1.5 GB)"
        )
        model_id = "Oriserve/Whisper-Hindi2Hinglish-Apex"
        device = "cpu"
        torch_dtype = torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        ).to(device)

        processor = AutoProcessor.from_pretrained(model_id)

        _model_cache["apex"] = hf_pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            dtype=torch_dtype,  # FIX: torch_dtype= deprecated in transformers ≥4.45, use dtype=
            device=device,
            generate_kwargs={"task": "transcribe", "language": "en"},
            chunk_length_s=30,  # handles long videos by splitting into chunks
            return_timestamps=True,
        )
        print("Model loaded successfully!")
    return _model_cache["apex"]


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe audio and return list of segments with timestamps."""
    pipe = load_model()
    result = pipe(audio_path)

    # Convert HuggingFace output → segment format expected by SRT generator
    segments = []
    for i, chunk in enumerate(result["chunks"]):
        segments.append(
            {
                "id": i,
                "start": chunk["timestamp"][0] or 0.0,
                "end": chunk["timestamp"][1] or 0.0,
                "text": chunk["text"],
            }
        )
    return segments


# ── END NEW ──────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────
# 3. SRT GENERATION  (unchanged)
# ─────────────────────────────────────────────


def seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds → HH:MM:SS,mmm (SRT format)."""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def segments_to_srt(segments: list[dict]) -> str:
    """Convert segments list to SRT string."""
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = seconds_to_srt_time(seg["start"])
        end = seconds_to_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 4. MAIN PIPELINE
# ─────────────────────────────────────────────

# ── OLD: generator-based pipeline  (yield, model_size + language params) ─────
#
# def generate_captions(video_file, model_size: str, language: str):
#     """Full pipeline: video → SRT file."""
#     if video_file is None:
#         return None, "⚠️ Please upload a video file first."
#
#     with tempfile.TemporaryDirectory() as tmp:
#         # Step 1 – extract audio
#         yield None, "🎵 Extracting audio from video..."
#         audio_path = extract_audio(video_file, tmp)
#
#         # Step 2 – transcribe
#         yield (
#             None,
#             f"🤖 Transcribing with Whisper ({model_size})... (this may take a minute)",
#         )
#         segments = transcribe(audio_path, model_size, language)
#
#         # Step 3 – build SRT
#         yield None, "📝 Generating SRT file..."
#         srt_content = segments_to_srt(segments)
#
#         # Step 4 – save SRT
#         srt_path = os.path.join(tmp, "captions.srt")
#         with open(srt_path, "w", encoding="utf-8") as f:
#             f.write(srt_content)
#
#         # Copy out of temp dir before it's deleted
#         # FIX: use tempfile.gettempdir() — /tmp is a symlink on macOS and
#         #      is rejected by Gradio 6's path-security guard
#         output_path = os.path.join(tempfile.gettempdir(), "captions.srt")
#         shutil.copy(srt_path, output_path)
#
#         num_lines = len(segments)
#         yield output_path, f"✅ Done! Generated {num_lines} caption segments."
#
# ── END OLD ──────────────────────────────────────────────────────────────────


# ── NEW: gr.Progress() based pipeline  (Apex model, no dropdowns) ────────────


def generate_captions(video_file, progress=gr.Progress()):
    """Full pipeline: video → SRT file."""
    if video_file is None:
        return None, "⚠️ Please upload a video file first."

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1 — extract audio
        progress(0.1, desc="🎵 Extracting audio...")
        audio_path = extract_audio(video_file, tmp)

        # Step 2 — transcribe
        # NOTE: bar will sit at 30% the entire time — this is normal.
        # On first run the ~1.5 GB model downloads here, then transcription runs on CPU.
        # Both are one blocking call with no internal progress hooks.
        progress(
            0.3,
            desc="🤖 Transcribing... (bar stays at 30% — normal. First run downloads ~1.5 GB model)",
        )
        segments = transcribe(audio_path)

        # Step 3 — build SRT
        progress(0.9, desc="📝 Generating SRT file...")
        srt_content = segments_to_srt(segments)

        # Step 4 — write SRT to a path Gradio 6 trusts
        # NOTE: /tmp is a symlink on macOS → Gradio 6 rejects it with InvalidPathError
        #       tempfile.gettempdir() returns the real system temp dir (/var/folders/…)
        output_path = os.path.join(tempfile.gettempdir(), "captions.srt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        progress(1.0, desc="✅ Done!")
        num_segments = len(segments)
        return output_path, f"✅ Done! Generated {num_segments} caption segments."


# ── END NEW ──────────────────────────────────────────────────────────────────


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


# ── OLD: build_ui with Whisper model + language dropdowns ────────────────────
#
# def build_ui():
#     with gr.Blocks(title="HinglishCaps") as demo:
#         gr.HTML("""
#             <div style="text-align:center; padding: 2rem 0 0.5rem">
#                 <h1>HinglishCaps ✦</h1>
#                 <p class="subtitle">Auto-captions for Hindi · English · Hinglish videos</p>
#             </div>
#         """)
#
#         with gr.Row():
#             with gr.Column(scale=3):
#                 video_input = gr.Video(label="Upload Video", sources=["upload"])
#             with gr.Column(scale=2):
#                 model_choice = gr.Dropdown(
#                     choices=["tiny", "base", "small", "medium", "large"],
#                     value="base",
#                     label="Whisper Model",
#                     info="Larger = more accurate, but slower",
#                 )
#                 lang_choice = gr.Dropdown(
#                     choices=["auto", "hi", "en"],
#                     value="auto",
#                     label="Language Hint",
#                     info="'hi' works best for Hinglish",
#                 )
#                 run_btn = gr.Button("Generate Captions ✦", variant="primary", size="lg")
#
#         status_box = gr.Textbox(
#             label="Status", interactive=False, lines=1, value="Waiting for upload..."
#         )
#         srt_output = gr.File(label="Download .SRT File", visible=True)
#
#         gr.HTML("""
#             <div style="color:#555; font-size:0.8rem; padding:1rem 0; border-top:1px solid #1e1e2a; margin-top:1.5rem">
#                 <b style="color:#777">How to use your SRT:</b>
#                 Import into Premiere Pro · DaVinci Resolve · CapCut · Final Cut Pro or any video editor that accepts subtitle files.
#             </div>
#         """)
#
#         run_btn.click(
#             fn=generate_captions,
#             inputs=[video_input, model_choice, lang_choice],
#             outputs=[srt_output, status_box],
#         )
#
#     return demo
#
# ── END OLD ──────────────────────────────────────────────────────────────────


# ── NEW: simplified UI — single upload, no model/language dropdowns ──────────


def build_ui():
    with gr.Blocks(title="HinglishCaps") as demo:
        gr.HTML("""
            <div style="text-align:center; padding: 2rem 0 0.5rem">
                <h1>HinglishCaps ✦</h1>
                <p class="subtitle">Auto-captions for Hindi · English · Hinglish — powered by Whisper-Hindi2Hinglish-Apex</p>
            </div>
        """)

        with gr.Row():
            video_input = gr.Video(label="Upload Video", sources=["upload"])

        run_btn = gr.Button("Generate Captions ✦", variant="primary", size="lg")
        status_box = gr.Textbox(
            label="Status", interactive=False, lines=1, value="Waiting for upload..."
        )
        srt_output = gr.File(label="Download .SRT File")

        gr.HTML("""
            <div style="color:#555; font-size:0.8rem; padding:1rem 0; border-top:1px solid #1e1e2a; margin-top:1.5rem">
                <b style="color:#777">Import SRT into:</b>
                CapCut (Text → Auto Captions → Import) &nbsp;·&nbsp;
                DaVinci Resolve (Timeline → Import Subtitle) &nbsp;·&nbsp;
                Premiere Pro (File → Import)
            </div>
        """)

        run_btn.click(
            fn=generate_captions,
            inputs=[video_input],
            outputs=[srt_output, status_box],
        )

    return demo


# ── END NEW ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app = build_ui()
    # FIX: css= moved to launch() — Gradio 6 deprecated it in gr.Blocks()
    # FIX: server_port removed — auto-selects next free port, no more OSError crash
    app.launch(css=CSS, share=False)
