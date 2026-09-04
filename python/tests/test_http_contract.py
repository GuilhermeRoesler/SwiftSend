from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pytest

from main import get_file_size


def test_dashboard_on_localhost(client):
    response = client.get("/", headers={"Host": "127.0.0.1:5000"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Servidor ativo" in body
    assert "badge-url" in body or "base_url" in body or "http://" in body


def test_home_on_lan_host(client):
    response = client.get("/", headers={"Host": "192.168.0.10:5000"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Transferência na LAN" in body
    assert "Servidor ativo" not in body


def test_browse_lists_public_files(client, folders):
    _upload, public = folders
    (public / "demo.txt").write_text("hello", encoding="utf-8")

    response = client.get("/browse")
    assert response.status_code == 200
    assert "demo.txt" in response.get_data(as_text=True)


def test_upload_page(client):
    response = client.get("/upload")
    assert response.status_code == 200


def test_api_upload_saves_with_timestamp(client, folders):
    upload, _public = folders
    data = {"file": (BytesIO(b"payload"), "nota.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}

    saved = list(upload.iterdir())
    assert len(saved) == 1
    assert re.match(r"^\d{8}_\d{6}_nota\.txt$", saved[0].name)
    assert saved[0].read_bytes() == b"payload"


def test_api_upload_multiple_files(client, folders):
    upload, _public = folders
    data = {
        "file": [
            (BytesIO(b"aa"), "a.txt"),
            (BytesIO(b"bb"), "b.txt"),
        ]
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}
    assert len(list(upload.iterdir())) == 2


def test_api_upload_without_file_returns_400(client):
    response = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_download_attachment(client, folders):
    _upload, public = folders
    (public / "arquivo.bin").write_bytes(b"abc")

    response = client.get("/download/arquivo.bin")
    assert response.status_code == 200
    assert response.data == b"abc"
    disposition = response.headers.get("Content-Disposition", "")
    assert "attachment" in disposition.lower()


def test_download_missing_returns_404(client):
    response = client.get("/download/missing.bin")
    assert response.status_code == 404


def test_download_rejects_path_traversal(client, folders):
    _upload, public = folders
    outside = public.parent / "secret.txt"
    outside.write_text("nope", encoding="utf-8")

    response = client.get("/download/../secret.txt")
    assert response.status_code in (404, 400)


def test_manager_routes_redirect(client):
    assert client.get("/upload_manager").status_code in (301, 302)
    assert client.get("/public_manager").status_code in (301, 302)


def test_static_css_served(client):
    response = client.get("/static/css/app.css")
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("nbytes", "expected"),
    [
        (0, "0.0 B"),
        (10, "10.0 B"),
        (1023, "1023.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
    ],
)
def test_get_file_size_units(tmp_path: Path, nbytes: int, expected: str):
    path = tmp_path / "sized.bin"
    path.write_bytes(b"x" * nbytes)
    assert get_file_size(str(path)) == expected
