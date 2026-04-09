#!/usr/bin/env python3
"""
HinglishCaps - Full Web Application (Run locally)

This is the complete web interface for HinglishCaps.
Run this on your local machine with sufficient RAM (8+ GB recommended).
"""

import datetime
import html
import json
import os
import sys
import zipfile
import tempfile

print("=" * 60)
print("HinglishCaps - Full Web Application")
print("=" * 60)
print("\nWarning: This app requires significant memory (8+ GB RAM)")
print("   First run will download model files (size depends on transcription engine)")
print("   Please be patient...\n")

# Import the batch processor for transcription functions
try:
    import batch
    print("Batch processor imported")
except ImportError as e:
    print(f"Error importing batch processor: {e}")
    print("Make sure all dependencies are installed:")
    print("  pip install -r requirements_full.txt")
    sys.exit(1)

import gradio as gr

APP_CSS = """
:root {
    --hc-bg: #0d1016;
    --hc-panel: rgba(20, 24, 34, 0.82);
    --hc-panel-strong: rgba(24, 29, 41, 0.94);
    --hc-panel-soft: rgba(255, 255, 255, 0.03);
    --hc-border: rgba(255, 255, 255, 0.08);
    --hc-text: #f5f7fb;
    --hc-muted: #9aa5ba;
    --hc-accent: #ff7b36;
    --hc-accent-soft: rgba(255, 123, 54, 0.16);
    --hc-success: #51c878;
    --hc-shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
}
body {
    background:
        radial-gradient(circle at top left, rgba(255, 123, 54, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(82, 153, 255, 0.16), transparent 26%),
        linear-gradient(180deg, #0b0e14 0%, #121722 100%);
}
.gradio-container {
    max-width: 1120px !important;
    margin: 0 auto;
    padding: 28px 18px 56px !important;
}
.gradio-container .prose,
.gradio-container .prose * {
    color: var(--hc-text);
}
.hc-shell {
    position: relative;
}
.hc-hero {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--hc-border);
    border-radius: 28px;
    padding: 34px 34px 28px;
    background:
        radial-gradient(circle at top right, rgba(255, 123, 54, 0.22), transparent 24%),
        radial-gradient(circle at bottom left, rgba(70, 120, 255, 0.14), transparent 28%),
        linear-gradient(145deg, rgba(22, 27, 39, 0.96), rgba(15, 18, 26, 0.92));
    box-shadow: var(--hc-shadow);
}
.hc-hero::after {
    content: "";
    position: absolute;
    inset: auto -60px -80px auto;
    width: 280px;
    height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 123, 54, 0.18), transparent 68%);
    pointer-events: none;
}
.hc-kicker {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #ffd7c3;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
}
.hc-hero-grid {
    display: grid;
    grid-template-columns: 1.7fr 1fr;
    gap: 22px;
    margin-top: 18px;
}
.hc-hero h1 {
    margin: 0;
    font-size: clamp(2.2rem, 5vw, 3.7rem);
    line-height: 0.98;
    letter-spacing: -0.04em;
}
.hc-hero p {
    margin: 16px 0 0;
    color: #d7dff0;
    font-size: 1.05rem;
    line-height: 1.7;
    max-width: 680px;
}
.hc-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 20px;
}
.hc-chip {
    padding: 10px 14px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.05);
    color: #eef2ff;
    font-size: 0.92rem;
}
.hc-metrics {
    display: grid;
    gap: 12px;
}
.hc-metric {
    border-radius: 20px;
    padding: 18px 18px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
}
.hc-metric strong {
    display: block;
    font-size: 1.65rem;
    margin-bottom: 4px;
}
.hc-metric span {
    color: var(--hc-muted);
    font-size: 0.94rem;
    line-height: 1.45;
}
.hc-section-head {
    margin: 30px 0 16px;
}
.hc-section-head h2 {
    margin: 0;
    font-size: 1.35rem;
}
.hc-section-head p {
    margin: 8px 0 0;
    color: var(--hc-muted);
    font-size: 0.98rem;
}
.hc-panel {
    background: var(--hc-panel);
    border: 1px solid var(--hc-border);
    border-radius: 24px;
    box-shadow: var(--hc-shadow);
    backdrop-filter: blur(14px);
}
.hc-subpanel {
    background: var(--hc-panel-soft);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 18px;
    padding: 16px;
}
.hc-info-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 24px;
}
.hc-info-card {
    border-radius: 20px;
    padding: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
    border: 1px solid rgba(255,255,255,0.08);
}
.hc-info-card h3 {
    margin: 0 0 8px;
    font-size: 1rem;
}
.hc-info-card p {
    margin: 0;
    color: var(--hc-muted);
    line-height: 1.55;
    font-size: 0.94rem;
}
.tabs {
    margin-top: 20px;
}
.tab-nav {
    gap: 10px;
    padding: 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
.tab-nav button {
    border-radius: 999px !important;
    padding: 10px 18px !important;
    font-weight: 700 !important;
}
.tabitem {
    padding-top: 18px;
}
.block,
.gr-box,
.gr-panel,
.gr-form,
.gr-group {
    border-radius: 20px !important;
}
.gr-box,
.gr-group,
.gr-form {
    background: var(--hc-panel-soft) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
}
.gr-button-primary,
button.primary {
    background: linear-gradient(135deg, #ff8936, #ff622e) !important;
    border: none !important;
    color: white !important;
    font-weight: 800 !important;
    letter-spacing: 0.01em;
    min-height: 54px;
    box-shadow: 0 16px 32px rgba(255, 110, 42, 0.28);
}
.gr-button-primary:hover,
button.primary:hover {
    filter: brightness(1.04);
}
.gradio-file,
.gradio-video,
.gradio-dropdown,
.gradio-slider,
.gradio-checkbox {
    background: transparent !important;
}
.status-shell {
    min-height: 110px;
    display: flex;
    align-items: stretch;
}
.status-card {
    width: 100%;
    min-height: 110px;
    border-radius: 18px;
    border: 1px solid #2f3441;
    background: linear-gradient(180deg, #1d2028 0%, #171920 100%);
    color: #f6f7fb;
    padding: 18px 20px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.status-card.status-ready {
    border-color: #2f3441;
}
.status-card.status-success {
    background: linear-gradient(180deg, #11271a 0%, #0e2116 100%);
    border-color: #2d7a4f;
}
.status-card.status-error {
    background: linear-gradient(180deg, #2a1718 0%, #211112 100%);
    border-color: #8e4047;
}
.status-card.status-warning {
    background: linear-gradient(180deg, #2b2315 0%, #221b11 100%);
    border-color: #9d7b39;
}
.status-label {
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #9ea7ba;
    margin-bottom: 8px;
}
.status-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 6px;
    color: #ffffff;
}
.status-message {
    font-size: 0.95rem;
    line-height: 1.5;
    color: #d7dceb;
    word-break: break-word;
}
.result-row {
    align-items: stretch;
    gap: 14px;
}
.result-row > div {
    min-height: 110px;
}
.result-row .gradio-file {
    border-radius: 18px;
    overflow: hidden;
}
.hc-footer {
    margin-top: 28px;
    border-radius: 24px;
    padding: 24px;
    background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.03));
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.hc-footer-grid {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 22px;
}
.hc-footer h3 {
    margin: 0 0 10px;
    font-size: 1.1rem;
}
.hc-footer ol,
.hc-footer ul {
    margin: 0;
    padding-left: 1.2rem;
    color: #d8deee;
    line-height: 1.85;
}
.hc-footer p {
    margin: 0 0 12px;
    color: var(--hc-muted);
    line-height: 1.65;
}
@media (max-width: 900px) {
    .hc-hero-grid,
    .hc-info-grid,
    .hc-footer-grid {
        grid-template-columns: 1fr;
    }
    .hc-hero {
        padding: 24px 22px;
        border-radius: 22px;
    }
}
"""


