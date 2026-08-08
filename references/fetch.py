#!/usr/bin/env python3
"""Универсальный загрузчик видео по ОТКРЫТОЙ ссылке — БЕЗ авторизации.

Дефолтный приём сырья для базовой нарезки рилсов. Пользователь передаёт открытую
ссылку, а скрипт скачивает её на диск подходящим способом:

  • Google Drive «доступ по ссылке»  → gdown (умеет большие файлы + страницу
    подтверждения вируса). Форматы: /file/d/<id>, open?id=, uc?id=, голый id.
  • YouTube / видеохосты             → yt-dlp.
  • Прямой http(s)-URL файла         → стрим на диск (urllib).

Авторизация НЕ нужна — ссылка должна быть ОТКРЫТОЙ («доступ по ссылке» в Drive,
публичное видео и т.п.). Если ссылка закрыта — внятная ошибка с просьбой дать доступ.
Приватные папки / заливку готового файла обратно на Drive см. в опциональном
references/drive_io.py (сервисный аккаунт).

Сигнатура:  fetch(link, dest) -> Path
  dest может быть папкой (имя возьмём из ссылки/метаданных) или путём файла.

Зависимости (см. requirements.txt): gdown, yt-dlp. Прямой URL — на stdlib.

CLI:  python3 fetch.py <ссылка> <dest>
"""
from __future__ import annotations

import inspect
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; reels-fetch/1.0)"


# ---------------------------------------------------------------- классификация
def _is_drive(link: str) -> bool:
    return "drive.google.com" in link or "docs.google.com" in link


def _is_youtube_or_host(link: str) -> bool:
    hosts = ("youtube.com", "youtu.be", "vimeo.com", "tiktok.com",
             "instagram.com", "facebook.com", "vk.com", "rutube.ru", "dailymotion.com")
    return any(h in link for h in hosts)


def drive_id(link: str) -> str:
    """Вытащить fileId из любой Drive-ссылки. Принимает и голый id."""
    s = link.strip()
    for pat in (r"/file/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)",
                r"/folders/([A-Za-z0-9_-]+)"):
        m = re.search(pat, s)
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
        return s
    raise ValueError(f"Не распознал Google Drive ID/ссылку: {link!r}")


# ----------------------------------------------------------------------- роутеры
def _fetch_drive(link: str, dest: Path) -> Path:
    try:
        import gdown
    except ImportError:
        raise SystemExit("Нет gdown. Установи: pip install gdown")
    fid = drive_id(link)
    if dest.is_dir() or str(dest).endswith(os.sep):
        dest.mkdir(parents=True, exist_ok=True)
        out = str(dest) + os.sep  # gdown сам подставит имя файла
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = str(dest)
    print(f"  gdown: Drive id={fid} → {dest}")
    try:
        # У разных версий gdown разная сигнатура: новые принимают fuzzy=,
        # старые (как на VPS) падают на unexpected keyword argument.
        kwargs = {"id": fid, "output": out, "quiet": False}
        if "fuzzy" in inspect.signature(gdown.download).parameters:
            kwargs["fuzzy"] = True
        path = gdown.download(**kwargs)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(_closed_hint(f"gdown не смог скачать ({e})"))
    if not path:
        raise SystemExit(_closed_hint("gdown вернул пусто — вероятно, ссылка закрыта"))
    return Path(path)


def _fetch_host(link: str, dest: Path) -> Path:
    if not shutil.which("yt-dlp"):
        try:
            import yt_dlp  # noqa: F401  (доступен как модуль)
            runner = [sys.executable, "-m", "yt_dlp"]
        except ImportError:
            raise SystemExit("Нет yt-dlp. Установи: pip install yt-dlp")
    else:
        runner = ["yt-dlp"]
    if dest.is_dir() or str(dest).endswith(os.sep):
        dest.mkdir(parents=True, exist_ok=True)
        tmpl = str(dest / "%(title).80s.%(ext)s")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmpl = str(dest)
    print(f"  yt-dlp: {link} → {dest}")
    # best mp4 (h264+aac) для совместимости с резаком; печатает прогресс сам
    cmd = runner + ["-f", "bv*+ba/b", "--merge-output-format", "mp4",
                    "-o", tmpl, "--no-playlist", link]
    if subprocess.run(cmd).returncode != 0:
        raise SystemExit(_closed_hint("yt-dlp упал"))
    if dest.is_dir() or str(dest).endswith(os.sep):
        files = sorted(Path(dest).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0] if files else dest
    return dest


def _fetch_direct(link: str, dest: Path) -> Path:
    if dest.is_dir() or str(dest).endswith(os.sep):
        name = Path(link.split("?")[0]).name or "download.bin"
        dest = Path(dest) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  http(s): {link} → {dest}")
    req = urllib.request.Request(link, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    print(f"  скачивание {got*100//total}%", end="\r")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(_closed_hint(f"прямая загрузка не удалась ({e})"))
    print(f"  скачано → {dest} ({dest.stat().st_size} байт)")
    return dest


def _closed_hint(msg: str) -> str:
    return (f"{msg}.\nВероятно, ссылка закрыта. Попроси владельца выставить «Доступ по "
            f"ссылке: всем, у кого есть ссылка» (Drive) или сделать видео публичным. "
            f"Для приватных папок — опциональный fallback references/drive_io.py "
            f"(сервисный аккаунт).")


# --------------------------------------------------------------------------- API
def fetch(link: str, dest: str | Path) -> Path:
    """Скачать видео по открытой ссылке. Роутинг по виду ссылки. -> Path к файлу."""
    link = link.strip()
    dest = Path(dest)
    if _is_drive(link):
        return _fetch_drive(link, dest)
    if _is_youtube_or_host(link):
        return _fetch_host(link, dest)
    if link.startswith(("http://", "https://")):
        return _fetch_direct(link, dest)
    raise SystemExit(f"Не похоже на ссылку: {link!r}")


def _main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    out = fetch(sys.argv[1], sys.argv[2])
    print(out)


if __name__ == "__main__":
    _main()
