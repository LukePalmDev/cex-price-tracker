# Dashboard Web

Questa cartella contiene la web app visualizzata su GitHub Pages.

## Accesso

**URL:** `https://TUO_USERNAME.github.io/cex-price-tracker`

## Contenuto

- `index.html` - Pagina principale
- `assets/css/` - Fogli di stile
- `assets/js/` - JavaScript per grafici e interazioni
- `data/` - Dati JSON esportati dal database

## Setup GitHub Pages

1. Vai su: **Repository → Settings → Pages**
2. Source: `Deploy from branch`
3. Branch: `main`
4. Folder: `/dashboard`
5. Salva

Il sito sarà disponibile in ~2 minuti.

## Wishlist Sync con DB

La dashboard può sincronizzare la wishlist direttamente nel database tramite API locale.

1. Avvia API:

```bash
python scripts/wishlist_api_server.py --db data/current/games.db --host 127.0.0.1 --port 8787
```

2. Apri dashboard con:

```text
.../dashboard/index.html?api=http://127.0.0.1:8787
```

Se il parametro `api` è presente, la wishlist viene letta/scritta su DB (`wishlist`) e usata anche dal notifier Telegram.