PRESET_STORAGE_PATH = os.path.join(
    os.path.dirname(__file__), "caption_presets.json"
)

CAPTION_FORMAT_OPTIONS = ["Subtitle"]
CAPTION_STREAM_OPTIONS = ["None"]
CAPTION_STYLE_OPTIONS = ["None"]
CAPTION_LINE_OPTIONS = ["Single", "Double"]
TRANSCRIPTION_ENGINE_LABEL_TO_ID = {
    "Whisper Large v3 (Recommended Quality)": "whisper-large-v3",
    "Whisper Large v3 Turbo (Fastest)": "whisper-large-v3-turbo",
    "Whisper Medium (Lighter)": "whisper-medium",
    "Whisper Small (Lightest)": "whisper-small",
    "Whisper Base (Smallest)": "whisper-base",
    "Apex Hinglish (Legacy)": "apex",
}
DEFAULT_TRANSCRIPTION_ENGINE_LABEL = "Whisper Large v3 (Recommended Quality)"

BUILTIN_CAPTION_PRESETS = {
    "Subtitle default": {
        "format_name": "Subtitle",
        "stream": "None",
        "style": "None",
        "max_chars": 42,
        "min_duration": 3.0,
        "gap_frames": 0,
        "lines": "Double",
    },
    "YouTube standard": {
        "format_name": "Subtitle",
        "stream": "None",
        "style": "None",
        "max_chars": 42,
        "min_duration": 2.0,
        "gap_frames": 0,
        "lines": "Double",
    },
    "Shorts single line": {
        "format_name": "Subtitle",
        "stream": "None",
        "style": "None",
        "max_chars": 18,
        "min_duration": 0.8,
        "gap_frames": 1,
        "lines": "Single",
    },
    "Reels punchy": {
        "format_name": "Subtitle",
        "stream": "None",
        "style": "None",
        "max_chars": 14,
        "min_duration": 0.6,
        "gap_frames": 2,
        "lines": "Single",
    },
}


