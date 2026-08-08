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

## How to adapt the visual style

The skill deliberately separates the **creative contract** from the **per-video plan**. Keep the contract consistent for a series; tune the plan for each individual Short.

### 1. Change the series-level design system

Edit [`references/style-system.md`](references/style-system.md) when you want to change the look of every future video.

| What you want to change | Where to change it | Keep in mind |
| --- | --- | --- |
| Brand colours | **Palette** | Keep one saturated accent on screen at a time; captions use only white + their semantic accent. |
| Font pair | **Typography** and `references/assets/fonts/` | Supply local, licensed font files and update the renderer's `@font-face` declarations. Do not rely on system-font fallbacks. |
| Hook appearance | **Hook title** | Define the size, position, entrance, exit, and the one optional accent word. It must stay clear of the top 220 px platform zone. |
| Subtitle look | **Karaoke captions** | Set the primary font, size, line-height, emphasis treatment, maximum width, and vertical position. Captions should remain readable in two lines or fewer. |
| PiP / proof treatment | **Floating card / phone mockup / full-screen b-roll** | Decide corner, size, rounding, shadow, and entry animation. Proof must be a real image or video, not a text placeholder. |
| CTA | **CTA lock** | Choose copy, colour, placement, and entry animation. Reserve it for the final beat and replace duplicate captions during that window. |
| Motion density | **Face tracking + semantic attention zoom** | Use 3–5 deliberate zooms per Short, each 1.03–1.08× and attached to a spoken point. |

After changing the style system, update the matching Remotion composition so the implementation and documentation describe the same design.

### 2. Tune one individual Short

Put creative choices for one video in `plan.json`, then convert them into Remotion props. The minimum useful shape is:

```json
{
  "hook": {"text": "НЕ ВЕДИ ОДИН ЧАТ", "accent": "один"},
  "proofAssets": [
    {
      "path": "/absolute/path/to/real-proof.png",
      "type": "image",
      "startSeconds": 4.2,
      "endSeconds": 7.5,
      "placement": "top-left",
      "source": "owned-media",
      "semanticMatch": "Shows the alternative workflow named in the speech.",
      "rightsNote": "Permission to use confirmed."
    }
  ],
  "zooms": [
    {"startSeconds": 1.4, "endSeconds": 2.4, "scale": 1.05, "reason": "main claim"}
  ],
  "focusTrack": [
    {"atSeconds": 0, "xPercent": 50, "yPercent": 42}
  ],
  "cta": {"text": "save this", "startSeconds": 28}
}
```

Use the transcript to choose the hook, the proof asset, the CTA, and the timestamps. `plan.json` is the source of truth: no random choices during rendering.

### 3. Safe defaults worth preserving

- Render at 1080×1920 unless a platform requires another format.
- Keep the top 220 px and right 140 px free for platform UI; end all text above y=1500.
- Use real source media for b-roll and record its source, semantic relevance, and rights note.
- Suppress any burned-in source subtitles before adding new captions.
- Do not overlap a zoom peak with a PiP entrance, split-screen transition, or CTA.
- Before publishing a new style, render stills for hook, captions, proof, zoom, CTA, and the final frame, then complete `references/qa-loop.md`.

### 4. What belongs where

| Change | Right place |
| --- | --- |
| New brand or visual language | `references/style-system.md` + Remotion composition |
| New hook, proof, timing, zooms, CTA | `plan.json` / input props |
| New source clip | Job folder (`public/jobs/<job-id>/`) |
| New transcription provider or caption segmentation | `references/transcribe_subs.py` |
| New acceptance rule | `SKILL.md` and `references/qa-loop.md` |

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
