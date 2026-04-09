import argparse
import json
import os
import traceback

DEFAULT_FORCED_ALIGN_MODEL = os.getenv("HINGLISHCAPS_FORCED_ALIGN_MODEL", "large-v3")
DEFAULT_FORCED_ALIGN_COMPUTE = os.getenv("HINGLISHCAPS_FORCED_ALIGN_COMPUTE_TYPE", "int8")
DEFAULT_FORCED_ALIGN_INITIAL_PROMPT = os.getenv(
    "HINGLISHCAPS_FORCED_ALIGN_INITIAL_PROMPT",
    "Yeh Hindi-Hinglish speech hai. Indian names, places, and acronyms ko dhyan se transcribe karo.",
)
DEFAULT_ALIGN_MODEL_NAME = os.getenv(
    "HINGLISHCAPS_WHISPERX_ALIGN_MODEL", "facebook/mms-300m"
)


def ensure_nltk_punkt_tab() -> None:
    """Make sure WhisperX sentence splitter resources are present."""
    import nltk

    resource_key = "tokenizers/punkt_tab/english/"
    local_nltk_data = os.path.join(os.path.dirname(__file__), ".nltk_data")
    os.makedirs(local_nltk_data, exist_ok=True)

    if local_nltk_data not in nltk.data.path:
        nltk.data.path.insert(0, local_nltk_data)

    try:
        nltk.data.find(resource_key)
        return
    except LookupError:
        pass

    nltk.download("punkt_tab", download_dir=local_nltk_data, quiet=True)
    nltk.data.find(resource_key)


def normalize_word_text(raw_text: str) -> str:
    """Clean token text for downstream chunking."""
    text = (raw_text or "").replace("\n", " ").replace("\t", " ").strip()
    if not text:
        return ""
    return " ".join(text.split())


def extract_aligned_words(aligned_result: dict) -> list[dict]:
    """Flatten WhisperX aligned word metadata into simple records."""
    words = []
    for segment in aligned_result.get("segments", []):
        for word in segment.get("words", []) or []:
            if not isinstance(word, dict):
                continue

            text = normalize_word_text(str(word.get("word", "")))
            start = word.get("start")
            end = word.get("end")
            if not text or start is None or end is None:
                continue

            start_value = float(start)
            end_value = float(end)
            if end_value <= start_value:
                continue

            words.append(
                {
                    "text": text,
                    "start": start_value,
                    "end": end_value,
                }
            )

    return words


def run_alignment(
    audio_path: str,
    model_size: str,
    language: str,
    device: str,
    compute_type: str,
    align_model_name: str,
    initial_prompt: str,
) -> dict:
    """Run WhisperX transcription + forced alignment and return normalized output."""
    ensure_nltk_punkt_tab()

    import whisperx

    audio = whisperx.load_audio(audio_path)
    asr_options = {"condition_on_previous_text": False}
    prompt = (initial_prompt or "").strip()
    if prompt:
        asr_options["initial_prompt"] = prompt

    model = whisperx.load_model(
        model_size,
        device,
        compute_type=compute_type,
        language=language,
        asr_options=asr_options,
    )
    transcript = model.transcribe(audio)
    detected_language = str(transcript.get("language") or language or "hi")

    # Try requested aligner first, then WhisperX defaults.
    # This keeps `facebook/mms-300m` preference while preserving robustness on
    # environments where that model id is incompatible with WhisperX loaders.
    alignment_attempts: list[tuple[str, str | None]] = [
        (detected_language, align_model_name or None),
        (detected_language, None),
        ("en", align_model_name or None),
        ("en", None),
    ]
    seen = set()
    align_error = None
    align_model = None
    align_metadata = None
    align_language = detected_language
    alignment_model_used = None

    for attempt_language, attempt_model_name in alignment_attempts:
        key = (attempt_language, attempt_model_name)
        if key in seen:
            continue
        seen.add(key)

        try:
            align_model, align_metadata = whisperx.load_align_model(
                language_code=attempt_language,
                device=device,
                model_name=attempt_model_name,
            )
            align_language = attempt_language
            alignment_model_used = (
                attempt_model_name
                if attempt_model_name is not None
                else "whisperx-default"
            )
            break
        except Exception as exc:
            align_error = exc

    if align_model is None or align_metadata is None:
        raise RuntimeError(
            "Failed to load any WhisperX alignment model "
            f"(requested='{align_model_name}')."
        ) from align_error

    aligned = whisperx.align(
        transcript.get("segments", []),
        align_model,
        align_metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    words = extract_aligned_words(aligned)

    return {
        "words": words,
        "detected_language": detected_language,
        "alignment_language": align_language,
        "requested_alignment_model": align_model_name,
        "alignment_model_used": alignment_model_used,
        "segment_count": len(aligned.get("segments", [])),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WhisperX forced alignment worker")
    parser.add_argument("--audio", required=True, help="Path to mono WAV audio")
    parser.add_argument(
        "--output-json", required=True, help="Where alignment JSON should be written"
    )
    parser.add_argument(
        "--model-size",
        default=DEFAULT_FORCED_ALIGN_MODEL,
        help="WhisperX ASR model size",
    )
    parser.add_argument("--language", default="hi", help="Preferred language code")
    parser.add_argument("--device", default="cpu", help="Torch device")
    parser.add_argument(
        "--compute-type",
        default=DEFAULT_FORCED_ALIGN_COMPUTE,
        help="WhisperX compute type (e.g., int8, float16, float32)",
    )
    parser.add_argument(
        "--align-model-name",
        default=DEFAULT_ALIGN_MODEL_NAME,
        help="Alignment model id (e.g., facebook/mms-300m)",
    )
    parser.add_argument(
        "--initial-prompt",
        default=DEFAULT_FORCED_ALIGN_INITIAL_PROMPT,
        help="Initial prompt passed into faster-whisper decoding",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        payload = run_alignment(
            audio_path=args.audio,
            model_size=args.model_size,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
            align_model_name=args.align_model_name,
            initial_prompt=args.initial_prompt,
        )
        with open(args.output_json, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True)
        return 0
    except Exception as exc:
        error_payload = {
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "audio": args.audio,
        }
        output_dir = os.path.dirname(args.output_json)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as handle:
            json.dump(error_payload, handle, ensure_ascii=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
