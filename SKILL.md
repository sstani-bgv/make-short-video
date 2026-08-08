---
name: make-short-video
description: "Автономно произвести финальный вертикальный Reels/Shorts/TikTok из выбранного исходного фрагмента: безопасные монтажные границы, karaoke-субтитры, face tracking и semantic zoom, реальный proof b-roll/PiP, CTA, Remotion render и обязательный audio/visual QA. Использовать для одного Short после отбора момента; не использовать для отбора, загрузки или публикации."
---

# Make Short Video

Этот skill превращает готовый фрагмент с говорящей головой, скринкастом или
интервью в финальный вертикальный ролик. Канонический renderer — указанный
в handoff Remotion-проект.

Композиция: `Make-Reels-Video`.

Перед работой полностью прочитать:

1. `references/style-system.md`;
2. `references/production-pipeline.md`;
3. `references/qa-loop.md`;
4. `.agents/skills/remotion-best-practices/SKILL.md`;
5. только нужные references Remotion-скиллов.

## Граница ответственности

- Один вызов = один изолированный Short.
- Отбор момента делает вызывающий producer; этот skill владеет монтажом,
  графикой, captions, render и QA.
- Не загружать ролик и не менять manifests/state вызывающего workspace.
- Не спрашивать о промежуточных творческих решениях. Storyboard блокирует
  производство только если handoff содержит `approval.storyboard_required: true`.
- Остановиться, если нет обязательного proof asset, исходник недоступен или нужна
  новая внешняя авторизация.

## Неподменяемый визуальный контракт

- Вертикаль 1080×1920 по умолчанию; квадрат проверяется внутри 9:16 platform mock.
- Хук появляется в первую секунду. Основной шрифт — Bebas Neue Cyrillic; ровно
  одно акцентное слово может быть Marggraff Kursiv Zarte, всегда lowercase.
- Karaoke captions покрывают всю речь, кроме намеренно заменённых hook/CTA окон.
  Основной текст: белый Bebas, 82 px, letter-spacing 1.1 px. Смысловой акцент:
  lowercase Marggraff, `#FF6A3D`, примерно 1.18em, baseline +7 px.
- У captions нет pill, рамки или непрозрачной плашки. Разрешён локальный
  градиентный scrim.
- Минимум один реальный proof b-roll/PiP asset, отличный от talking-head.
  Storyboard note нельзя превращать в placeholder-карточку.
- Для proof сохранять provenance, OCR/semantic match и rights/source note.
  Собственные опубликованные материалы предпочтительнее стока, если доказывают тезис.
- Исходные burned-in captions должны быть полностью подавлены чистым crop,
  recomposition или проверенным маскирующим слоем.
- На один Short — 3–5 semantic zoom: scale 1.03–1.08, вход 0.7–1.3 s,
  привязка к конкретной фразе. Zoom не конфликтует с PiP, split или CTA.
- Любой текст проходит safe-zone: верхние 220 px свободны, правая рейка 140 px
  свободна, нижняя граница текста выше y=1500.
- CTA зависит от назначения: Short из long-form — «полное видео — по кнопке
  ниже»; standalone — CTA из brief или «сохрани / подпишись».
- Плёночное открытие использует локальные `lut4.mp4` и `boom.mp3`, не режет
  первую фонему и не меняет длительность больше чем на один кадр.

Точные токены, шрифты, layout-варианты и SHA файлов находятся только в
`references/style-system.md`.

## Источники и транскрипция

- Для смысловой транскрипции использовать глобальный skill `transcribe`.
- `references/transcribe_subs.py` остаётся локальным: он создаёт word-level
  тайминги и `subs.json` для karaoke captions и boundary QA.
- Для длинного источника делить аудио на чанки по 1500 s и объединять через
  `references/merge_subs.py`.
- Таймкоды ASR — ориентир, а не точки реза. Каждая склейка должна пройти
  `references/audio_boundary_qa.py` с запасом минимум 100 ms.

## Изоляция файлов

- Job-root: `/tmp/montage-<job_id>/`.
- Downloads, chunks, EDL, frames, storyboard, props, QA stills, previews и логи
  держать только в job-root.
- Медиа, которые должен читать Remotion, временно stage в
  `<remotion-project>/public/jobs/<job_id>/`; папка игнорируется Git.
- Финальный принятый MP4 копировать в `deliverables_dir` из handoff.
- Не писать токены, cookies или содержимое `.env` в props, plan или receipt.

## Канонический pipeline

1. Проверить источник через `ffprobe`; выбрать или подтвердить точные границы.
2. Получить transcript и `subs.json`; исправить ASR и убрать overlaps.
3. Построить детерминированный `plan.json`: hook, proof assets, focus track,
   3–5 zoom events, CTA, safe zones и provenance.
