#!/usr/bin/env python3
"""
Transcribe Dr Andrew Corbett's Daily Bible Reading videos.

Usage:
    python scripts/transcribe.py 91              # transcribe day 91
    python scripts/transcribe.py 91 108          # transcribe days 91 through 108
    python scripts/transcribe.py 91 --force      # re-transcribe even if file exists
    python scripts/transcribe.py --list          # show what's already done
    python scripts/transcribe.py --next          # transcribe the next undone day
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---- Configuration ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
READING_PLAN = PROJECT_ROOT / "data" / "reading_plan.json"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
AUDIO_DIR = PROJECT_ROOT / "audio"  # gitignored, temp working dir

# Adjust this path if your whisper model lives elsewhere
WHISPER_MODEL = Path.home() / "whisper-models" / "ggml-base.en.bin"

# Command names — script auto-detects which one you have installed
WHISPER_COMMANDS = ["whisper-cli", "whisper-cpp"]


def find_whisper_command():
    """Find which whisper-cpp binary is installed."""
    for cmd in WHISPER_COMMANDS:
        if shutil.which(cmd):
            return cmd
    return None


def load_plan():
    """Load the 366-day reading plan."""
    with open(READING_PLAN) as f:
        return json.load(f)


def get_reading(day_num):
    """Get a specific day's reading info."""
    plan = load_plan()
    for reading in plan["readings"]:
        if reading["day"] == day_num:
            return reading
    raise ValueError(f"Day {day_num} not found in reading plan")


def transcript_path(day_num):
    """Where the transcript markdown file lives."""
    return TRANSCRIPTS_DIR / f"day-{day_num:03d}.md"


def transcript_exists(day_num):
    return transcript_path(day_num).exists()


