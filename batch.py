import argparse
import audioop
import datetime
import difflib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass

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
_timing_model_cache = {}
_timing_words_cache = {}
_faster_whisper_timing_words_cache = {}
_forced_alignment_words_cache = {}
_custom_replacements_cache = {}

OUTPUT_EXTENSION = ".srt"
FORCED_ALIGNMENT_MODEL_SIZE = os.getenv(
    "HINGLISHCAPS_FORCED_ALIGN_MODEL", "large-v3"
).strip()
FORCED_ALIGNMENT_TIMEOUT_SECONDS = 1800
FORCED_ALIGNMENT_COMPUTE_TYPE = os.getenv(
    "HINGLISHCAPS_FORCED_ALIGN_COMPUTE_TYPE", "int8"
).strip()
FORCED_ALIGNMENT_INITIAL_PROMPT = os.getenv(
    "HINGLISHCAPS_FORCED_ALIGN_INITIAL_PROMPT",
    "Yeh Hindi-Hinglish speech hai. Indian names, places, and acronyms ko dhyan se transcribe karo.",
).strip()
WHISPERX_ALIGNMENT_MODEL_NAME = os.getenv(
    "HINGLISHCAPS_WHISPERX_ALIGN_MODEL", "facebook/mms-300m"
).strip()
DEFAULT_TRANSCRIPTION_BACKEND = os.getenv(
    "HINGLISHCAPS_TRANSCRIPTION_BACKEND", "whisper-large-v3"
).strip().lower()
DEFAULT_FASTER_WHISPER_DEVICE = os.getenv(
    "HINGLISHCAPS_FASTER_WHISPER_DEVICE", "cpu"
).strip().lower()
DEFAULT_FASTER_WHISPER_COMPUTE_TYPE = os.getenv(
    "HINGLISHCAPS_FASTER_WHISPER_COMPUTE_TYPE", "int8"
).strip()
DEFAULT_FASTER_WHISPER_INITIAL_PROMPT = os.getenv(
    "HINGLISHCAPS_FASTER_WHISPER_INITIAL_PROMPT",
    "Yeh Hindi-Hinglish speech hai. Indian names, places, and technical words ko sahi likho.",
).strip()
DEFAULT_FASTER_WHISPER_VAD_FILTER = (
    os.getenv("HINGLISHCAPS_FASTER_WHISPER_VAD_FILTER", "1").strip().lower()
    not in {"0", "false", "no", "off"}
)
WHISPER_ROMANIZE_OUTPUT = (
    os.getenv("HINGLISHCAPS_WHISPER_ROMANIZE", "1").strip().lower()
    not in {"0", "false", "no", "off"}
)
DEFAULT_ENABLE_CUSTOM_REPLACEMENTS = (
    os.getenv("HINGLISHCAPS_ENABLE_CUSTOM_REPLACEMENTS", "0").strip().lower()
    in {"1", "true", "yes", "on"}
)
DEFAULT_CUSTOM_REPLACEMENTS_FILE = os.getenv(
    "HINGLISHCAPS_CUSTOM_REPLACEMENTS_FILE", ""
).strip()
SUPPORTED_TRANSCRIPTION_BACKENDS = {
    "apex",
    "whisper-base",
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "whisper-small",
    "whisper-medium",
}

DEVANAGARI_BLOCK_RE = re.compile(r"[\u0900-\u097F]")
DEVANAGARI_RUN_RE = re.compile(r"^[\u0900-\u097F]+$")

DEVANAGARI_INDEPENDENT_VOWELS = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "i",
    "उ": "u",
    "ऊ": "u",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
}

DEVANAGARI_CONSONANTS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    "क़": "q",
    "ख़": "kh",
    "ग़": "gh",
    "ज़": "z",
    "फ़": "f",
    "ड़": "r",
    "ढ़": "rh",
    "ऱ": "r",
}

DEVANAGARI_MATRAS = {
    "ा": "a",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "ृ": "ri",
    "ॄ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॅ": "e",
    "ॉ": "o",
    "ॆ": "e",
    "ॊ": "o",
}

DEVANAGARI_DIGITS = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}

SAFE_HINGLISH_ROMAN_REPLACEMENTS = (
    (re.compile(r"\bkar ke\b", flags=re.IGNORECASE), "karke"),
    (re.compile(r"\busane\b", flags=re.IGNORECASE), "usne"),
    (re.compile(r"\byah\b", flags=re.IGNORECASE), "ye"),
    (re.compile(r"\bvah\b", flags=re.IGNORECASE), "woh"),
    (re.compile(r"\bvo\b", flags=re.IGNORECASE), "woh"),
)


@dataclass
class CaptionSettings:
    format_name: str = "Subtitle"
    stream: str = "None"
    style: str = "None"
    max_chars: int = 42
    min_duration: float = 3.0
    gap_frames: int = 0
    lines: str = "Double"


DEFAULT_CAPTION_SETTINGS = CaptionSettings()


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

        _model_cache["apex_model"] = model
        _model_cache["apex_processor"] = processor

        _model_cache["apex"] = hf_pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            device=device,
            chunk_length_s=30,
            stride_length_s=5,
            ignore_warning=True,
        )
        print("Model loaded successfully!\n")

    return _model_cache["apex"]


def load_word_timing_pipeline():
    """Load a dedicated Apex pipeline for short-clip word timestamps."""
    load_model()

    if "apex_word" not in _model_cache:
        processor = _model_cache["apex_processor"]
        model = _model_cache["apex_model"]
        _model_cache["apex_word"] = hf_pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            device="cpu",
            ignore_warning=True,
        )

    return _model_cache["apex_word"]


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


def get_media_duration(media_path: str) -> float | None:
    """Return media duration in seconds when FFmpeg can detect it."""
    try:
        probe = ffmpeg.probe(media_path)
        duration = probe.get("format", {}).get("duration")
        if duration is not None:
            return float(duration)
    except Exception:
        return None
    return None


def parse_fraction(value: str | None) -> float | None:
    """Convert an FFmpeg fraction like 30000/1001 into a float."""
    if not value:
        return None

    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            denominator_value = float(denominator)
            if abs(denominator_value) < 1e-9:
                return None
            return float(numerator) / denominator_value
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def get_media_fps(media_path: str, default_fps: float = 30.0) -> float:
    """Return the video's frame rate when available."""
    try:
        probe = ffmpeg.probe(media_path)
        for stream in probe.get("streams", []):
            if stream.get("codec_type") != "video":
                continue

            fps = parse_fraction(stream.get("avg_frame_rate"))
            if fps is None or fps <= 0:
                fps = parse_fraction(stream.get("r_frame_rate"))
            if fps is not None and fps > 0:
                return fps
    except Exception:
        pass

    return default_fps


def normalize_caption_settings(
    caption_settings: CaptionSettings | dict | None,
) -> CaptionSettings:
    """Return a CaptionSettings object from dict input or defaults."""
    if caption_settings is None:
        return CaptionSettings()

    if isinstance(caption_settings, CaptionSettings):
        return caption_settings

    return CaptionSettings(
        format_name=str(caption_settings.get("format_name", "Subtitle")),
        stream=str(caption_settings.get("stream", "None")),
        style=str(caption_settings.get("style", "None")),
        max_chars=max(1, int(caption_settings.get("max_chars", 42))),
        min_duration=max(0.0, float(caption_settings.get("min_duration", 3.0))),
        gap_frames=max(0, int(caption_settings.get("gap_frames", 0))),
        lines=str(caption_settings.get("lines", "Double")).title(),
    )


# ─────────────────────────────────────────────
# TRANSCRIPTION
# ─────────────────────────────────────────────


def normalize_transcription_backend(transcription_backend: str | None) -> str:
    """Return a supported backend id, falling back to the default backend."""
    backend = (transcription_backend or DEFAULT_TRANSCRIPTION_BACKEND).strip().lower()
    if backend in SUPPORTED_TRANSCRIPTION_BACKENDS:
        return backend
    print(
        f"Unknown transcription backend '{backend}', "
        f"falling back to '{DEFAULT_TRANSCRIPTION_BACKEND}'."
    )
    return DEFAULT_TRANSCRIPTION_BACKEND