4. Создать storyboard из реальных кадров через `references/storyboard.py`.
5. Если approval обязателен — вернуть `awaiting_storyboard_approval`. Иначе идти дальше.
6. Прогнать waveform gate; поправить небезопасные границы и повторить.
7. Stage source/assets в `public/jobs/<job_id>/` и собрать Remotion input props.
8. Проверить композицию и representative frames, затем render:

   ```bash
   cd <remotion-project>
   npx remotion compositions src/index.ts
   npx remotion still src/index.ts Make-Reels-Video /tmp/montage-<job_id>/qa/frame.png \
     --frame=30 --props=/tmp/montage-<job_id>/props.json
   npx remotion render src/index.ts Make-Reels-Video /tmp/montage-<job_id>/render.mp4 \
     --props=/tmp/montage-<job_id>/props.json --codec=h264
   ```

9. Прогнать обязательный QA из `references/qa-loop.md`.
10. После успешного QA перенести MP4, пересчитать SHA-256 и записать Montage receipt.

## Remotion safety contract

- Всё движение зависит только от `useCurrentFrame()`, `interpolate()`,
  `spring()` и фиксированных props.
- Для временных сцен использовать `<Sequence>`; отрицательные локальные frames
  до входа сцены не должны влиять на анимацию.
- Видео подключать через `<Video>` из `@remotion/media`; trim задавать в frames
  через `trimBefore`/`trimAfter`.
- Project-relative media подключать через `staticFile()`.
- Никаких `Math.random()`, `Date.now()`, browser timers и сетевых запросов во время render.
- Captions используют Remotion `Caption` JSON и
  `createTikTokStyleCaptions()` из `@remotion/captions`.
- `durationInFrames` вычисляется из `durationSeconds` в `calculateMetadata`.
- Face/focus track и zoom events полностью фиксируются в props/`plan.json`.
- Рендер обязан быть seek-safe: любой кадр корректен при прямом переходе к нему.

## Формат `plan.json`

```json
{
  "jobId": "short-01",
  "source": "/abs/source.mp4",
  "hook": {"text": "ГЛАВНАЯ мысль", "accent": "мысль"},
  "segment": {"startSeconds": 12.4, "durationSeconds": 37.2},
  "proofAssets": [
    {
      "path": "/abs/proof.png",
      "type": "image",
      "startSeconds": 5,
      "endSeconds": 8.2,
      "placement": "top-left",
      "source": "owned-media",
      "sourcePost": "https://example.com/source",
      "semanticMatch": "подтверждает названную цифру",
      "rightsNote": "собственный опубликованный материал"
    }
  ],
  "zooms": [
    {"startSeconds": 3.2, "endSeconds": 4.3, "scale": 1.06, "reason": "ключевая фраза"}
  ],
  "focusTrack": [
    {"atSeconds": 0, "xPercent": 50, "yPercent": 42},
    {"atSeconds": 37.2, "xPercent": 51, "yPercent": 42}
  ],
  "cta": {"text": "полное видео — по кнопке ниже", "startSeconds": 34}
}
```

Proof asset без provenance не считается реальным proof. Все числовые поля после
проверки переводятся в Remotion input props без случайной генерации.

## Acceptance

`status: done` допустим только если:

- `real_proof_broll_asset_count >= 1`;
- captions непрерывны, approved style соблюдён, Marggraff всегда lowercase;
- source burned-in captions подавлены;
- attention zoom count находится в диапазоне 3–5, jitter и collisions отсутствуют;
- waveform report имеет `ok: true`, edge ASR совпадает;
- `npm run lint`, composition discovery и representative stills прошли;
- финальный MP4 просмотрен покадрово и прослушан на всех склейках;
- platform UI mock пройден;
- MP4 находится вне `/tmp`, а hash пересчитан после переноса.

## Лёгкий путь без motion-графики

Если нужна только чистая нарезка пауз/вдохов, использовать:

`fetch.py → transcribe_subs.py → silence_cut.py → audio_boundary_qa.py → render_cut.py`

Этот путь остаётся ffmpeg-only. Он не заменяет Remotion для роликов с hook,
proof b-roll, captions, zoom и CTA.

## Файлы skill

- `references/style-system.md` — визуальный источник истины.
- `references/production-pipeline.md` — подготовка, staging, props и render.
- `references/qa-loop.md` — обязательная приёмка.
- `references/transcribe_subs.py`, `merge_subs.py` — word-level captions.
- `references/audio_boundary_qa.py` — waveform gate.
- `references/storyboard.py` — storyboard из реальных кадров.
- `references/cut/` — лёгкий ffmpeg-only cut.
- `references/assets/` — локальные fonts, film opening и sound effect.
