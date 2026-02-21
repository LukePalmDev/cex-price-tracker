# CEX_PRICE_TRACKER_GUIDA_PARAMETRICA

## 1. IDENTITÀ E ARCHITETTURA

| Voce | Valore |
|---|---|
| Nome app | `CEX Price Tracker` |
| Lingua interfaccia | Italiano (`<html lang="it">`) |
| Tipo file | Single-file HTML con CSS e JS inline |
| Framework UI | Nessuno |
| Libreria grafici | Chart.js via CDN |
| Build tools | Nessuno (runtime browser puro) |

### Dipendenze esterne (CDN)

| Nome | Versione/Pesi | URL |
|---|---|---|
| Google Fonts `JetBrains Mono` | `300,400,500,700` | `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;600;700;800&display=swap` |
| Google Fonts `Syne` | `400,600,700,800` | `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;600;700;800&display=swap` |
| Chart.js UMD | `4.4.1` | `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js` |

### Fonte dati

| Voce | Valore |
|---|---|
| Base raw GitHub | `https://raw.githubusercontent.com/LukePalmDev/cex-price-tracker/main` |
| Dataset giochi | `${RAW}/dashboard/data/games.json` |
| Report giornalieri cambi | `${RAW}/data/reports/changes_YYYYMMDD.json` |
| Metodo | `fetch` HTTP `GET` |
| Cache busting | Query `?t=${Date.now()}` su entrambi i fetch |
| Formato atteso | JSON |

### Costanti di configurazione

| Costante | Valore attuale | Ruolo |
|---|---|---|
| `RAW` | `https://raw.githubusercontent.com/LukePalmDev/cex-price-tracker/main` | Base URL remoto |
| `GAMES_URL` | `${RAW}/dashboard/data/games.json` | Endpoint catalogo |
| `REPORTS_BASE` | `${RAW}/data/reports` | Base report cambi |
| `PAGE_SIZE` | `50` | Righe tabella per pagina |
| `CONSOLE_META` | mappa 9 categorie | Colori + gruppo per card/charts/tabella |
| `GROUP_META` | mappa 4 gruppi (`Xbox`,`PS4`,`Wii`,`Switch`) | Etichetta+colore colonna "Gruppo" |

---

## 2. DESIGN SYSTEM

### Palette colori completa (CSS custom properties)

| Variabile | HEX | Ruolo |
|---|---|---|
| `--bg` | `#0a0a0f` | Sfondo globale |
| `--surface` | `#0f0f1a` | Superfici secondarie |
| `--card` | `#13131f` | Card/pannelli |
| `--border` | `#1e1e30` | Bordi |
| `--amber` | `#f5a623` | Accent principale |
| `--amber-dim` | `#7a5112` | Accent amber attenuato |
| `--green` | `#22c55e` | Disponibile/valori positivi nel tema |
| `--red` | `#ef4444` | Stato negativo/valori in aumento prezzo |
| `--blue` | `#3b82f6` | Hover bottone storico |
| `--purple` | `#a855f7` | Variabile definita ma non usata direttamente |
| `--text` | `#e2e8f0` | Testo principale |
| `--muted` | `#64748b` | Testo secondario |
| `--dim` | `#334155` | Thumb scrollbar |
| `--xbox` | `#107c10` | Colore famiglia Xbox |
| `--xbox360` | `#52b043` | Colore Xbox 360 |
| `--xboxone` | `#0e7a0d` | Colore Xbox One |
| `--xboxcross` | `#4caf50` | Colore Xbox CrossGen |
| `--xboxseries` | `#00d95f` | Colore Xbox Series |
| `--psp` | `#00439c` | Colore PSP |
| `--ps4` | `#4a7fff` | Colore PS4 |
| `--wii` | `#c7c7c7` | Colore Wii |
| `--sw` | `#e60012` | Colore Switch |

### Colori extra non in `:root` (hardcoded)

| Valore | Dove |
|---|---|
| `#94a3b8` | Tick/legend testo Chart.js |
| `rgba(10,10,15,0.92)` | Sfondo header sticky |
| `rgba(245,166,35,0.06)` | Glow radial body |
| `rgba(245,166,35,.03)` | Overlay card |
| `rgba(245,166,35,.04)` | Hover righe tabella |
| `rgba(245,166,35,.1)` | Fill line chart modal |
| `rgba(34,197,94,.7)` | Dataset bar "Disponibili" |
| `rgba(100,116,139,.3)` | Dataset bar "Non disponibili" |
| `rgba(34,197,94,.12)` | Badge disponibilità yes |
| `rgba(34,197,94,.3)` | Bordo badge yes |
| `rgba(100,116,139,.1)` | Badge disponibilità no |
| `rgba(0,0,0,.8)` | Backdrop modal |
| `rgba(0,0,0,.6)` | Ombra modal |