def get_audio_duration_seconds(audio_path: str) -> float:
    """Return WAV audio duration in seconds."""
    with wave.open(audio_path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def chunks_to_segments(raw_chunks: list[dict], audio_duration: float) -> list[dict]:
    """Convert timestamped chunk output into normalized segment records."""
    n = len(raw_chunks)
    segments = []

    for i, chunk in enumerate(raw_chunks):
        ts = chunk.get("timestamp", (None, None))
        text = chunk.get("text", "").strip()
        if not text:
            continue

        if ts[0] is not None:
            start = float(ts[0])
        else:
            start = (i / n) * audio_duration if n > 0 else 0.0

        if ts[1] is not None:
            end = float(ts[1])
        elif i + 1 < n:
            next_ts = raw_chunks[i + 1].get("timestamp", (None, None))
            end = (
                float(next_ts[0])
                if next_ts[0] is not None
                else start + (audio_duration / n if n > 0 else 0.05)
            )
        else:
            end = audio_duration

        end = max(start + 0.05, float(end))
        segments.append(
            {
                "id": len(segments),
                "start": float(start),
                "end": float(end),
                "text": text,
            }
        )

    return segments


def transcribe_with_apex(audio_path: str) -> list[dict]:
    """Transcribe audio using the Apex Hinglish model."""
    pipe = load_model()
    result = pipe(audio_path, return_timestamps=True)
    raw_chunks = result.get("chunks") or []
    audio_duration = get_audio_duration_seconds(audio_path)
    return chunks_to_segments(raw_chunks, audio_duration)


def load_whisper_text_model(model_size: str):
    """Load and cache a faster-whisper model used for text transcription."""
    cache_key = (
        f"faster_whisper_text::{model_size}::"
        f"{DEFAULT_FASTER_WHISPER_DEVICE}::{DEFAULT_FASTER_WHISPER_COMPUTE_TYPE}"
    )
    if cache_key not in _model_cache:
        print(
            "Loading faster-whisper text model: "
            f"{model_size} ({DEFAULT_FASTER_WHISPER_COMPUTE_TYPE}) ..."
        )
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is required for Whisper text backends. "
                "Install it with: pip install faster-whisper"
            ) from exc

        _model_cache[cache_key] = WhisperModel(
            model_size,
            device=DEFAULT_FASTER_WHISPER_DEVICE,
            compute_type=DEFAULT_FASTER_WHISPER_COMPUTE_TYPE,
        )
    return _model_cache[cache_key]


def romanize_devanagari_token(token: str) -> str:
    """Romanize one Devanagari token using a lightweight Hinglish-style map."""
    output: list[str] = []
    pending_consonant = None
    appended_implicit_final_a = False

    for char in token:
        if char in DEVANAGARI_INDEPENDENT_VOWELS:
            if pending_consonant is not None:
                output.append("a")
                pending_consonant = None
            output.append(DEVANAGARI_INDEPENDENT_VOWELS[char])
            continue

        if char in DEVANAGARI_CONSONANTS:
            if pending_consonant is not None:
                output.append("a")
            output.append(DEVANAGARI_CONSONANTS[char])
            pending_consonant = char
            continue

        if char in DEVANAGARI_MATRAS:
            if pending_consonant is not None:
                output.append(DEVANAGARI_MATRAS[char])
                pending_consonant = None
            else:
                output.append(DEVANAGARI_MATRAS[char])
            continue

        if char == "्":
            pending_consonant = None
            continue

        if char in {"ं", "ँ"}:
            output.append("n")
            pending_consonant = None
            continue

        if char == "ः":
            output.append("h")
            pending_consonant = None
            continue

        if char == "़":
            # Nukta is handled in precomposed consonants when present.
            continue

        if char in DEVANAGARI_DIGITS:
            if pending_consonant is not None:
                output.append("a")
                pending_consonant = None
            output.append(DEVANAGARI_DIGITS[char])
            continue

        if pending_consonant is not None:
            output.append("a")
            pending_consonant = None
        output.append(char)

    if pending_consonant is not None:
        output.append("a")
        appended_implicit_final_a = True

    romanized = "".join(output)
    # Simple schwa deletion for word-final implicit 'a' (e.g., "pagala" -> "pagal").
    if (
        appended_implicit_final_a
        and
        len(romanized) > 3
        and romanized.endswith("a")
        and not romanized.endswith(("aa", "ia", "ua", "oa", "ya"))
    ):
        romanized = romanized[:-1]
    return romanized


def romanize_devanagari_text(text: str) -> str:
    """Convert Devanagari text to romanized Hinglish-like text."""
    if not text or not DEVANAGARI_BLOCK_RE.search(text):
        return text

    # Split into Devanagari runs and non-Devanagari runs to preserve punctuation.
    parts = re.split(r"([\u0900-\u097F]+)", text)
    romanized_parts = []
    for part in parts:
        if not part:
            continue
        if DEVANAGARI_RUN_RE.match(part):
            romanized_parts.append(romanize_devanagari_token(part))
        else:
            romanized_parts.append(part)
    return "".join(romanized_parts)


def parse_regex_flags(flag_value) -> int:
    """Parse regex flags like 'i', 'im', or numeric values."""
    if isinstance(flag_value, int):
        return int(flag_value)

    if flag_value is None:
        return re.IGNORECASE

    flags = 0
    flag_text = str(flag_value).lower()
    if "i" in flag_text:
        flags |= re.IGNORECASE
    if "m" in flag_text:
        flags |= re.MULTILINE
    if "s" in flag_text:
        flags |= re.DOTALL
    return flags


def compile_custom_replacement_rules(raw_payload) -> list[tuple[re.Pattern, str]]:
    """Compile custom replacement rules from JSON payload."""
    raw_rules = raw_payload
    if isinstance(raw_payload, dict) and "replacements" in raw_payload:
        raw_rules = raw_payload.get("replacements", [])
    elif isinstance(raw_payload, dict):
        raw_rules = [
            {"pattern": pattern, "replacement": replacement}
            for pattern, replacement in raw_payload.items()
        ]

    if not isinstance(raw_rules, list):
        raise ValueError(
            "Custom replacement file must contain a list, a pattern map, "
            "or an object with a 'replacements' list."
        )

    compiled_rules: list[tuple[re.Pattern, str]] = []
    for entry in raw_rules:
        if not isinstance(entry, dict):
            continue

        pattern_text = str(entry.get("pattern", "")).strip()
        if not pattern_text:
            continue

        replacement_text = str(entry.get("replacement", ""))
        flags = parse_regex_flags(entry.get("flags", "i"))
        compiled_rules.append((re.compile(pattern_text, flags=flags), replacement_text))

    return compiled_rules


def load_custom_replacement_rules(
    replacements_file: str,
) -> list[tuple[re.Pattern, str]]:
    """Load and cache custom regex replacements from a JSON file."""
    resolved_path = os.path.abspath(os.path.expanduser(replacements_file))
    if not os.path.isfile(resolved_path):
        print(f"Custom replacement dictionary not found: {resolved_path}")
        return []

    try:
        stat = os.stat(resolved_path)
        cache_key = (
            resolved_path,
            getattr(stat, "st_mtime_ns", None),
            getattr(stat, "st_size", None),
        )
        if cache_key in _custom_replacements_cache:
            return _custom_replacements_cache[cache_key]

        with open(resolved_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        compiled_rules = compile_custom_replacement_rules(payload)
        _custom_replacements_cache[cache_key] = compiled_rules
        print(
            f"Loaded {len(compiled_rules)} custom replacement rule(s) from "
            f"{resolved_path}"
        )
        return compiled_rules
    except Exception as exc:
        print(f"Failed to load custom replacement dictionary '{resolved_path}': {exc}")
        return []


def resolve_custom_replacement_rules(
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
) -> list[tuple[re.Pattern, str]]:
    """Resolve custom replacement rules based on flags and optional file path."""
    enabled = (
        DEFAULT_ENABLE_CUSTOM_REPLACEMENTS
        if enable_custom_replacements is None
        else bool(enable_custom_replacements)
    )
    if not enabled:
        return []

    file_path = (custom_replacements_file or DEFAULT_CUSTOM_REPLACEMENTS_FILE).strip()
    if not file_path:
        print(
            "Custom replacement dictionary is enabled but no file path was provided; "
            "skipping custom replacements."
        )
        return []

    return load_custom_replacement_rules(file_path)


def normalize_hinglish_roman_text(
    text: str,
    custom_replacements: list[tuple[re.Pattern, str]] | None = None,
) -> str:
    """Apply safe Hinglish normalization, plus optional custom replacements."""
    normalized = text
    for pattern, replacement in SAFE_HINGLISH_ROMAN_REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)

    if custom_replacements:
        for pattern, replacement in custom_replacements:
            normalized = pattern.sub(replacement, normalized)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def transcript_tokens_from_segments(segments: list[dict]) -> list[str]:
    """Flatten transcript segments into normalized comparison tokens."""
    tokens: list[str] = []
    for segment in segments:
        for raw_word in str(segment.get("text", "")).split():
            token = normalize_alignment_token(raw_word)
            if token:
                tokens.append(token)
    return tokens


def longest_repeated_token_run(tokens: list[str]) -> int:
    """Return longest contiguous repetition run of a token."""
    if not tokens:
        return 0

    best_run = 1
    current_run = 1
    previous_token = tokens[0]

    for token in tokens[1:]:
        if token == previous_token:
            current_run += 1
            best_run = max(best_run, current_run)
        else:
            previous_token = token
            current_run = 1

    return best_run


def transcript_quality_score(segments: list[dict]) -> float:
    """Heuristic quality score to compare multiple transcript candidates."""
    if not segments:
        return -1.0

    tokens = transcript_tokens_from_segments(segments)
    if not tokens:
        return -1.0

    unique_ratio = len(set(tokens)) / float(len(tokens))
    repeat_run = longest_repeated_token_run(tokens)
    segment_bonus = min(10, len(segments)) * 0.03
    repeat_penalty = max(0, repeat_run - 2) * 0.08

    return unique_ratio + segment_bonus - repeat_penalty


