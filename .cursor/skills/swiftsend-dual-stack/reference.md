# Referência — SwiftSend (dual-stack Python + C#)

Documento de domínio, contrato HTTP e **processo de migração** para persistência de contexto entre sessões do agente.

Espelha o padrão do AutoClicker (`python/` + implementação nativa secundária), adaptado a um app **HTTP + WebView** com UI compartilhada.

---

## 1. Visão geral

O **SwiftSend** elimina pen-drive/nuvem para arquivos pesados na mesma rede física:

1. O host inicia o app → sobe servidor HTTP + janela desktop.
2. O dashboard mostra o IP/link de compartilhamento.
3. Visitantes abrem o link no navegador → baixam de `arquivos_publicos` ou enviam para `arquivos_recebidos`.

Não há autenticação, banco nem fila. É um utilitário LAN de arquivo + UI web.

---

## 2. Stack

### Primária (Python) — estado atual e alvo

| Item | Detalhe |
|------|---------|
| Linguagem | Python 3.x |
| HTTP | Flask (`threaded=True`, `0.0.0.0:5000`) |
| Desktop | pywebview → `http://127.0.0.1:5000` |
| UI (hoje) | Templates Jinja em strings dentro de `main.py` + Tailwind/Material via CDN |
| UI (alvo) | Arquivos estáticos/templates em `shared/` |
| Empacotamento | PyInstaller (`--onefile`, `--noconsole`) via `build.py` |
| Deps atuais | `flask`, `pywebview`, `pyinstaller` |

### Secundária (C#) — a implementar

| Item | Detalhe |
|------|---------|
| Runtime | .NET (LTS atual do projeto na época da implementação) |
| HTTP | ASP.NET Core (Kestrel), mesmas rotas/pastas |
| Desktop | WebView2 (WPF ou WinForms) apontando para localhost |
| UI | Consome **`shared/`** (não reimplementar Material em XAML) |
| Empacotamento | `dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true` |
| Papel | Release Windows otimizado (análogo ao `windows-optimized.exe` do AutoClicker C++) |

### Decisão de stack (histórico da conversa)

- Python + Flask + pywebview foi **adequada** ao produto; o padrão arquitetural (HTTP local + WebView) já é o correto.
- C# + WebView2 é upgrade de **plataforma Windows** (publish, integração SO), não mudança de ideia de produto.
- Alternativas mencionadas e **não** adotadas como secundária oficial: Tauri (meio-termo moderno), reescrita total abandonando Python.
- Não migrar “só porque C# é mais rápido”: throughput na LAN limita-se à rede/disco.

---

## 3. Estrutura do repositório

### 3.1 Atual (pré-migração)

```
SwiftSend/
├── main.py              # Flask + templates + pywebview (monólito)
├── build.py             # PyInstaller
├── requirements.txt
├── README.md
├── icon.png
├── images/              # Screenshots do README
├── arquivos_publicos/   # Runtime (gitignored)
└── arquivos_recebidos/  # Runtime (gitignored)
```

Entrypoint real: `main.py` (README ainda pode citar `app.py` — inconsistência a corrigir na migração).

### 3.2 Alvo (pós-migração)

```
SwiftSend/
├── run.bat / run.sh           # Atalho → python/run.*
├── python/
│   ├── main.py                # Flask + pywebview (sem HTML embutido longo)
│   ├── build.py
│   ├── requirements.txt
│   ├── run.bat / run.sh
│   └── dist/                  # PyInstaller (não versionar)
├── csharp/
│   ├── SwiftSend.sln / *.csproj
│   ├── Program.cs             # Kestrel + rotas
│   ├── Desktop/               # Host WebView2 (opcional pasta)
│   └── run.bat                # Windows: build se preciso + run
├── shared/
│   ├── static/                # css, js, fonts, icon (preferir local, sem CDN)
│   ├── templates/             # dashboard + home pública (Jinja ou HTML estático)
│   └── README.md              # (opcional) contrato da UI
├── assets/ ou images/         # Screenshots / marketing
├── .cursor/
│   ├── rules/swiftsend-context.mdc
│   └── skills/swiftsend-dual-stack/
└── README.md
```

