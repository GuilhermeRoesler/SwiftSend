"""Entrada do SwiftSend (Flask + pywebview)."""

from __future__ import annotations

import logging
import sys
import threading

from flask import Flask

import desktop
import fsutil
import paths
from routes import register_routes

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(
    __name__,
    template_folder=str(paths.SHARED_DIR / "templates"),
    static_folder=str(paths.SHARED_DIR / "static"),
    static_url_path="/static",
)
app.config["UPLOAD_FOLDER"] = str(paths.UPLOAD_FOLDER)
app.config["PUBLIC_FOLDER"] = str(paths.PUBLIC_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024 * 1024  # 16GB

register_routes(app)

# Reexports usados por testes / monkeypatch legado.
UPLOAD_FOLDER = paths.UPLOAD_FOLDER
PUBLIC_FOLDER = paths.PUBLIC_FOLDER
open_folder = fsutil.open_folder
get_file_size = fsutil.get_file_size


def start_server() -> None:
    app.run(host="0.0.0.0", port=paths.PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    import webview

    desktop.configure_windows_app_identity()
    # Só consulta GitHub em build empacotado; em dev o VERSION local pode
    # ficar atrás do release e o botão apareceria sem necessidade.
    if getattr(sys, "frozen", False):
        paths.UPDATE_SERVICE.start_background_check()
    else:
        paths.UPDATE_SERVICE.mark_skipped("dev")

    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    print("--- Servidor Iniciado ---")
    print(f"Versao: {paths.APP_VERSION}")
    print(f"IP Local: {paths.LOCAL_IP}")
    print(f"Pasta Publica: {paths.PUBLIC_FOLDER}")
    print(f"Pasta Recebidos: {paths.UPLOAD_FOLDER}")
    print(f"Shared: {paths.SHARED_DIR}")

    icon_path = desktop.resolve_window_icon()
    screens = webview.screens
    primary_screen = screens[0] if screens else None
    window = webview.create_window(
        "SwiftSend - Transferência de Arquivos",
        f"http://127.0.0.1:{paths.PORT}",
        width=900,
        height=700,
        screen=primary_screen,
    )
    window.events.shown += lambda: desktop.force_windows_taskbar_icon(window, icon_path)
    webview.start(icon=icon_path)
