---
name: swiftsend-architecture
description: >-
  Arquitetura dual-stack do SwiftSend: python/ (primária), csharp/ (secundária
  Windows), shared/ (UI única). Use ao reorganizar o repo, escolher stack,
  espelhar AutoClicker, alterar shells pywebview/WebView2 ou discutir papéis
  de cada backend.
---

# SwiftSend — Arquitetura Dual-Stack

## Layout

```
SwiftSend/
├── run.bat / run.sh      → Python (padrão)
├── python/               → primária (Flask + pywebview + PyInstaller)
├── csharp/               → secundária Windows (Kestrel + WebView2 + Fluid)
├── shared/               → UI única (templates + static)
├── installer/            → Inno Setup (Windows; empacota build Python)
├── arquivos_publicos/    → runtime (gitignored; em Windows frozen → Documentos)
└── arquivos_recebidos/   → runtime (gitignored; idem)
```

## Papéis

| Path | Papel |
|------|--------|
| `python/` | Padrão / multiplataforma |
| `csharp/` | Windows otimizado (publish single-file) |
| `shared/` | HTML/CSS/JS/fonts — **nunca** duplicar UI por stack |

## Runtime

```
WebView (127.0.0.1:5000)  →  dashboard (host)
         │
HTTP 0.0.0.0:5000 (Flask | Kestrel)  ← UI de shared/
         │
   arquivos_publicos  ↔  visitantes LAN
   arquivos_recebidos ← uploads
```

Sem IPC nativo: tudo via HTTP. Comunicação shell ↔ servidor = mesma origem local.

## Decisão de stack

- Python não é “errada”: adequada ao MVP e multiplataforma.
- C# é upgrade de **empacotamento/integração Windows**, não reescrita de produto.
- Não reescrever por performance de linguagem: gargalo típico é rede/disco.
- Não substituir a UI web por XAML/WinUI nativo — quebra visitantes e `shared/`.
- Não remover Python ao evoluir C#; `run.*` na raiz continuam apontando para Python.

## Relação com AutoClicker

| AutoClicker | SwiftSend |
|-------------|-----------|
| `python/` + `cpp/` | `python/` + `csharp/` |
| UI duplicada | UI **única** em `shared/` |
| Secundária = input nativo | Secundária = host HTTP + publish Windows |

## Ao editar

1. Extrair/alterar UI só em `shared/`.
2. Mudança de contrato → as duas backends ([http-contract](../swiftsend-http-contract/SKILL.md)).
3. Preferir paths relativos a `DATA_ROOT` / `shared/`, não hardcode de máquina.
