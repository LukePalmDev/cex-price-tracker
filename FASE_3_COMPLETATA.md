# ✅ FASE 3 COMPLETATA - Scraper Integrato con Database

## 📁 File Creati

```
scraper/
├── main_scraper.py         ✅ Orchestratore principale
├── changes_analyzer.py     ✅ Rilevamento e report cambiamenti
└── test_fase3.py           ✅ Test senza Selenium (dati simulati)

scripts/
└── export_data.py          ✅ Export DB → JSON per dashboard
```

---

## 🏗️ Architettura

```
main_scraper.py
     │
     ├── cex_selenium_scraper.py  ← Scraper esistente (invariato)
     │        scrape_category()
     │
     ├── database_manager.py      ← Fase 2
     │        upsert_game()
     │        export_to_json()
     │
     └── changes_analyzer.py      ← Nuovo
              record()
              build_report()
              → data/reports/changes_YYYYMMDD.json
```

---

## 🧪 TEST RAPIDO (SENZA Selenium)

Testa tutto il flusso con dati simulati:

```bash
cd scraper
python test_fase3.py
```

**Output atteso:**

```
==============================================================
🧪 CEX PRICE TRACKER - Test Fase 3
==============================================================

==============================================================
🔄 Simulazione: PRIMO SCRAPING (inserimento iniziale)
==============================================================

==============================================================
📊 RIEPILOGO CAMBIAMENTI
==============================================================
🆕 Nuovi giochi:           0
💰 Cambiamenti prezzo:     0
📦 Cambiamenti disponib.:  0
⏸️  Nessun cambiamento:     10
==============================================================

📊 Database: 10 giochi | Disponibili: 7 | Prezzo medio: €XX.XX

==============================================================
🔄 Simulazione: SECONDO SCRAPING (rilevamento cambiamenti)
==============================================================
  💰 Prezzo cambiato: God of War → €24.99
  📦 Disponibilità: The Last of Us → ✅ Disponibile
  📦 Disponibilità: Halo Infinite → ❌ Esaurito
  💰 Prezzo cambiato: Halo 3 → €3.00
  💰 Prezzo cambiato: Mario Kart 8 Deluxe → €55.00

==============================================================
📊 RIEPILOGO CAMBIAMENTI
==============================================================
🆕 Nuovi giochi:           0
💰 Cambiamenti prezzo:     3
📦 Cambiamenti disponib.:  2
⏸️  Nessun cambiamento:     6
==============================================================

📊 Database: 11 giochi | Disponibili: X | Prezzo medio: €XX.XX

==============================================================
🧪 Test Export JSON
==============================================================
✅ Export OK: 11 giochi esportati
   File: ../dashboard/data/test_games.json

🧹 Database di test rimosso

==============================================================
✅ TEST FASE 3 COMPLETATO!
==============================================================
```

---

## 🚀 TEST REALE (con Selenium)

> ⚠️ Esegui questo **SOLO dopo** aver completato il test rapido!
> Lo scraping completo richiede ~15-30 minuti.

```bash
cd scraper
python main_scraper.py
```

**Cosa succede:**
1. Apre Chrome headless
2. Scarica tutti i giochi da CEX (Xbox, PS4, PSP, Wii, Switch)
3. Salva nel database `data/current/games.db`
4. Genera report `data/reports/changes_YYYYMMDD.json`
5. Esporta `dashboard/data/games.json`

**Verifica post-scraping:**

```bash
# Controlla database
sqlite3 ../data/current/games.db
SELECT console, COUNT(*) FROM games GROUP BY console;
.quit

# Controlla report
cat ../data/reports/changes_$(date +%Y%m%d).json | python -m json.tool | head -50

# Controlla JSON dashboard
wc -c ../dashboard/data/games.json   # dovrebbe essere > 500KB
```

---

## 📋 Riepilogo Script

### `main_scraper.py`
- Orchestratore principale
- Configura le console da monitorare (`CONSOLES_TO_TRACK`)
- Importa dinamicamente `cex_selenium_scraper.py`
- Chiama `scrape_category()` per ogni console
- Normalizza i dati al formato `DatabaseManager`
- Salva tutto + genera report

### `changes_analyzer.py`
- Raccoglie i cambiamenti durante l'upsert
- Distingue: nuovi giochi / variazioni prezzo / variazioni disponibilità
- Calcola variazione percentuale prezzo
- Genera report JSON completo
- Ha anche `load_latest_report()` usato dal notify.yml (Fase 4)

### `export_data.py`
- Esporta DB → JSON per la dashboard
- Arricchisce con storico prezzi 30 giorni
- Calcola trend % per ogni gioco
- Aggiunge daily summary dal report giornaliero
- Usato da GitHub Actions dopo ogni scraping

---

## 🎯 Prossimi Passi

**FASE 4: GitHub Actions** (30 minuti)
- `daily-scrape.yml` → scraping automatico alle 6:00 AM
- `notify.yml` → notifiche Telegram dopo lo scraping
- `monthly-snapshot.yml` → backup mensile

---

**Tempo impiegato:** ~45 minuti  
**Prossima fase:** Fase 4 - GitHub Actions
