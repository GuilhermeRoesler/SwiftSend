---
name: swiftsend-ui
description: >-
  UI compartilhada do SwiftSend em shared/ (templates Jinja/Fluid, CSS/JS/fonts
  locais). Use ao editar dashboard, home, browse, upload, estilos de produto,
  assets estáticos ou textos da interface.
---

# SwiftSend — UI (`shared/`)

## Estrutura

```
shared/
├── templates/
│   ├── dashboard.html   # host (localhost)
│   ├── home.html        # visitante
│   ├── browse.html      # lista / download
│   ├── upload.html      # envio
│   └── manager.html     # host: Recebidos / Públicos (listar, DnD, renomear, apagar)
├── static/
│   ├── css/app.css
│   ├── js/app.js        # copy, QR, ícones por tipo
│   ├── js/upload.js
│   ├── js/manager.js    # ações host + upload para pastas gerenciadas
│   ├── js/qrcode.js     # QR local (sem CDN)
│   ├── fonts/           # Sora + JetBrains Mono + Material Symbols
│   ├── icon.png
│   └── icon.ico
```

Demo estática (GitHub Pages): `python demo/build.py` → `demo/dist/` (templates com dados mock + `upload-demo.js`). Não altera o contrato das backends.

## Convenções

- Idioma da UI: **português** (`lang="pt-br"`).
- Visual: identidade própria (Sora + JetBrains Mono, azul/teal sobre ink), assets **locais** (sem CDN obrigatório).
- Templates compatíveis com **Jinja2 e Fluid** — não introduzir filtros/tags só de um motor sem equivalente no outro.
- Identificadores de rotas/API em inglês (`/api/upload`, `/browse`); cópia visível em PT.
- Upload: `upload.js` (XHR + progresso com velocidade/ETA + drag-and-drop) — manter contrato com `POST /api/upload`.

## Páginas

| Template | Audiência | Função |
|----------|-----------|--------|
| `dashboard.html` | Host | Cockpit: link+QR dominantes, métrica densa, howto compacto se `received_count == 0` |
| `home.html` | Visitante | Hero de marca (wordmark) + cena LAN + Baixar / Enviar |
| `browse.html` | Visitante | Lista flat com ícone por tipo + download |
| `upload.html` | Visitante | Drop zone + transfer meter (%, velocidade, ETA) + sucesso |
| `manager.html` | Host | Espelha Recebidos ou Públicos: DnD, renomear, apagar, abrir no SO |

## Ao editar

1. Mudar HTML/CSS/JS só sob `shared/` (ambas as backends consomem daqui).
2. Não recolocar templates grandes dentro de `python/` ou `csharp/`.
3. Testar mentalmente host (WebView) e visitante (browser na LAN).