### Tipografia

| Font | Provider | Pesi caricati | Uso |
|---|---|---|---|
| `Syne, sans-serif` | Google Fonts | `400,600,700,800` | Body e testo generale |
| `JetBrains Mono, monospace` | Google Fonts | `300,400,500,700` | Label tecniche, pulsanti, pill, tabelle, metriche, grafici |
| `monospace` (fallback inline) | System | n/a | Placeholder caricamento/casi fallback inline |

### Effetti visivi globali

| Effetto | Parametri |
|---|---|
| Background glow | `radial-gradient(ellipse 80% 50% at 50% -20%, rgba(245,166,35,0.06) 0%, transparent 60%)` |
| Header glass | `backdrop-filter: blur(12px)` |
| Loader ring animato | `animation: spin 0.8s linear infinite` |
| Transizioni frequenti | `.15s`, `.2s`, `.3s cubic-bezier(.4,0,.2,1)` |
| Scrollbar custom | `4px` width/height, thumb `var(--dim)` |
| Tema | Dark-only |

---

## 3. STRUTTURA LAYOUT

### Schema ASCII

```text
BODY
├─ #loading (overlay full-screen)
├─ header (sticky, h=56)
│  ├─ .logo
│  ├─ .header-pills (status, data update, totale)
│  └─ .header-right (.btn-refresh)
├─ #wishlist-panel (off-canvas right)
├─ #modal-backdrop
│  └─ .modal
│     ├─ .modal-header
│     └─ .modal-body
│        ├─ #modal-stats
│        ├─ #modal-chart
│        └─ #modal-table
└─ main (max-width:1600, centered)
   ├─ #stats-grid (4 card KPI)
   ├─ #console-stats-grid (card dinamiche per categoria)
   ├─ .charts-row
   │  ├─ donut chart
   │  ├─ bar chart
   │  └─ list cambi prezzo
   ├─ .export-bar
   ├─ .filters-bar
   └─ .table-wrap
      ├─ table
      └─ #pagination
```

### Dimensioni e sistema layout

| Area | Sistema | Misure |
|---|---|---|
| `main` | block | `max-width:1600px`, `padding:20px 24px 40px` |
| KPI grid | CSS Grid | `repeat(auto-fit, minmax(180px,1fr))`, `gap:12px` |
| Charts row | CSS Grid | desktop `300px 1fr 280px`, `gap:12px` |
| Modal | Flex column | `width:560px`, `max-width:95vw`, `max-height:85vh` |
| Wishlist panel | Fixed side panel | `width:320px`, `top:56px`, hidden via `translateX(100%)` |
| Table pagination | Flex | center + pulsanti `30x30px` |

---

## 4. COMPONENTI UI (UNO PER UNO)

### Header

| Campo | Dettaglio |
|---|---|
| Ruolo | Branding + stato dataset + refresh manuale |
| Posizione | Top sticky (`z-index:100`) |
| Dati | `pill-update` (data), `pill-total` (conteggio titoli), `pill-status` statico `Online` |
| Interazioni | Click `↻ Aggiorna` -> `loadData(true)` |
| Stile | Altezza `56px`, blur `12px`, amber accent su logo e bottone |

### Loading Screen

| Campo | Dettaglio |
|---|---|
| Ruolo | Overlay durante fetch iniziale/refresh |
| Posizione | Fullscreen fixed `z-index:999` |
| Dati | `#loading-msg` testo dinamico |
| Interazioni | Mostrato a inizio `loadData`, nascosto a fine successo |
| Stile | Ring `48px`, bordo `2px`, animazione spin `0.8s` |

### Card statistiche principali

| Campo | Dettaglio |
|---|---|
| Ruolo | KPI generali catalogo |
| Posizione | Prima `stats-grid` |
| Dati | Totale, disponibili, prezzo medio, cambi giornalieri |
| Interazioni | Hover bordo amber-dim |
| Stile | Card `padding:16px 18px`, radius `8px`, value `28px` |

### Card statistiche per console/categoria (dinamiche)

