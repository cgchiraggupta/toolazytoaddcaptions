import argparse
import datetime
import os
import sys
import tempfile
import time
import wave

import ffmpeg
import torch
import whisper
import whisper_timestamped
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from transformers import pipeline as hf_pipeline

# ─────────────────────────────────────────────
# MODEL  (shared cache — loaded once for entire batch)
# ─────────────────────────────────────────────

_model_cache = {}


def load_model():
    """Load and cache the Apex model. Downloads automatically on first run (~1.5 GB)."""
    if "apex" not in _model_cache:
        print("Loading Whisper-Hindi2Hinglish-Apex...")
        print(
            "(First run will download ~1.5 GB — this happens once, then it's cached forever)\n"
        )

        model_id = "Oriserve/Whisper-Hindi2Hinglish-Apex"
        device = "cpu"
        dtype = torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            dtype=dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        ).to(device)

        processor = AutoProcessor.from_pretrained(model_id)

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
            return_timestamps=True,
            ignore_warning=True,
        )
        print("Model loaded successfully!\n")

    return _model_cache["apex"]


# ─────────────────────────────────────────────
# AUDIO EXTRACTION
# ─────────────────────────────────────────────


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract mono 16kHz WAV audio from a video file using FFmpeg."""
    audio_path = os.path.join(output_dir, "audio.wav")
    (
        ffmpeg.input(video_path)
        .output(audio_path, ac=1, ar="16000", format="wav")
        .overwrite_output()
        .run(quiet=True)
    )
    return audio_path


# ─────────────────────────────────────────────
# TRANSCRIPTION
# ─────────────────────────────────────────────


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe audio and return list of segments with timestamps."""
    pipe = load_model()
    result = pipe(audio_path)

    raw_chunks = result.get("chunks", [])

    # Get audio duration to estimate timestamps when model returns None
    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    n = len(raw_chunks)
    segments = []

    for i, chunk in enumerate(raw_chunks):
        ts = chunk.get("timestamp", (None, None))
        text = chunk.get("text", "").strip()

        if not text:
            continue

        # Estimate start if missing
        if ts[0] is not None:
            start = ts[0]
        else:
            start = (i / n) * audio_duration if n > 0 else 0.0

        # Estimate end if missing
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


# ─────────────────────────────────────────────
# WORD-LEVEL TIMESTAMPS (whisper-timestamped)
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
# SRT GENERATION
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
    """Extract video frame rate using ffprobe."""
    try:
        import json
        import subprocess

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "json",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        fps_str = data["streams"][0]["r_frame_rate"]
        # Parse fraction like "30000/1001" or "25/1"
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)
        return fps
    except Exception as e:
        print(f"Warning: Could not detect FPS, defaulting to 25: {e}")
        return 25.0


def seconds_to_timecode(seconds: float, fps: float = 25.0) -> str:
    """Convert seconds to HH:MM:SS:FF format for Premiere Pro."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds - int(seconds)) * fps)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def segments_to_pr_text(segments: list[dict], fps: float = 25.0) -> str:
    """
    Convert segments to Premiere Pro Text format (.txt).
    Format: HH:MM:SS:FF - HH:MM:SS:FF
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
    Convert segments to frame-accurate SRT format.
    Same as standard SRT but with precise timing.
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
# SINGLE VIDEO PIPELINE
# ─────────────────────────────────────────────

# Supported video extensions
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".m4v",
    ".ts",
    ".wmv",
}


