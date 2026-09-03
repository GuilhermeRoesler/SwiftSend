import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SHARED = REPO / "shared"


def build():
    print("--- Iniciando Build do SwiftSend (Python) ---")

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

    # PyInstaller --add-data: no Windows usa ;
    sep = ";" if sys.platform == "win32" else ":"
    add_data = f"{SHARED}{sep}shared"

    args = [
        str(ROOT / "main.py"),
        "--name=SwiftSend",
        "--onefile",
        "--noconsole",
        "--clean",
        "--log-level=WARN",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT}",
        f"--add-data={add_data}",
    ]

    # PyInstaller prefere .ico no Windows; png pode ser ignorado
    icon = REPO / "icon.ico"
    if icon.exists():
        args.append(f"--icon={icon}")

    print("Gerando executável... (isso pode levar alguns minutos)")
    print(f"Incluindo shared: {SHARED}")
    try:
        os.chdir(ROOT)
        PyInstaller.__main__.run(args)
        print("\nSUCESSO!")
        print(f"O executável foi criado em: {ROOT / 'dist' / 'SwiftSend.exe'}")
    except Exception as e:
        print(f"\nERRO durante o build: {e}")
        raise


if __name__ == "__main__":
    build()
