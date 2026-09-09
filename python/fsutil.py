"""Helpers de filesystem compartilhados pelas rotas HTTP."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import paths

log = logging.getLogger(__name__)

# Alinhado com C# FileSystemUtil (Path.GetInvalidFileNameChars no Windows + NUL).
_INVALID_FILENAME_CHARS = '<>:"/\\|?*\0'


def get_file_size(filepath: str) -> str:
    size = float(os.path.getsize(filepath))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def open_folder(path: Path) -> None:
    path_str = str(path)
    try:
        if sys.platform == "win32":
            os.startfile(path_str)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path_str], check=False)
        else:
            subprocess.run(["xdg-open", path_str], check=False)
    except OSError as e:
        log.warning("Não foi possível abrir pasta %s: %s", path_str, e)


def sanitize_basename(name: str) -> str:
    """Nome de arquivo seguro (sem path). Vazio / . / .. → \"\"."""
    # Aceita / e \ como separadores (path Windows em host Linux).
    base = Path(name.replace("\\", "/")).name.strip()
    if not base or base in (".", ".."):
        return ""
    for ch in _INVALID_FILENAME_CHARS:
        base = base.replace(ch, "_")
    return base


def resolve_managed_folder(kind: str) -> Path | None:
    if kind == "received":
        return paths.UPLOAD_FOLDER
    if kind == "public":
        return paths.PUBLIC_FOLDER
    return None


def safe_path_in_folder(folder: Path, name: str) -> Path | None:
    safe = sanitize_basename(name)
    if not safe:
        return None
    folder_resolved = folder.resolve()
    full = (folder / safe).resolve()
    try:
        full.relative_to(folder_resolved)
    except ValueError:
        return None
    return full


def unique_dest(folder: Path, filename: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    n = 2
    while True:
        candidate = folder / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def list_folder_files(folder: Path) -> list[dict[str, str]]:
    files_data: list[dict[str, str]] = []
    if not folder.exists():
        return files_data
    try:
        for f in sorted(os.listdir(folder)):
            fp = folder / f
            if fp.is_file():
                files_data.append({"name": f, "size": get_file_size(str(fp))})
    except OSError as e:
        log.warning("Falha ao listar %s: %s", folder, e)
    return files_data


def wants_replace(raw: str | None) -> bool:
    value = (raw or "").strip().lower()
    return value in ("1", "true", "yes", "on")