def process_video(
    video_path: str,
    output_dir: str,
    word_level: bool = False,
    words_per_line: int = 2,
    output_format: str = "srt",
) -> str | None:
    """
    Full pipeline for a single video:
    video → audio → transcription → caption file

    Returns the path to the generated file, or None on failure.
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Determine output filename based on format
    if output_format == "pr-text":
        output_filename = f"{video_name}.txt"
    else:
        output_filename = f"{video_name}.srt"

    output_path = os.path.join(output_dir, output_filename)

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1 — extract audio
        print("  Extracting audio...")
        try:
            audio_path = extract_audio(video_path, tmp)
        except Exception as e:
            print(f"  Audio extraction failed: {e}")
            return None

        # Step 2 — transcribe
        if word_level:
            print("  Transcribing with word-level timestamps...")
            try:
                segments = transcribe_word_level(
                    audio_path, words_per_line=words_per_line
                )
            except Exception as e:
                print(f"  Word-level transcription failed: {e}")
                return None
        else:
            print("  Transcribing... (may take a while on CPU)")
            try:
                segments = transcribe(audio_path)
            except Exception as e:
                print(f"  Transcription failed: {e}")
                return None

        if not segments:
            print("No speech detected - skipping.")
            return None

        # Step 3 — detect FPS for Premiere Pro formats
        fps = 25.0
        if output_format in ["pr-text", "pr-srt"]:
            print("  Detecting video FPS...")
            fps = get_video_fps(video_path)
            print(f"     FPS: {fps}")

        # Step 4 — generate output based on format
        print(f"  Generating caption file ({output_format})...")

        if output_format == "pr-text":
            # Premiere Pro Text format (.txt)
            content = segments_to_pr_text(segments, fps)
        elif output_format == "pr-srt":
            # Premiere Pro optimized SRT (frame-accurate)
            content = segments_to_pr_srt(segments)
        else:
            # Standard SRT
            content = segments_to_srt(segments)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  Done! {len(segments)} segments -> {output_path}")
        return output_path


# ─────────────────────────────────────────────
# BATCH RUNNER
# ─────────────────────────────────────────────


def collect_videos(inputs: list[str]) -> list[str]:
    """
    Given a list of paths (files and/or folders), return all video files found.
    Folders are scanned non-recursively by default.
    """
    videos = []

    for path in inputs:
        path = os.path.abspath(path)

        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                videos.append(path)
            else:
                print(f"Skipping '{path}' — not a supported video format.")

        elif os.path.isdir(path):
            found = [
                os.path.join(path, f)
                for f in sorted(os.listdir(path))
                if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
            ]
            if not found:
                print(f"No videos found in folder: {path}")
            videos.extend(found)

        else:
            print(f"Path not found: {path}")

    return videos


def run_batch(
    videos: list[str],
    output_dir: str,
    word_level: bool = False,
    words_per_line: int = 2,
    output_format: str = "srt",
):
    """Process a list of video files and write caption files to output_dir."""

    total = len(videos)
    succeeded = []
    failed = []

    # Load model once before the loop — not per video
    print("─" * 60)
    load_model()
    print("─" * 60)

    format_name = {
        "srt": "Standard SRT",
        "pr-srt": "Premiere Pro SRT",
        "pr-text": "Premiere Pro Text",
    }.get(output_format, "SRT")

    ext = ".txt" if output_format == "pr-text" else ".srt"
    print(f"Starting batch: {total} video(s) → {format_name} ({ext})")
    print(f"Output directory: {output_dir}\n")

    batch_start = time.time()

    for i, video_path in enumerate(videos, start=1):
        print(f"[{i}/{total}] {os.path.basename(video_path)}")
        video_start = time.time()

        result = process_video(
            video_path, output_dir, word_level, words_per_line, output_format
        )

        elapsed = time.time() - video_start
        print(f"  ⏱  Took {elapsed:.1f}s\n")

        if result:
            succeeded.append(video_path)
        else:
            failed.append(video_path)

    # ── Summary ──────────────────────────────
    total_time = time.time() - batch_start
    minutes, seconds = divmod(int(total_time), 60)

    print("─" * 60)
    print(f"Batch complete in {minutes}m {seconds}s")
    print(f"  Succeeded : {len(succeeded)}/{total}")
    print(f"  Failed    : {len(failed)}/{total}")

    if failed:
        print("\nFailed videos:")
        for f in failed:
            print(f"  - {f}")

    print("─" * 60)


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="batch.py",
        description=(
            "HinglishCaps Batch CLI — generate SRT subtitle files for multiple videos at once.\n"
            "Powered by Oriserve/Whisper-Hindi2Hinglish-Apex.\n\n"
            "Examples:\n"
            "  # Single video\n"
            "  python batch.py video.mp4\n\n"
            "  # Multiple videos\n"
            "  python batch.py clip1.mp4 clip2.mov clip3.mkv\n\n"
            "  # Entire folder of videos\n"
            "  python batch.py /path/to/videos/\n\n"
            "  # Mix of files and folders\n"
            "  python batch.py intro.mp4 /path/to/more/videos/\n\n"
            "  # Custom output folder\n"
            "  python batch.py /videos/ --output /subtitles/\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        metavar="VIDEO_OR_FOLDER",
        help=(
            "One or more video files or folders containing videos. "
            f"Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}"
        ),
    )

    parser.add_argument(
        "--output",
        "-o",
        metavar="OUTPUT_DIR",
        default=None,
        help=(
            "Folder where SRT files will be saved. "
            "Defaults to same folder as each video. "
            "If a single folder input is given, defaults to that same folder."
        ),
    )

    parser.add_argument(
        "--word-level",
        "-w",
        action="store_true",
        help="Enable word-level timestamps (karaoke-style captions, 2-3 words per line)",
    )

    parser.add_argument(
        "--words-per-line",
        "-wp",
        type=int,
        default=2,
        metavar="N",
        help="Number of words per caption line when using --word-level (default: 2, max: 5)",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["srt", "pr-srt", "pr-text"],
        default="srt",
        help=(
            "Output format: srt (standard), pr-srt (Premiere Pro SRT), "
            "pr-text (Premiere Pro Text). Default: srt"
        ),
    )

    args = parser.parse_args()

    # Collect all video files
    videos = collect_videos(args.inputs)

    if not videos:
        print("No valid video files found. Nothing to do.")
        sys.exit(1)

    print(f"\nFound {len(videos)} video(s) to process:")
    for v in videos:
        print(f"   {v}")
    print()

    # Resolve output directory
    if args.output:
        output_dir = os.path.abspath(args.output)
        os.makedirs(output_dir, exist_ok=True)
    else:
        # If all videos are in the same folder, put SRTs there too
        # Otherwise use current working directory
        dirs = {os.path.dirname(v) for v in videos}
        if len(dirs) == 1:
            output_dir = dirs.pop()
        else:
            output_dir = os.getcwd()

    print(f"Output directory: {output_dir}\n")

    if args.word_level:
        print(f"Word-level mode: {args.words_per_line} words per line")

    format_name = {
        "srt": "Standard SRT",
        "pr-srt": "Premiere Pro SRT",
        "pr-text": "Premiere Pro Text",
    }.get(args.format, "SRT")
    print(f"Output format: {format_name}\n")

    run_batch(videos, output_dir, args.word_level, args.words_per_line, args.format)


if __name__ == "__main__":
    main()
