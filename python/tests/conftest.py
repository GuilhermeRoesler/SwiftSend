from __future__ import annotations

from pathlib import Path

import pytest

import main


@pytest.fixture
def folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload = tmp_path / "arquivos_recebidos"
    public = tmp_path / "arquivos_publicos"
    upload.mkdir()
    public.mkdir()

    monkeypatch.setattr(main, "UPLOAD_FOLDER", upload)
    monkeypatch.setattr(main, "PUBLIC_FOLDER", public)
    monkeypatch.setattr(main, "open_folder", lambda _path: None)
    main.app.config["UPLOAD_FOLDER"] = str(upload)
    main.app.config["PUBLIC_FOLDER"] = str(public)
    return upload, public


@pytest.fixture
def client(folders):
    return main.app.test_client()
