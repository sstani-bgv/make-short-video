# Production pipeline — Make Reels Video on Remotion

## A. Job-root и проверка сырья

Работать в `/tmp/montage-<job_id>/`. Проверить source:

```bash
ffprobe -v error -show_streams -show_format -of json /abs/source.mp4 \
  > /tmp/montage-<job_id>/source-probe.json
```

Зафиксировать start/duration, fps, размеры, audio layout и rotation metadata.
ASR boundary нельзя принимать за безопасную склейку.

## B. Transcript, captions и EDL

Смысловой transcript создаёт глобальный `transcribe`. Для word-level captions:

```bash
GROQ_API_KEY=... python3 references/transcribe_subs.py /abs/source.mp4 \
  -o /tmp/montage-<job_id>/subs.json
```

Убрать ASR-ошибки и перекрытия: `end` предыдущей фразы должен быть не позже
`start` следующей минус 0.02 s. Для долгого файла использовать чанки 1500 s и
`merge_subs.py`.

Если нужна чистка пауз:

```bash
python3 references/cut/silence_cut.py \
  --work /abs/source.mp4 \
  --words /tmp/montage-<job_id>/subs.json \
  --out /tmp/montage-<job_id>/edl.json \
  --debreath --audio
```

Перед любым render:

```bash
python3 references/audio_boundary_qa.py /abs/source.mp4 \
  --ranges /tmp/montage-<job_id>/edl.json \
  --out /tmp/montage-<job_id>/audio-boundary-qa \
  --min-handle-ms 100
```

Продолжать только при exit code 0, `report.json.ok=true` и визуально проверенном
`contact-sheet.png`.

## C. Storyboard и approval

Codex строит `plan.json` из transcript, brief и `style-system.md`. Каждый
`B-ROLL`, `PIP` или `SPLIT` содержит реальный asset и provenance.

```bash
UV_CACHE_DIR=/tmp/montage-uv-cache uv run \
  --with-requirements requirements.txt \
  python3 references/storyboard.py \
  /tmp/montage-<job_id>/plan.json /abs/source.mp4 \
  -o /tmp/montage-<job_id>/storyboard.png
```

Если `storyboard_required=false`, storyboard — проверяемый production artifact,
а не пауза. Если `true`, render начинается только после явного approval.

## D. Stage media

Remotion читает локальные assets через `staticFile()`. Для каждого job:

```text
<remotion-project>/public/jobs/<job_id>/
  source.mp4
  proof-01.png
  proof-02.mp4
```

Имена нормализовать, collision не перезаписывать. В props передавать путь
относительно `public`, например `jobs/short-01/source.mp4`.

Постоянные assets skill находятся в:

```text
<remotion-project>/public/reels/
  fonts/
  film/lut4.mp4
  sfx/boom.mp3
```

## E. Input props

Сохранить `/tmp/montage-<job_id>/props.json`. Минимальный пример:

```json
{
  "source": "jobs/short-01/source.mp4",
  "durationSeconds": 32.4,
  "trimStartSeconds": 14.8,
  "hook": {"text": "ТЫ ТЕРЯЕШЬ время", "accent": "время"},
  "captions": [
    {
      "text": "ты теряешь время",
      "startMs": 0,
      "endMs": 1300,
      "timestampMs": 0,
      "confidence": 0.97
    }
  ],
  "proofAssets": [
    {
      "src": "jobs/short-01/proof-01.png",
      "type": "image",
      "startSeconds": 4.2,
      "endSeconds": 7.6,
      "placement": "top-left",
      "source": "owned-media",
      "sourcePost": "https://example.com/source",
      "semanticMatch": "показывает заявленную цифру",
      "rightsNote": "own published media"
    }
  ],
  "zooms": [
    {"startSeconds": 2.1, "endSeconds": 3.1, "scale": 1.05, "reason": "ключевая фраза"},
    {"startSeconds": 8, "endSeconds": 9, "scale": 1.06, "reason": "контраст"},
    {"startSeconds": 14, "endSeconds": 15.1, "scale": 1.04, "reason": "payoff"}
  ],
  "focusTrack": [
    {"atSeconds": 0, "xPercent": 50, "yPercent": 42},
    {"atSeconds": 32.4, "xPercent": 50, "yPercent": 42}
  ],
  "cta": {"text": "полное видео — по кнопке ниже", "startSeconds": 29}
}
```

Caption timestamps должны быть относительно выбранного сегмента. Для конвертации
из `subs.json` вычесть `trimStartSeconds * 1000`.

## F. Remotion checks и render

```bash
cd <remotion-project>
npm run lint
npx remotion compositions src/index.ts
npx remotion still src/index.ts Make-Reels-Video \
  /tmp/montage-<job_id>/qa/hook.png \
  --frame=30 --props=/tmp/montage-<job_id>/props.json
npx remotion render src/index.ts Make-Reels-Video \
  /tmp/montage-<job_id>/render.mp4 \
  --props=/tmp/montage-<job_id>/props.json \
  --codec=h264 --audio-codec=aac
```

Снимать stills сразу после входа и в пике каждого hook, proof, zoom и CTA.

## G. Film opening

Film opening реализован внутри Remotion:

- визуальный overlay `reels/film/lut4.mp4`;
- boom `reels/sfx/boom.mp3`;
- первый звук source остаётся полным;
- overlay не добавляет frames и не меняет duration;
- peak не клиппует.

Повторный запуск с теми же props не должен удваивать эффект.

## H. Финализация

После QA:

1. скопировать render в `deliverables_dir`;
2. проверить `ffprobe`;
3. пересчитать SHA-256 после копирования;
4. записать `qa/acceptance.json`;
5. записать receipt по `montage-receipt.schema.json`;
6. удалить staged job media из `public/jobs/<job_id>` после подтверждённой доставки.

Не считать render принятым только на основании успешного exit code.
