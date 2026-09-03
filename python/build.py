import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SHARED = REPO / "shared"


def binary_name() -> str:
    return "SwiftSend.exe" if sys.platform == "win32" else "SwiftSend"


def build() -> Path:
    print("--- Iniciando Build do SwiftSend (Python) ---")
    print(f"Plataforma: {sys.platform} ({os.name})")

    if not SHARED.is_dir():
        raise FileNotFoundError(f"Pasta shared não encontrada: {SHARED}")

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

    # PyInstaller --add-data: Windows usa ; , Unix usa :
    sep = ";" if sys.platform == "win32" else ":"
    add_data = f"{SHARED}{sep}shared"

    args = [
        str(ROOT / "main.py"),
        "--name=SwiftSend",
        "--onefile",
        "--clean",
        "--log-level=WARN",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT}",
        f"--add-data={add_data}",
        # Garante backends nativos do pywebview por SO (Win/macOS/Linux).
        "--collect-all=webview",
    ]

    # --windowed no macOS cria .app; preferimos binário simples em dist/ em todos os SOs.
    if sys.platform == "win32":
        args.append("--noconsole")

    icon_ico = REPO / "icon.ico"
    icon_png = REPO / "icon.png"
    if sys.platform == "win32" and icon_ico.exists():
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

    print("\nSUCESSO!")
    print(f"O executável foi criado em: {out}")
    return out


if __name__ == "__main__":
    build()
