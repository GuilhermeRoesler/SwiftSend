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
# Windows → python/dist/SwiftSend.exe
# Linux/macOS → python/dist/SwiftSend
```

Build **nativo por SO** (sem cross-compile). Inclui `shared/` e `--collect-all=webview`.
No Linux de CI: GTK 3 + WebKitGTK + `PyGObject`.

### C# → publish profiles (win-x64)

```powershell
dotnet publish csharp/SwiftSend/SwiftSend.csproj -c Release -p:PublishProfile=FrameworkDependent  # → csharp/dist/fdd
dotnet publish csharp/SwiftSend/SwiftSend.csproj -c Release -p:PublishProfile=SelfContained         # → csharp/dist/scd
dotnet publish csharp/SwiftSend/SwiftSend.csproj -c Release -p:PublishProfile=ReadyToRun            # → csharp/dist/r2r
```

| Perfil | Conteúdo | Requisito extra |
|--------|----------|-----------------|
| `FrameworkDependent` | single-file FDD | .NET 8 Desktop + ASP.NET Core Runtime |
| `SelfContained` | single-file SCD | — (só WebView2) |
| `ReadyToRun` | SCD + R2R | — (só WebView2); Native AOT (`PublishAot`) **não** funciona com WPF |

## Notas

- C# = Windows only; Python = multiplataforma (releases win/linux/mac).
- PyInstaller: binário grande / possíveis falsos positivos de antivírus.
- CD: tag `v*` → Python (`windows-amd64`, `linux-amd64`, `macos-arm64`, `macos-amd64`) + zips C# (`fdd` / `scd` / `r2r`).
- Demo Pages: `python demo/build.py` + workflow `.github/workflows/pages.yml` (UI estática a partir de `shared/`).
