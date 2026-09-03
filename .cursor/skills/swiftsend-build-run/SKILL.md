---
name: swiftsend-build-run
description: >-
  Como executar e empacotar o SwiftSend (run.bat/sh, venv Python, PyInstaller,
  dotnet run/publish WebView2). Use ao alterar scripts de run, build.py,
  csproj, publish single-file ou documentação de setup.
---

# SwiftSend — Build e Run

## Executar

| Entrada | Efeito |
|---------|--------|
| `run.bat` / `run.sh` (raiz) | → `python/run.*` (padrão) |
| `python/run.bat` | `main.py` (usa `venv` se existir) |
| `csharp/run.bat` | `dotnet build` Release + inicia `.exe` |
| `csharp/run.sh` | Recusa (Windows-only) |

### Python (dev)

```powershell
cd python
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Deps: `flask`, `pywebview`, `pyinstaller`.

### C# (Windows)

Requisitos: .NET 8 SDK + [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).

```powershell
.\csharp\run.bat
```

## Empacotar

### Python → PyInstaller

```powershell
cd python
python build.py
# → python/dist/SwiftSend.exe
```

Incluir `shared/` nos datas do PyInstaller se o build deixar de achar templates/static.

### C# → single-file

```powershell
dotnet publish csharp/SwiftSend/SwiftSend.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o csharp/dist
```

## Notas

- Artefato C# = “windows-optimized”; macOS/Linux continuam na stack Python.
- PyInstaller: binário grande / possíveis falsos positivos de antivírus.
- CI de release com dois artefatos Windows é opcional (ainda não obrigatório).
