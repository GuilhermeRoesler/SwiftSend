"""Checagem e aplicação de atualizações via GitHub Releases."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

GITHUB_REPO = "GuilhermeRoesler/SwiftSend"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = "SwiftSend-Updater"
CHECK_TIMEOUT_SEC = 12
DOWNLOAD_TIMEOUT_SEC = 600
FORCE_KILL_TIMEOUT_SEC = 10


@dataclass
class UpdateStatus:
    current: str
    latest: str | None = None
    available: bool = False
    download_url: str | None = None
    asset_name: str | None = None
    checked: bool = False
    error: str | None = None
    applying: bool = False

    def as_dict(self) -> dict:
        return {
            "current": self.current,
            "latest": self.latest,
            "available": self.available,
            "download_url": self.download_url,
            "asset_name": self.asset_name,
            "checked": self.checked,
            "error": self.error,
            "applying": self.applying,
        }


FetchJson = Callable[[str], dict]


def normalize_version(tag: str) -> tuple[int, int, int]:
    raw = (tag or "").strip()
    if raw.lower().startswith("v"):
        raw = raw[1:]
    core = raw.split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def is_newer(latest: str, current: str) -> bool:
    return normalize_version(latest) > normalize_version(current)


def platform_asset_matcher(system: str | None = None) -> Callable[[str], bool]:
    plat = (system or sys.platform).lower()

    def windows(name: str) -> bool:
        lower = name.lower()
        return lower.startswith("swiftsend-setup-") and lower.endswith(".exe")

    def linux(name: str) -> bool:
        lower = name.lower()
        return "linux" in lower and lower.endswith(".appimage")

    def macos(name: str) -> bool:
        lower = name.lower()
        return "macos" in lower and lower.endswith(".dmg")

    if plat.startswith("win"):
        return windows
    if plat == "darwin":
        return macos
    return linux


def default_fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SEC) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_version(search_roots: list[Path]) -> str:
    for root in search_roots:
        candidate = root / "VERSION"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    return "0.0.0-dev"


class UpdateService:
    def __init__(
        self,
        current_version: str,
        scripts_dir: Path,
        *,
        fetch_json: FetchJson | None = None,
        download_dir: Path | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._status = UpdateStatus(current=current_version)
        self._scripts_dir = scripts_dir
        self._fetch_json = fetch_json or default_fetch_json
        self._download_dir = download_dir or Path(tempfile.gettempdir()) / "SwiftSendUpdates"
        self._matcher = platform_asset_matcher()

    @property
    def status(self) -> UpdateStatus:
        with self._lock:
            return UpdateStatus(**self._status.__dict__)

    def start_background_check(self) -> None:
        thread = threading.Thread(target=self.check_now, name="SwiftSendUpdateCheck", daemon=True)
        thread.start()

    def mark_skipped(self, reason: str | None = None) -> None:
        """Marca checagem concluída sem update (ex.: modo desenvolvimento)."""
        with self._lock:
            self._status.checked = True
            self._status.available = False
            self._status.latest = None
            self._status.download_url = None
            self._status.asset_name = None
            self._status.error = reason

    def check_now(self) -> UpdateStatus:
        try:
            data = self._fetch_json(GITHUB_API_LATEST)
            tag = str(data.get("tag_name") or "").strip()
            if not tag:
                raise ValueError("Release sem tag_name")

            assets = data.get("assets") or []
            download_url = None
            asset_name = None
            for asset in assets:
                name = str(asset.get("name") or "")
                url = str(asset.get("browser_download_url") or "")
                if name and url and self._matcher(name):
                    download_url = url
                    asset_name = name
                    break

            latest_display = tag[1:] if tag[:1].lower() == "v" else tag
            newer = is_newer(tag, self._status.current)
            available = newer and bool(download_url)
            with self._lock:
                self._status.latest = latest_display
                self._status.available = available
                self._status.download_url = download_url
                self._status.asset_name = asset_name
                self._status.checked = True
                self._status.error = (
                    "Sem artefato para esta plataforma" if newer and not download_url else None
                )
                return UpdateStatus(**self._status.__dict__)
        except Exception as exc:  # noqa: BLE001 — falha de rede/API não deve derrubar o app
            with self._lock:
                self._status.checked = True
                self._status.available = False
                self._status.error = str(exc)
                return UpdateStatus(**self._status.__dict__)

    def apply_update(self) -> dict:
        with self._lock:
            if self._status.applying:
                return {"success": False, "error": "Atualização já em andamento"}
            if not self._status.available or not self._status.download_url or not self._status.asset_name:
                return {"success": False, "error": "Nenhuma atualização disponível"}
            self._status.applying = True
            url = self._status.download_url
            asset_name = self._status.asset_name

        try:
            installer = self._download(url, asset_name)
            self._spawn_apply_script(installer)
            return {"success": True, "installer": str(installer)}
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._status.applying = False
            return {"success": False, "error": str(exc)}

    def _download(self, url: str, asset_name: str) -> Path:
        self._download_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(asset_name).name
        dest = self._download_dir / safe_name
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SEC) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)
        if dest.stat().st_size <= 0:
            raise RuntimeError("Download vazio")
        return dest

    def _resolve_script(self) -> Path:
        if sys.platform == "win32":
            name = "apply_update.ps1"
        else:
            name = "apply_update.sh"
        candidates = [
            self._scripts_dir / name,
            Path(getattr(sys, "_MEIPASS", "")) / "scripts" / name,
            Path(__file__).resolve().parent.parent / "scripts" / name,
        ]
        for path in candidates:
            if path.is_file():
                return path
        raise FileNotFoundError(f"Script de update não encontrado: {name}")

    def _spawn_apply_script(self, installer: Path) -> None:
        src = self._resolve_script()
        # Copia para TEMP: em frozen o _MEIPASS some quando o processo morre.
        staging = Path(tempfile.gettempdir()) / src.name
        shutil.copy2(src, staging)
        if sys.platform != "win32":
            staging.chmod(staging.stat().st_mode | 0o111)

        pid = os.getpid()
        if sys.platform == "win32":
            args = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(staging),
                "-TargetPid",
                str(pid),
                "-Installer",
                str(installer),
                "-TimeoutSec",
                str(FORCE_KILL_TIMEOUT_SEC),
            ]
            creationflags = 0
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.Popen(
                args,
                close_fds=True,
                creationflags=creationflags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["/bin/bash", str(staging), str(pid), str(installer), str(FORCE_KILL_TIMEOUT_SEC)],
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
