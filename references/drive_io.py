#!/usr/bin/env python3
"""ОПЦИОНАЛЬНЫЙ fallback: приём/отдача через Google Drive (сервисный аккаунт).

⚠️ НЕ дефолтный путь. Дефолтный приём сырья — references/fetch.py (загрузка по
ОТКРЫТОЙ ссылке без авторизации). Этот модуль нужен ТОЛЬКО когда:
  • сырьё лежит в ПРИВАТНОЙ Drive-папке (не «доступ по ссылке»); или
  • готовый файл нужно передать ссылкой через Google Drive.
Сервисный аккаунт подключается только при необходимости.

AUTH — СЕРВИСНЫЙ АККАУНТ (без интерактивного OAuth, работает на голом VPS):
  переменная окружения GOOGLE_SERVICE_ACCOUNT_JSON = путь к JSON-ключу сервисного
аккаунта. Пользователь расшаривает входную и выходную Drive-папки на email сервисного
  аккаунта (client_email из этого же JSON). Без расшаривания Drive вернёт 404.

ЗАВИСИМОСТИ (ОПЦИОНАЛЬНЫЕ, закомментированы в requirements.txt):
  pip install google-api-python-client google-auth

API:
  download(file_id_or_link, dest)          -> Path     скачать файл (любой размер, чанками)
  upload(path, folder_id)                  -> str      залить, вернуть шаримую ссылку
  list_inbox(folder_id)                    -> list[dict]  новые файлы во входной папке

CLI (удобно для теста с VPS):
  python3 drive_io.py download <id|link> <dest>
  python3 drive_io.py upload <path> <folder_id>
  python3 drive_io.py list <folder_id>
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]


# --------------------------------------------------------------------------- auth
def _service():
    """Drive API v3 service от сервисного аккаунта (GOOGLE_SERVICE_ACCOUNT_JSON)."""
    key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not key_path:
        raise SystemExit(
            "Нет GOOGLE_SERVICE_ACCOUNT_JSON в окружении — укажи путь к JSON-ключу "
            "сервисного аккаунта (и расшарь Drive-папки на его client_email)."
        )
    if not Path(key_path).exists():
        raise SystemExit(f"Файл ключа не найден: {key_path}")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit(
            "Нет google-api-python-client / google-auth. Установи: "
            "pip install google-api-python-client google-auth"
        )
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    # cache_discovery=False — на VPS без записи в кэш discovery-документа
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ----------------------------------------------------------------------- helpers
def resolve_file_id(file_id_or_link: str) -> str:
    """Из ссылки Google Drive вытащить fileId. Принимает и голый ID."""
    s = file_id_or_link.strip()
    # /file/d/<ID>/...
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    # ?id=<ID> или &id=<ID> (open?id=, uc?id=)
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    # /folders/<ID> (на случай, если дали папку)
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    # уже голый ID
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
        return s
    raise ValueError(f"Не смог распознать Google Drive ID/ссылку: {file_id_or_link!r}")


# -------------------------------------------------------------------------- download
def download(file_id_or_link: str, dest: str | Path) -> Path:
    """Скачать файл Drive в dest. Без лимита размера — качаем чанками.

    dest может быть папкой (тогда имя берётся из метаданных) или путём файла.
    Возвращает Path к скачанному файлу.
    """
    from googleapiclient.http import MediaIoBaseDownload

    svc = _service()
    fid = resolve_file_id(file_id_or_link)
    meta = svc.files().get(
        fileId=fid, fields="id,name,size,mimeType", supportsAllDrives=True
    ).execute()

    dest = Path(dest)
    if dest.is_dir() or str(dest).endswith(os.sep):
        dest = dest / meta["name"]
    dest.parent.mkdir(parents=True, exist_ok=True)

    req = svc.files().get_media(fileId=fid, supportsAllDrives=True)
    with io.FileIO(str(dest), "wb") as fh:
        downloader = MediaIoBaseDownload(fh, req, chunksize=16 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  скачивание {int(status.progress() * 100)}%", end="\r")
    print(f"  скачано → {dest} ({meta.get('size','?')} байт)")
    return dest


# ---------------------------------------------------------------------------- upload
def upload(path: str | Path, folder_id: str) -> str:
    """Залить файл в выходную папку folder_id. Вернуть шаримую ссылку.

    Делает файл доступным «по ссылке» (reader anyone).
    """
    from googleapiclient.http import MediaFileUpload

    svc = _service()
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"Нет файла для заливки: {path}")

    body = {"name": path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(path), resumable=True)
    f = svc.files().create(
        body=body, media_body=media, fields="id,webViewLink", supportsAllDrives=True
    ).execute()
    fid = f["id"]

    # доступ по ссылке для чтения (если папка не расшарена публично)
    try:
        svc.permissions().create(
            fileId=fid, body={"type": "anyone", "role": "reader"}, supportsAllDrives=True
        ).execute()
    except Exception as e:  # noqa: BLE001 — общая папка может уже давать доступ
        print(f"  (предупреждение: не выставил anyone-reader: {e})")

    link = f.get("webViewLink") or f"https://drive.google.com/file/d/{fid}/view"
    print(f"  залито → {link}")
    return link


# ------------------------------------------------------------------------- list_inbox
def list_inbox(folder_id: str) -> list[dict]:
    """Файлы во входной папке (новые сверху). Вернуть [{id,name,mimeType,createdTime}]."""
    svc = _service()
    res = svc.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,mimeType,size,createdTime)",
        orderBy="createdTime desc",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    return res.get("files", [])


# ---------------------------------------------------------------------------- cli
def _main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "download":
        download(sys.argv[2], sys.argv[3])
    elif cmd == "upload":
        print(upload(sys.argv[2], sys.argv[3]))
    elif cmd == "list":
        for f in list_inbox(sys.argv[2]):
            print(f"{f['id']}  {f['name']}  ({f.get('size','?')}B, {f.get('createdTime','')})")
    else:
        sys.exit(f"неизвестная команда: {cmd} (download|upload|list)")


if __name__ == "__main__":
    _main()