| Campo | Dettaglio |
|---|---|
| Ruolo | Breakdown per sotto-console |
| Posizione | `#console-stats-grid` sotto KPI |
| Dati | Conteggio titoli per categoria + disponibili (%) |
| Interazioni | Click card -> `filterByConsole(cat)` + scroll ai filtri |
| Stile | Colore testo/pallino da `CONSOLE_META[cat].color`, inline style dinamico |

### Donut chart

| Campo | Dettaglio |
|---|---|
| Ruolo | Distribuzione titoli per categoria |
| Posizione | Prima card in `.charts-row` |
| Dati | `cats`/`vals` derivati da `(g.category || g.console)` |
| Interazioni | Tooltip Chart.js |
| Stile | Cutout `65%`, legenda right, `hoverOffset:6`, center value custom |

### Bar chart stacked

| Campo | Dettaglio |
|---|---|
| Ruolo | Disponibili vs non disponibili per categoria |
| Posizione | Seconda card `.charts-row` |
| Dati | `availData`, `unavailData` per categoria |
| Interazioni | Tooltip `mode:index`, `intersect:false` |
| Stile | Barre stacked, radius `3`, colori RGBA hardcoded |

### Lista cambi prezzo giornalieri

| Campo | Dettaglio |
|---|---|
| Ruolo | Ticker dei cambi del giorno (max 60) |
| Posizione | Terza card `.charts-row` |
| Dati | `price_changes` da `changes_YYYYMMDD.json` |
| Interazioni | Click riga -> `openModal(game_id)` |
| Stile | Riga `5px 8px`, border-left `2px` verde/rosso, prezzo monospace |

### Barra export + toggle wishlist

| Campo | Dettaglio |
|---|---|
| Ruolo | Export dataset filtrato + apertura pannello wishlist |
| Posizione | Sotto sezione grafici |
| Dati | Conteggio wishlist in `#wl-count` |
| Interazioni | `exportCSV()`, `exportJSON()`, `toggleWishlist()` |
| Stile | Bottoni trasparenti, hover verde (export) / amber (wishlist) |

### Filtri

| Campo | Dettaglio |
|---|---|
| Ruolo | Ricerca, filtro console/stato/trend, filtro wishlist-only |
| Posizione | Sotto export bar |
| Dati | Input testo + 3 select + stato boolean `wishlistOnly` |
| Interazioni | `oninput`, `onchange`, reset, toggle wishlist-only |
| Stile | Barra `padding:14px 16px`, separatore verticale `1px x 24px` |

### Tabella dati + paginazione

| Campo | Dettaglio |
|---|---|
| Ruolo | Elenco giochi filtrati/ordinati |
| Posizione | Parte bassa `main` |
| Dati | `filtered.slice(...)`, `PAGE_SIZE=50` |
| Interazioni | Sort on header click, row click modal, star wishlist, storico |
| Stile | Header uppercase `9px`, row hover amber translucido, price amber `13px` |

### Wishlist panel laterale

| Campo | Dettaglio |
|---|---|
| Ruolo | Lista giochi salvati localmente |
| Posizione | Off-canvas destro, full-height sotto header |
| Dati | `wishlist` (array ID) + matching `allGames` |
| Interazioni | Toggle open/close, remove item |
| Stile | `width:320px`, animazione `transform .3s cubic-bezier(.4,0,.2,1)` |

### Modal storico prezzi

| Campo | Dettaglio |
|---|---|
| Ruolo | Dettaglio gioco: mini KPI, line chart, tabella variazioni |
| Posizione | Overlay centrale (`z-index:200`) |
| Dati | `price_history_30d`, `current_price`, `is_available` |
| Interazioni | Click riga tabella/lista, close su backdrop, X, o tasto `Escape` |
| Stile | Modal `560px` max, shadow forte, chart `height:200px` |

---

## 5. STRUTTURA DEI DATI

### 5.1 `games.json` (catalogo)

Endpoint atteso: `GAMES_URL`.

Nota pratica: il codice usa `data.statistics` ma ha fallback data update su `data.metadata.exported_at`.

Schema osservato/atteso:

