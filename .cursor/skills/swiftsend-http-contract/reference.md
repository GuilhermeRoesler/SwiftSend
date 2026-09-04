# Referência — Contrato HTTP

## POST `/api/upload`

- Campo multipart: `file` (um ou vários).
- Destino: `{DATA_ROOT}/arquivos_recebidos/`.
- Nome no disco: `{yyyyMMdd_HHmmss_}{nomeSanitizado}`.
- Sucesso: JSON `{ "success": true }` (HTTP 200).
- Erro (sem arquivo / falha): HTTP 400 + JSON de erro.

### Sanitização de nome

| Stack | Comportamento |
|-------|----------------|
| Python | `werkzeug.utils.secure_filename` |
| C# | Remove caracteres inválidos do SO; fallback `"arquivo"` |

## GET `/download/<filename>`

- Resolve sob `arquivos_publicos/` apenas (sem path traversal).
- Resposta: `Content-Disposition: attachment`.

## Abrir pastas (`*_manager`)

| Stack | Comportamento |
|-------|----------------|
| Python | Windows `os.startfile` / macOS `open` / Linux `xdg-open` |
| C# | Windows `explorer.exe` (secundária é Windows-first) |

Ambas redirecionam para `/` após disparar o gerenciador de arquivos.

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
- [ ] Upload grava em `arquivos_recebidos`
- [ ] Arquivo em `arquivos_publicos` lista e baixa
- [ ] Limite 16 GB alinhado (Flask + Kestrel MultipartBodyLengthLimit)
- [ ] Abrir pastas no host (Windows) funciona
- [ ] `/static` e ícone consistentes