Pastas de runtime (`arquivos_*`) continuam relativas ao **cwd** do processo (documentar: rodar a partir da pasta esperada ou usar base path explícito igual nas duas stacks).

---

## 4. Contrato HTTP (alinhar Python e C#)

| Método | Rota | Comportamento |
|--------|------|----------------|
| GET | `/` | Se `Host` contém `localhost` ou `127.0.0.1` → dashboard do host; senão → home pública |
| POST | `/api/upload` | Upload → `arquivos_recebidos/` (JSON de sucesso/erro) |
| GET | download por nome | Serve arquivo de `arquivos_publicos/` como attachment |
| GET | `/icon.png` (ou estático) | Ícone do app |

Configuração alinhada:

| Constante | Valor |
|-----------|--------|
| Porta | `5000` |
| Bind | `0.0.0.0` |
| `MAX` upload | 16 GB (ou documentar o mesmo limite no Kestrel/`MultipartBodyLengthLimit`) |
| Extensões | Aceitar qualquer (equivalente a `ALLOWED_EXTENSIONS = None`) |
| IP local | Descoberta UDP “connect” a `8.8.8.8:80` (ou equivalente) só para exibir o link |

Abrir pastas no SO (dashboard): Windows Explorer / macOS `open` / Linux `xdg-open` — C# no Windows usa `Process.Start` no Explorer; macOS/Linux na secundária C# são opcionais (secundária é Windows-first).

---

## 5. Arquitetura em runtime

```
┌─────────────────────────────┐
│  Shell desktop (WebView)    │
│  http://127.0.0.1:5000      │  → Dashboard (host)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  HTTP server (Flask|Kestrel)│
│  0.0.0.0:5000               │
│  UI files from shared/      │
└──────────────┬──────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
arquivos_publicos   arquivos_recebidos
     ▲                   ▲
     │                   │
 Visitantes LAN (browser) ─ download / upload
```

Sem IPC nativo: comunicação = HTTP. Thread/task do servidor + UI WebView no processo (ou processo host + servidor, desde que a UX continue “um app”).

---

## 6. Processo de migração (checklist)

Copiar e marcar progresso ao executar a migração:

```
Migração SwiftSend dual-stack:
- [ ] Fase 0 — Preparação
- [ ] Fase 1 — Extrair shared/
- [ ] Fase 2 — Mover Python para python/
- [ ] Fase 3 — Run scripts raiz
- [ ] Fase 4 — Implementar csharp/
- [ ] Fase 5 — Paridade de contrato
- [ ] Fase 6 — Docs + (opcional) CI
```

### Fase 0 — Preparação

1. Confirmar que o app atual sobe: Flask + janela + upload/download na LAN.
2. Listar todas as rotas e templates em `main.py` (única fonte da verdade hoje).
3. Não começar C# antes de `shared/` existir — evita duplicar UI.

### Fase 1 — Extrair `shared/`

1. Criar `shared/templates/` (dashboard host + home visitante + layout base).
2. Criar `shared/static/` (CSS/JS/fonts/ícone).
3. **Preferir assets locais**: remover dependência obrigatória de `cdn.tailwindcss.com` / Google Fonts em runtime offline.
4. Flask passa a usar `template_folder` / `static_folder` apontando para `shared/` (paths relativos corretos a partir de `python/`).
5. Validar: UI idêntica à anterior no browser e no pywebview.

### Fase 2 — Mover stack Python → `python/`

