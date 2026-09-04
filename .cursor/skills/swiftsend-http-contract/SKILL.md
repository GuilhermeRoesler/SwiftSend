---
name: swiftsend-http-contract
description: >-
  Contrato HTTP do SwiftSend (rotas, Host localhost vs LAN, upload/download,
  limites). Use ao criar ou alterar endpoints Flask/Kestrel, paridade Python/C#,
  detecção host/visitante, ou comportamento de pastas via HTTP.
---

# SwiftSend — Contrato HTTP

Python (Flask) e C# (Kestrel) devem expor o **mesmo** contrato. Mudança numa stack → atualizar a outra, salvo pedido explícito em contrário.

## Configuração

| Item | Valor |
|------|--------|
| Porta | `5000` |
| Bind | `0.0.0.0` / ListenAnyIP |
| Limite upload | 16 GB |
| Extensões | Qualquer |
| Estáticos | `/static/...` a partir de `shared/static` |

## Rotas

| Método | Rota | Comportamento |
|--------|------|----------------|
| GET | `/` | `Host` contém `localhost` ou `127.0.0.1` → dashboard; senão → home pública |
| GET | `/browse` | Lista `arquivos_publicos/` |
| GET | `/upload` | Página de envio |
| POST | `/api/upload` | Multipart `file` → `arquivos_recebidos/` (prefixo `yyyyMMdd_HHmmss_`); JSON `{success:true}` ou 400 |
| GET | `/download/<filename>` | Attachment de `arquivos_publicos/` |
| GET | `/upload_manager` | **Host only**: tela Recebidos (espelha a pasta); LAN → redirect `/` |
| GET | `/public_manager` | **Host only**: tela Públicos; LAN → redirect `/` |
| GET | `/api/host/open?folder=` | **Host only**: abre pasta no SO (`received` \| `public`); JSON |
| POST | `/api/host/delete` | **Host only**: JSON `{folder,name}` → apaga arquivo |
| POST | `/api/host/rename` | **Host only**: JSON `{folder,name,new_name}` → renomeia |
| POST | `/api/host/upload` | **Host only**: multipart `file` + `folder` → grava sem timestamp |

Detalhes de payload, sanitização e diferenças menores Python/C#: [reference.md](reference.md).

## Regras ao editar

1. Não mudar porta, pastas ou rotas só numa backend.
2. Detecção host/visitante continua pelo header `Host` (não por User-Agent).
3. IP LAN (UDP connect a `8.8.8.8:80`) é só para **exibir** o link no dashboard.
4. Após mudança: validar mentalmente dashboard localhost → home no IP → upload → download → pastas no disco.
