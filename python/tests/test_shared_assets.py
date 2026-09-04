from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED = REPO_ROOT / "shared"


def test_required_templates_exist():
    for name in ("dashboard.html", "home.html", "browse.html", "upload.html"):
        assert (SHARED / "templates" / name).is_file(), name


def test_required_static_assets_exist():
    assert (SHARED / "static" / "css" / "app.css").is_file()
    assert (SHARED / "static" / "js" / "upload.js").is_file()
    assert (SHARED / "static" / "icon.png").is_file()
    assert (SHARED / "static" / "icon.ico").is_file()


def test_dynamic_templates_use_compatible_tags():
    """Templates com variáveis devem usar sintaxe Jinja/Fluid ({{ }} / {% %})."""
    for name in ("dashboard.html", "browse.html"):
        text = (SHARED / "templates" / name).read_text(encoding="utf-8")
        assert "{{" in text or "{%" in text, name