def caption_settings_to_dict(settings):
    """Normalize raw preset values into the backend caption settings shape."""
    normalized = batch.normalize_caption_settings(settings)
    return {
        "format_name": normalized.format_name,
        "stream": normalized.stream,
        "style": normalized.style,
        "max_chars": normalized.max_chars,
        "min_duration": normalized.min_duration,
        "gap_frames": normalized.gap_frames,
        "lines": normalized.lines,
    }


def load_custom_presets():
    """Read user-saved caption presets from disk."""
    if not os.path.exists(PRESET_STORAGE_PATH):
        return {}

    try:
        with open(PRESET_STORAGE_PATH, "r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    presets = {}
    for name, settings in raw_data.items():
        presets[str(name)] = caption_settings_to_dict(settings)
    return presets


def save_custom_presets(presets):
    """Persist user-saved presets to disk."""
    with open(PRESET_STORAGE_PATH, "w", encoding="utf-8") as handle:
        json.dump(presets, handle, indent=2, ensure_ascii=True)


def get_caption_presets():
    """Return built-in presets plus any user-saved presets."""
    presets = {
        name: caption_settings_to_dict(settings)
        for name, settings in BUILTIN_CAPTION_PRESETS.items()
    }
    presets.update(load_custom_presets())
    return presets


def get_preset_choices():
    """Return preset dropdown choices in stable order."""
    return list(get_caption_presets().keys())


def get_preset_settings(preset_name):
    """Return settings for a preset name, falling back to the default preset."""
    presets = get_caption_presets()
    if preset_name in presets:
        return presets[preset_name]
    return presets["Subtitle default"]


def build_caption_settings(
    format_name,
    stream,
    style,
    max_chars,
    min_duration,
    gap_frames,
    lines,
):
    """Build the caption settings payload passed to the backend."""
    return caption_settings_to_dict(
        {
            "format_name": format_name,
            "stream": stream,
            "style": style,
            "max_chars": max_chars,
            "min_duration": min_duration,
            "gap_frames": gap_frames,
            "lines": lines,
        }
    )


def resolve_transcription_backend(engine_label):
    """Map UI engine label to backend id understood by batch.py."""
    return TRANSCRIPTION_ENGINE_LABEL_TO_ID.get(
        str(engine_label or "").strip(),
        TRANSCRIPTION_ENGINE_LABEL_TO_ID[DEFAULT_TRANSCRIPTION_ENGINE_LABEL],
    )


def load_preset_controls(preset_name):
    """Return UI values for a selected preset."""
    settings = get_preset_settings(preset_name)
    return (
        settings["format_name"],
        settings["stream"],
        settings["style"],
        settings["max_chars"],
        settings["min_duration"],
        settings["gap_frames"],
        settings["lines"],
        preset_name,
    )


def save_preset_values(
    preset_name,
    format_name,
    stream,
    style,
    max_chars,
    min_duration,
    gap_frames,
    lines,
):
    """Save a custom preset and return updated dropdown metadata."""
    name = (preset_name or "").strip()
    if not name:
        return None, render_status(
            "Enter a preset name before saving.",
            "warning",
            "Preset name needed",
        )

    if name in BUILTIN_CAPTION_PRESETS:
        return None, render_status(
            "Built-in presets are read-only. Save under a new name instead.",
            "warning",
            "Choose a new preset name",
        )

    presets = load_custom_presets()
    presets[name] = build_caption_settings(
        format_name,
        stream,
        style,
        max_chars,
        min_duration,
        gap_frames,
        lines,
    )
    save_custom_presets(presets)
    return name, render_status(
        f"Saved preset '{name}'.",
        "success",
        "Preset saved",
    )


def delete_preset_value(preset_name):
    """Delete a custom preset and return the next selected preset name."""
    name = (preset_name or "").strip()
    if not name:
        return None, render_status(
            "Select a preset to delete.",
            "warning",
            "Nothing selected",
        )

    if name in BUILTIN_CAPTION_PRESETS:
        return None, render_status(
            "Built-in presets cannot be deleted.",
            "warning",
            "Preset locked",
        )

    presets = load_custom_presets()
    if name not in presets:
        return None, render_status(
            f"Preset '{name}' was not found.",
            "warning",
            "Preset missing",
        )

    presets.pop(name, None)
    save_custom_presets(presets)
    next_name = "Subtitle default"
    return next_name, render_status(
        f"Deleted preset '{name}'.",
        "success",
        "Preset deleted",
    )


def refresh_preset_dropdowns(selected_name, status_html):
    """Return synchronized dropdown updates for both tabs."""
    choices = get_preset_choices()
    fallback = selected_name if selected_name in choices else "Subtitle default"
    update = gr.update(choices=choices, value=fallback)
    return update, update, fallback, fallback, status_html


def save_preset_and_refresh(
    preset_name,
    format_name,
    stream,
    style,
    max_chars,
    min_duration,
    gap_frames,
    lines,
):
    """Save a preset, then refresh both preset dropdowns."""
    selected_name, status_html = save_preset_values(
        preset_name,
        format_name,
        stream,
        style,
        max_chars,
        min_duration,
        gap_frames,
        lines,
    )
    fallback = (preset_name or "").strip() or "Subtitle default"
    return refresh_preset_dropdowns(selected_name or fallback, status_html)


def delete_preset_and_refresh(preset_name):
    """Delete a preset, then refresh both preset dropdowns."""
    selected_name, status_html = delete_preset_value(preset_name)
    fallback = (preset_name or "").strip() or "Subtitle default"
    return refresh_preset_dropdowns(selected_name or fallback, status_html)


def reserve_output_dir():
    """Create a temp directory that survives long enough for Gradio downloads."""
    return tempfile.mkdtemp(prefix="hinglishcaps_")


def resolve_path(file_value):
    """Extract a local filesystem path from Gradio file values."""
    if isinstance(file_value, str):
        return file_value
    if hasattr(file_value, "name"):
        return file_value.name
    if isinstance(file_value, dict):
        return file_value.get("path") or file_value.get("name")
    raise ValueError("Unsupported uploaded file format")


def render_status(message, tone="ready", title=None):
    """Render a styled status card for the UI."""
    titles = {
        "ready": "Ready",
        "success": "Completed",
        "error": "Something went wrong",
        "warning": "Check result",
    }
    safe_message = html.escape(message)
    safe_title = html.escape(title or titles.get(tone, "Status"))
    return f"""
    <div class="status-shell">
      <div class="status-card status-{tone}">
        <div class="status-label">Status</div>
        <div class="status-title">{safe_title}</div>
        <div class="status-message">{safe_message}</div>
      </div>
    </div>
    """

def build_caption_content(segments):
    """Build the final SRT subtitle content."""
    return batch.segments_to_srt(segments)


def generate_captions(
    video_path,
    word_level=False,
    transcription_engine=DEFAULT_TRANSCRIPTION_ENGINE_LABEL,
    enable_custom_replacements=False,
    custom_replacements_file="",
    caption_preset="Subtitle default",
    format_name="Subtitle",
    stream="None",
    style="None",
    max_chars=42,
    min_duration=3.0,
    gap_frames=0,
    lines="Double",
    offset_seconds=0.0,
):
    """Generate captions for a single video."""
    if not video_path:
        return None, render_status("Please upload a video first.", "warning", "Upload needed")
    
    try:
        video_path = resolve_path(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        transcription_backend = resolve_transcription_backend(transcription_engine)
        custom_replacements_path = (custom_replacements_file or "").strip() or None

        # Extract audio
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = batch.extract_audio(video_path, tmp)
            
            # Transcribe
            if word_level:
                caption_settings = build_caption_settings(
                    format_name,
                    stream,
                    style,
                    max_chars,
                    min_duration,
                    gap_frames,
                    lines,
                )
                segments = batch.transcribe_word_level(
                    audio_path,
                    video_path=video_path,
                    caption_settings=caption_settings,
                    transcription_backend=transcription_backend,
                    enable_custom_replacements=enable_custom_replacements,
                    custom_replacements_file=custom_replacements_path,
                )
            else:
                segments = batch.transcribe(
                    audio_path,
                    transcription_backend=transcription_backend,
                    enable_custom_replacements=enable_custom_replacements,
                    custom_replacements_file=custom_replacements_path,
                )
            
            if not segments:
                return None, render_status("No speech detected in the video.", "warning", "No speech found")

            if abs(offset_seconds) >= 1e-9:
                segments = batch.shift_segments(segments, float(offset_seconds))

            segments = batch.trim_segments_to_duration(
                segments, batch.get_media_duration(video_path)
            )
            if not segments:
                return None, render_status(
                    "No captions remained after trimming to the video duration.",
                    "warning",
                    "Nothing to export",
                )

            # Generate output
            content = build_caption_content(segments)
            filename = f"{video_name}_captions{batch.OUTPUT_EXTENSION}"
            
            # Save to temp file
            output_dir = reserve_output_dir()
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            success_message = "Captions generated successfully and ready to download."
            if word_level:
                success_message = (
                    f"Captions generated successfully with preset '{caption_preset}' "
                    f"using {transcription_engine}."
                )
            if enable_custom_replacements:
                success_message += " Custom replacement dictionary: enabled."
            return output_path, render_status(success_message, "success")
    
    except Exception as e:
        return None, render_status(str(e), "error")

def generate_captions_batch(
    video_files,
    word_level=False,
    transcription_engine=DEFAULT_TRANSCRIPTION_ENGINE_LABEL,
    enable_custom_replacements=False,
    custom_replacements_file="",
    caption_preset="Subtitle default",
    format_name="Subtitle",
    stream="None",
    style="None",
    max_chars=42,
    min_duration=3.0,
    gap_frames=0,
    lines="Double",
    offset_seconds=0.0,
):
    """Generate captions for multiple videos."""
    if not video_files:
        return None, render_status("Please upload video files first.", "warning", "Upload needed")
    
    try:
        results = []
        failed = []
        transcription_backend = resolve_transcription_backend(transcription_engine)
        custom_replacements_path = (custom_replacements_file or "").strip() or None
        
        for video_file in video_files:
            video_label = getattr(video_file, "name", None) or str(video_file)
            try:
                video_path = resolve_path(video_file)
                video_label = os.path.basename(video_path)

                # Extract audio
                with tempfile.TemporaryDirectory() as tmp:
                    audio_path = batch.extract_audio(video_path, tmp)
                    
                    # Transcribe
                    if word_level:
                        caption_settings = build_caption_settings(
                            format_name,
                            stream,
                            style,
                            max_chars,
                            min_duration,
                            gap_frames,
                            lines,
                        )
                        segments = batch.transcribe_word_level(
                            audio_path,
                            video_path=video_path,
                            caption_settings=caption_settings,
                            transcription_backend=transcription_backend,
                            enable_custom_replacements=enable_custom_replacements,
                            custom_replacements_file=custom_replacements_path,
                        )
                    else:
                        segments = batch.transcribe(
                            audio_path,
                            transcription_backend=transcription_backend,
                            enable_custom_replacements=enable_custom_replacements,
                            custom_replacements_file=custom_replacements_path,
                        )
                    
                    if not segments:
                        failed.append(f"{video_label}: No speech detected")
                        continue

                    if abs(offset_seconds) >= 1e-9:
                        segments = batch.shift_segments(segments, float(offset_seconds))

                    segments = batch.trim_segments_to_duration(
                        segments, batch.get_media_duration(video_path)
                    )
                    if not segments:
                        failed.append(
                            f"{video_label}: No captions remained after trimming to the video duration"
                        )
                        continue

                    # Generate output
                    video_name = os.path.splitext(os.path.basename(video_path))[0]
                    content = build_caption_content(segments)
                    filename = f"{video_name}_captions{batch.OUTPUT_EXTENSION}"
                    
                    # Save to temp directory
                    output_dir = reserve_output_dir()
                    output_path = os.path.join(output_dir, filename)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    results.append((output_path, filename))
            
            except Exception as e:
                failed.append(f"{video_label}: {str(e)}")
                continue
        
        if not results:
            return None, render_status(f"All videos failed. {', '.join(failed)}", "error")
        
        # Create ZIP file
        zip_dir = reserve_output_dir()
        zip_path = os.path.join(zip_dir, "hinglishcaps_batch.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, filename in results:
                zipf.write(file_path, filename)
        
        status = f"Processed {len(results)} video(s)"
        status += f" using {transcription_engine}"
        if enable_custom_replacements:
            status += " with custom replacements"
        if word_level:
            status += f" with preset '{caption_preset}'"
        if failed:
            status += f", failed {len(failed)}: {', '.join(failed[:3])}"
            if len(failed) > 3:
                status += f"... (and {len(failed)-3} more)"
        
        tone = "warning" if failed else "success"
        title = "Processed with warnings" if failed else "Batch complete"
        return zip_path, render_status(status, tone, title)
    
    except Exception as e:
        return None, render_status(str(e), "error")

def build_ui():
    """Build the Gradio interface."""
    with gr.Blocks(title="HinglishCaps - Auto Captions") as demo:
        gr.HTML(f"<style>{APP_CSS}</style>")

        gr.HTML("""
        <div class="hc-shell">
          <section class="hc-hero">
            <div class="hc-kicker">HinglishCaps Studio</div>
            <div class="hc-hero-grid">
              <div>
                <h1>Captions built for Hindi, English, and real Hinglish speech.</h1>
                <p>
                  Turn raw video into clean subtitle files with a local workflow designed for Indian accents,
                  code-switching, and quick editor handoff. Upload once, generate captions, and export with
                  clarity instead of wrestling with generic caption tools.
                </p>
                <div class="hc-chip-row">
                  <div class="hc-chip">Single video or batch uploads</div>
                  <div class="hc-chip">Word-level timestamps</div>
                  <div class="hc-chip">Clean SRT exports</div>
                </div>
              </div>
                <div class="hc-metrics">
                <div class="hc-metric">
                  <strong>1 format</strong>
                  <span>Exports clean SRT subtitle files that drop directly into most editing workflows.</span>
                </div>
                <div class="hc-metric">
                  <strong>Local-first</strong>
                  <span>Built for local runs with enough memory, so you can process real files without cloud friction.</span>
                </div>
                <div class="hc-metric">
                  <strong>Hinglish-aware</strong>
                  <span>Uses a model tuned for Indian speech patterns and mixed-language dialogue.</span>
                </div>
              </div>
            </div>
          </section>
        </div>
        """)

        gr.HTML("""
        <div class="hc-info-grid">
          <div class="hc-info-card">
            <h3>Upload your source</h3>
            <p>Drop a single clip for quick subtitle generation or multiple files when you are processing a full content batch.</p>
          </div>
          <div class="hc-info-card">
            <h3>Tune the timing</h3>
            <p>Switch on word-level captions when you want shorter, punchier subtitle chunks while keeping the Hinglish transcript style.</p>
          </div>
          <div class="hc-info-card">
            <h3>Export for editing</h3>
            <p>Generate a clean SRT file you can import into your editor and style there.</p>
          </div>
        </div>
        """)

        gr.HTML("""
        <div class="hc-section-head">
          <h2>Choose your workflow</h2>
          <p>Both flows use the same transcription engine. Pick the one that matches how you are working today.</p>
        </div>
        """)

        preset_choices = get_preset_choices()

        with gr.Tabs(elem_classes="tabs"):
            with gr.TabItem("Single Video", id="single"):
                gr.HTML("""
                <div class="hc-panel">
                  <div style="padding: 22px 22px 10px;">
                    <div class="hc-section-head" style="margin:0 0 14px;">
                      <h2>Single Video</h2>
                      <p>Preview a clip, adjust caption settings, and export one finished subtitle file.</p>
                    </div>
                  </div>
                </div>
                """)

                with gr.Group(elem_classes="hc-panel"):
                    video_input = gr.Video(label="Upload Video", interactive=True)

                with gr.Group(elem_classes="hc-panel"):
                    with gr.Row():
                        word_level_check = gr.Checkbox(label="Word-level timestamps", value=False)
                        transcription_engine_dropdown = gr.Dropdown(
                            choices=list(TRANSCRIPTION_ENGINE_LABEL_TO_ID.keys()),
                            value=DEFAULT_TRANSCRIPTION_ENGINE_LABEL,
                            label="Transcription Engine",
                            info="Whisper engines are auto-converted to Hinglish roman script.",
                        )
                        custom_replacements_check = gr.Checkbox(
                            label="Enable Custom Phrase Dictionary",
                            value=False,
                            info="Optional and off by default.",
                        )

                    with gr.Group(
                        visible=False, elem_classes="hc-subpanel"
                    ) as single_custom_replacements_panel:
                        custom_replacements_file_input = gr.Textbox(
                            value="",
                            label="Custom Dictionary JSON Path",
                            placeholder="C:\\path\\to\\replacements.json",
                            info=(
                                "Optional per-channel phrase fixes. "
                                "Use only when you want custom rules."
                            ),
                        )

                    offset_seconds_input = gr.Number(
                        value=0.0,
                        precision=3,
                        label="Subtitle Offset (seconds)",
                        info="Positive delays captions, negative shows them earlier.",
                    )

                    with gr.Group(visible=False, elem_classes="hc-subpanel") as single_word_level_panel:
                        single_preset_status = gr.HTML(
                            render_status(
                                "Load a preset or save your current settings for repeatable word-level captions.",
                                "ready",
                                "Caption presets",
                            )
                        )
                        with gr.Row():
                            caption_preset_dropdown = gr.Dropdown(
                                choices=preset_choices,
                                value="Subtitle default",
                                label="Caption Preset",
                            )
                            preset_name_input = gr.Textbox(
                                value="Subtitle default",
                                label="Preset Name",
                                placeholder="Save these settings as a custom preset",
                            )
                        with gr.Row():
                            save_preset_btn = gr.Button("Save Preset")
                            delete_preset_btn = gr.Button("Delete Preset")
                        with gr.Accordion(
                            "Captioning Preferences (format, max/min length, lines)",
                            open=True,
                        ):
                            format_dropdown = gr.Dropdown(
                                choices=CAPTION_FORMAT_OPTIONS,
                                value="Subtitle",
                                label="Format",
                                interactive=False,
                            )
                            stream_dropdown = gr.Dropdown(
                                choices=CAPTION_STREAM_OPTIONS,
                                value="None",
                                label="Stream",
                                interactive=False,
                            )
                            style_dropdown = gr.Dropdown(
                                choices=CAPTION_STYLE_OPTIONS,
                                value="None",
                                label="Style",
                                interactive=False,
                            )
                            max_chars_slider = gr.Slider(
                                minimum=10,
                                maximum=70,
                                value=42,
                                step=1,
                                label="Maximum length in characters",
                            )
                            min_duration_slider = gr.Slider(
                                minimum=0.2,
                                maximum=4.0,
                                value=3.0,
                                step=0.1,
                                label="Minimum duration in seconds",
                            )
                            gap_frames_slider = gr.Slider(
                                minimum=0,
                                maximum=12,
                                value=0,
                                step=1,
                                label="Gap between captions (frames)",
                            )
                            lines_radio = gr.Radio(
                                choices=CAPTION_LINE_OPTIONS,
                                value="Double",
                                label="Lines",
                            )

                run_btn = gr.Button("Generate Captions", variant="primary", size="lg")

                with gr.Row(elem_classes="result-row"):
                    output = gr.File(label="Download Captions")
                    status_box = gr.HTML(render_status("Upload a video and generate captions.", "ready"))

            with gr.TabItem("Batch Processing", id="batch"):
                gr.HTML("""
                <div class="hc-panel">
                  <div style="padding: 22px 22px 10px;">
                    <div class="hc-section-head" style="margin:0 0 14px;">
                      <h2>Batch Processing</h2>
                      <p>Queue multiple videos, process them together, and download a single ZIP with all captions.</p>
                    </div>
                  </div>
                </div>
                """)

                with gr.Group(elem_classes="hc-panel"):
                    batch_video_input = gr.File(
                        label="Upload Videos",
                        file_count="multiple",
                        file_types=["video"],
                        interactive=True
                    )

                with gr.Group(elem_classes="hc-panel"):
                    with gr.Row():
                        batch_word_level_check = gr.Checkbox(label="Word-level timestamps", value=False)
                        batch_transcription_engine_dropdown = gr.Dropdown(
                            choices=list(TRANSCRIPTION_ENGINE_LABEL_TO_ID.keys()),
                            value=DEFAULT_TRANSCRIPTION_ENGINE_LABEL,
                            label="Transcription Engine",
                            info="Whisper engines are auto-converted to Hinglish roman script.",
                        )
                        batch_custom_replacements_check = gr.Checkbox(
                            label="Enable Custom Phrase Dictionary",
                            value=False,
                            info="Optional and off by default.",
                        )

                    with gr.Group(
                        visible=False, elem_classes="hc-subpanel"
                    ) as batch_custom_replacements_panel:
                        batch_custom_replacements_file_input = gr.Textbox(
                            value="",
                            label="Custom Dictionary JSON Path",
                            placeholder="C:\\path\\to\\replacements.json",
                            info=(
                                "Optional per-channel phrase fixes for batch mode."
                            ),
                        )

                    batch_offset_seconds_input = gr.Number(
                        value=0.0,
                        precision=3,
                        label="Subtitle Offset (seconds)",
                        info="Positive delays captions, negative shows them earlier.",
                    )

                    with gr.Group(visible=False, elem_classes="hc-subpanel") as batch_word_level_panel:
                        batch_preset_status = gr.HTML(
                            render_status(
                                "Use the same caption rules across a whole batch with presets.",
                                "ready",
                                "Caption presets",
                            )
                        )
                        with gr.Row():
                            batch_caption_preset_dropdown = gr.Dropdown(
                                choices=preset_choices,
                                value="Subtitle default",
                                label="Caption Preset",
                            )
                            batch_preset_name_input = gr.Textbox(
                                value="Subtitle default",
                                label="Preset Name",
                                placeholder="Save these settings as a custom preset",
                            )
                        with gr.Row():
                            batch_save_preset_btn = gr.Button("Save Preset")
                            batch_delete_preset_btn = gr.Button("Delete Preset")
                        with gr.Accordion(
                            "Captioning Preferences (format, max/min length, lines)",
                            open=True,
                        ):
                            batch_format_dropdown = gr.Dropdown(
                                choices=CAPTION_FORMAT_OPTIONS,
                                value="Subtitle",
                                label="Format",
                                interactive=False,
                            )
                            batch_stream_dropdown = gr.Dropdown(
                                choices=CAPTION_STREAM_OPTIONS,
                                value="None",
                                label="Stream",
                                interactive=False,
                            )
                            batch_style_dropdown = gr.Dropdown(
                                choices=CAPTION_STYLE_OPTIONS,
                                value="None",
                                label="Style",
                                interactive=False,
                            )
                            batch_max_chars_slider = gr.Slider(
                                minimum=10,
                                maximum=70,
                                value=42,
                                step=1,
                                label="Maximum length in characters",
                            )
                            batch_min_duration_slider = gr.Slider(
                                minimum=0.2,
                                maximum=4.0,
                                value=3.0,
                                step=0.1,
                                label="Minimum duration in seconds",
                            )
                            batch_gap_frames_slider = gr.Slider(
                                minimum=0,
                                maximum=12,
                                value=0,
                                step=1,
                                label="Gap between captions (frames)",
                            )
                            batch_lines_radio = gr.Radio(
                                choices=CAPTION_LINE_OPTIONS,
                                value="Double",
                                label="Lines",
                            )

                batch_run_btn = gr.Button("Process All Videos", variant="primary", size="lg")

                with gr.Row(elem_classes="result-row"):
                    batch_output = gr.File(label="Download ZIP File")
                    batch_status_box = gr.HTML(render_status("Upload one or more videos to start batch processing.", "ready"))

        word_level_check.change(
            lambda enabled: gr.update(visible=enabled),
            inputs=[word_level_check],
            outputs=[single_word_level_panel],
        )
        batch_word_level_check.change(
            lambda enabled: gr.update(visible=enabled),
            inputs=[batch_word_level_check],
            outputs=[batch_word_level_panel],
        )
        custom_replacements_check.change(
            lambda enabled: gr.update(visible=enabled),
            inputs=[custom_replacements_check],
            outputs=[single_custom_replacements_panel],
        )
        batch_custom_replacements_check.change(
            lambda enabled: gr.update(visible=enabled),
            inputs=[batch_custom_replacements_check],
            outputs=[batch_custom_replacements_panel],
        )

        caption_preset_dropdown.change(
            load_preset_controls,
            inputs=[caption_preset_dropdown],
            outputs=[
                format_dropdown,
                stream_dropdown,
                style_dropdown,
                max_chars_slider,
                min_duration_slider,
                gap_frames_slider,
                lines_radio,
                preset_name_input,
            ],
        )
        batch_caption_preset_dropdown.change(
            load_preset_controls,
            inputs=[batch_caption_preset_dropdown],
            outputs=[
                batch_format_dropdown,
                batch_stream_dropdown,
                batch_style_dropdown,
                batch_max_chars_slider,
                batch_min_duration_slider,
                batch_gap_frames_slider,
                batch_lines_radio,
                batch_preset_name_input,
            ],
        )

        save_preset_btn.click(
            save_preset_and_refresh,
            inputs=[
                preset_name_input,
                format_dropdown,
                stream_dropdown,
                style_dropdown,
                max_chars_slider,
                min_duration_slider,
                gap_frames_slider,
                lines_radio,
            ],
            outputs=[
                caption_preset_dropdown,
                batch_caption_preset_dropdown,
                preset_name_input,
                batch_preset_name_input,
                single_preset_status,
            ],
        )
        batch_save_preset_btn.click(
            save_preset_and_refresh,
            inputs=[
                batch_preset_name_input,
                batch_format_dropdown,
                batch_stream_dropdown,
                batch_style_dropdown,
                batch_max_chars_slider,
                batch_min_duration_slider,
                batch_gap_frames_slider,
                batch_lines_radio,
            ],
            outputs=[
                caption_preset_dropdown,
                batch_caption_preset_dropdown,
                preset_name_input,
                batch_preset_name_input,
                batch_preset_status,
            ],
        )
        delete_preset_btn.click(
            delete_preset_and_refresh,
            inputs=[caption_preset_dropdown],
            outputs=[
                caption_preset_dropdown,
                batch_caption_preset_dropdown,
                preset_name_input,
                batch_preset_name_input,
                single_preset_status,
            ],
        )
        batch_delete_preset_btn.click(
            delete_preset_and_refresh,
            inputs=[batch_caption_preset_dropdown],
            outputs=[
                caption_preset_dropdown,
                batch_caption_preset_dropdown,
                preset_name_input,
                batch_preset_name_input,
                batch_preset_status,
            ],
        )

        run_btn.click(
            generate_captions,
            inputs=[
                video_input,
                word_level_check,
                transcription_engine_dropdown,
                custom_replacements_check,
                custom_replacements_file_input,
                caption_preset_dropdown,
                format_dropdown,
                stream_dropdown,
                style_dropdown,
                max_chars_slider,
                min_duration_slider,
                gap_frames_slider,
                lines_radio,
                offset_seconds_input,
            ],
            outputs=[output, status_box],
        )
        batch_run_btn.click(
            generate_captions_batch,
            inputs=[
                batch_video_input,
                batch_word_level_check,
                batch_transcription_engine_dropdown,
                batch_custom_replacements_check,
                batch_custom_replacements_file_input,
                batch_caption_preset_dropdown,
                batch_format_dropdown,
                batch_stream_dropdown,
                batch_style_dropdown,
                batch_max_chars_slider,
                batch_min_duration_slider,
                batch_gap_frames_slider,
                batch_lines_radio,
                batch_offset_seconds_input,
            ],
            outputs=[batch_output, batch_status_box],
        )

        gr.HTML("""
        <section class="hc-footer">
          <div class="hc-footer-grid">
            <div>
              <h3>How to use it</h3>
              <ol>
                <li>Upload one video or a batch of videos.</li>
                <li>Enable word-level timing if you want Premiere-style caption controls for shorter Hinglish subtitle chunks.</li>
                <li>Pick a caption preset or tune max length, minimum duration, gaps, and line layout.</li>
                <li>Use subtitle offset only if captions need to appear earlier or later.</li>
                <li>Generate captions and download the final SRT file or ZIP.</li>
              </ol>
            </div>
            <div>
              <h3>Good to know</h3>
              <p>The first run downloads the transcription model once, so it will feel slower up front and much faster after that.</p>
              <ul>
                <li>Best with clear dialogue and low background noise.</li>
                <li>Supports MP4, MOV, AVI, MKV, WEBM, FLV, M4V, and WMV.</li>
                <li>Exports standard SRT subtitle files.</li>
              </ul>
            </div>
          </div>
        </section>
        """)
    
    return demo

if __name__ == "__main__":
    port = os.environ.get("PORT") or os.environ.get("GRADIO_SERVER_PORT") or "7860"

    print("\nStarting web server...")
    print(f"Open http://localhost:{port} in your browser")
    print("Loading AI model (this may take a minute)...")
    
    app = build_ui()
    launch_kwargs = {
        "server_name": "127.0.0.1",
        "share": False,
        "debug": False,
        "server_port": int(port),
    }
    app.launch(**launch_kwargs)