```json
{
  "metadata": {
    "exported_at": "2026-02-21T06:56:12.564699",
    "total_games": 6092,
    "statistics": {
      "total_games": 6092,
      "available_games": 3124,
      "unavailable_games": 2968,
      "by_console": {
        "Xbox": 2514,
        "PS4": 1577,
        "Wii": 1002,
        "Switch": 999
      },
      "average_price": 13.05,
      "last_update": "2026-02-21"
    }
  },
  "statistics": {
    "total_games": 11,
    "available_games": 9,
    "unavailable_games": 2,
    "by_console": {
      "PS4": 4,
      "Xbox": 3,
      "Switch": 2,
      "PSP": 1,
      "Wii": 1
    },
    "average_price": 23.9,
    "last_update": "2026-02-17",
    "daily_summary": {
      "price_changes": 0,
      "availability_changes": 0
    }
  },
  "games": [
    {
      "id": 1,
      "title": "God of War",
      "console": "PS4",
      "category": "PS4",
      "current_price": 24.99,
      "is_available": 1,
      "condition": null,
      "url": "https://it.webuy.com/product-detail/?id=sgodofwar",
      "first_seen": "2026-02-17",
      "last_updated": "2026-02-17",
      "last_price_change": "2026-02-17",
      "last_availability_change": null,
      "image_url": null,
      "price_history_30d": [
        {
          "old_price": 29.99,
          "new_price": 24.99,
          "changed_at": "2026-02-17 08:56:33"
        }
      ],
      "price_trend_pct": null
    }
  ]
}
```

#### Campi `games[]` usati in UI

| Campo | Tipo | Usato in |
|---|---|---|
| `id` | `number` | Row key implicita, wishlist, modal, changes cross-reference |
| `title` | `string` | Ricerca, tabella, modal, wishlist, changes list |
| `console` | `string` | Colonna "Gruppo", modal sub, wishlist meta, CSV |
| `category` | `string` | Filtri console, card/categorie, donut/bar, colonna "Categoria" |
| `current_price` | `number` | Prezzo tabella, KPI, modal, wishlist, changes delta |
| `is_available` | `0/1` | Badge stato, filtri, grafico bar, KPI availability |
| `url` | `string` | Link titolo tabella |
| `first_seen` | `YYYY-MM-DD` | Export CSV |
| `last_updated` | `YYYY-MM-DD` | Export CSV |
| `price_history_30d` | `array` opzionale | Modal chart/table, changes diff old/new |
| `price_trend_pct` | `number/null` | Colonna trend, filtro trend, sort trend |
| `last_price_change` | `date/null` | Dato presente, non render diretto |
| `last_availability_change` | `date/null` | Dato presente, non render diretto |
| `condition` | `null/string` | Non usato in UI |
| `image_url` | `null/string` | Non usato in UI |

### 5.2 `changes_YYYYMMDD.json` (report giornaliero)

Endpoint atteso: `${REPORTS_BASE}/changes_${YYYYMMDD}.json`.

```json
{
  "metadata": {
    "generated_at": "2026-02-21T06:56:12.538005",
    "date": "2026-02-21",
    "duration_sec": 1718.1,
    "total_scraped": 7244
  },
  "summary": {
    "new_games": 0,
    "price_changes": 183,
    "availability_changes": 37,
    "unchanged": 7024,
    "errors": 0
  },
  "new_games": [],
  "price_changes": [
    {
      "game_id": 60,
      "title": "Burnout Revenge",
      "console": "Xbox",
      "new_price": 2.0
    }
  ],
  "availability_changes": [
    {
      "game_id": 60,
      "title": "Burnout Revenge",
      "console": "Xbox",
      "new_status": "Esaurito"
    }
  ],
  "errors": []
}
```

#### Campi report usati in UI

| Campo | Tipo | Uso |
|---|---|---|
| `price_changes[]` | array | Popola ticker cambi prezzo |
| `price_changes[].game_id` | number | `openModal(game_id)` |
| `price_changes[].title` | string | Etichetta riga |
| `price_changes[].console` | string | Badge console |
| `price_changes[].new_price` | number | Prezzo mostrato |

`availability_changes` e `new_games` non sono usati in rendering corrente del ticker.

---

## 6. LOGICA JAVASCRIPT

### Variabili di stato globali

| Nome | Tipo | Descrizione |
|---|---|---|
| `allGames` | `Array<object>` | Dataset completo caricato |
| `filtered` | `Array<object>` | Dataset dopo filtri + sort |
| `sortKey` | `string` | Chiave ordinamento corrente (`title` default) |
| `sortDir` | `1/-1` | Direzione ordinamento |
| `currentPage` | `number` | Pagina corrente |
| `wishlist` | `Array<number>` | ID giochi salvati in localStorage |
| `wishlistOnly` | `boolean` | Flag filtro "solo wishlist" |
| `donutChart` | `Chart|null` | Istanza chart donut |
| `barChart` | `Chart|null` | Istanza chart bar |
| `modalChart` | `Chart|null` | Istanza chart line modal |

