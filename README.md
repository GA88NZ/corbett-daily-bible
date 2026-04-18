# Corbett Daily Bible

Transcripts and study notes for Dr Andrew Corbett's [Read the Bible in a Year](https://www.andrewcorbett.net/daily-bible-reading/) daily readings.

This repo automates:
1. Downloading audio from Pastor Corbett's YouTube videos
2. Transcribing with `whisper-cpp`
3. Storing clean markdown files with passage references, video URL, and space for notes

## Setup (one-time)

Assumes macOS. Built/tested on a 2017 Intel iMac running macOS Ventura.

### 1. Install dependencies

```bash
brew install whisper-cpp ffmpeg
pip3 install yt-dlp
```

### 2. Download a whisper model

`base.en` is a good starting point — ~150MB, decent quality, fast on Intel Macs.

```bash
mkdir -p ~/whisper-models
cd ~/whisper-models
curl -L -o ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

If quality is rough, upgrade to `small.en` later:
```bash
curl -L -o ggml-small.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
```
Then edit `scripts/transcribe.py` and change `WHISPER_MODEL` to point at the new file.

### 3. Clone this repo

```bash
cd ~/Projects   # or wherever you keep projects
git clone https://github.com/GA88NZ/corbett-daily-bible.git
cd corbett-daily-bible
```

## Usage

### Transcribe a single day

```bash
python3 scripts/transcribe.py 91
```

### Transcribe a range (e.g. catching up)

```bash
python3 scripts/transcribe.py 91 108
```

### Transcribe the next undone day

```bash
python3 scripts/transcribe.py --next
```

### See what's already done

```bash
python3 scripts/transcribe.py --list
```

### Re-transcribe (e.g. after upgrading the whisper model)

```bash
python3 scripts/transcribe.py 91 --force
```

## Committing transcripts

After running the script, commit and push:

```bash
git add transcripts/
git commit -m "Transcribe day 91"
git push
```

Once pushed, Claude can fetch the transcript directly from:
```
https://raw.githubusercontent.com/GA88NZ/corbett-daily-bible/main/transcripts/day-091.md
```

So in a chat, you just say *"day 91"* and Claude can pull the whole thing.

## Folder structure

```
corbett-daily-bible/
├── README.md
├── .gitignore
├── scripts/
│   └── transcribe.py            # the transcription pipeline
├── data/
│   └── reading_plan.json        # all 366 days mapped to passages + YouTube URLs
├── transcripts/
│   └── day-NNN.md               # one per day, with YAML frontmatter + transcript + notes
└── audio/                       # temp working dir (gitignored)
```

## Transcript file format

Each transcript is a markdown file with YAML frontmatter:

```markdown
---
day: 91
date_original: 2020-03-31
passages: Joshua 21-22; Matthew 20
video_url: https://youtu.be/QTwc4BNiQKE
transcribed_at: 2026-04-18
---

# Day 91 — Joshua 21-22; Matthew 20

**Video:** https://youtu.be/QTwc4BNiQKE

## Transcript

[whisper-generated transcript here]

## My Notes

[your own observations]

## Claude's Analysis

[paste insights from Claude conversations]
```

## Troubleshooting

**`yt-dlp` fails to download:** YouTube occasionally blocks or rate-limits. Try again after a few minutes, or update yt-dlp: `pip3 install -U yt-dlp`.

**Whisper mangles Hebrew place names:** Expected. The biblical commentary (what matters) comes through clean. If needed, upgrade to `small.en` or `medium.en` model for better quality at the cost of speed.

**Gaps between daily readings:** Run `python3 scripts/transcribe.py --list` to see which days are missing and fill them in.

## Notes

- Pastor Corbett's daily readings follow a specific meta-narrative approach reading Scripture in 'books' rather than 'bits', connecting Old and New Testament through Covenant Theology.
- Pastor Corbett holds a partial-preterist / covenantal reading of prophecy — worth keeping in mind when analysing his commentary.
- Source: [andrewcorbett.net/daily-bible-reading](https://www.andrewcorbett.net/daily-bible-reading/)
