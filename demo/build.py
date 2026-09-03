"""Gera site estático de demo a partir de shared/ (GitHub Pages)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SHARED = REPO / "shared"
DIST = ROOT / "dist"

MOCK_FILES = [
    {"name": "apresentacao-projeto.pdf", "size": "2.4 MB"},
    {"name": "backup-fotos.zip", "size": "850 MB"},
    {"name": "video-reuniao.mp4", "size": "1.2 GB"},
]

DEMO_BANNER = """
<div class="demo-banner" role="status">
  <strong>Demo estática</strong>
  — visualização no GitHub Pages; transferência real só no app desktop.
  <span class="demo-nav">
    <a href="index.html">Visitante</a>
    ·
    <a href="dashboard.html">Host</a>
  </span>
</div>
<style>
  .demo-banner {
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 0.875rem;
    padding: 0.6rem 1rem;
    text-align: center;
    border-bottom: 1px solid #d2e3fc;
  }
  .demo-banner a { color: inherit; font-weight: 500; }
  .demo-nav { margin-left: 0.5rem; white-space: nowrap; }
  body.flex.flex-col.h-screen { min-height: 100vh; }
</style>
"""

DEMO_TOAST_SCRIPT = """
<script>
(function () {
  function toast(msg) {
    var el = document.createElement("div");
    el.textContent = msg;
    el.setAttribute("role", "status");
    el.style.cssText = "position:fixed;bottom:1.25rem;left:50%;transform:translateX(-50%);background:#202124;color:#fff;padding:0.75rem 1.25rem;border-radius:999px;font-size:0.875rem;z-index:9999;box-shadow:0 4px 16px rgba(0,0,0,.2);";
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 2800);
  }
  document.querySelectorAll("[data-demo-action]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      toast("Disponível apenas no app SwiftSend (rede local).");
    });
  });
})();
</script>
"""


def rewrite_asset_paths(html: str) -> str:
    html = html.replace('href="/static/', 'href="static/')
    html = html.replace('src="/static/', 'src="static/')
    html = html.replace('href="/browse"', 'href="browse.html"')
    html = html.replace('href="/upload"', 'href="upload.html"')
    html = html.replace('href="/"', 'href="index.html"')
    html = html.replace('href="/upload_manager"', 'href="#" data-demo-action')
    html = html.replace('href="/public_manager"', 'href="#" data-demo-action')
    html = re.sub(
        r'href="/download/[^"]*"',
        'href="#" data-demo-action',
        html,
    )
    # Demo usa JS próprio (sem POST real).
    html = html.replace('src="static/js/upload.js"', 'src="static/js/upload-demo.js"')
    return html


def inject_demo_chrome(html: str) -> str:
    html = html.replace("<body", "<body", 1)
    html = re.sub(
        r"(<body[^>]*>)",
        r"\1" + DEMO_BANNER,
        html,
        count=1,
    )
    if "</body>" in html:
        html = html.replace("</body>", DEMO_TOAST_SCRIPT + "\n</body>", 1)
    return html


def render_pages(env: Environment) -> dict[str, str]:
    pages = {
        "index.html": env.get_template("home.html").render(is_desktop=False),
        "dashboard.html": env.get_template("dashboard.html").render(
            is_desktop=True,
            base_url="http://192.168.0.15:5000",
            received_count=3,
            upload_path="arquivos_recebidos/",
        ),
        "browse.html": env.get_template("browse.html").render(
            is_desktop=False,
            files=MOCK_FILES,
        ),
        "upload.html": env.get_template("upload.html").render(is_desktop=False),
    }
    return {
        name: inject_demo_chrome(rewrite_asset_paths(html))
        for name, html in pages.items()
    }


def copy_static() -> None:
    dest = DIST / "static"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SHARED / "static", dest)

    css = dest / "css" / "app.css"
    text = css.read_text(encoding="utf-8")
    # Paths absolutos quebram em project Pages (/repo/...).
    css.write_text(
        text.replace('url("/static/fonts/', 'url("../fonts/'), encoding="utf-8"
    )

    demo_js = ROOT / "upload-demo.js"
    shutil.copy2(demo_js, dest / "js" / "upload-demo.js")


def build() -> None:
    if not SHARED.is_dir():
        raise FileNotFoundError(f"shared/ não encontrado: {SHARED}")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(SHARED / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )

    copy_static()
    for name, html in render_pages(env).items():
        (DIST / name).write_text(html, encoding="utf-8")

    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Demo gerada em: {DIST}")


if __name__ == "__main__":
    build()