def transcript_looks_unstable(segments: list[dict]) -> bool:
    """Detect likely hallucination/repetition failures in transcript text."""
    if not segments:
        return True

    tokens = transcript_tokens_from_segments(segments)
    if len(tokens) < 18:
        return False

    unique_ratio = len(set(tokens)) / float(len(tokens))
    repeat_run = longest_repeated_token_run(tokens)
    span = float(segments[-1].get("end", 0.0)) - float(segments[0].get("start", 0.0))

    if unique_ratio < 0.38:
        return True
    if repeat_run >= 4:
        return True
    if len(segments) == 1 and span > 12.0 and len(tokens) > 24:
        return True

    return False


def transcribe_with_whisper(
    audio_path: str,
    model_size: str,
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
) -> list[dict]:
    """Transcribe audio using faster-whisper with Hindi/Hinglish-friendly decoding."""
    model = load_whisper_text_model(model_size)
    custom_replacements = resolve_custom_replacement_rules(
        enable_custom_replacements=enable_custom_replacements,
        custom_replacements_file=custom_replacements_file,
    )

    segments_iter, _ = model.transcribe(
        audio_path,
        language="hi",
        task="transcribe",
        temperature=0.0,
        condition_on_previous_text=False,
        initial_prompt=DEFAULT_FASTER_WHISPER_INITIAL_PROMPT or None,
        vad_filter=DEFAULT_FASTER_WHISPER_VAD_FILTER,
    )

    raw_segments = list(segments_iter)
    if not raw_segments:
        return []

    audio_duration = get_audio_duration_seconds(audio_path)
    segments = []
    for i, segment in enumerate(raw_segments):
        text = str(getattr(segment, "text", "")).strip()
        if WHISPER_ROMANIZE_OUTPUT:
            text = romanize_devanagari_text(text)
            text = normalize_hinglish_roman_text(
                text,
                custom_replacements=custom_replacements,
            )
        if not text:
            continue

        start = float(getattr(segment, "start", 0.0))
        end = float(getattr(segment, "end", start + 0.05))
        start = max(0.0, start)
        end = min(max(start + 0.05, end), audio_duration)

        segments.append(
            {
                "id": len(segments),
                "start": start,
                "end": end,
                "text": text,
            }
        )

    return segments


def transcribe(
    audio_path: str,
    transcription_backend: str | None = None,
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
) -> list[dict]:
    """Transcribe audio and return list of segments with timestamps."""
    backend = normalize_transcription_backend(transcription_backend)

    if backend.startswith("whisper-"):
        model_size = backend.split("-", 1)[1]
        try:
            segments = transcribe_with_whisper(
                audio_path,
                model_size=model_size,
                enable_custom_replacements=enable_custom_replacements,
                custom_replacements_file=custom_replacements_file,
            )
            if segments:
                selected_model_size = model_size

                if model_size == "large-v3" and transcript_looks_unstable(segments):
                    print(
                        "large-v3 transcript looked unstable for this clip; "
                        "retrying with large-v3-turbo fallback."
                    )
                    try:
                        turbo_segments = transcribe_with_whisper(
                            audio_path,
                            model_size="large-v3-turbo",
                            enable_custom_replacements=enable_custom_replacements,
                            custom_replacements_file=custom_replacements_file,
                        )
                    except Exception as fallback_exc:
                        turbo_segments = []
                        print(
                            "large-v3-turbo fallback attempt failed: "
                            f"{fallback_exc}"
                        )

                    if turbo_segments:
                        primary_score = transcript_quality_score(segments)
                        turbo_score = transcript_quality_score(turbo_segments)
                        if turbo_score > primary_score + 0.05:
                            segments = turbo_segments
                            selected_model_size = "large-v3-turbo"
                            print(
                                "Using large-v3-turbo fallback transcript "
                                "for better stability."
                            )
                        else:
                            print(
                                "Kept large-v3 transcript after fallback "
                                "quality comparison."
                            )

                print(
                    f"Using faster-whisper ({selected_model_size}) for transcript text."
                )
                return segments
            print(
                f"faster-whisper ({model_size}) returned no segments, "
                "falling back to Apex transcript text."
            )
        except Exception as exc:
            print(
                f"faster-whisper ({model_size}) text backend failed, "
                f"falling back to Apex: {exc}"
            )

    segments = transcribe_with_apex(audio_path)
    if segments:
        print("Using Apex transcript text.")
    return segments


def transcribe_apex_words(audio_path: str) -> list[dict]:
    """Get word-level timestamps directly from the Apex transcript when available."""
    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    if audio_duration > 29.5:
        return []

    pipe = load_word_timing_pipeline()
    try:
        result = pipe(audio_path, return_timestamps="word")
    except Exception as exc:
        print(f"Apex word timestamps unavailable, falling back to timing model: {exc}")
        return []

    if not isinstance(result, dict):
        return []

    chunks = result.get("chunks") or []
    if not chunks:
        return []

    words = []
    for chunk in chunks:
        word_text = chunk.get("text", "").strip()
        start, end = chunk.get("timestamp", (None, None))
        if not word_text or start is None or end is None:
            continue
        words.append(
            {
                "text": word_text,
                "start": float(start),
                "end": float(end),
            }
        )

    return words


# ─────────────────────────────────────────────
# HINGLISH SHORT-CHUNK MODE
# ─────────────────────────────────────────────

def get_alignment_worker_script_path() -> str:
    """Return the helper script path used for WhisperX forced alignment."""
    return os.path.join(os.path.dirname(__file__), "forced_align_worker.py")


def discover_alignment_python() -> str | None:
    """Pick the Python executable that has WhisperX dependencies installed."""
    env_python = os.getenv("HINGLISHCAPS_ALIGN_PYTHON")
    candidates = [env_python] if env_python else []

    project_root = os.path.dirname(__file__)
    if os.name == "nt":
        candidates.append(
            os.path.join(project_root, ".venv-align", "Scripts", "python.exe")
        )
        candidates.append(os.path.join(project_root, "py312", "python.exe"))
    else:
        candidates.append(os.path.join(project_root, ".venv-align", "bin", "python"))
        candidates.append(os.path.join(project_root, "py312", "bin", "python"))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def discover_alignment_pythonpath() -> str | None:
    """
    Return extra site-packages path for alignment worker.

    This is needed because `.venv-align` is intentionally minimal and dependencies
    are installed straight into its site-packages folder.
    """
    env_pythonpath = os.getenv("HINGLISHCAPS_ALIGN_PYTHONPATH")
    if env_pythonpath:
        return env_pythonpath

    project_root = os.path.dirname(__file__)
    venv_root = os.path.join(project_root, ".venv-align")
    candidates = []

    if os.name == "nt":
        candidates.append(os.path.join(venv_root, "Lib", "site-packages"))
    else:
        lib_root = os.path.join(venv_root, "lib")
        if os.path.isdir(lib_root):
            for entry in os.listdir(lib_root):
                if entry.startswith("python"):
                    candidates.append(os.path.join(lib_root, entry, "site-packages"))

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    return None