### Tabella funzioni

| Funzione | Trigger | Cosa fa |
|---|---|---|
| `loadData(force=false)` | Avvio (`loadData()`), click refresh | Fetch giochi, aggiorna KPI/pill/card console, grafici, ticker, tabella |
| `filterByConsole(consoleName)` | Click card categoria dinamica | Imposta select console, filtra, scroll ai filtri |
| `buildDonut(games)` | Chiamata interna da `loadData` | Crea donut Chart.js distribuzione categoria |
| `buildBar(games)` | Chiamata interna da `loadData` | Crea bar stacked disponibilità |
| `loadChanges(dateStr)` | Chiamata interna da `loadData` | Fetch report giorno, popola lista cambi prezzo |
| `applyFilters()` | Input search, onchange select, reset, toggle WL, sort | Applica filtri multipli, ordina, reset pagina, aggiorna risultati+tabella |
| `sortBy(key)` | Click header tabella | Toggle direzione, aggiorna frecce sort, rilancia filtri |
| `resetFilters()` | Click bottone reset | Azzera campi filtro + `wishlistOnly` |
| `toggleWishlistFilter()` | Click bottone solo wishlist | Toggle flag filtro wishlist-only |
| `renderTable()` | Da `applyFilters`, `toggleWL`, `goPage` | Render righe pagina corrente |
| `renderPagination()` | Chiamata interna da `renderTable` | Render controlli paginazione con ellissi |
| `goPage(p)` | Click page-btn | Cambia pagina, rerender, scroll top smooth |
| `toggleWL(e,id)` | Click stella riga o remove wishlist | Add/remove ID wishlist, salva localStorage, aggiorna UI |
| `toggleWishlist()` | Click bottone wishlist/header panel | Apre/chiude pannello laterale |
| `updateWishlistUI()` | Da `loadData`, `toggleWL` | Render contenuto pannello wishlist |
| `openModal(id)` | Click riga tabella, bottone storico, riga changes | Popola e apre modal con storico prezzi |
| `closeModal(e)` | Click backdrop modal | Chiude modal solo se click su backdrop |
| `closeModalDirect()` | Click X modal, tasto ESC | Chiusura diretta modal |
| `exportCSV()` | Click export CSV | Crea CSV da `filtered`, avvia download |
| `exportJSON()` | Click export JSON | Crea JSON prettified da `filtered`, avvia download |
| `download(content,filename,mime)` | Chiamata da export | Blob + URL.createObjectURL + click `<a>` |
| `today()` | Chiamata da export | Data ISO `YYYY-MM-DD` per nome file |

### Logica filtro e ordinamento

```js
filtered = allGames.filter(g => {
  // search su titolo (contains, lowercase)
  // filtro console: category fallback console
  // filtro disponibilità: confronto stringa "0"/"1"
  // filtro trend: down => price_trend_pct < 0, up => > 0
  // filtro wishlistOnly: id presente in wishlist
});

filtered.sort((a,b) => {
  // string => localeCompare
  // numeri => sottrazione
  // direzione via sortDir (1 o -1)
});
```

### Logica export

| Export | Formato | Campi | Nome file | MIME |
|---|---|---|---|---|
| `exportCSV()` | CSV separato da virgola | `ID,Titolo,Console,Prezzo,Disponibile,URL,Primo Visto,Ultimo Aggiornamento` | `cex-export-YYYY-MM-DD.csv` | `text/csv` |
| `exportJSON()` | JSON prettified indent 2 | Intero array `filtered` | `cex-export-YYYY-MM-DD.json` | `application/json` |

### Persistenza

| Storage | Chiave | Tipo valore | Dove letta/scritta |
|---|---|---|---|
| `localStorage` | `cex-wishlist` | JSON array di ID (`[number,...]`) | Lettura in init stato, scrittura in `toggleWL` |

---

## 7. RESPONSIVE

Unico breakpoint definito:

| Media query | Comportamento |
|---|---|
| `@media (max-width: 900px)` | `.charts-row` passa da `300px 1fr 280px` a `1fr`; `#wishlist-panel` passa da `320px` a `100%` |

Nessun altro breakpoint esplicito; il resto è adattivo via `auto-fit`, `minmax`, `flex-wrap`, `max-width`.

---

## 8. PARAMETRI MODIFICABILI RAPIDAMENTE

