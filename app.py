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
import whisper  # For word-level timestamps
import whisper_timestamped  # Word-level timestamp support
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

        # FIX: set generation params directly on generation_config
        # Passing them via generate_kwargs is deprecated in transformers ≥5.x
        # no_repeat_ngram_size=5 — kills hallucination loops ("chup chup chup..." etc.)
        # condition_on_prev_tokens=False — stops hallucinations spreading chunk to chunk
        model.generation_config.task = "transcribe"
        model.generation_config.language = "en"
        model.generation_config.no_repeat_ngram_size = 5
        model.generation_config.condition_on_prev_tokens = False

        _model_cache["apex"] = hf_pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            device=device,
            chunk_length_s=30,
            stride_length_s=5,
            # FIX: return_timestamps=True (boolean), NOT "word"
            # "word" requires alignment_heads on the model — fine-tuned checkpoints
            # almost never have these, causing: TypeError: 'NoneType' is not iterable
            # boolean True uses the model's own <|timestamp|> tokens instead
            return_timestamps=True,
            ignore_warning=True,
        )
        print("Model loaded successfully!")
    return _model_cache["apex"]


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe audio and return list of segments with timestamps."""
    import wave

    pipe = load_model()
    result = pipe(audio_path)

    raw_chunks = result.get("chunks", [])

    # Get audio duration so we can estimate timestamps when the model returns None
    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    n = len(raw_chunks)
    segments = []

    for i, chunk in enumerate(raw_chunks):
        ts = chunk.get("timestamp", (None, None))
        text = chunk.get("text", "").strip()

        if not text:
            continue

        # Estimate start if missing — divide audio evenly across chunks
        if ts[0] is not None:
            start = ts[0]
        else:
            start = (i / n) * audio_duration if n > 0 else 0.0

        # Estimate end if missing — use next chunk's start or end of audio
        if ts[1] is not None:
            end = ts[1]
        elif i + 1 < n:
            next_ts = raw_chunks[i + 1].get("timestamp", (None, None))
            end = next_ts[0] if next_ts[0] is not None else start + (audio_duration / n)
        else:
            end = audio_duration

        segments.append(
            {
                "id": len(segments),
                "start": start,
                "end": end,
                "text": text,
            }
        )

    return segments


# ── END NEW ──────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────
# 2b. WORD-LEVEL TRANSCRIPTION (whisper-timestamped)
# ─────────────────────────────────────────────

_whisper_model_cache = {}


def load_whisper_model(model_size: str = "base"):
    """Load and cache OpenAI Whisper model for word-level timestamps."""
    if model_size not in _whisper_model_cache:
        print(f"Loading Whisper model for word-level timestamps: {model_size} ...")
        _whisper_model_cache[model_size] = whisper.load_model(model_size)
    return _whisper_model_cache[model_size]


def transcribe_word_level(
    audio_path: str, model_size: str = "base", words_per_line: int = 2
) -> list[dict]:
    """
    Transcribe audio with word-level timestamps using whisper-timestamped.
    Groups words into lines with specified words_per_line.
    """
    model = load_whisper_model(model_size)

    # Get word-level timestamps
    result = whisper_timestamped.transcribe_timestamped(
        model, audio_path, language="en", task="transcribe", verbose=False
    )

    # Extract all words with timestamps
    words = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_text = word_info.get("text", "").strip()
            if word_text:
                words.append(
                    {
                        "text": word_text,
                        "start": word_info.get("start", 0),
                        "end": word_info.get("end", 0),
                    }
                )

    if not words:
        return []

    # Group words into lines (words_per_line words per caption)
    segments = []
    current_line_words = []
    line_start = words[0]["start"]
    line_end = words[0]["end"]

    for i, word in enumerate(words):
        current_line_words.append(word["text"])
        line_end = word["end"]

        # Create a new segment when we hit words_per_line
        if len(current_line_words) >= words_per_line:
            segments.append(
                {
                    "id": len(segments),
                    "start": line_start,
                    "end": line_end,
                    "text": " ".join(current_line_words),
                }
            )
            current_line_words = []
            # Start next line from next word's start time
            if i + 1 < len(words):
                line_start = words[i + 1]["start"]

    # Add remaining words as final segment
    if current_line_words:
        segments.append(
            {
                "id": len(segments),
                "start": line_start,
                "end": line_end,
                "text": " ".join(current_line_words),
            }
        )

    return segments


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
# PREMIERE PRO FORMAT SUPPORT
# ─────────────────────────────────────────────


def get_video_fps(video_path: str) -> float:
    """Extract FPS from video file using ffprobe."""
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "video"),
            None,
        )
        if video_stream:
            fps_str = video_stream.get("r_frame_rate", "25/1")
            # Parse fraction like "30/1" or "25/1"
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
    except Exception:
        pass
    return 25.0  # Default to 25 FPS if detection fails


def seconds_to_timecode(seconds: float, fps: float = 25.0) -> str:
    """Convert seconds to HH:MM:SS:FF format (Premiere Pro timecode)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds - int(seconds)) * fps)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def segments_to_pr_text(segments: list[dict], fps: float = 25.0) -> str:
    """
    Convert segments to Premiere Pro Text format (.txt).
    Format: HH:MM:SS:FF - HH:MM:SS:FF\\nText\\n\\n
    """
    lines = []
    for seg in segments:
        start_tc = seconds_to_timecode(seg["start"], fps)
        end_tc = seconds_to_timecode(seg["end"], fps)
        lines.append(f"{start_tc} - {end_tc}")
        lines.append(seg["text"].strip())
        lines.append("")  # Blank line between entries
    return "\n".join(lines)


