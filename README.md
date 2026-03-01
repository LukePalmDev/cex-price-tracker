# 🎮 CEX Price Tracker

**Sistema automatico di monitoraggio prezzi videogiochi usati su CEX Italia**

> Traccia prezzi, ricevi notifiche su Telegram, analizza trend di mercato - 100% gratuito con GitHub Actions

---

## 📊 Features

- ✅ **Scraping automatico giornaliero** via GitHub Actions
- ✅ **Database SQLite** con storico prezzi e disponibilità
- ✅ **Notifiche Telegram** per wishlist personalizzata
- ✅ **Dashboard web interattiva** con grafici e statistiche
- ✅ **Backup mensile automatico** dei dati
- ✅ **100% gratuito** - nessun costo di hosting

---

## 🎯 Giochi Monitorati

- Xbox (tutte le generazioni)
- PlayStation 4
- PSP
- Wii
- Nintendo Switch

**Totale:** ~10.000 titoli tracciati

---

## 🏗️ Architettura

```
GitHub Actions (Scraping ogni 24h)
         ↓
   SQLite Database
         ↓
    ├── Dashboard Web (GitHub Pages)
    └── Notifiche Telegram
```

---

## 🚀 Quick Start

### 1. Clona Repository

```bash
git clone https://github.com/LukePalmDev/cex-price-tracker.git
cd cex-price-tracker
```

### 2. Installa Dipendenze

```bash
pip install -r requirements.txt
```

### 3. Test Locale

```bash
# Inizializza database
python scraper/init_database.py

# Esegui scraping manuale (test)
python scraper/main_scraper.py
```

### 4. Configura GitHub Actions

- Vai su **Settings → Secrets and variables → Actions**
- Aggiungi:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

### 5. Attiva GitHub Pages

- **Settings → Pages**
- Source: `Deploy from branch`
- Branch: `main`
- Folder: `/dashboard`

---

## 📁 Struttura Progetto

```
cex-price-tracker/
├── .github/workflows/       # GitHub Actions
│   ├── daily-scrape.yml     # Scraping automatico
│   ├── notify.yml           # Sistema notifiche
│   └── monthly-snapshot.yml # Backup mensile
├── data/
│   ├── current/            # Database SQLite attuale
│   ├── history/            # Backup mensili
│   └── reports/            # Report cambiamenti giornalieri
├── scraper/                # Scraper Selenium
├── notifications/          # Telegram Bot
├── dashboard/              # Web app (GitHub Pages)
└── scripts/                # Utility varie
```

---

## 🔔 Sistema Notifiche

1. **Crea bot Telegram** con @BotFather
2. **Aggiungi giochi** alla wishlist (dashboard web)
3. **Ricevi alert** quando:
   - Prezzo scende sotto soglia target
   - Gioco torna disponibile

### Sync Wishlist Dashboard ↔ DB (stessa wishlist per Telegram)

Per usare una singola wishlist condivisa tra dashboard e notifiche:

1. Avvia API locale wishlist:

```bash
python scripts/wishlist_api_server.py --db data/current/games.db --host 127.0.0.1 --port 8787
```

2. Apri la dashboard con il parametro `api`:

```text
http://127.0.0.1:5500/dashboard/index.html?api=http://127.0.0.1:8787
```

Da quel momento click su ★ legge/scrive nel DB (`wishlist`), quindi Telegram usa la stessa lista.

Nota: se esponi questa API su internet senza protezione, chiunque può modificare la wishlist.

---

## 📈 Dashboard

**Live:** [https://LukePalmDev.github.io/cex-price-tracker](https://LukePalmDev.github.io/cex-price-tracker)

Features:
- 🔍 Ricerca e filtri avanzati
- 📊 Grafici prezzi storici
- ⭐ Sistema wishlist
- 📥 Export CSV/JSON

---

## 🛠️ Tecnologie

- **Backend:** Python 3.x
- **Scraping:** Python + Algolia Search API
- **Database:** SQLite
- **Automazione:** GitHub Actions
- **Frontend:** HTML/CSS/JavaScript + Chart.js
- **Notifiche:** Telegram Bot API

---

## 📅 Roadmap

- [x] ~~Setup base e scraping~~
- [x] ~~Database schema~~
- [x] ~~GitHub Actions automation~~
- [x] ~~Dashboard web~~
- [x] ~~Sistema notifiche~~
- [ ] Tracking console (Fase 2)
- [ ] Alert personalizzati avanzati
- [ ] Machine learning predizioni prezzi
- [ ] App mobile nativa

---

## 📝 Licenza

MIT License - vedi [LICENSE](LICENSE)

---

## 🤝 Contributing

Pull requests benvenute! Per modifiche importanti, apri prima una issue.

---

## 📧 Contatti

Per supporto o domande, apri una [GitHub Issue](../../issues).

---

**Creato con ❤️ usando Claude AI**
