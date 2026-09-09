"""Integração com o shell nativo (ícone Windows / pywebview)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import paths

log = logging.getLogger(__name__)


def resolve_window_icon() -> str | None:
    """Ícone nativo da janela/taskbar (pywebview). Fonte: shared/static."""
    static = paths.SHARED_DIR / "static"
    candidates: list[Path] = []
    if sys.platform == "win32":
        candidates.append(static / "icon.ico")
    candidates.append(static / "icon.png")
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def configure_windows_app_identity() -> None:
    """Evita que a taskbar use o ícone do python.exe ao rodar via run.bat."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "SwiftSend.LocalTransfer"
        )
    except (AttributeError, OSError) as e:
        log.debug("AppUserModelID não aplicado: %s", e)


def force_windows_taskbar_icon(window, icon_path: str | None) -> None:
    """Garante ICON_SMALL + ICON_BIG (taskbar/Alt+Tab) após a janela nativa existir."""
    if sys.platform != "win32" or not icon_path:
        return
    try:
        import ctypes

        native = getattr(window, "native", None)
        if native is None:
            return
        hwnd = int(native.Handle.ToInt32())
        user32 = ctypes.windll.user32
        image_icon = 1
        lr_loadfromfile = 0x0010
        wm_seticon = 0x0080

        def load(size: int) -> int:
            return int(user32.LoadImageW(None, icon_path, image_icon, size, size, lr_loadfromfile))

        small = load(16)
        big = load(32)
        if small:
            user32.SendMessageW(hwnd, wm_seticon, 0, small)
        if big:
            user32.SendMessageW(hwnd, wm_seticon, 1, big)
    except (AttributeError, OSError, TypeError, ValueError) as e:
        log.debug("Ícone da taskbar não aplicado: %s", e)
