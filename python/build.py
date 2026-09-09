import os
import shutil
import subprocess
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SHARED = REPO / "shared"
SCRIPTS = REPO / "scripts"
VERSION_FILE = REPO / "VERSION"


def binary_name() -> str:
    return "SwiftSend.exe" if sys.platform == "win32" else "SwiftSend"


def _strip_v(tag: str) -> str:
    tag = tag.strip()
    if tag[:1] in ("v", "V"):
        return tag[1:]
    return tag


def resolve_version() -> str:
    """Versão embutida no binário: env → tag git no HEAD → VERSION → 0.0.0-dev.

    Em release (tag v*), o CI define SWIFTSEND_VERSION ou GITHUB_REF_NAME.
    Não é preciso editar VERSION no repo a cada tag.
    """
    for key in ("SWIFTSEND_VERSION", "GITHUB_REF_NAME"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        # GITHUB_REF_NAME em workflow_dispatch sem tag pode ser o branch
        if key == "GITHUB_REF_NAME" and os.environ.get("GITHUB_REF_TYPE") == "branch":
            continue
        if key == "GITHUB_REF_NAME" and raw.startswith("refs/"):
            continue
        cleaned = _strip_v(raw)
        if cleaned and cleaned not in ("main", "master", "dev"):
            return cleaned

    try:
        exact = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        if exact.returncode == 0 and exact.stdout.strip():
            return _strip_v(exact.stdout.strip())
    except OSError:
        pass

    if VERSION_FILE.is_file():
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
        if text:
            return _strip_v(text)

    return "0.0.0-dev"


def build() -> Path:
    print("--- Iniciando Build do SwiftSend (Python) ---")
    print(f"Plataforma: {sys.platform} ({os.name})")

    if not SHARED.is_dir():
        raise FileNotFoundError(f"Pasta shared não encontrada: {SHARED}")

    version = resolve_version()
    print(f"Versão embutida: {version}")

    for folder in ("build", "dist"):
        path = ROOT / folder
        if path.exists():
            try:
                shutil.rmtree(path)
            except OSError as e:
                print(f"Aviso: Não foi possível limpar {folder}: {e}")

    spec = ROOT / "SwiftSend.spec"
    if spec.exists():
        spec.unlink()

    embed_dir = ROOT / "build" / "embed"
    embed_dir.mkdir(parents=True, exist_ok=True)
    embed_version = embed_dir / "VERSION"
    embed_version.write_text(version + "\n", encoding="utf-8")

    # PyInstaller --add-data: Windows usa ; , Unix usa :
    sep = ";" if sys.platform == "win32" else ":"
    datas = [f"{SHARED}{sep}shared"]
    if SCRIPTS.is_dir():
        datas.append(f"{SCRIPTS}{sep}scripts")
    datas.append(f"{embed_version}{sep}.")

    args = [
        str(ROOT / "main.py"),
        "--name=SwiftSend",
        "--onefile",
        "--clean",
        "--log-level=WARN",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT}",
        # Garante backends nativos do pywebview por SO (Win/macOS/Linux).
        "--collect-all=webview",
    ]
    for item in datas:
        args.append(f"--add-data={item}")

    # --windowed no macOS cria .app; preferimos binário simples em dist/ em todos os SOs.
    if sys.platform == "win32":
        args.append("--noconsole")

    # Windows exige .ico (ou Pillow para converter PNG). Fonte única: shared/static.
    icon_ico = SHARED / "static" / "icon.ico"
    icon_png = SHARED / "static" / "icon.png"
    if icon_ico.exists():
        args.append(f"--icon={icon_ico}")
    elif icon_png.exists():
        args.append(f"--icon={icon_png}")

    out = ROOT / "dist" / binary_name()
    print("Gerando executável... (isso pode levar alguns minutos)")
    print(f"Incluindo shared: {SHARED}")
    try:
        os.chdir(ROOT)
        PyInstaller.__main__.run(args)
    except Exception as e:
        print(f"\nERRO durante o build: {e}")
        raise

    if not out.is_file():
        raise FileNotFoundError(f"Build não gerou o binário esperado: {out}")

    if sys.platform != "win32":
        out.chmod(out.stat().st_mode | 0o111)

    # Cópia ao lado do exe (Inno / inspeção local); não altera VERSION do repo.
    (out.parent / "VERSION").write_text(version + "\n", encoding="utf-8")

    print("\nSUCESSO!")
    print(f"O executável foi criado em: {out}")
    print(f"VERSION embutida: {version}")
    return out


if __name__ == "__main__":
    build()