def download_audio(video_url, output_path):
    """Download audio from YouTube using yt-dlp."""
    print(f"  Downloading audio from {video_url}")
    cmd = [
        "yt-dlp",
        "-x",  # extract audio
        "--audio-format", "wav",  # whisper-cpp prefers wav
        "--audio-quality", "0",  # best quality
        "-o", str(output_path.with_suffix(".%(ext)s")),
        "--no-playlist",
        video_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  yt-dlp failed:\n{result.stderr}")
        return False
    return True


def convert_to_whisper_format(input_wav, output_wav):
    """whisper-cpp requires 16kHz mono WAV. Convert to that format."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_wav),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def run_whisper(whisper_cmd, audio_path, output_base):
    """Run whisper-cpp on the audio file."""
    print(f"  Transcribing with {whisper_cmd}...")
    cmd = [
        whisper_cmd,
        "-m", str(WHISPER_MODEL),
        "-f", str(audio_path),
        "-otxt",  # output as plain text
        "-of", str(output_base),  # output file (without extension)
        "--print-progress",
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0


def clean_transcript(raw_text):
    """Clean up whisper output: remove timestamps if present, tidy whitespace."""
    # Remove timestamp-style lines like [00:00:00.000 --> 00:00:05.000]
    cleaned = re.sub(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\]\s*", "", raw_text)
    # Collapse multiple blank lines
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def write_markdown(day_num, reading, transcript_text):
    """Write the final markdown file with YAML frontmatter."""
    today = datetime.now().strftime("%Y-%m-%d")
    content = f"""---
day: {day_num}
date_original: {reading['date_original']}
passages: {reading['passages']}
video_url: {reading['video_url']}
transcribed_at: {today}
---

# Day {day_num} — {reading['passages']}

**Video:** {reading['video_url']}

## Transcript

{transcript_text}

## My Notes

<!-- Add your own observations, questions, or insights here -->

## Claude's Analysis

<!-- Paste analysis from Claude conversations here for future reference -->
"""
    path = transcript_path(day_num)
    path.write_text(content)
    return path


def transcribe_day(day_num, whisper_cmd, force=False):
    """Full pipeline for one day: download, convert, transcribe, write markdown."""
    if transcript_exists(day_num) and not force:
        print(f"Day {day_num}: already done (use --force to redo)")
        return True

    try:
        reading = get_reading(day_num)
    except ValueError as e:
        print(f"Error: {e}")
        return False

    print(f"\n=== Day {day_num} — {reading['passages']} ===")

    AUDIO_DIR.mkdir(exist_ok=True)
    raw_audio = AUDIO_DIR / f"day-{day_num:03d}-raw"
    wav_audio = AUDIO_DIR / f"day-{day_num:03d}.wav"

    # Download
    if not download_audio(reading["video_url"], raw_audio):
        return False

    # yt-dlp will have saved it as .wav, but at whatever sample rate
    downloaded_wav = raw_audio.with_suffix(".wav")
    if not downloaded_wav.exists():
        print(f"  Expected {downloaded_wav} but it doesn't exist")
        return False

    # Convert to 16kHz mono (whisper-cpp format)
    print("  Converting to 16kHz mono...")
    converted_wav = AUDIO_DIR / f"day-{day_num:03d}-16k.wav"
    if not convert_to_whisper_format(downloaded_wav, converted_wav):
        print("  ffmpeg conversion failed")
        return False

    # Run whisper
    output_base = AUDIO_DIR / f"day-{day_num:03d}-transcript"
    if not run_whisper(whisper_cmd, converted_wav, output_base):
        print("  whisper-cpp failed")
        return False

    # Read result and clean it
    txt_file = output_base.with_suffix(".txt")
    if not txt_file.exists():
        print(f"  Expected transcript file {txt_file} but it doesn't exist")
        return False

    raw_text = txt_file.read_text()
    cleaned = clean_transcript(raw_text)

    # Write final markdown
    md_path = write_markdown(day_num, reading, cleaned)
    print(f"  ✓ Written: {md_path.relative_to(PROJECT_ROOT)}")

    # Cleanup temp audio files
    for f in [downloaded_wav, converted_wav, txt_file]:
        if f.exists():
            f.unlink()

    return True


def list_done():
    """Show which days have been transcribed."""
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    done = sorted(TRANSCRIPTS_DIR.glob("day-*.md"))
    if not done:
        print("No transcripts yet.")
        return
    days = [int(re.search(r"day-(\d+)", f.name).group(1)) for f in done]
    print(f"Transcribed: {len(days)} days")
    print(f"First: day {min(days)}, Last: day {max(days)}")
    # Find gaps
    gaps = []
    for i in range(min(days), max(days)):
        if i not in days:
            gaps.append(i)
    if gaps:
        print(f"Gaps: {gaps}")


def find_next_undone():
    """Find the next day that hasn't been transcribed yet."""
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    for day in range(1, 367):
        if not transcript_exists(day):
            return day
    return None


def main():
    parser = argparse.ArgumentParser(description="Transcribe Pastor Corbett's daily Bible readings")
    parser.add_argument("start", nargs="?", type=int, help="Day to transcribe (or start of range)")
    parser.add_argument("end", nargs="?", type=int, help="End of range (inclusive)")
    parser.add_argument("--force", action="store_true", help="Re-transcribe even if file exists")
    parser.add_argument("--list", action="store_true", help="Show which days are already done")
    parser.add_argument("--next", action="store_true", help="Transcribe next undone day")
    args = parser.parse_args()

    if args.list:
        list_done()
        return

    # Preflight checks
    if not WHISPER_MODEL.exists():
        print(f"ERROR: Whisper model not found at {WHISPER_MODEL}")
        print("Download it with:")
        print(f"  mkdir -p {WHISPER_MODEL.parent}")
        print(f"  cd {WHISPER_MODEL.parent}")
        print("  curl -L -o ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin")
        sys.exit(1)

    whisper_cmd = find_whisper_command()
    if not whisper_cmd:
        print(f"ERROR: Neither {' nor '.join(WHISPER_COMMANDS)} found on PATH")
        print("Install with: brew install whisper-cpp")
        sys.exit(1)

    if args.next:
        day = find_next_undone()
        if day is None:
            print("All 366 days are done! Amazing.")
            return
        print(f"Next undone day: {day}")
        transcribe_day(day, whisper_cmd, force=args.force)
        return

    if args.start is None:
        parser.print_help()
        sys.exit(1)

    start = args.start
    end = args.end if args.end else start

    if start < 1 or end > 366 or start > end:
        print(f"Invalid range: {start}..{end}")
        sys.exit(1)

    succeeded = 0
    failed = 0
    for day in range(start, end + 1):
        if transcribe_day(day, whisper_cmd, force=args.force):
            succeeded += 1
        else:
            failed += 1

    print(f"\n=== Done: {succeeded} succeeded, {failed} failed ===")


if __name__ == "__main__":
    main()
