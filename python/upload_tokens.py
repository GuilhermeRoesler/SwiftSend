"""Tokens efêmeros para o visitante desfazer o próprio upload (~10 min)."""

from __future__ import annotations

import secrets
import threading
import time

UPLOAD_MANAGE_SECONDS = 600

_upload_tokens: dict[str, dict[str, object]] = {}
_upload_tokens_lock = threading.Lock()


def _purge_expired(now: float | None = None) -> None:
    ts = time.time() if now is None else now
    expired = [token for token, meta in _upload_tokens.items() if float(meta["expires"]) <= ts]
    for token in expired:
        del _upload_tokens[token]


def issue_upload_token(name: str) -> dict[str, object]:
    token = secrets.token_urlsafe(24)
    expires = time.time() + UPLOAD_MANAGE_SECONDS
    with _upload_tokens_lock:
        _purge_expired()
        stale = [t for t, meta in _upload_tokens.items() if meta["name"] == name]
        for t in stale:
            del _upload_tokens[t]
        _upload_tokens[token] = {"name": name, "expires": expires}
    return {"name": name, "token": token, "expires_in": UPLOAD_MANAGE_SECONDS}


def consume_upload_token(token: str) -> str | None:
    if not token:
        return None
    with _upload_tokens_lock:
        _purge_expired()
        meta = _upload_tokens.pop(token, None)
    if meta is None:
        return None
    return str(meta["name"])
