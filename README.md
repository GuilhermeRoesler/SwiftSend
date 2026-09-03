# <img src="icon.png" width="40" align="left" style="margin-right: .8rem">**SwiftSend — Transferência de Arquivos Local**

O **SwiftSend** é uma aplicação desktop leve para enviar e receber arquivos pesados na rede local (Wi-Fi/LAN), sem pen-drive nem nuvem.

![Main interface](images/main_interface.png)

## Funcionalidades

- Servidor HTTP na LAN (`0.0.0.0:5000`)
- Janela desktop (WebView) com dashboard do host
- UI pública para visitantes (baixar / enviar)
- Pastas locais: `arquivos_publicos/` e `arquivos_recebidos/`
- Detecção automática do IP local

## Estrutura (dual-stack)

```
SwiftSend/
├── run.bat / run.sh     # atalho → versão Python
├── python/              # primária (Flask + pywebview)
├── csharp/              # secundária (ASP.NET + WebView2, Windows)
├── shared/              # UI única (templates + static)
├── images/
└── icon.png
```

Mesmo contrato HTTP nas duas backends; a UI vive em `shared/`.

## Stack

| | Primária | Secundária |
|--|----------|------------|
| Runtime | Python 3 | .NET 8 (Windows) |
| HTTP | Flask | ASP.NET Core / Kestrel |
| Desktop | pywebview | WebView2 (WPF) |
| UI | `shared/` | `shared/` |
| Build | PyInstaller | `dotnet publish` |

## Executar

Na raiz (Python por padrão):

```powershell
.\run.bat
```

```bash
./run.sh
```

Por stack:

```powershell
.\python\run.bat
.\csharp\run.bat
```

### Python (desenvolvimento)

```powershell
cd python
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Python (build .exe)

```powershell
cd python
python build.py
# → python/dist/SwiftSend.exe
```

### C# (Windows)

Requisitos: .NET 8 SDK e [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).

```powershell
.\csharp\run.bat
```

Publish single-file (Windows otimizado):

```powershell
dotnet publish csharp/SwiftSend/SwiftSend.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o csharp/dist
```

## Como usar

1. Abra o app — o dashboard mostra o link (ex.: `http://192.168.0.15:5000`).
2. Coloque arquivos em `arquivos_publicos/` (ou use **Gerenciar Públicos**).
3. Na mesma rede, abra o link no navegador para baixar ou enviar.
4. Uploads chegam em `arquivos_recebidos/`.

![Download view](images/download_view.png)

![Upload view](images/upload_view.png)

## Licença

Uso pessoal e educacional.
