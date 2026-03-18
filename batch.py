import argparse
import datetime
import os
import sys
import tempfile
import time
import wave

import ffmpeg
import torch
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
        print("(First run will download ~1.5 GB — this happens once, then it's cached forever)\n")

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
        print("✅ Model loaded successfully!\n")

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
# SINGLE VIDEO PIPELINE
# ─────────────────────────────────────────────

# Supported video extensions
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v", ".ts", ".wmv"}


def process_video(video_path: str, output_dir: str) -> str | None:
    """
    Full pipeline for a single video:
    video → audio → transcription → SRT file

    Returns the path to the generated SRT file, or None on failure.
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_filename = f"{video_name}.srt"
    srt_path = os.path.join(output_dir, srt_filename)

    with tempfile.TemporaryDirectory() as tmp:
        # Step 1 — extract audio
        print(f"  🎵 Extracting audio...")
        try:
            audio_path = extract_audio(video_path, tmp)
        except Exception as e:
            print(f"  ❌ Audio extraction failed: {e}")
            return None

        # Step 2 — transcribe
        print(f"  🤖 Transcribing... (may take a while on CPU)")
        try:
            segments = transcribe(audio_path)
        except Exception as e:
            print(f"  ❌ Transcription failed: {e}")
            return None

        if not segments:
            print(f"  ⚠️  No speech detected — skipping.")
            return None

        # Step 3 — generate SRT
        print(f"  📝 Generating SRT...")
        srt_content = segments_to_srt(segments)

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        print(f"  ✅ Done! {len(segments)} segments → {srt_path}")
        return srt_path


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
                print(f"⚠️  Skipping '{path}' — not a supported video format.")

        elif os.path.isdir(path):
            found = [
                os.path.join(path, f)
                for f in sorted(os.listdir(path))
                if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
            ]
            if not found:
                print(f"⚠️  No videos found in folder: {path}")
            videos.extend(found)

        else:
            print(f"⚠️  Path not found: {path}")

    return videos


def run_batch(videos: list[str], output_dir: str):
    """Process a list of video files and write SRT files to output_dir."""

    total = len(videos)
    succeeded = []
    failed = []

    # Load model once before the loop — not per video
    print("─" * 60)
    load_model()
    print("─" * 60)
    print(f"Starting batch: {total} video(s) → SRTs will be saved to: {output_dir}\n")

    batch_start = time.time()

    for i, video_path in enumerate(videos, start=1):
        print(f"[{i}/{total}] {os.path.basename(video_path)}")
        video_start = time.time()

        result = process_video(video_path, output_dir)

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
    print(f"  ✅ Succeeded : {len(succeeded)}/{total}")
    print(f"  ❌ Failed    : {len(failed)}/{total}")

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

    args = parser.parse_args()

    # Collect all video files
    videos = collect_videos(args.inputs)

    if not videos:
        print("❌ No valid video files found. Nothing to do.")
        sys.exit(1)

    print(f"\n🎬 Found {len(videos)} video(s) to process:")
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

    print(f"📂 SRT files will be saved to: {output_dir}\n")

    run_batch(videos, output_dir)


if __name__ == "__main__":
    main()
