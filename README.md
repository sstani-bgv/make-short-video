# Make Short Video

Production skill for turning one selected source segment into a finished vertical Reels, Shorts, or TikTok video with captions, proof visuals, semantic zooms, CTA, and a repeatable QA pass.

## What it does

1. Validates the source with `ffprobe` and checks safe edit boundaries.
2. Generates word-level Russian captions with Groq Whisper.
3. Produces a deterministic `plan.json` and storyboard from real source frames.
4. Stages source and proof media for a Remotion composition.
5. Renders a 1080×1920 H.264/AAC MP4.
6. Verifies composition discovery, linting, captions, safe zones, proof provenance, and final audio/video output.

## Included references

| File or folder | Purpose |
| --- | --- |
| `SKILL.md` | Main operating contract and acceptance criteria. |
| `references/style-system.md` | Typography, colours, layout, captions, PiP, CTA, and safe-zone rules. |
| `references/production-pipeline.md` | Source preparation, staging, props, rendering, and handoff. |
| `references/qa-loop.md` | Required static, visual, audio, and platform QA. |
| `references/transcribe_subs.py` | Groq Whisper word-level transcription and caption phrasing. |
| `references/storyboard.py` | Storyboard PNG from real video frames and a plan. |
| `references/audio_boundary_qa.py` | PCM waveform gate for safe audio cuts. |
| `references/cut/` | Optional ffmpeg-only silence-cut path. |
| `references/assets/` | Bundled fonts and film-opening assets. |

## Requirements

- Python 3.10+ and `ffmpeg`/`ffprobe`.
- A Remotion project that provides a `Make-Reels-Video` composition compatible with the props described in `references/production-pipeline.md`.
- `GROQ_API_KEY` for word-level transcription. Copy `.env.example` to your environment; never commit a real key.

Install the Python helpers:

```bash
uv run --with-requirements requirements.txt python3 references/storyboard.py --help
```

## Minimal workflow

```bash
mkdir -p /tmp/montage-short-01
ffprobe -v error -show_streams -show_format -of json input.mp4
python3 references/transcribe_subs.py input.mp4 -o /tmp/montage-short-01/subs.json
python3 references/audio_boundary_qa.py input.mp4 --range 0:30 \
  --out /tmp/montage-short-01/audio-boundary-qa
```

Create a `plan.json`, run `storyboard.py`, then follow the staging, Remotion render, and QA instructions in `references/production-pipeline.md`.

## Privacy and publishing

This public version contains no real API keys, user names, workspace paths, account IDs, source media, or private URLs. The `.env.example` file is a placeholder only. Before adding your own media or plans, confirm that you have the rights to publish them.

## Notes

The bundled font and media assets retain their original rights. Check their licences and your intended distribution before using this skill commercially or redistributing the assets.