def extract_forced_alignment_words(
    audio_path: str, model_size: str = FORCED_ALIGNMENT_MODEL_SIZE
) -> list[dict]:
    """
    Extract speech-aligned word timings via WhisperX (true forced alignment).

    Returns an empty list when alignment tooling is unavailable so callers can
    safely fall back to the legacy timing model.
    """
    audio_stat = None
    try:
        audio_stat = os.stat(audio_path)
    except OSError:
        pass

    cache_key = (
        audio_path,
        getattr(audio_stat, "st_mtime_ns", None),
        getattr(audio_stat, "st_size", None),
        model_size,
    )
    if cache_key in _forced_alignment_words_cache:
        return _forced_alignment_words_cache[cache_key]

    worker_python = discover_alignment_python()
    worker_script = get_alignment_worker_script_path()
    if not worker_python or not os.path.isfile(worker_script):
        _forced_alignment_words_cache[cache_key] = []
        return []

    output_json = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, dir=os.path.dirname(audio_path)
        ) as tmp_output:
            output_json = tmp_output.name

        command = [
            worker_python,
            worker_script,
            "--audio",
            audio_path,
            "--output-json",
            output_json,
            "--model-size",
            model_size,
            "--language",
            "hi",
            "--compute-type",
            FORCED_ALIGNMENT_COMPUTE_TYPE,
            "--align-model-name",
            WHISPERX_ALIGNMENT_MODEL_NAME,
        ]
        if FORCED_ALIGNMENT_INITIAL_PROMPT:
            command.extend(["--initial-prompt", FORCED_ALIGNMENT_INITIAL_PROMPT])

        worker_env = os.environ.copy()
        worker_pythonpath = discover_alignment_pythonpath()
        if worker_pythonpath:
            existing_path = worker_env.get("PYTHONPATH", "")
            worker_env["PYTHONPATH"] = (
                f"{worker_pythonpath}{os.pathsep}{existing_path}"
                if existing_path
                else worker_pythonpath
            )

        tmp_root = os.path.join(os.path.dirname(__file__), ".tmp_py")
        os.makedirs(tmp_root, exist_ok=True)
        worker_env["TMP"] = tmp_root
        worker_env["TEMP"] = tmp_root

        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FORCED_ALIGNMENT_TIMEOUT_SECONDS,
            check=False,
            env=worker_env,
        )

        if process.returncode != 0:
            details = ""
            if output_json and os.path.exists(output_json):
                try:
                    with open(output_json, "r", encoding="utf-8") as handle:
                        error_payload = json.load(handle)
                    details = str(error_payload.get("error", "")).strip()
                except Exception:
                    details = ""

            if not details:
                details = (process.stderr or process.stdout or "").strip()

            if details:
                print(
                    "Forced alignment worker failed, falling back to timing model: "
                    f"{details.splitlines()[-1]}"
                )
            else:
                print(
                    "Forced alignment worker failed with no details, "
                    "falling back to timing model."
                )
            _forced_alignment_words_cache[cache_key] = []
            return []

        with open(output_json, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        payload_words = payload.get("words", [])
        if not isinstance(payload_words, list):
            _forced_alignment_words_cache[cache_key] = []
            return []

        words = []
        for word_info in payload_words:
            if not isinstance(word_info, dict):
                continue

            word_text = str(word_info.get("text", "")).strip()
            start = word_info.get("start")
            end = word_info.get("end")
            if not word_text or start is None or end is None:
                continue

            start_value = float(start)
            end_value = float(end)
            if end_value <= start_value:
                continue

            words.append(
                {
                    "text": word_text,
                    "start": start_value,
                    "end": end_value,
                }
            )

        _forced_alignment_words_cache[cache_key] = words
        return words

    except subprocess.TimeoutExpired:
        print("Forced alignment timed out, falling back to timing model.")
        _forced_alignment_words_cache[cache_key] = []
        return []
    except Exception as exc:
        print(f"Forced alignment unavailable, falling back to timing model: {exc}")
        _forced_alignment_words_cache[cache_key] = []
        return []
    finally:
        if output_json and os.path.exists(output_json):
            try:
                os.remove(output_json)
            except OSError:
                pass


def load_timing_model(model_size: str = "base"):
    """Load and cache the timing-only Whisper model used for word boundaries."""
    if model_size not in _timing_model_cache:
        print(f"Loading timing model for word boundaries: {model_size} ...")
        _timing_model_cache[model_size] = whisper.load_model(model_size)
    return _timing_model_cache[model_size]


def extract_timing_words(audio_path: str, model_size: str = "base") -> list[dict]:
    """Extract approximate speech-word timings from audio."""
    cache_key = (audio_path, model_size)
    if cache_key in _timing_words_cache:
        return _timing_words_cache[cache_key]

    model = load_timing_model(model_size)
    result = whisper_timestamped.transcribe_timestamped(
        model,
        audio_path,
        task="transcribe",
        verbose=False,
    )

    timing_words = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_text = word_info.get("text", "").strip()
            start = word_info.get("start")
            end = word_info.get("end")
            if not word_text or start is None or end is None:
                continue
            timing_words.append(
                {
                    "text": word_text,
                    "start": float(start),
                    "end": float(end),
                }
            )

    _timing_words_cache[cache_key] = timing_words
    return timing_words


def extract_faster_whisper_timing_words(
    audio_path: str, model_size: str
) -> list[dict]:
    """Extract word timings from faster-whisper directly."""
    audio_stat = None
    try:
        audio_stat = os.stat(audio_path)
    except OSError:
        pass

    cache_key = (
        audio_path,
        getattr(audio_stat, "st_mtime_ns", None),
        getattr(audio_stat, "st_size", None),
        model_size,
        DEFAULT_FASTER_WHISPER_DEVICE,
        DEFAULT_FASTER_WHISPER_COMPUTE_TYPE,
        DEFAULT_FASTER_WHISPER_VAD_FILTER,
    )
    if cache_key in _faster_whisper_timing_words_cache:
        return _faster_whisper_timing_words_cache[cache_key]

    try:
        model = load_whisper_text_model(model_size)
        segment_iter, _ = model.transcribe(
            audio_path,
            language="hi",
            task="transcribe",
            temperature=0.0,
            condition_on_previous_text=False,
            initial_prompt=DEFAULT_FASTER_WHISPER_INITIAL_PROMPT or None,
            vad_filter=DEFAULT_FASTER_WHISPER_VAD_FILTER,
            word_timestamps=True,
        )
        segments = list(segment_iter)
    except Exception as exc:
        print(f"faster-whisper word timestamp extraction failed: {exc}")
        _faster_whisper_timing_words_cache[cache_key] = []
        return []

    words = []
    for segment in segments:
        for word_info in getattr(segment, "words", None) or []:
            word_text = str(getattr(word_info, "word", "")).strip()
            start = getattr(word_info, "start", None)
            end = getattr(word_info, "end", None)
            if not word_text or start is None or end is None:
                continue
            start_value = float(start)
            end_value = float(end)
            if end_value <= start_value:
                continue
            words.append(
                {
                    "text": word_text,
                    "start": start_value,
                    "end": end_value,
                }
            )

    _faster_whisper_timing_words_cache[cache_key] = words
    return words


def is_timing_word_coverage_sufficient(
    source_segments: list[dict], timing_words: list[dict]
) -> bool:
    """Return True when timing words reasonably cover transcript span/content."""
    if not source_segments or not timing_words:
        return False

    source_word_count = sum(
        len(str(segment.get("text", "")).split()) for segment in source_segments
    )
    if source_word_count <= 0:
        return False

    source_start = float(source_segments[0].get("start", 0.0))
    source_end = float(source_segments[-1].get("end", source_start + 0.05))
    source_span = max(0.05, source_end - source_start)

    timing_start = float(timing_words[0].get("start", 0.0))
    timing_end = float(timing_words[-1].get("end", timing_start))
    timing_span = max(0.0, timing_end - timing_start)

    if source_word_count <= 4:
        min_word_target = 2
    else:
        min_word_target = max(4, int(math.ceil(source_word_count * 0.35)))
    min_span_target = max(1.0, source_span * 0.35)

    if len(timing_words) < min_word_target or timing_span < min_span_target:
        return False

    source_tokens = [
        normalize_alignment_token(word_text)
        for segment in source_segments
        for word_text in str(segment.get("text", "")).split()
    ]
    source_tokens = [token for token in source_tokens if token]
    timing_tokens = [
        normalize_alignment_token(str(word_info.get("text", "")))
        for word_info in timing_words
    ]
    timing_tokens = [token for token in timing_tokens if token]

    if len(source_tokens) >= 4 and len(timing_tokens) >= 4:
        _, alignment_score = find_best_token_shift(
            source_tokens,
            timing_tokens,
            max_shift=min(12, max(0, len(timing_tokens) - 1)),
        )
        if alignment_score < 0.46:
            return False

    return True


def percentile(values: list[float], pct: float) -> float:
    """Return a percentile from a non-empty list of numeric values."""
    if not values:
        raise ValueError("percentile() needs a non-empty list")
    if len(values) == 1:
        return float(values[0])

    sorted_values = sorted(float(v) for v in values)
    index = max(0.0, min(1.0, pct)) * (len(sorted_values) - 1)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return sorted_values[lower]

    fraction = index - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def estimate_activity_end(audio_path: str, min_start: float = 0.0) -> float | None:
    """
    Estimate when strong speech activity ends using RMS energy windows.

    This is used as a safety net when alignment models return timestamps that
    collapse the conversation too early.
    """
    try:
        with wave.open(audio_path, "rb") as wf:
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            total_frames = wf.getnframes()
            audio_buffer = wf.readframes(total_frames)
    except Exception:
        return None

    if sample_rate <= 0 or sample_width <= 0 or total_frames <= 0:
        return None

    window_seconds = 0.03
    window_frames = max(1, int(sample_rate * window_seconds))
    rms_values: list[float] = []

    for frame_start in range(0, total_frames, window_frames):
        frame_end = min(total_frames, frame_start + window_frames)
        byte_start = frame_start * sample_width
        byte_end = frame_end * sample_width
        chunk = audio_buffer[byte_start:byte_end]
        if not chunk:
            continue
        rms_values.append(float(audioop.rms(chunk, sample_width)))

    non_zero = [value for value in rms_values if value > 0.0]
    if not non_zero:
        return None

    noise_floor = percentile(non_zero, 0.25)
    loud_floor = percentile(non_zero, 0.95)
    if loud_floor <= 0:
        return None

    min_window_index = max(0, int(min_start / window_seconds))
    duration = total_frames / float(sample_rate)
    selected_end = None

    # Prefer tighter thresholds first to avoid extending into low-energy
    # tail noise after speech has ended.
    for threshold_factor in (0.70, 0.60, 0.50):
        activity_threshold = max(
            120.0, noise_floor + (loud_floor - noise_floor) * threshold_factor
        )

        active_indices = [
            index
            for index, rms_value in enumerate(rms_values)
            if index >= min_window_index and rms_value >= activity_threshold
        ]
        if not active_indices:
            continue

        # Find the last contiguous active run (allowing short pauses).
        runs: list[tuple[int, int]] = []
        run_start = active_indices[0]
        run_end = active_indices[0]
        for index in active_indices[1:]:
            if index - run_end <= 8:
                run_end = index
                continue
            runs.append((run_start, run_end))
            run_start = index
            run_end = index
        runs.append((run_start, run_end))

        # Ignore tiny blips and choose the last meaningful run.
        meaningful_runs = [
            (start, end)
            for start, end in runs
            if (end - start + 1) * window_seconds >= 0.18
        ]
        if not meaningful_runs:
            continue

        candidate_end = min(duration, (meaningful_runs[-1][1] + 1) * window_seconds)
        if candidate_end <= min_start:
            continue

        selected_end = candidate_end
        break

    return selected_end


def maybe_expand_alignment_window(
    aligned_words: list[dict], audio_path: str, media_duration: float | None = None
) -> list[dict]:
    """
    Expand a collapsed word timeline when alignment stops far before speech end.

    Keeps relative in-word timing while stretching the overall window.
    """
    if not aligned_words:
        return aligned_words

    current_start = float(aligned_words[0]["start"])
    current_end = float(aligned_words[-1]["end"])
    if current_end <= current_start + 0.2:
        return aligned_words

    activity_end = estimate_activity_end(audio_path, min_start=current_start)
    if activity_end is None:
        return aligned_words

    if media_duration is not None:
        activity_end = min(float(media_duration), activity_end)

    extension = activity_end - current_end
    if extension < 1.2:
        return aligned_words

    old_span = current_end - current_start
    new_span = activity_end - current_start
    if old_span <= 1e-6 or new_span <= old_span:
        return aligned_words

    scale = new_span / old_span
    if scale > 2.8 and extension > 8.0:
        # Guardrail against overly aggressive stretching in noisy tracks.
        return aligned_words

    print(
        "Expanding word timing window based on speech activity: "
        f"{current_end:.3f}s -> {activity_end:.3f}s"
    )

    stretched_words = []
    for word_info in aligned_words:
        raw_start = float(word_info["start"])
        raw_end = float(word_info["end"])
        relative_start = (raw_start - current_start) / old_span
        relative_end = (raw_end - current_start) / old_span

        stretched_start = current_start + relative_start * new_span
        stretched_end = current_start + relative_end * new_span
        stretched_end = max(stretched_start + 0.02, stretched_end)

        stretched_words.append(
            {
                "text": word_info["text"],
                "start": stretched_start,
                "end": stretched_end,
            }
        )

    return stretched_words


def build_uniform_chunks(
    source_segments: list[dict], words_per_line: int = 2
) -> list[dict]:
    """Fallback chunker when timing words are unavailable."""
    grouped_segments = []
    min_duration = 0.05

    for source_segment in source_segments:
        words = source_segment["text"].split()
        if not words:
            continue

        total_words = len(words)
        segment_start = source_segment["start"]
        segment_end = max(segment_start + min_duration, source_segment["end"])
        segment_duration = segment_end - segment_start

        for start_index in range(0, total_words, words_per_line):
            end_index = min(start_index + words_per_line, total_words)
            text = " ".join(words[start_index:end_index]).strip()
            if not text:
                continue

            chunk_start = segment_start + segment_duration * (start_index / total_words)
            if end_index == total_words:
                chunk_end = segment_end
            else:
                chunk_end = segment_start + segment_duration * (end_index / total_words)
            chunk_end = max(chunk_start + min_duration, chunk_end)

            grouped_segments.append(
                {
                    "id": len(grouped_segments),
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": text,
                }
            )

    return grouped_segments


def build_segment_timed_chunks(
    source_segment: dict, timing_words: list[dict], words_per_line: int = 2
) -> list[dict]:
    """Build short chunks for one source segment using only local timing words."""
    words = source_segment["text"].split()
    if not words:
        return []

    segment_start = float(source_segment["start"])
    segment_end = max(segment_start + 0.05, float(source_segment["end"]))

    if not timing_words:
        return build_uniform_chunks([source_segment], words_per_line)

    speech_start = max(segment_start, timing_words[0]["start"])
    speech_end = min(segment_end, timing_words[-1]["end"])

    if speech_end <= speech_start:
        return build_uniform_chunks([source_segment], words_per_line)

    total_words = len(words)
    total_timing_words = len(timing_words)
    chunk_count = (total_words + words_per_line - 1) // words_per_line

    # If the timing pass found fewer usable words than caption chunks,
    # split inside the detected speech window instead of stretching the text.
    if total_timing_words < chunk_count:
        return build_uniform_chunks(
            [{**source_segment, "start": speech_start, "end": speech_end}],
            words_per_line,
        )

    grouped_segments = []
    min_duration = 0.05
    previous_end = speech_start

    for start_index in range(0, total_words, words_per_line):
        end_index = min(start_index + words_per_line, total_words)
        text = " ".join(words[start_index:end_index]).strip()
        if not text:
            continue

        timing_start_index = min(
            total_timing_words - 1,
            (start_index * total_timing_words) // total_words,
        )
        timing_end_index = max(
            timing_start_index + 1,
            (end_index * total_timing_words + total_words - 1) // total_words,
        )
        timing_end_index = min(total_timing_words, timing_end_index)

        chunk_start = max(previous_end, timing_words[timing_start_index]["start"])
        raw_end = timing_words[timing_end_index - 1]["end"]
        chunk_end = raw_end if end_index < total_words else speech_end
        chunk_end = min(segment_end, speech_end, chunk_end)
        chunk_end = max(chunk_start + min_duration, chunk_end)

        if chunk_end > segment_end:
            chunk_end = segment_end

        if chunk_end <= chunk_start:
            continue

        grouped_segments.append(
            {
                "id": len(grouped_segments),
                "start": chunk_start,
                "end": chunk_end,
                "text": text,
            }
        )
        previous_end = chunk_end

    return grouped_segments


def build_timed_chunks(
    source_segments: list[dict], timing_words: list[dict], words_per_line: int = 2
) -> list[dict]:
    """Assign Apex Hinglish text onto local speech spans detected by timing words."""
    if not source_segments or not timing_words:
        return []

    grouped_segments = []
    timing_index = 0
    total_timing_words = len(timing_words)

    for source_segment in source_segments:
        segment_start = float(source_segment["start"])
        segment_end = max(segment_start + 0.05, float(source_segment["end"]))

        while (
            timing_index < total_timing_words
            and timing_words[timing_index]["end"] <= segment_start
        ):
            timing_index += 1

        local_timing_words = []
        scan_index = timing_index
        while scan_index < total_timing_words:
            word_info = timing_words[scan_index]
            if word_info["start"] >= segment_end:
                break
            if word_info["end"] > segment_start:
                local_timing_words.append(word_info)
            scan_index += 1

        grouped_segments.extend(
            build_segment_timed_chunks(
                source_segment, local_timing_words, words_per_line
            )
        )
        timing_index = scan_index

    return [{**segment, "id": index} for index, segment in enumerate(grouped_segments)]


def build_uniform_word_sequence(
    source_segment: dict, segment_start: float | None = None, segment_end: float | None = None
) -> list[dict]:
    """Assign evenly spaced timings to each word inside one source segment."""
    words = source_segment["text"].split()
    if not words:
        return []

    start = float(source_segment["start"] if segment_start is None else segment_start)
    end = float(source_segment["end"] if segment_end is None else segment_end)
    end = max(start + 0.05, end)
    duration = end - start
    total_words = len(words)

    aligned_words = []
    for index, word_text in enumerate(words):
        word_start = start + duration * (index / total_words)
        word_end = end if index + 1 == total_words else start + duration * ((index + 1) / total_words)
        word_end = max(word_start + 0.02, word_end)
        aligned_words.append(
            {
                "text": word_text,
                "start": word_start,
                "end": word_end,
            }
        )

    return aligned_words


def build_segment_aligned_word_sequence(
    source_segment: dict, timing_words: list[dict]
) -> list[dict]:
    """Map each Apex word to a local speech timing span for one segment."""
    words = source_segment["text"].split()
    if not words:
        return []

    segment_start = float(source_segment["start"])
    segment_end = max(segment_start + 0.05, float(source_segment["end"]))

    if not timing_words:
        return build_uniform_word_sequence(source_segment)

    speech_start = max(segment_start, timing_words[0]["start"])
    speech_end = min(segment_end, timing_words[-1]["end"])
    if speech_end <= speech_start:
        return build_uniform_word_sequence(source_segment)

    total_words = len(words)
    total_timing_words = len(timing_words)

    if total_timing_words < total_words:
        # If local timing words are sparse, keep original segment span instead of
        # compressing everything into a short detected speech pocket.
        return build_uniform_word_sequence(source_segment)

    aligned_words = []
    previous_end = speech_start

    for index, word_text in enumerate(words):
        timing_start_index = min(
            total_timing_words - 1,
            (index * total_timing_words) // total_words,
        )
        timing_end_index = max(
            timing_start_index + 1,
            ((index + 1) * total_timing_words + total_words - 1) // total_words,
        )
        timing_end_index = min(total_timing_words, timing_end_index)

        word_start = max(previous_end, timing_words[timing_start_index]["start"])
        raw_end = timing_words[timing_end_index - 1]["end"]
        word_end = raw_end if index + 1 < total_words else speech_end
        word_end = min(segment_end, speech_end, word_end)
        word_end = max(word_start + 0.02, word_end)

        aligned_words.append(
            {
                "text": word_text,
                "start": word_start,
                "end": word_end,
            }
        )
        previous_end = word_end

    return aligned_words


def normalize_alignment_token(text: str) -> str:
    """Normalize token text so transcript/timing words can be compared robustly."""
    if not text:
        return ""

    normalized = romanize_devanagari_text(str(text))
    normalized = normalize_hinglish_roman_text(normalized)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", normalized).lower()
    return normalized


def token_similarity_score(source_token: str, timing_token: str) -> float:
    """Return a fuzzy token similarity score in [0, 1]."""
    if not source_token or not timing_token:
        return 0.0

    if source_token == timing_token:
        return 1.0

    score = difflib.SequenceMatcher(None, source_token, timing_token).ratio()
    if source_token in timing_token or timing_token in source_token:
        score = max(score, 0.82)

    # Prefix agreement is a strong signal for Hinglish variants
    # like "gaya"/"gae" or "aukaat"/"ukad".
    for prefix_len, prefix_score in ((5, 0.86), (4, 0.78), (3, 0.68)):
        if (
            len(source_token) >= prefix_len
            and len(timing_token) >= prefix_len
            and source_token[:prefix_len] == timing_token[:prefix_len]
        ):
            score = max(score, prefix_score)
            break

    return score


def find_best_token_shift(
    reference_tokens: list[str],
    candidate_tokens: list[str],
    max_shift: int,
) -> tuple[int, float]:
    """Find shift that best aligns candidate token sequence to reference tokens."""
    if not reference_tokens or not candidate_tokens:
        return 0, 0.0

    best_shift = 0
    best_score = -1.0

    bounded_max_shift = min(max_shift, max(0, len(candidate_tokens) - 1))
    for shift in range(0, bounded_max_shift + 1):
        remaining = len(candidate_tokens) - shift
        compare_count = min(16, len(reference_tokens), remaining)
        if compare_count < 4:
            continue

        score_sum = 0.0
        for index in range(compare_count):
            score_sum += token_similarity_score(
                reference_tokens[index], candidate_tokens[shift + index]
            )

        score = (score_sum / float(compare_count)) - (shift * 0.01)
        if score > best_score:
            best_score = score
            best_shift = shift

    if best_score < 0:
        return 0, 0.0
    return best_shift, best_score


def trim_timing_words_to_transcript(
    source_segments: list[dict], timing_words: list[dict]
) -> list[dict]:
    """
    Remove obvious leading/trailing timing-word hallucinations.

    WhisperX can occasionally prepend or append stray words in long silence,
    which shifts otherwise-good caption timings slightly out of sync.
    """
    if not source_segments or not timing_words:
        return timing_words

    source_tokens = [
        normalize_alignment_token(word_text)
        for segment in source_segments
        for word_text in str(segment.get("text", "")).split()
    ]
    source_tokens = [token for token in source_tokens if token]
    timing_tokens = [
        normalize_alignment_token(str(word_info.get("text", "")))
        for word_info in timing_words
    ]
    timing_tokens = [token for token in timing_tokens if token]

    if len(source_tokens) < 4 or len(timing_tokens) < 4:
        return timing_words

    max_shift = min(10, max(0, len(timing_tokens) - 4))
    lead_shift, lead_score = find_best_token_shift(
        source_tokens,
        timing_tokens,
        max_shift=max_shift,
    )
    if lead_shift > 0 and lead_score >= 0.58:
        timing_words = timing_words[lead_shift:]
        timing_tokens = timing_tokens[lead_shift:]
    else:
        lead_shift = 0

    tail_shift = 0
    tail_score = 0.0
    if len(timing_tokens) >= 4 and len(source_tokens) >= 4:
        tail_shift, tail_score = find_best_token_shift(
            list(reversed(source_tokens)),
            list(reversed(timing_tokens)),
            max_shift=min(10, max(0, len(timing_tokens) - 4)),
        )
        if tail_shift > 0 and tail_score >= 0.58:
            timing_words = timing_words[:-tail_shift]
        else:
            tail_shift = 0

    if lead_shift or tail_shift:
        print(
            "Adjusted timing token window for better sync: "
            f"-{lead_shift} leading, -{tail_shift} trailing word(s)."
        )

    return timing_words


def build_aligned_word_sequence_by_segment_window(
    source_segments: list[dict], timing_words: list[dict]
) -> list[dict]:
    """Build timed words by aligning timing windows inside each source segment."""
    if not source_segments:
        return []

    if not timing_words:
        aligned_words = []
        for source_segment in source_segments:
            aligned_words.extend(build_uniform_word_sequence(source_segment))
        return aligned_words

    timing_words = trim_timing_words_to_transcript(source_segments, timing_words)
    if not timing_words:
        aligned_words = []
        for source_segment in source_segments:
            aligned_words.extend(build_uniform_word_sequence(source_segment))
        return aligned_words

    aligned_words = []
    timing_index = 0
    total_timing_words = len(timing_words)

    for source_segment in source_segments:
        segment_start = float(source_segment["start"])
        segment_end = max(segment_start + 0.05, float(source_segment["end"]))
        relaxed_segment_end = segment_end + 1.0

        while (
            timing_index < total_timing_words
            and timing_words[timing_index]["end"] <= segment_start
        ):
            timing_index += 1

        next_timing_index = timing_index
        while next_timing_index < total_timing_words:
            if timing_words[next_timing_index]["start"] >= segment_end:
                break
            next_timing_index += 1

        local_timing_words = []
        scan_index = timing_index
        while scan_index < total_timing_words:
            word_info = timing_words[scan_index]
            if word_info["start"] >= relaxed_segment_end:
                break
            if word_info["end"] > segment_start:
                local_timing_words.append(word_info)
            scan_index += 1

        aligned_words.extend(
            build_segment_aligned_word_sequence(source_segment, local_timing_words)
        )
        timing_index = next_timing_index

    return aligned_words


def build_aligned_word_sequence(
    source_segments: list[dict], timing_words: list[dict]
) -> list[dict]:
    """Build a sequential list of timed words for the full transcript."""
    if not source_segments:
        return []

    if not timing_words:
        aligned_words = []
        for source_segment in source_segments:
            aligned_words.extend(build_uniform_word_sequence(source_segment))
        return aligned_words

    timing_words = trim_timing_words_to_transcript(source_segments, timing_words)
    if not timing_words:
        aligned_words = []
        for source_segment in source_segments:
            aligned_words.extend(build_uniform_word_sequence(source_segment))
        return aligned_words

    # Very short clips often come as a few large source segments with big silent
    # gaps. Segment-window alignment preserves those gaps better than global
    # interpolation in that scenario.
    if len(source_segments) <= 4:
        local_aligned_words = build_aligned_word_sequence_by_segment_window(
            source_segments, timing_words
        )
        if local_aligned_words:
            return local_aligned_words

    speech_start = max(0.0, float(timing_words[0]["start"]))
    # Trust timing-model end as the primary speech boundary. Any needed
    # expansion beyond this is handled by audio-activity heuristics later.
    speech_end = max(speech_start + 0.05, float(timing_words[-1]["end"]))

    filtered_timing_words = [
        word_info
        for word_info in timing_words
        if word_info["end"] > speech_start and word_info["start"] < speech_end
    ]

    if not filtered_timing_words:
        aligned_words = []
        for source_segment in source_segments:
            aligned_words.extend(build_uniform_word_sequence(source_segment))
        return aligned_words

    apex_words = []
    for source_segment in source_segments:
        apex_words.extend(source_segment["text"].split())

    if not apex_words:
        return []

    total_apex_words = len(apex_words)
    total_timing_words = len(filtered_timing_words)

    # When timing words are too sparse compared with transcript words, use a
    # smooth distribution across the detected speech window instead of forcing
    # many transcript words onto a small set of timing anchors.
    if total_timing_words < total_apex_words:
        anchor_starts = [float(word_info["start"]) for word_info in filtered_timing_words]
        anchor_ends = [float(word_info["end"]) for word_info in filtered_timing_words]
        max_anchor_index = max(1, total_timing_words - 1)

        def interpolate(anchors: list[float], position: float) -> float:
            if not anchors:
                return 0.0
            if len(anchors) == 1:
                return anchors[0]

            bounded = max(0.0, min(float(max_anchor_index), position))
            left_index = int(math.floor(bounded))
            right_index = int(math.ceil(bounded))
            if left_index == right_index:
                return anchors[left_index]

            blend = bounded - left_index
            return anchors[left_index] + (anchors[right_index] - anchors[left_index]) * blend

        aligned_words = []
        previous_end = max(speech_start, anchor_starts[0])

        for index, word_text in enumerate(apex_words):
            if total_apex_words == 1:
                start_position = 0.0
                end_position = float(max_anchor_index)
            else:
                start_position = (index * max_anchor_index) / float(total_apex_words - 1)
                end_position = ((index + 1) * max_anchor_index) / float(total_apex_words - 1)

            word_start = max(previous_end, interpolate(anchor_starts, start_position))
            if index + 1 < total_apex_words:
                word_end = interpolate(anchor_ends, end_position)
            else:
                word_end = anchor_ends[-1]

            word_end = max(word_start + 0.02, word_end)
            aligned_words.append(
                {
                    "text": word_text,
                    "start": word_start,
                    "end": word_end,
                }
            )
            previous_end = word_end

        return aligned_words

    aligned_words = []
    previous_end = max(speech_start, filtered_timing_words[0]["start"])

    for index, word_text in enumerate(apex_words):
        timing_start_index = min(
            total_timing_words - 1,
            (index * total_timing_words) // total_apex_words,
        )
        timing_end_index = max(
            timing_start_index + 1,
            ((index + 1) * total_timing_words + total_apex_words - 1)
            // total_apex_words,
        )
        timing_end_index = min(total_timing_words, timing_end_index)

        word_start = max(previous_end, filtered_timing_words[timing_start_index]["start"])
        raw_end = filtered_timing_words[timing_end_index - 1]["end"]
        word_end = raw_end if index + 1 < total_apex_words else speech_end
        word_end = min(speech_end, word_end)
        word_end = max(word_start + 0.02, word_end)

        aligned_words.append(
            {
                "text": word_text,
                "start": word_start,
                "end": word_end,
            }
        )
        previous_end = word_end

    return aligned_words


def plain_caption_text(words: list[str]) -> str:
    """Join caption words into a single plain string."""
    return " ".join(words).strip()


def format_double_line_text(words: list[str], max_chars: int) -> str:
    """Split text into one or two readable lines for double-line captions."""
    full_text = plain_caption_text(words)
    if len(words) < 2 or len(full_text) <= math.ceil(max_chars / 2):
        return full_text

    best_lines = None
    best_score = None

    for split_index in range(1, len(words)):
        first_line = plain_caption_text(words[:split_index])
        second_line = plain_caption_text(words[split_index:])
        score = (
            max(len(first_line), len(second_line)),
            abs(len(first_line) - len(second_line)),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_lines = (first_line, second_line)

    if not best_lines:
        return full_text

    return "\n".join(best_lines)


def format_caption_text(words: list[str], caption_settings: CaptionSettings) -> str:
    """Format one caption block as single or double line text."""
    if caption_settings.lines.lower() == "single":
        return plain_caption_text(words)
    return format_double_line_text(words, caption_settings.max_chars)


def build_settings_based_chunks(
    aligned_words: list[dict], caption_settings: CaptionSettings
) -> list[dict]:
    """Group timed words into captions based on character limits and pauses."""
    if not aligned_words:
        return []

    grouped_segments = []
    current_words = []
    pause_threshold = 0.18 if caption_settings.lines.lower() == "single" else 0.28
    if caption_settings.max_chars <= 20:
        pause_threshold = min(pause_threshold, 0.16)

    for word_info in aligned_words:
        word_text = word_info["text"].strip()
        if not word_text:
            continue

        if current_words:
            previous_word = current_words[-1]
            pause = max(0.0, float(word_info["start"]) - float(previous_word["end"]))
            candidate_text = plain_caption_text(
                [entry["text"] for entry in current_words] + [word_text]
            )
            punctuation_break = previous_word["text"].rstrip().endswith((".", "?", "!"))

            if (
                len(candidate_text) > caption_settings.max_chars
                or pause >= pause_threshold
                or (
                    caption_settings.lines.lower() == "single"
                    and punctuation_break
                )
                or (
                    punctuation_break
                    and pause >= 0.08
                    and len(plain_caption_text([entry["text"] for entry in current_words]))
                    >= math.ceil(caption_settings.max_chars / 2)
                )
            ):
                text_words = [entry["text"] for entry in current_words]
                grouped_segments.append(
                    {
                        "id": len(grouped_segments),
                        "start": float(current_words[0]["start"]),
                        "end": float(current_words[-1]["end"]),
                        "text": format_caption_text(text_words, caption_settings),
                    }
                )
                current_words = []

        current_words.append(word_info)

    if current_words:
        text_words = [entry["text"] for entry in current_words]
        grouped_segments.append(
            {
                "id": len(grouped_segments),
                "start": float(current_words[0]["start"]),
                "end": float(current_words[-1]["end"]),
                "text": format_caption_text(text_words, caption_settings),
            }
        )

    return grouped_segments


def build_word_count_chunks(words: list[dict], words_per_line: int = 2) -> list[dict]:
    """Fallback chunker that groups already-timed words by a fixed word count."""
    if not words:
        return []

    grouped_segments = []
    chunk_size = max(1, int(words_per_line))

    for start_index in range(0, len(words), chunk_size):
        chunk_words = words[start_index:start_index + chunk_size]
        if not chunk_words:
            continue

        grouped_segments.append(
            {
                "id": len(grouped_segments),
                "start": float(chunk_words[0]["start"]),
                "end": float(chunk_words[-1]["end"]),
                "text": plain_caption_text([entry["text"] for entry in chunk_words]),
            }
        )

    return grouped_segments


def apply_caption_preferences(
    segments: list[dict],
    caption_settings: CaptionSettings,
    fps: float,
    max_duration: float | None = None,
    enforce_min_duration: bool = True,
) -> list[dict]:
    """Apply minimum duration and frame gaps without breaking sync."""
    if not segments:
        return []

    adjusted_segments = []
    min_visible_duration = 0.05
    gap_seconds = (
        caption_settings.gap_frames / fps if fps and caption_settings.gap_frames > 0 else 0.0
    )

    for index, segment in enumerate(segments):
        start = max(0.0, float(segment["start"]))
        raw_end = max(start + min_visible_duration, float(segment["end"]))

        hard_ceiling = max_duration if max_duration is not None else raw_end
        next_start = None
        if index + 1 < len(segments):
            next_start = float(segments[index + 1]["start"])
            hard_ceiling = min(
                hard_ceiling,
                max(start + min_visible_duration, next_start - gap_seconds),
            )

        target_end = (
            max(raw_end, start + caption_settings.min_duration)
            if enforce_min_duration
            else raw_end
        )
        end = min(target_end, hard_ceiling)

        if next_start is not None and end > next_start:
            end = max(start + min_visible_duration, next_start)

        if max_duration is not None:
            end = min(end, max_duration)

        if end <= start:
            continue

        adjusted_segments.append(
            {
                **segment,
                "id": len(adjusted_segments),
                "start": start,
                "end": end,
            }
        )

    return adjusted_segments


def transcribe_word_level(
    audio_path: str,
    model_size: str = "base",
    words_per_line: int = 2,
    caption_settings: CaptionSettings | dict | None = None,
    video_path: str | None = None,
    transcription_backend: str | None = None,
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
) -> list[dict]:
    """
    Preserve the Apex Hinglish transcript while splitting segments into
    shorter word groups.

    The chunk timings are distributed proportionally within each original
    segment so the output stays close to the source timing without swapping
    to a different English-biased model.
    """
    backend = normalize_transcription_backend(transcription_backend)

    if backend == "apex":
        apex_timed_words = transcribe_apex_words(audio_path)
        if apex_timed_words:
            print("Using Apex word timestamps for short-clip alignment.")
            if caption_settings is not None:
                settings = normalize_caption_settings(caption_settings)
                media_duration = get_media_duration(video_path) if video_path else None
                speech_ceiling = float(apex_timed_words[-1]["end"])
                if media_duration is not None:
                    speech_ceiling = min(speech_ceiling, media_duration)
                fps = get_media_fps(video_path) if video_path else 30.0
                segments = build_settings_based_chunks(apex_timed_words, settings)
                segments = apply_caption_preferences(
                    segments,
                    settings,
                    fps=fps,
                    max_duration=speech_ceiling,
                    enforce_min_duration=False,
                )
                if segments:
                    return segments

            fixed_word_chunks = build_word_count_chunks(apex_timed_words, words_per_line)
            if fixed_word_chunks:
                return fixed_word_chunks

    source_segments = transcribe(
        audio_path,
        transcription_backend=backend,
        enable_custom_replacements=enable_custom_replacements,
        custom_replacements_file=custom_replacements_file,
    )
    if not source_segments:
        return []

    timing_words: list[dict] = []
    forced_alignment_words = extract_forced_alignment_words(
        audio_path, model_size=FORCED_ALIGNMENT_MODEL_SIZE
    )
    if forced_alignment_words and is_timing_word_coverage_sufficient(
        source_segments, forced_alignment_words
    ):
        timing_words = forced_alignment_words
        print("Using WhisperX forced alignment for word timings.")
    elif forced_alignment_words:
        print(
            "WhisperX forced alignment looked sparse for this clip; "
            "falling back to safer timing extraction."
        )

    if not timing_words and backend.startswith("whisper-"):
        whisper_model_size = backend.split("-", 1)[1]
        candidate_models = [whisper_model_size]
        if whisper_model_size == "large-v3":
            candidate_models.append("large-v3-turbo")

        for candidate_model_size in candidate_models:
            faster_whisper_words = extract_faster_whisper_timing_words(
                audio_path,
                model_size=candidate_model_size,
            )
            if faster_whisper_words and is_timing_word_coverage_sufficient(
                source_segments, faster_whisper_words
            ):
                timing_words = faster_whisper_words
                print(
                    "Using faster-whisper word timestamps for word timings "
                    f"({candidate_model_size})."
                )
                break

        if not timing_words and candidate_models:
            print(
                "faster-whisper timing coverage is still sparse; "
                "trying legacy timing model fallback."
            )

    if not timing_words:
        fallback_timing_words = extract_timing_words(audio_path, model_size=model_size)
        if fallback_timing_words and is_timing_word_coverage_sufficient(
            source_segments, fallback_timing_words
        ):
            timing_words = fallback_timing_words
            print("Using legacy timing model for word timings.")
        elif fallback_timing_words:
            print(
                "Legacy timing model coverage is sparse; "
                "falling back to transcript-uniform timing."
            )
    if caption_settings is not None:
        settings = normalize_caption_settings(caption_settings)
        aligned_words = build_aligned_word_sequence(source_segments, timing_words)
        if aligned_words:
            media_duration = get_media_duration(video_path) if video_path else None
            aligned_words = maybe_expand_alignment_window(
                aligned_words,
                audio_path,
                media_duration=media_duration,
            )
            speech_ceiling = float(aligned_words[-1]["end"])
            if media_duration is not None:
                speech_ceiling = min(speech_ceiling, media_duration)
            fps = get_media_fps(video_path) if video_path else 30.0
            segments = build_settings_based_chunks(aligned_words, settings)
            segments = apply_caption_preferences(
                segments,
                settings,
                fps=fps,
                max_duration=speech_ceiling,
                enforce_min_duration=False,
            )
            if segments:
                return segments

    if timing_words:
        timed_chunks = build_timed_chunks(source_segments, timing_words, words_per_line)
        if timed_chunks:
            return timed_chunks

    return build_uniform_chunks(source_segments, words_per_line)


def shift_segments(segments: list[dict], offset_seconds: float) -> list[dict]:
    """Shift segment timestamps by offset_seconds, clamping starts to >= 0."""
    if abs(offset_seconds) < 1e-9:
        return segments

    shifted = []
    min_duration = 0.05
    for seg in segments:
        start = max(0.0, seg["start"] + offset_seconds)
        end = max(start + min_duration, seg["end"] + offset_seconds)
        shifted.append({**seg, "start": start, "end": end})
    return shifted


def trim_segments_to_duration(
    segments: list[dict], max_duration: float | None
) -> list[dict]:
    """Drop or clamp segments so they stay inside the media duration."""
    if max_duration is None:
        return segments

    trimmed = []
    min_duration = 0.05

    for seg in segments:
        start = max(0.0, float(seg["start"]))
        end = min(float(seg["end"]), max_duration)

        if start >= max_duration:
            continue

        if end <= start:
            end = min(max_duration, start + min_duration)

        if end <= start:
            continue

        trimmed.append(
            {
                **seg,
                "id": len(trimmed),
                "start": start,
                "end": end,
            }
        )

    return trimmed


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
    offset_seconds: float = 0.0,
    transcription_backend: str | None = None,
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
) -> str | None:
    """
    Full pipeline for a single video:
    video → audio → transcription → caption file

    Returns the path to the generated file, or None on failure.
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    output_filename = f"{video_name}{OUTPUT_EXTENSION}"

    output_path = os.path.join(output_dir, output_filename)
    video_duration = get_media_duration(video_path)

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
            print("  Transcribing with Hinglish-preserving short caption chunks...")
            try:
                segments = transcribe_word_level(
                    audio_path,
                    words_per_line=words_per_line,
                    transcription_backend=transcription_backend,
                    enable_custom_replacements=enable_custom_replacements,
                    custom_replacements_file=custom_replacements_file,
                )
            except Exception as e:
                print(f"  Word-level transcription failed: {e}")
                return None
        else:
            print("  Transcribing... (may take a while on CPU)")
            try:
                segments = transcribe(
                    audio_path,
                    transcription_backend=transcription_backend,
                    enable_custom_replacements=enable_custom_replacements,
                    custom_replacements_file=custom_replacements_file,
                )
            except Exception as e:
                print(f"  Transcription failed: {e}")
                return None

        if not segments:
            print("No speech detected - skipping.")
            return None

        # Step 3 — detect FPS for Premiere Pro formats
        if abs(offset_seconds) >= 1e-9:
            print(f"  Applying subtitle offset: {offset_seconds:+.3f}s")
            segments = shift_segments(segments, offset_seconds)

        segments = trim_segments_to_duration(segments, video_duration)
        if not segments:
            print("No caption segments remain after trimming to video duration.")
            return None

        print("  Generating caption file (srt)...")

        # Step 4 — generate output based on format
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
    offset_seconds: float = 0.0,
    transcription_backend: str | None = None,
    enable_custom_replacements: bool | None = None,
    custom_replacements_file: str | None = None,
):
    """Process a list of video files and write caption files to output_dir."""

    total = len(videos)
    succeeded = []
    failed = []
    backend = normalize_transcription_backend(transcription_backend)

    # Load selected text backend once before the loop.
    print("─" * 60)
    if backend.startswith("whisper-"):
        model_size = backend.split("-", 1)[1]
        try:
            load_whisper_text_model(model_size)
        except Exception as exc:
            print(
                f"Failed to preload Whisper ({model_size}), "
                f"falling back to Apex text backend: {exc}"
            )
            backend = "apex"
            load_model()
    else:
        load_model()
    print("─" * 60)

    format_name = "Standard SRT"
    ext = OUTPUT_EXTENSION
    print(f"Starting batch: {total} video(s) → {format_name} ({ext})")
    print(f"Transcription backend: {backend}")
    print(
        "Custom replacements: "
        f"{'enabled' if enable_custom_replacements else 'disabled'}"
    )
    if enable_custom_replacements and custom_replacements_file:
        print(f"Custom replacement dictionary: {custom_replacements_file}")
    print(f"Output directory: {output_dir}\n")

    batch_start = time.time()

    for i, video_path in enumerate(videos, start=1):
        print(f"[{i}/{total}] {os.path.basename(video_path)}")
        video_start = time.time()

        result = process_video(
            video_path,
            output_dir,
            word_level,
            words_per_line,
            offset_seconds=offset_seconds,
            transcription_backend=backend,
            enable_custom_replacements=enable_custom_replacements,
            custom_replacements_file=custom_replacements_file,
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
            "Powered by selectable transcription backends (Whisper or Apex).\n\n"
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
        help="Enable shorter Hinglish caption chunks (about 2-3 words per line)",
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
        "--offset-seconds",
        "-os",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=(
            "Shift all subtitle timings by this amount. "
            "Use positive to delay captions, negative to start earlier."
        ),
    )
    parser.add_argument(
        "--transcription-backend",
        "-tb",
        choices=sorted(SUPPORTED_TRANSCRIPTION_BACKENDS),
        default=DEFAULT_TRANSCRIPTION_BACKEND,
        help=(
            "Transcript text engine. "
            "Use whisper-large-v3 for best quality, whisper-large-v3-turbo "
            "for a faster tradeoff, or apex for legacy Hinglish output."
        ),
    )
    parser.add_argument(
        "--enable-custom-replacements",
        action="store_true",
        help=(
            "Enable optional custom phrase replacement dictionary for "
            "Whisper romanized output."
        ),
    )
    parser.add_argument(
        "--custom-replacements-file",
        metavar="JSON_FILE",
        default=DEFAULT_CUSTOM_REPLACEMENTS_FILE or None,
        help=(
            "Path to a JSON replacement dictionary. Used only when "
            "--enable-custom-replacements is set."
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
    selected_backend = normalize_transcription_backend(args.transcription_backend)

    if args.word_level:
        print(f"Word-level mode: {args.words_per_line} words per line")

    print("Output format: Standard SRT\n")
    print(f"Transcription backend: {selected_backend}\n")
    print(
        "Custom replacements: "
        f"{'enabled' if args.enable_custom_replacements else 'disabled'}\n"
    )

    if abs(args.offset_seconds) >= 1e-9:
        print(f"Subtitle offset: {args.offset_seconds:+.3f}s\n")

    run_batch(
        videos,
        output_dir,
        args.word_level,
        args.words_per_line,
        args.offset_seconds,
        selected_backend,
        args.enable_custom_replacements,
        args.custom_replacements_file,
    )


if __name__ == "__main__":
    main()
