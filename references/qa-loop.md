# Обязательный QA-loop

Remotion даёт детерминированный seek-safe render, но технический успех не равен
монтажной приёмке. После любого изменения композиции или props повторять цикл.

## 0. Audio boundary gate

- Запустить `audio_boundary_qa.py`.
- Exit code 0 и `report.json.ok=true`.
- Просмотреть `contact-sheet.png`.
- На обеих сторонах каждой речи есть минимум 100 ms неактивного аудио.
- После финального render прослушать все склейки и повторно проверить edge ASR.

Любая срезанная фонема блокирует отдачу.

## 1. Static checks

```bash
cd <remotion-project>
npm run lint
npx remotion compositions src/index.ts
```

Проверить, что `Make-Reels-Video` обнаружена, fps/width/height/duration совпадают
с props, а console не содержит warnings/errors.

## 2. Event-driven stills

Для каждого hook, proof asset, zoom, caption-window и CTA снять кадр сразу после
входа, в визуальном пике и перед выходом, плюс representative кадры начала,
середины и конца:

```bash
npx remotion still src/index.ts Make-Reels-Video \
  /tmp/montage-<job_id>/qa/frame-0030.png \
  --frame=30 --props=/tmp/montage-<job_id>/props.json
```

Проверить глазами:

- лицо не обрезано и не закрыто;
- focus track не прыгает;
- proof видим, читаем и соответствует тезису;
- captions не перекрывают лицо, proof или CTA;
- hook/CTA не обрезаны;
- отсутствуют два слоя captions;
- локальные fonts реально отрисованы;
- emoji/кириллица не ушли в tofu;
- нет пустых, чёрных или frozen frames.

## 3. Platform UI mock

Наложить UI mock на representative frames. Для 1080×1920:

- верх 220 px пуст;
- справа 140 px пуст;
- весь текст заканчивается выше y=1500.

Для square source проверить центрирование внутри вертикального mock. Сохранить
mock/contact sheet и измеренные bounds в acceptance.

## 4. Render и post-render QA

```bash
npx remotion render src/index.ts Make-Reels-Video \
  /tmp/montage-<job_id>/render.mp4 \
  --props=/tmp/montage-<job_id>/props.json \
  --codec=h264 --audio-codec=aac

ffprobe -v error -show_streams -show_format -of json \
  /tmp/montage-<job_id>/render.mp4 \
  > /tmp/montage-<job_id>/qa/final-probe.json
```

Из финального MP4 извлечь кадры начала, середины, конца и каждого event-window.
Финальный MP4, а не Studio preview, является источником истины.

Проверить:

- 1080×1920, ожидаемые fps/duration, H.264 + AAC;
- A/V sync;
- первая и последняя фонемы целы;
- нет clipping, clicks, провалов и двойного boom;
- film opening видим и слышим, но не меняет duration;
- captions покрывают речь и синхронны словам;
- все assets декодируются, нет missing frame;
- нет визуальных коллизий или unsafe text.

## 5. Acceptance JSON

Минимальные поля `qa/acceptance.json`:

```json
{
  "status": "accepted",
  "renderer": "remotion",
  "composition_id": "Make-Reels-Video",
  "real_proof_broll_asset_count": 1,
  "proof_sources": [],
  "storyboard_placeholder_text_count": 0,
  "subtitle_style_match": true,
  "subtitle_speech_coverage": true,
  "all_marggraff_elements_lowercase": true,
  "source_burned_captions_suppressed": true,
  "attention_zoom_count": 3,
  "attention_zoom_spec_match": true,
  "face_tracking_no_jitter": true,
  "overlay_collision_count": 0,
  "audio_boundary_report_ok": true,
  "edge_asr_match": true,
  "remotion_lint_errors": 0,
  "remotion_composition_discovery_passed": true,
  "platform_ui_mock_passed": true,
  "film_opening": {
    "applied": true,
    "first_word_intact": true,
    "no_clipping": true
  }
}
```

Любой `false`, `real_proof_broll_asset_count < 1`, zoom count вне 3–5,
ненулевой collision/error или неполный provenance возвращает job на монтаж.
