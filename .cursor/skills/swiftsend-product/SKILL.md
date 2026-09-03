---
name: swiftsend-product
description: >-
  Modelo de produto do SwiftSend: transferência de arquivos pesados na LAN via
  HTTP local + WebView, sem nuvem nem pen-drive. Use ao discutir escopo, UX
  host/visitante, pastas de arquivos, limitações do MVP ou invariantes de produto.
---

# SwiftSend — Produto

## O que é

App desktop híbrido: o host sobe um servidor HTTP na rede local; a UI web serve o dashboard na janela do app e a área pública nos navegadores dos visitantes.

## Fluxo

1. Host inicia o app → HTTP em `0.0.0.0:5000` + janela WebView em `http://127.0.0.1:5000` (dashboard).
2. Dashboard exibe o link LAN (`http://<IP>:5000`).
3. Host coloca arquivos em `arquivos_publicos/` (ou via “Gerenciar Públicos”).
4. Visitantes na mesma rede abrem o link → home pública → baixar (`/browse`) ou enviar (`/upload`).
5. Uploads gravam em `arquivos_recebidos/`.

## Direção dos arquivos

| Pasta | Quem escreve | Quem lê |
|-------|--------------|---------|
| `arquivos_publicos/` | Host | Visitantes (download) |
| `arquivos_recebidos/` | Visitantes (upload) | Host |

## Invariantes de produto

- Sem autenticação, banco, HTTPS, mDNS ou fila de transfers.
- Persistência = sistema de arquivos local na raiz de dados (`DATA_ROOT`).
- Clientes na LAN não devem perceber qual runtime (Python ou C#) hospeda o servidor.
- Strings de UI em **português** (`pt-br`).
- Porta padrão **5000**; bind **`0.0.0.0`**.

## Fora de escopo (MVP)

Auth, criptografia em trânsito, discovery automático de hosts, sync em nuvem, testes automatizados, CI de release (opcional futuro).

## Skills relacionadas

- Contrato HTTP → [swiftsend-http-contract](../swiftsend-http-contract/SKILL.md)
- Layout dual-stack → [swiftsend-architecture](../swiftsend-architecture/SKILL.md)
- UI → [swiftsend-ui](../swiftsend-ui/SKILL.md)
- Build/run → [swiftsend-build-run](../swiftsend-build-run/SKILL.md)
