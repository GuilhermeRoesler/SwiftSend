---
name: swiftsend-dual-stack
description: >-
  Domínio do SwiftSend (transferência de arquivos na LAN) e migração dual-stack
  Python primário + C# secundário, no molde do AutoClicker. Use ao reorganizar o
  repo, extrair UI para shared/, implementar csharp/, alterar rotas Flask/Kestrel,
  pywebview/WebView2, pastas de arquivos, build PyInstaller/dotnet, ou discutir
  stack/arquitetura do projeto.
---

# SwiftSend — Dual Stack

## Product model

App desktop híbrido para transferir arquivos pesados na **rede local (LAN)** sem pen-drive nem nuvem.

1. Host sobe servidor HTTP em `0.0.0.0:5000`.
2. Janela desktop (WebView) abre o **dashboard** em `http://127.0.0.1:5000`.
3. Outros dispositivos acessam `http://<IP-LAN>:5000` → UI pública (download/upload).
4. Arquivos em pastas locais: `arquivos_publicos/` e `arquivos_recebidos/`.

Roteamento por `Host`: `localhost` / `127.0.0.1` → dashboard; caso contrário → home pública.

## Estado atual vs alvo

| Estado | Layout |
|--------|--------|
| **Atual (pré-migração)** | Monólito flat: `main.py`, `build.py`, templates embutidos |
| **Alvo (pós-migração)** | `python/` + `csharp/` + `shared/` (UI única) |

Espelha o [AutoClicker](https://github.com/GuilhermeRoesler/AutoClicker) (`python/` + `cpp/`), com diferença crítica: **UI web fica em `shared/`** — não duplicar HTML entre stacks.

## Architecture (alvo)

| Path | Role |
|------|------|
| `python/` | **Primária** — Flask + pywebview + PyInstaller |
| `csharp/` | **Secundária** — ASP.NET Core (Kestrel) + WebView2 + `dotnet publish` |
| `shared/` | HTML/CSS/JS, ícone — servido por ambas as backends |

| Concern | Python | C# |
|---------|--------|-----|
| HTTP | Flask | ASP.NET Core Minimal APIs / MVC estático |
| Desktop shell | pywebview (WebView2 no Windows) | WebView2 (WPF/WinForms) |
| UI | `shared/` | `shared/` |
| Build | `python/build.py` → PyInstaller | `dotnet publish` single-file |
| Papel | padrão / multiplataforma | Windows otimizado (`windows-optimized`) |

## Invariants (não quebrar)

- Porta padrão **5000**; bind **`0.0.0.0`** para LAN.
- Pastas **`arquivos_publicos`** e **`arquivos_recebidos`** (criar se não existirem).
- Mesmas rotas e comportamento host vs visitante nas duas backends.
- UI de produção vem de **`shared/`** (sem CDN obrigatório no alvo; preferir assets locais).
- Sem banco: persistência = sistema de arquivos.
- Clientes na LAN não devem depender de qual runtime hospeda o servidor.
- Mudança de contrato (rotas, pastas, fluxo) → atualizar **Python e C#**, salvo pedido de uma stack só.

## Stack decision (contexto)

- Stack Python atual foi **adequada** ao MVP; não é “errada”.
- C# não inventa o modelo desktop+web — **já é o padrão atual** (HTTP local + WebView).
- C# justifica-se por empacotamento Windows e integração com o SO, não por milagre de throughput na LAN.
- Não reescrever só por performance de linguagem: gargalo é rede/disco.

## When editing

1. Leia [reference.md](reference.md) para migração passo a passo, rotas e estrutura.
2. Se o repo ainda estiver flat, trate mudanças grandes como parte da migração (não inventar outro layout).
3. Prefira extrair/alterar UI em `shared/` em vez de templates só numa backend.
4. Strings de UI em **português**, alinhadas ao README.
5. Após mudar API/pastas, verificar mentalmente: dashboard localhost → IP na LAN → upload → download → pastas no disco.

## Migração (resumo)

Ordem obrigatória — detalhes em [reference.md](reference.md):

1. Extrair templates/assets → `shared/`
2. Mover código atual → `python/` e apontar para `shared/`
3. Criar `run.bat` / `run.sh` (raiz → Python)
4. Implementar `csharp/` com o mesmo contrato HTTP + WebView2
5. Atualizar README (primária / secundária / builds)
6. (Opcional) CI de release com artefato `windows-optimized` (C#)