def segments_to_pr_srt(segments: list[dict]) -> str:
    """
    Convert segments to frame-accurate SRT for Premiere Pro.
    Uses standard SRT format with precise millisecond timestamps.
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = seconds_to_srt_time(seg["start"])
        end = seconds_to_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Blank line
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


def generate_captions(
    video_file,
    word_level: bool = False,
    words_per_line: int = 2,
    output_format: str = "srt",
    progress=gr.Progress(),
):
    """Full pipeline: video → caption file."""
    if video_file is None:
        return None, "⚠️ Please upload a video file first."

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1 — extract audio
        progress(0.1, desc="🎵 Extracting audio...")
        audio_path = extract_audio(video_file, tmp)

        # Step 2 — transcribe
        if word_level:
            progress(
                0.3,
                desc="🤖 Transcribing with word-level timestamps... (downloading Whisper model if needed)",
            )
            segments = transcribe_word_level(audio_path, words_per_line=words_per_line)
        else:
            # NOTE: bar will sit at 30% the entire time — this is normal.
            # On first run the ~1.5 GB model downloads here, then transcription runs on CPU.
            progress(
                0.3,
                desc="🤖 Transcribing... (bar stays at 30% — normal. First run downloads ~1.5 GB model)",
            )
            segments = transcribe(audio_path)

        # Step 3 — detect FPS for Premiere Pro formats
        fps = 25.0
        if output_format in ["pr-text", "pr-srt"]:
            progress(0.85, desc="🎬 Detecting video FPS...")
            fps = get_video_fps(video_file)

        # Step 4 — generate output based on format
        progress(0.9, desc="📝 Generating caption file...")

        if output_format == "pr-text":
            # Premiere Pro Text format (.txt)
            content = segments_to_pr_text(segments, fps)
            output_filename = "captions.txt"
        elif output_format == "pr-srt":
            # Premiere Pro optimized SRT (frame-accurate)
            content = segments_to_pr_srt(segments)
            output_filename = "captions.srt"
        else:
            # Standard SRT
            content = segments_to_srt(segments)
            output_filename = "captions.srt"

        # Step 5 — write to output path
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        progress(1.0, desc="✅ Done!")
        num_segments = len(segments)

        format_name = {
            "srt": "Standard SRT",
            "pr-srt": "Premiere Pro SRT",
            "pr-text": "Premiere Pro Text",
        }.get(output_format, "SRT")

        return (
            output_path,
            f"✅ Done! Generated {num_segments} caption segments ({format_name}).",
        )


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

        with gr.Row():
            with gr.Column():
                word_level_check = gr.Checkbox(
                    label="Word-level timestamps",
                    value=False,
                    info="Split captions into 2-3 words per line (karaoke style)",
                )
                words_per_line_slider = gr.Slider(
                    minimum=1,
                    maximum=5,
                    value=2,
                    step=1,
                    label="Words per caption line",
                    visible=False,  # Hidden by default, shown when word-level is enabled
                )

        with gr.Row():
            with gr.Column():
                output_format_dropdown = gr.Dropdown(
                    choices=[
                        ("Standard SRT", "srt"),
                        ("Premiere Pro SRT", "pr-srt"),
                        ("Premiere Pro Text (.txt)", "pr-text"),
                    ],
                    value="srt",
                    label="Output Format",
                    info="Choose format for your video editor",
                )

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

        # Show/hide words_per_line slider based on word_level checkbox
        word_level_check.change(
            fn=lambda x: gr.update(visible=x),
            inputs=[word_level_check],
            outputs=[words_per_line_slider],
        )

        run_btn.click(
            fn=generate_captions,
            inputs=[
                video_input,
                word_level_check,
                words_per_line_slider,
                output_format_dropdown,
            ],
            outputs=[srt_output, status_box],
        )

    return demo


# ── END NEW ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app = build_ui()
    # FIX: css= moved to launch() — Gradio 6 deprecated it in gr.Blocks()
    # FIX: server_port removed — auto-selects next free port, no more OSError crash
    app.launch(css=CSS, share=False)
