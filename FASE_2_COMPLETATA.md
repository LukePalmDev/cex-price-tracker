# ✅ FASE 2 COMPLETATA - Database Manager

## 📁 File Creati

```
scraper/
├── __init__.py                 # ✅ Package Python
├── README.md                   # ✅ Documentazione modulo
├── database_manager.py         # ✅ Classe principale database (450+ righe)
├── init_database.py            # ✅ Script inizializzazione
└── test_import_csv.py          # ✅ Script import CSV per test
```

## 🎯 Funzionalità Implementate

### 1. **DatabaseManager Class** (`database_manager.py`)

**Metodi principali:**
- `init_database()` - Crea schema completo SQLite
- `upsert_game(game_data)` - Insert/Update con tracking automatico cambiamenti
- `get_all_games(console)` - Recupera tutti i giochi
- `get_game_by_id(id)` - Recupera singolo gioco
- `get_price_history(game_id, days)` - Storico prezzi
- `get_availability_history(game_id, days)` - Storico disponibilità
- `get_statistics()` - Statistiche generali database
- `add_to_wishlist()` / `remove_from_wishlist()` - Gestione wishlist
- `get_wishlist()` - Recupera wishlist completa
- `export_to_json(path)` - Export per dashboard

**Features:**
- ✅ Context manager per connessioni sicure
- ✅ Tracking automatico cambiamenti prezzi/disponibilità
- ✅ Indici database per performance
- ✅ Foreign keys con CASCADE DELETE
- ✅ UNIQUE constraints per evitare duplicati
- ✅ Row factory per accesso colonne per nome

### 2. **Database Schema** (SQLite)

**Tabelle create:**
```sql
- games                     # Stato attuale giochi
- price_history             # Storico prezzi (solo cambiamenti)
- availability_history      # Storico disponibilità (solo cambiamenti)
- wishlist                  # Giochi tracciati per notifiche
```

**Indici creati:**
```sql
- idx_games_console
- idx_games_price
- idx_games_available
- idx_games_last_updated
- idx_price_history_game
- idx_price_history_date
- idx_availability_history_game
- idx_availability_history_date
- idx_wishlist_game
```

### 3. **Script Utility**

**`init_database.py`:**
- Inizializza database vuoto
- Verifica creazione corretta
- Mostra statistiche iniziali

**`test_import_csv.py`:**
- Importa dati da CSV esistente
- Parsing automatico prezzi (€ → float)
- Parsing disponibilità (string → boolean)
- Mapping console types
- Progress indicator
- Error handling
- Export automatico JSON per dashboard

## 🧪 Testing

### Test 1: Inizializzazione Database

```bash
cd scraper
python init_database.py
```

**Output atteso:**
```
==============================================================
🎮 CEX PRICE TRACKER - DATABASE INITIALIZATION
==============================================================

🔧 Inizializzazione database...
✅ Database schema inizializzato con successo!
✅ Database creato: ../data/current/games.db
   Dimensione: X.XX KB

📊 Statistiche iniziali:
   Totale giochi: 0
   Disponibili: 0
   Console trackate: 0

==============================================================
✅ INIZIALIZZAZIONE COMPLETATA!
==============================================================
```

### Test 2: Import CSV (Opzionale)

```bash
cd scraper
python test_import_csv.py /path/to/DBCEX20260215_182223.csv
```

**Output atteso:**
```
==============================================================
📥 CEX PRICE TRACKER - CSV IMPORT
==============================================================

📄 File CSV: DBCEX20260215_182223.csv

🔄 Importazione in corso...
   Processati: 2877 giochi...

✅ Importazione completata!
   Giochi importati: 2877
   Cambiamenti prezzo: 0
   Cambiamenti disponibilità: 0

📊 Statistiche database:
   Totale giochi: 2877
   Disponibili: 2500+
   Prezzo medio: €XX.XX

   Giochi per console:
   - Xbox: XXX
   - PS4: XXX
   - PSP: XXX
   - Wii: XXX
   - Switch: XXX

📤 Export JSON per dashboard...
✅ Esportati 2877 giochi in ../dashboard/data/games.json

==============================================================
✅ IMPORT COMPLETATO!
==============================================================
```

### Test 3: Verifica Database con SQLite

```bash
sqlite3 data/current/games.db

# Comandi dentro SQLite:
.tables                          # Mostra tabelle
.schema games                    # Mostra schema
SELECT COUNT(*) FROM games;      # Conta giochi
SELECT * FROM games LIMIT 5;     # Primi 5 giochi
.quit
```

## 📊 Esempi Uso DatabaseManager

### Esempio 1: Inserire nuovo gioco

```python
from database_manager import DatabaseManager

db = DatabaseManager("../data/current/games.db")

game = {
    'title': 'God of War',
    'console': 'PS4',
    'current_price': 39.99,
    'is_available': True,
    'url': 'https://it.webuy.com/...'
}

game_id, price_chg, avail_chg = db.upsert_game(game)
print(f"Gioco ID: {game_id}")
print(f"Prezzo cambiato: {price_chg}")
print(f"Disponibilità cambiata: {avail_chg}")
```

### Esempio 2: Aggiornare prezzo (tracking automatico)

```python
# Primo inserimento
game = {'title': 'Halo Infinite', 'console': 'Xbox', 'current_price': 59.99}
game_id, _, _ = db.upsert_game(game)

# Aggiornamento con nuovo prezzo
game['current_price'] = 49.99
game_id, price_changed, _ = db.upsert_game(game)
print(f"Prezzo cambiato: {price_changed}")  # True

# Storico viene salvato automaticamente in price_history
history = db.get_price_history(game_id)
print(history)  # [{'old_price': 59.99, 'new_price': 49.99, ...}]
```

### Esempio 3: Statistiche

```python
stats = db.get_statistics()
print(f"Totale: {stats['total_games']}")
print(f"Disponibili: {stats['available_games']}")
print(f"Prezzo medio: €{stats['average_price']}")
print(f"Console: {stats['by_console']}")
```

### Esempio 4: Wishlist

```python
# Aggiungi a wishlist
db.add_to_wishlist(game_id=1, target_price=29.99, notes="Regalo per Natale")

# Recupera wishlist
wishlist = db.get_wishlist()
for item in wishlist:
    print(f"{item['title']} - Target: €{item['target_price']}")
```

## 🎯 Prossimi Passi

**FASE 3: Scraper Modificato** (45 min)
- Adattare `cex_selenium_scraper.py` esistente
- Integrare con DatabaseManager
- Generare report cambiamenti giornalieri
- Script per export JSON dashboard

**Files da creare in Fase 3:**
- `scraper/main_scraper.py` - Scraper principale modificato
- `scraper/changes_analyzer.py` - Analisi cambiamenti
- `scripts/export_data.py` - Export automatico JSON

---

**Tempo impiegato:** ~30 minuti  
**Prossima fase:** Fase 3 - Scraper Modificato (45 minuti stimati)
