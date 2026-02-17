# Scraper Module

Questo modulo gestisce lo scraping dei dati da CEX e la gestione del database.

## File Principali

### `database_manager.py`
Classe principale per gestire tutte le operazioni sul database SQLite.

**Funzionalità:**
- Inizializzazione schema database
- Insert/Update giochi con tracking automatico cambiamenti
- Recupero dati (per console, per ID, statistiche)
- Gestione wishlist
- Export JSON per dashboard

**Uso:**
```python
from database_manager import DatabaseManager

db = DatabaseManager("../data/current/games.db")
db.init_database()

# Inserisci/aggiorna gioco
game_data = {
    'title': 'The Last of Us',
    'console': 'PS4',
    'current_price': 29.99,
    'is_available': True,
    'url': 'https://...'
}
game_id, price_changed, avail_changed = db.upsert_game(game_data)

# Ottieni statistiche
stats = db.get_statistics()
print(f"Totale giochi: {stats['total_games']}")
```

### `init_database.py`
Script per inizializzare il database (prima volta).

**Uso:**
```bash
cd scraper
python init_database.py
```

### `test_import_csv.py`
Script per importare dati da CSV esistente (solo per testing).

**Uso:**
```bash
cd scraper
python test_import_csv.py /path/to/your/file.csv
```

### `main_scraper.py` (Fase 3)
Scraper principale che usa Selenium per scaricare i dati da CEX.

## Testing Locale

1. **Inizializza database:**
   ```bash
   python init_database.py
   ```

2. **Import dati di test (opzionale):**
   ```bash
   python test_import_csv.py ../path/to/csv.csv
   ```

3. **Verifica database:**
   ```bash
   sqlite3 ../data/current/games.db
   .tables
   SELECT COUNT(*) FROM games;
   .quit
   ```

## Database Schema

### Tabella `games`
- `id` - ID univoco
- `title` - Titolo gioco
- `console` - Console (Xbox, PS4, PSP, Wii, Switch)
- `current_price` - Prezzo attuale
- `is_available` - Disponibilità (1=sì, 0=no)
- `first_seen` - Data prima volta visto
- `last_updated` - Data ultimo aggiornamento
- `last_price_change` - Data ultimo cambio prezzo
- `last_availability_change` - Data ultimo cambio disponibilità

### Tabella `price_history`
Storico di tutti i cambiamenti di prezzo.

### Tabella `availability_history`
Storico di tutti i cambiamenti di disponibilità.

### Tabella `wishlist`
Giochi tracciati dall'utente per notifiche.

## Dipendenze

Vedi `../requirements.txt`
