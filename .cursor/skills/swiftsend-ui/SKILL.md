---
name: swiftsend-ui
description: >-
  UI compartilhada do SwiftSend em shared/ (templates Jinja/Fluid, CSS/JS/fonts
  locais). Use ao editar dashboard, home, browse, upload, estilos Material 3,
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
│   └── upload.html      # envio
├── static/
│   ├── css/app.css
│   ├── js/upload.js
│   ├── fonts/           # Roboto + Material Symbols
│   └── icon.png
```

Demo estática (GitHub Pages): `python demo/build.py` → `demo/dist/` (templates com dados mock + `upload-demo.js`). Não altera o contrato das backends.

## Convenções

- Idioma da UI: **português** (`lang="pt-br"`).
- Visual: Material Design 3, assets **locais** (sem CDN obrigatório).
- Templates compatíveis com **Jinja2 e Fluid** — não introduzir filtros/tags só de um motor sem equivalente no outro.
- Identificadores de rotas/API em inglês (`/api/upload`, `/browse`); cópia visível em PT.
- Upload: `upload.js` (XHR + progresso + drag-and-drop) — manter contrato com `POST /api/upload`.

## Páginas

| Template | Audiência | Função |
|----------|-----------|--------|
| `dashboard.html` | Host | Link LAN, contagem, abrir pastas, passos |
| `home.html` | Visitante | Entrada Baixar / Enviar |
| `browse.html` | Visitante | Tabela nome/tamanho/download |
| `upload.html` | Visitante | Drop zone + progresso |

## Ao editar

1. Mudar HTML/CSS/JS só sob `shared/` (ambas as backends consomem daqui).
2. Não recolocar templates grandes dentro de `python/` ou `csharp/`.
3. Testar mentalmente host (WebView) e visitante (browser na LAN).
