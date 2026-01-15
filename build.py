import PyInstaller.__main__
import os
import shutil
import sys

def build():
    print("--- Iniciando Build do SwiftSend ---")

    # 1. Limpeza de builds anteriores
    print("Limpando arquivos temporários...")
    folders_to_clean = ['build', 'dist']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Aviso: Não foi possível limpar {folder}: {e}")

    if os.path.exists('SwiftSend.spec'):
        os.remove('SwiftSend.spec')

    # 2. Definição dos argumentos do PyInstaller
    # --noconsole: Remove a tela preta do terminal (fundo)
    # --onefile: Gera um único arquivo .exe
    args = [
        'main.py',
        '--name=SwiftSend',
        '--onefile',
        '--noconsole',
        '--clean',
        '--log-level=WARN',
    ]

    # Adicionar ícone se existir (opcional)
    # if os.path.exists('icon.ico'):
    #     args.append('--icon=icon.ico')

    # 3. Executar o PyInstaller
    print("Gerando executável... (isso pode levar alguns minutos)")
    try:
        PyInstaller.__main__.run(args)
        print("\nSUCESSO!")
        print(f"O executável foi criado em: {os.path.join(os.getcwd(), 'dist')}")
    except Exception as e:
        print(f"\nERRO durante o build: {e}")

if __name__ == "__main__":
    build()