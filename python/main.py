import logging
import os
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

# --- Paths ---
# Dev: repo root = parent of python/
# Frozen: pasta do executável
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    # PyInstaller extrai datas em _MEIPASS
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    SHARED_DIR = BUNDLE_ROOT / "shared"
    if not SHARED_DIR.exists():
        SHARED_DIR = APP_ROOT / "shared"
    DATA_ROOT = APP_ROOT
else:
    APP_ROOT = Path(__file__).resolve().parent
    DATA_ROOT = APP_ROOT.parent  # repo root
    SHARED_DIR = DATA_ROOT / "shared"

UPLOAD_FOLDER = DATA_ROOT / "arquivos_recebidos"
PUBLIC_FOLDER = DATA_ROOT / "arquivos_publicos"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
PUBLIC_FOLDER.mkdir(parents=True, exist_ok=True)

PORT = 5000

app = Flask(
    __name__,
    template_folder=str(SHARED_DIR / "templates"),
    static_folder=str(SHARED_DIR / "static"),
    static_url_path="/static",
)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["PUBLIC_FOLDER"] = str(PUBLIC_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024 * 1024  # 16GB

logging.getLogger("werkzeug").setLevel(logging.ERROR)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:{PORT}"


def get_file_size(filepath: str) -> str:
    size = float(os.path.getsize(filepath))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def is_desktop_host() -> bool:
    host_header = request.headers.get("Host") or ""
    return "localhost" in host_header or "127.0.0.1" in host_header


def resolve_window_icon() -> str | None:
    """Ícone nativo da janela/taskbar (pywebview). No Windows prefira .ico."""
    candidates: list[Path] = []
    if sys.platform == "win32":
        candidates.extend(
            (
                DATA_ROOT / "icon.ico",
                SHARED_DIR / "static" / "icon.ico",
                APP_ROOT / "icon.ico",
            )
        )
    candidates.extend(
        (
            SHARED_DIR / "static" / "icon.png",
            DATA_ROOT / "icon.png",
            APP_ROOT / "icon.png",
        )
    )
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
    except Exception:
        pass


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
    except Exception:
        pass


def open_folder(path: Path) -> None:
    path_str = str(path)
    if sys.platform == "win32":
        os.startfile(path_str)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path_str}"')
    else:
        os.system(f'xdg-open "{path_str}"')


@app.route("/")
def index():
    if is_desktop_host():
        files_received = len(list(UPLOAD_FOLDER.iterdir())) if UPLOAD_FOLDER.exists() else 0
        return render_template(
            "dashboard.html",
            base_url=BASE_URL,
            received_count=files_received,
            upload_path=str(UPLOAD_FOLDER),
            is_desktop=True,
        )
    return render_template("home.html", is_desktop=False)


@app.route("/upload_manager")
def open_upload_folder():
    open_folder(UPLOAD_FOLDER)
    return redirect(url_for("index"))


@app.route("/public_manager")
def open_public_folder():
    open_folder(PUBLIC_FOLDER)
    return redirect(url_for("index"))


@app.route("/browse")
def browse():
    files_data = []
    try:
        for f in sorted(os.listdir(app.config["PUBLIC_FOLDER"])):
            fp = os.path.join(app.config["PUBLIC_FOLDER"], f)
            if os.path.isfile(fp):
                files_data.append({"name": f, "size": get_file_size(fp)})
    except OSError as e:
        print(e)
    return render_template("browse.html", files=files_data, is_desktop=False)


@app.route("/upload")
def upload_page():
    return render_template("upload.html", is_desktop=False)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    for file in request.files.getlist("file"):
        if not file.filename:
            continue
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], timestamp + filename))

    return jsonify({"success": True}), 200


@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(app.config["PUBLIC_FOLDER"], filename, as_attachment=True)


def start_server():
    app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    import webview

    configure_windows_app_identity()

    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    print("--- Servidor Iniciado ---")
    print(f"IP Local: {LOCAL_IP}")
    print(f"Pasta Publica: {PUBLIC_FOLDER}")
    print(f"Pasta Recebidos: {UPLOAD_FOLDER}")
    print(f"Shared: {SHARED_DIR}")

    icon_path = resolve_window_icon()
    window = webview.create_window(
        "SwiftSend - Transferência de Arquivos",
        f"http://127.0.0.1:{PORT}",
        width=900,
        height=700,
    )
    window.events.shown += lambda: force_windows_taskbar_icon(window, icon_path)
    webview.start(icon=icon_path)
