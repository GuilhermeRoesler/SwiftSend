"""Resolução de pastas e metadados de runtime (DATA_ROOT, shared, versão)."""

from __future__ import annotations

import logging
import socket
import sys
from pathlib import Path

from update_service import UpdateService, read_version

log = logging.getLogger(__name__)

PORT = 5000


def _windows_documents_dir() -> Path:
    """Pasta Documentos do usuário (CSIDL_PERSONAL), com fallback."""
    try:
        import ctypes
        from ctypes import wintypes

        csidl_personal = 5
        shgfp_type_current = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        hr = ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[attr-defined]
            None, csidl_personal, None, shgfp_type_current, buf
        )
        if hr == 0 and buf.value:
            return Path(buf.value)
    except (AttributeError, OSError, ValueError) as e:
        log.debug("SHGetFolderPathW indisponível: %s", e)
    return Path.home() / "Documents"


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError as e:
        log.debug("Falha ao detectar IP LAN: %s", e)
        return "127.0.0.1"
    finally:
        s.close()


# Dev: repo root = parent of python/
# Frozen (qualquer SO): Documentos/SwiftSend (gravável; AppImage/.app/Program Files são só leitura)
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    SHARED_DIR = BUNDLE_ROOT / "shared"
    if not SHARED_DIR.exists():
        SHARED_DIR = APP_ROOT / "shared"
    if sys.platform == "win32":
        DATA_ROOT = _windows_documents_dir() / "SwiftSend"
    else:
        DATA_ROOT = Path.home() / "Documents" / "SwiftSend"
else:
    APP_ROOT = Path(__file__).resolve().parent
    DATA_ROOT = APP_ROOT.parent  # repo root
    SHARED_DIR = DATA_ROOT / "shared"

UPLOAD_FOLDER = DATA_ROOT / "arquivos_recebidos"
PUBLIC_FOLDER = DATA_ROOT / "arquivos_publicos"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
PUBLIC_FOLDER.mkdir(parents=True, exist_ok=True)

LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:{PORT}"

_version_roots = [APP_ROOT, SHARED_DIR.parent if SHARED_DIR.parent.exists() else APP_ROOT]
if getattr(sys, "frozen", False):
    _version_roots.insert(0, Path(getattr(sys, "_MEIPASS", APP_ROOT)))
else:
    _version_roots.insert(0, APP_ROOT.parent)

APP_VERSION = read_version(_version_roots)
if getattr(sys, "frozen", False):
    _script_candidates = [
        APP_ROOT / "scripts",
        Path(getattr(sys, "_MEIPASS", APP_ROOT)) / "scripts",
    ]
else:
    _script_candidates = [APP_ROOT.parent / "scripts", APP_ROOT / "scripts"]
SCRIPTS_DIR = next((p for p in _script_candidates if p.is_dir()), _script_candidates[0])

UPDATE_SERVICE = UpdateService(APP_VERSION, SCRIPTS_DIR)
