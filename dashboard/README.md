# Dati dashboard

Questa cartella non è il sito. GitHub Pages pubblica la **root** del repository (`index.html` + `CNAME`).

Qui ci sono solo i JSON esportati dal database:

- `data/games.json`
- `data/last_update.json`

## Accesso

**URL:** `https://cex.byluke.org`

## Setup GitHub Pages

1. Vai su: **Repository → Settings → Pages**
2. Source: `Deploy from branch`
3. Branch: `main`
4. Folder: `/` (root)
5. Salva

Il file `CNAME` nella root deve contenere `cex.byluke.org`.

## Wishlist Sync con DB

La dashboard può sincronizzare la wishlist direttamente nel database tramite API locale.

1. Avvia API:

```bash
python scripts/wishlist_api_server.py --db data/current/games.db --host 127.0.0.1 --port 8787
```

2. Apri dashboard con:

```text
http://127.0.0.1:5500/index.html?api=http://127.0.0.1:8787
```

Se il parametro `api` è presente, la wishlist viene letta/scritta su DB (`wishlist`) e usata anche dal notifier Telegram.
