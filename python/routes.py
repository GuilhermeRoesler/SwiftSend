"""Rotas Flask do contrato HTTP SwiftSend."""

from __future__ import annotations

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

import fsutil
import paths
import upload_tokens


def is_desktop_host() -> bool:
    host_header = request.headers.get("Host") or ""
    return "localhost" in host_header or "127.0.0.1" in host_header


def host_forbidden():
    return jsonify({"error": "Forbidden"}), 403


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        if is_desktop_host():
            files_received = (
                len(list(paths.UPLOAD_FOLDER.iterdir())) if paths.UPLOAD_FOLDER.exists() else 0
            )
            return render_template(
                "dashboard.html",
                base_url=paths.BASE_URL,
                received_count=files_received,
                upload_path=str(paths.UPLOAD_FOLDER),
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
            page_sub=(
                "Arquivos enviados pelos visitantes — apague ou renomeie se pedirem correção, "
                "ou adicione aqui."
            ),
            empty_hint=(
                "Nada recebido ainda. Visitantes enviam pela página Enviar, ou arraste arquivos acima."
            ),
            files=fsutil.list_folder_files(paths.UPLOAD_FOLDER),
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
            files=fsutil.list_folder_files(paths.PUBLIC_FOLDER),
            is_desktop=True,
        )

    @app.route("/api/host/open")
    def api_host_open():
        if not is_desktop_host():
            return host_forbidden()
        folder = fsutil.resolve_managed_folder(request.args.get("folder") or "")
        if folder is None:
            return jsonify({"error": "Pasta inválida"}), 400
        fsutil.open_folder(folder)
        return jsonify({"success": True})

    @app.route("/api/host/delete", methods=["POST"])
    def api_host_delete():
        if not is_desktop_host():
            return host_forbidden()
        data = request.get_json(silent=True) or {}
        folder = fsutil.resolve_managed_folder(str(data.get("folder") or ""))
        target = fsutil.safe_path_in_folder(folder, str(data.get("name") or "")) if folder else None
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
        folder = fsutil.resolve_managed_folder(str(data.get("folder") or ""))
        src = fsutil.safe_path_in_folder(folder, str(data.get("name") or "")) if folder else None
        new_name = fsutil.sanitize_basename(str(data.get("new_name") or ""))
        if folder is None or src is None or not new_name:
            return jsonify({"error": "Pedido inválido"}), 400
        if not src.is_file():
            return jsonify({"error": "Arquivo não encontrado"}), 404
        dest = fsutil.safe_path_in_folder(folder, new_name)
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
        folder = fsutil.resolve_managed_folder(folder_kind)
        if folder is None:
            return jsonify({"error": "Pasta inválida"}), 400
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        saved = 0
        for file in request.files.getlist("file"):
            if not file.filename:
                continue
            filename = fsutil.sanitize_basename(file.filename)
            if not filename:
                continue
            dest = fsutil.unique_dest(folder, filename)
            file.save(str(dest))
            saved += 1

        if saved == 0:
            return jsonify({"error": "No file part"}), 400
        return jsonify({"success": True}), 200

    @app.route("/api/host/update", methods=["GET", "POST"])
    def api_host_update():
        if not is_desktop_host():
            return host_forbidden()
        if request.method == "GET":
            return jsonify(paths.UPDATE_SERVICE.status.as_dict())
        result = paths.UPDATE_SERVICE.apply_update()
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)

    @app.route("/browse")
    def browse():
        return render_template(
            "browse.html",
            files=fsutil.list_folder_files(paths.PUBLIC_FOLDER),
            is_desktop=False,
        )

    @app.route("/upload")
    def upload_page():
        return render_template("upload.html", is_desktop=False)

    @app.route("/api/upload", methods=["POST"])
    def upload_file():
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        replace = fsutil.wants_replace(request.form.get("replace"))
        prepared: list[tuple[object, str]] = []
        for file in request.files.getlist("file"):
            if not file.filename:
                continue
            filename = fsutil.sanitize_basename(file.filename)
            if not filename:
                continue
            prepared.append((file, filename))

        if not prepared:
            return jsonify({"error": "No file part"}), 400

        collisions = sorted({name for _, name in prepared if (paths.UPLOAD_FOLDER / name).exists()})
        if collisions and not replace:
            return (
                jsonify(
                    {
                        "error": "Arquivo já existe",
                        "exists": True,
                        "names": collisions,
                    }
                ),
                409,
            )

        saved: list[dict[str, object]] = []
        for file, filename in prepared:
            dest = paths.UPLOAD_FOLDER / filename
            file.save(str(dest))
            saved.append(upload_tokens.issue_upload_token(filename))

        return (
            jsonify(
                {
                    "success": True,
                    "files": saved,
                    "manage_seconds": upload_tokens.UPLOAD_MANAGE_SECONDS,
                }
            ),
            200,
        )

    @app.route("/api/upload/undo", methods=["POST"])
    def upload_undo():
        data = request.get_json(silent=True) or {}
        name = upload_tokens.consume_upload_token(str(data.get("token") or ""))
        if not name:
            return jsonify({"error": "Token inválido ou expirado"}), 404
        target = fsutil.safe_path_in_folder(paths.UPLOAD_FOLDER, name)
        if target is None or not target.is_file():
            return jsonify({"error": "Arquivo não encontrado"}), 404
        try:
            target.unlink()
        except OSError:
            return jsonify({"error": "Não foi possível apagar"}), 400
        return jsonify({"success": True, "name": name})

    @app.route("/download/<path:filename>")
    def download_file(filename):
        return send_from_directory(app.config["PUBLIC_FOLDER"], filename, as_attachment=True)