1. Mover `main.py`, `build.py`, `requirements.txt` → `python/`.
2. Ajustar paths: `shared/` um nível acima (`../shared`), pastas `arquivos_*` (definir regra única: cwd = raiz do repo ou cwd = `python/` — **igualar depois no C#**).
3. Atualizar `build.py` (entrypoint, datas do PyInstaller para incluir `shared/` se necessário).
4. Criar `python/run.bat` e `python/run.sh`.
5. Smoke test: run + build `.exe`.

### Fase 3 — Atalhos na raiz

1. `run.bat` / `run.sh` na raiz encaminham para `python/run.*` (como no AutoClicker).
2. README: “na raiz = Python por padrão”.

### Fase 4 — Implementar `csharp/`

1. Criar solução ASP.NET Core que:
   - Serve arquivos estáticos/templates de `../shared`
   - Expõe as mesmas rotas e pastas
   - Detecta host vs visitante pelo header `Host`
2. Adicionar host desktop WebView2 → `http://127.0.0.1:5000` (mesma UX).
3. `csharp/run.bat`: restore/build se preciso + executar.
4. Publish single-file como artefato Windows otimizado.

### Fase 5 — Paridade de contrato

Checklist de aceitação (rodar nas duas stacks):

- [ ] Dashboard em localhost mostra IP e link corretos
- [ ] Celular/outro PC na LAN abre home pública (não dashboard)
- [ ] Upload grava em `arquivos_recebidos`
- [ ] Arquivo em `arquivos_publicos` aparece e baixa
- [ ] Limite/grande arquivo: comportamento documentado e alinhado
- [ ] Abrir pasta no Explorer (host) funciona no Windows
- [ ] Ícone/UI consistente (mesmos arquivos `shared/`)

### Fase 6 — Documentação e CI

1. Reescrever README no estilo AutoClicker: estrutura, Python primária, C# secundária, builds, releases.
2. Corrigir menção a `app.py` → entrypoint real.
3. (Opcional) `.github/workflows/release.yml`: artefato Python + `windows-optimized` (C#).
4. Manter esta skill/rule atualizadas se o contrato mudar.

---

## 7. Ordem do que NÃO fazer

- Não criar UI C# nativa (WinUI/XAML) como substituto da web — quebra o compartilhamento com visitantes e com `shared/`.
- Não manter templates grandes só em `python/main.py` depois da Fase 1.
- Não mudar porta/pastas/rotas só numa stack.
- Não remover a stack Python ao adicionar C# (Python permanece **primária** / default dos `run.*`).
- Não tratar a migração como “reescrita total”: é **reorganização + segunda backend**.

---

## 8. Executar e compilar (alvo)

### Python

```powershell
cd python
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Build:

```powershell
cd python
python build.py
# → python/dist/SwiftSend.exe
```

### C#

```powershell
cd csharp
dotnet run
# ou publish single-file win-x64
```

### Raiz

```powershell
.\run.bat    # → Python
.\csharp\run.bat
```

---

## 9. Limitações conhecidas (hoje / pós-MVP)

- Sem auth, HTTPS, discovery mDNS/Bonjour, ou fila de transfers
- UI ainda pode depender de CDN até a Fase 1 completar assets locais
- PyInstaller: binário grande / falsos positivos de antivírus
- C# secundária: foco Windows; macOS/Linux continuam na primária Python
- Sem testes automatizados no estado atual do repo

---

## 10. Relação com o AutoClicker

| AutoClicker | SwiftSend |
|-------------|-----------|
| `python/` + `cpp/` | `python/` + `csharp/` |
| UI duplicada (Tk vs Win32) | UI **única** em `shared/` |
| Secundária = latência/input nativo | Secundária = host HTTP + publish Windows |
| `windows-optimized.exe` (C++) | `windows-optimized` (C# / WebView2) |
| Rule + skill em `.cursor/` | Mesmo padrão (este documento) |

Ao implementar, preferir a mesma ergonomia de DX: `run.*` na raiz, README bilingue de stacks, releases com dois artefatos Windows quando houver CI.