| Parametro | Dove si trova | Valore attuale | Effetto del cambiamento |
|---|---|---|---|
| URL base dati | JS costante `RAW` | `https://raw.githubusercontent.com/LukePalmDev/cex-price-tracker/main` | Cambia origine di tutti i fetch |
| Endpoint catalogo | JS `GAMES_URL` | `${RAW}/dashboard/data/games.json` | Cambia dataset principale |
| Endpoint report | JS `REPORTS_BASE` | `${RAW}/data/reports` | Cambia ticker cambi prezzo |
| Righe per pagina | JS `PAGE_SIZE` | `50` | Cambia densità tabella/paginazione |
| Colori tema base | CSS `:root` (`--bg`, `--card`, `--text`, `--amber`, ecc.) | valori in tabella palette | Rebranding immediato UI |
| Colori console | JS `CONSOLE_META`, `GROUP_META` | 9 categorie + 4 gruppi | Cambia badge/card/chart colori e label gruppo |
| Font primario | CSS `body{font-family:'Syne'}` | `Syne` | Cambia look tipografico globale |
| Font tecnico | Selettori monospace + Google Fonts link | `JetBrains Mono` | Cambia stile dati/metriche/tabella |
| Breakpoint mobile | CSS `@media (max-width: 900px)` | `900px` | Anticipa/posticipa layout mobile |
| Larghezza wishlist panel | CSS `#wishlist-panel{width:320px}` | `320px` | Pannello più stretto/largo desktop |
| Griglia charts desktop | CSS `.charts-row{grid-template-columns:300px 1fr 280px}` | `300px 1fr 280px` | Ridistribuisce spazio grafici/ticker |
| Cutout donut | JS `buildDonut` `cutout:'65%'` | `65%` | Varia spessore anello donut |
| Max elementi ticker | JS `loadChanges` `.slice(0,60)` | `60` | Numero righe cambi prezzo visualizzate |
| Ordine default tabella | JS stato `sortKey='title'`, `sortDir=1` | titolo/asc | Cambia ordinamento iniziale |
| Nome file export | JS `download('cex-export-' + today())` | prefisso `cex-export-` | Cambia naming download |
| Testi UI principali | HTML statico + stringhe JS | Italiano | Localizzazione in altra lingua |
| Key localStorage | JS `cex-wishlist` | `cex-wishlist` | Isola/riusa wishlist tra ambienti diversi |

---

## 9. FUNZIONALITÀ NON PRESENTI

Funzionalità deducibili ma non implementate:

1. Refresh automatico periodico (esiste solo refresh manuale).
2. Gestione robusta di payload alternativi (es. `statistics` solo annidato in `metadata`).
3. Persistenza completa dei filtri/sort/pagina in localStorage o URL query.
4. Multi-colonna sort o sort stabile avanzato.
5. Filtri range prezzo, fascia data, disponibilità per periodo.
6. Import/export wishlist dedicato e sincronizzazione cloud.
7. Supporto immagini prodotto (`image_url` è presente nei dati ma non usato).
8. Gestione/visualizzazione `availability_changes` e `new_games` nel ticker.
9. Accessibilità avanzata (focus styles completi, ARIA, keyboard navigation estesa oltre ESC).
10. Modal con confronto periodi multipli e timeframe selezionabile.
11. Internationalization strutturata (i18n) e switch lingua.
12. Gestione errori di rete più granulare (retry/backoff/stati offline).

---

## Allegato rapido: mapping categorie/gruppi

```json
{
  "CONSOLE_META": {
    "Xbox":          { "color": "#107c10", "group": "Xbox" },
    "Xbox 360":      { "color": "#52b043", "group": "Xbox" },
    "Xbox One":      { "color": "#0e7a0d", "group": "Xbox" },
    "Xbox CrossGen": { "color": "#4caf50", "group": "Xbox" },
    "Xbox Series":   { "color": "#00d95f", "group": "Xbox" },
    "PSP":           { "color": "#00439c", "group": "PS" },
    "PS4":           { "color": "#4a7fff", "group": "PS" },
    "Wii":           { "color": "#c7c7c7", "group": "Wii" },
    "Switch":        { "color": "#e60012", "group": "Switch" }
  },
  "GROUP_META": {
    "Xbox":   { "label": "Xbox",   "color": "#107c10" },
    "PS4":    { "label": "PS",     "color": "#4a7fff" },
    "Wii":    { "label": "Wii",    "color": "#c7c7c7" },
    "Switch": { "label": "Switch", "color": "#e60012" }
  }
}
```
