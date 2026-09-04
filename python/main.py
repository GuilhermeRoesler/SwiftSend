import logging
import os
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


def _windows_documents_dir() -> Path:
    """Pasta Documentos do usuário (CSIDL_PERSONAL), com fallback."""
    try:
        import ctypes
        from ctypes import wintypes

        csidl_personal = 5
        shgfp_type_current = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        hr = ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[attr-defined]
            None, csidl_personal, None, shgfp_type_current, buf
        )
        if hr == 0 and buf.value:
            return Path(buf.value)
    except Exception:
        pass
    return Path.home() / "Documents"


# --- Paths ---
# Dev: repo root = parent of python/
# Frozen (qualquer SO): Documentos/SwiftSend (gravável; AppImage/.app/Program Files são só leitura)
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    # PyInstaller extrai datas em _MEIPASS
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    SHARED_DIR = BUNDLE_ROOT / "shared"
    if not SHARED_DIR.exists():
        SHARED_DIR = APP_ROOT / "shared"
    if sys.platform == "win32":
        DATA_ROOT = _windows_documents_dir() / "SwiftSend"
    else:
        DATA_ROOT = Path.home() / "Documents" / "SwiftSend"
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
    """Ícone nativo da janela/taskbar (pywebview). Fonte: shared/static."""
    static = SHARED_DIR / "static"
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


def sanitize_basename(name: str) -> str:
    """Nome de arquivo seguro (sem path); usado nas APIs host."""
    base = Path(name).name.strip()
    if not base or base in (".", ".."):
        return ""
    for ch in '<>:"/\\|?*\0':
        base = base.replace(ch, "_")
    return base or "arquivo"


def resolve_managed_folder(kind: str) -> Path | None:
    if kind == "received":
        return UPLOAD_FOLDER
    if kind == "public":
        return PUBLIC_FOLDER
    return None


def safe_path_in_folder(folder: Path, name: str) -> Path | None:
    safe = sanitize_basename(name)
    if not safe:
        return None
    folder_resolved = folder.resolve()
    full = (folder / safe).resolve()
    try:
        full.relative_to(folder_resolved)
    except ValueError:
        return None
    return full


def unique_dest(folder: Path, filename: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    n = 2
    while True:
        candidate = folder / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def list_folder_files(folder: Path) -> list[dict[str, str]]:
    files_data: list[dict[str, str]] = []
    if not folder.exists():
        return files_data
    try:
        for f in sorted(os.listdir(folder)):
            fp = folder / f
            if fp.is_file():
                files_data.append({"name": f, "size": get_file_size(str(fp))})
    except OSError as e:
        print(e)
    return files_data


def host_forbidden():
    return jsonify({"error": "Forbidden"}), 403


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
def upload_manager():
    if not is_desktop_host():
        return redirect(url_for("index"))
    return render_template(
        "manager.html",
        folder="received",
        page_title="Recebidos",
        eyebrow="Host",
        eyebrow_icon="inbox",
        page_sub="Arquivos enviados pelos visitantes — apague, renomeie ou adicione aqui.",
        empty_hint="Nada recebido ainda. Visitantes enviam pela página Enviar, ou arraste arquivos acima.",
        files=list_folder_files(UPLOAD_FOLDER),
        is_desktop=True,
    )


@app.route("/public_manager")
def public_manager():
    if not is_desktop_host():
        return redirect(url_for("index"))
    return render_template(
        "manager.html",
        folder="public",
        page_title="Públicos",
        eyebrow="Host",
        eyebrow_icon="folder_shared",
        page_sub="O que os visitantes veem em Baixar — gerencie sem sair do app.",
        empty_hint="Nada público ainda. Arraste arquivos acima para disponibilizar na rede.",
        files=list_folder_files(PUBLIC_FOLDER),
        is_desktop=True,
    )


@app.route("/api/host/open")
def api_host_open():
    if not is_desktop_host():
        return host_forbidden()
    folder = resolve_managed_folder(request.args.get("folder") or "")
    if folder is None:
        return jsonify({"error": "Pasta inválida"}), 400
    open_folder(folder)
    return jsonify({"success": True})


@app.route("/api/host/delete", methods=["POST"])
def api_host_delete():
    if not is_desktop_host():
        return host_forbidden()
    data = request.get_json(silent=True) or {}
    folder = resolve_managed_folder(str(data.get("folder") or ""))
    target = safe_path_in_folder(folder, str(data.get("name") or "")) if folder else None
    if folder is None or target is None:
        return jsonify({"error": "Pedido inválido"}), 400
    if not target.is_file():
        return jsonify({"error": "Arquivo não encontrado"}), 404
    try:
        target.unlink()
    except OSError:
        return jsonify({"error": "Não foi possível apagar"}), 400
    return jsonify({"success": True})


@app.route("/api/host/rename", methods=["POST"])
def api_host_rename():
    if not is_desktop_host():
        return host_forbidden()
    data = request.get_json(silent=True) or {}
    folder = resolve_managed_folder(str(data.get("folder") or ""))
    src = safe_path_in_folder(folder, str(data.get("name") or "")) if folder else None
    new_name = sanitize_basename(str(data.get("new_name") or ""))
    if folder is None or src is None or not new_name:
        return jsonify({"error": "Pedido inválido"}), 400
    if not src.is_file():
        return jsonify({"error": "Arquivo não encontrado"}), 404
    dest = safe_path_in_folder(folder, new_name)
    if dest is None:
        return jsonify({"error": "Nome inválido"}), 400
    if dest.exists():
        return jsonify({"error": "Já existe um arquivo com esse nome"}), 409
    try:
        src.rename(dest)
    except OSError:
        return jsonify({"error": "Não foi possível renomear"}), 400
    return jsonify({"success": True})


@app.route("/api/host/upload", methods=["POST"])
def api_host_upload():
    if not is_desktop_host():
        return host_forbidden()
    folder_kind = request.form.get("folder") or ""
    folder = resolve_managed_folder(folder_kind)
    if folder is None:
        return jsonify({"error": "Pasta inválida"}), 400
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    saved = 0
    for file in request.files.getlist("file"):
        if not file.filename:
            continue
        filename = sanitize_basename(file.filename)
        if not filename:
            continue
        dest = unique_dest(folder, filename)
        file.save(str(dest))
        saved += 1

    if saved == 0:
        return jsonify({"error": "No file part"}), 400
    return jsonify({"success": True}), 200


@app.route("/browse")
def browse():
    return render_template("browse.html", files=list_folder_files(PUBLIC_FOLDER), is_desktop=False)


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
    # Centraliza no monitor principal (x/y omitidos + screen).
    screens = webview.screens
    primary_screen = screens[0] if screens else None
    window = webview.create_window(
        "SwiftSend - Transferência de Arquivos",
        f"http://127.0.0.1:{PORT}",
        width=900,
        height=700,
        screen=primary_screen,
    )
    window.events.shown += lambda: force_windows_taskbar_icon(window, icon_path)
    webview.start(icon=icon_path)
