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

Deps: `flask`, `pywebview`, `pyinstaller`, `pillow` (conversão de ícone PNG→ICO no Windows).

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
No Linux de CI: GTK 3 + WebKitGTK + `libgirepository-2.0-dev` + `PyGObject` (≥3.51 exige girepository 2.0).

### Instaladores (canônicos — release)

| SO | Script | Artefato |
|----|--------|----------|
| Windows | `installer/build_installer.ps1` | `SwiftSend-Setup-*.exe` (Inno Setup 6) |
| Linux | `installer/linux/build_appimage.sh` | `SwiftSend-*-x86_64.AppImage` |
| macOS | `installer/macos/build_dmg.sh` | `SwiftSend-*-macos-arm64.dmg` |

```powershell
.\installer\build_installer.ps1 -Version 1.0.0
# → installer/output/SwiftSend-Setup-1.0.0.exe
# -SkipBuild usa python/dist/SwiftSend.exe já existente
```

```bash
./installer/linux/build_appimage.sh 1.0.0          # ou --skip-build
./installer/macos/build_dmg.sh 1.0.0               # só no Darwin
```

- **Windows:** instala em `{autopf}\SwiftSend`, Menu Iniciar + desinstalador; tenta WebView2 se ausente.
- **Linux:** AppImage portátil; runtime GTK 3 + WebKitGTK no sistema.
- **macOS:** DMG com `SwiftSend.app` (arrastar para Aplicativos).
- Dados do usuário (frozen, todos os SOs): `Documentos/SwiftSend/` (não apagados na desinstalação).

### C# → publish local (devs only)

Não entra no GitHub Release. Perfis em `csharp/SwiftSend/Properties/PublishProfiles/`.

```powershell
.\csharp\publish.bat           # fdd + scd + r2r → csharp/dist/
.\csharp\publish.bat scd       # só Self-Contained
```

| Perfil | Conteúdo | Requisito extra |
|--------|----------|-----------------|
| `FrameworkDependent` | single-file FDD + `shared/` | .NET 8 Desktop + ASP.NET Core Runtime |
| `SelfContained` | single-file SCD + `shared/` | — (só WebView2) |
| `ReadyToRun` | SCD + R2R + `shared/` | — (só WebView2); Native AOT (`PublishAot`) **não** funciona com WPF |

O `csproj` copia `shared/` para output e publish (ao lado do `.exe`). Sem isso a UI responde HTTP 500.

## Notas

- C# = Windows only / **só local**; Python = multiplataforma (releases + instaladores).
- PyInstaller: binário grande / possíveis falsos positivos de antivírus.
- CD: tag `v*` → PyInstaller (win/linux/mac) + instaladores (Inno / AppImage / DMG) + portables Python.
- Frozen: `DATA_ROOT` = `Documentos/SwiftSend` (pastas `arquivos_*`).
- Demo Pages: `python demo/build.py` + workflow `.github/workflows/pages.yml` (UI estática a partir de `shared/`).
