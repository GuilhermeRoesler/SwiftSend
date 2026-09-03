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
    ·
    <a href="browse.html">Baixar</a>
    ·
    <a href="upload.html">Enviar</a>
  </span>
</div>
<style>
  .demo-banner {
    background: #0b1220;
    color: #d7e3ff;
    font-family: "Sora", system-ui, sans-serif;
    font-size: 0.875rem;
    padding: 0.65rem 1rem;
    text-align: center;
    border-bottom: 1px solid #1a2436;
    position: relative;
    z-index: 20;
  }
  .demo-banner a { color: #9ec0ff; font-weight: 600; text-decoration: none; }
  .demo-banner a:hover { text-decoration: underline; }
  .demo-nav { margin-left: 0.5rem; white-space: nowrap; }
  body.flex.flex-col.h-screen { min-height: 100vh; }
  .demo-window {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    max-width: 72rem;
    width: 100%;
    margin: 1.25rem auto 2rem;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(11, 18, 32, 0.14);
    box-shadow: 0 28px 60px rgba(11, 18, 32, 0.22);
    background: #e8eef6;
  }
  .demo-window .site-header {
    border-radius: 0;
    border-bottom: 1px solid #d8dee8;
  }
  body.page-host {
    background:
      radial-gradient(ellipse 70% 50% at 50% 0%, rgba(21, 101, 239, 0.18), transparent 55%),
      #c5d0e0 !important;
  }
  body.page-host.flex.flex-col.h-screen {
    height: auto;
    min-height: 100vh;
  }
</style>
"""

DEMO_TOAST_SCRIPT = """
<script>
(function () {
  function toast(msg) {
    var el = document.createElement("div");
    el.textContent = msg;
    el.setAttribute("role", "status");
    el.style.cssText = "position:fixed;bottom:1.25rem;left:50%;transform:translateX(-50%);background:#0b1220;color:#fff;padding:0.75rem 1.25rem;border-radius:999px;font-size:0.875rem;z-index:9999;font-family:Sora,system-ui,sans-serif;";
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


def inject_demo_chrome(html: str, *, desktop_frame: bool = False) -> str:
    html = re.sub(
        r"(<body[^>]*>)",
        r"\1" + DEMO_BANNER,
        html,
        count=1,
    )

    if desktop_frame:
        # Abre moldura após o <style> do banner; fecha antes dos scripts.
        html = re.sub(
            r"(</style>)",
            r"\1\n<div class=\"demo-window\">",
            html,
            count=1,
        )
        html = re.sub(
            r"(<script\b)",
            r"</div>\n\1",
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
    out = {}
    for name, html in pages.items():
        rewritten = rewrite_asset_paths(html)
        out[name] = inject_demo_chrome(
            rewritten, desktop_frame=(name == "dashboard.html")
        )
    return out


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
