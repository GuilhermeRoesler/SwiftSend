# Referência — Contrato HTTP

## POST `/api/upload`

- Campo multipart: `file` (um ou vários); opcional `replace` = `1` / `true` / `yes` / `on`.
- Destino: `{DATA_ROOT}/arquivos_recebidos/`.
- Nome no disco: nome sanitizado. Se já existir **e** `replace` ausente → **409** `{ "error", "exists": true, "names": [...] }` sem gravar.
- Com `replace` (ou nome novo): grava/sobrescreve no nome sanitizado (não gera `nome-2` no upload de visitante).
- Sucesso: JSON `{ "success": true, "files": [{ "name", "token", "expires_in" }], "manage_seconds": 600 }` (HTTP 200).
- Cada `token` permite `POST /api/upload/undo` por ~10 minutos (memória do processo; reinício do app invalida).
- Erro (sem arquivo / falha): HTTP 400 + JSON de erro.
- **Pasta inteira (UI):** o cliente compacta a pasta em um `.zip` no navegador (`fflate`) e envia como um único `file`. Sem rota nova; estrutura de pastas fica dentro do ZIP.

## POST `/api/upload/undo`

- JSON `{ "token": "..." }` (visitante na LAN ok; sem auth).
- Se token válido e arquivo ainda existe com aquele nome → apaga e `{ "success": true, "name" }`.
- Token inválido/expirado/já usado → 404.

### Sanitização de nome

| Stack | Comportamento |
|-------|----------------|
| Python | `werkzeug.utils.secure_filename` |
| C# | Remove caracteres inválidos do SO; fallback `"arquivo"` |

## GET `/download/<filename>`

- Resolve sob `arquivos_publicos/` apenas (sem path traversal).
- Resposta: `Content-Disposition: attachment`.

## Abrir pastas / gerenciador host

| Rota | Comportamento |
|------|----------------|
| `GET /upload_manager` | Host (localhost): renderiza `manager.html` (Recebidos). LAN: redirect `/`. |
| `GET /public_manager` | Host: `manager.html` (Públicos). LAN: redirect `/`. |
| `GET /api/host/open?folder=received\|public` | Host: abre pasta no SO (Python `startfile`/`open`/`xdg-open`; C# `explorer`). JSON `{success:true}`. |
| `POST /api/host/delete` | Host: `{ "folder", "name" }` — apaga arquivo sob a pasta gerenciada. |
| `POST /api/host/rename` | Host: `{ "folder", "name", "new_name" }` — 409 se destino existe. |
| `POST /api/host/upload` | Host: multipart `file` + form `folder` — grava com nome sanitizado; colisão → `nome-2.ext`. Pasta na UI → um `.zip` (compactação no cliente). |
| `GET /api/host/update` | Host: JSON `{current,latest,available,checked,error,…}`. Checagem em background no startup (GitHub Releases). |
| `POST /api/host/update` | Host: baixa o artefato da plataforma e dispara `scripts/apply_update.*` (encerra o app com force kill em 10s; só então abre o instalador). |

Todas as rotas `/api/host/*` e as páginas `*_manager` exigem `Host` com `localhost` ou `127.0.0.1` (403 / redirect caso contrário).

## `DATA_ROOT`

| Stack | Resolução |
|-------|-----------|
| Python | Parent de `python/` em dev; frozen → `Documentos/SwiftSend` (todos os SOs) |
| C# | Env `SWIFTSEND_ROOT`, ou sobe diretórios até achar `shared/templates`, ou `BaseDirectory` |

Pastas `arquivos_publicos` e `arquivos_recebidos` vivem em `DATA_ROOT` (criar se não existirem).

## Templates

| Stack | Motor | Pasta |
|-------|-------|-------|
| Python | Jinja2 | `shared/templates` |
| C# | Fluid (Liquid) | `shared/templates` |

HTML deve permanecer compatível com **ambos** (`{% %}` / `{{ }}` usados hoje).

## Checklist de paridade

- [ ] Dashboard em localhost mostra IP e link
- [ ] Acesso via IP LAN mostra home (não dashboard)
- [ ] Upload grava em `arquivos_recebidos`; colisão sem `replace` → 409; com `replace` sobrescreve
- [ ] Pós-upload: `files[].token` + `/api/upload/undo` remove dentro da janela (~10 min)
- [ ] Host em Recebidos continua podendo apagar/renomear (correção pedida pelo visitante)
- [ ] Arquivo em `arquivos_publicos` lista e baixa
- [ ] Limite 16 GB alinhado (Flask + Kestrel MultipartBodyLengthLimit)
- [ ] Abrir pastas no host (Windows) via “Abrir no SO” nas telas manager
- [ ] Telas `/upload_manager` e `/public_manager` só no localhost; APIs `/api/host/*` retornam 403 na LAN
- [ ] `/static` e ícone consistentes
