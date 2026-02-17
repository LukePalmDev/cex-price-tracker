# Data Directory

Questa cartella contiene tutti i dati del tracker.

## Struttura

```
data/
├── current/            # Stato attuale
│   └── games.db        # Database SQLite principale
├── history/            # Backup storici
│   └── YYYY-MM-snapshot.csv.gz
└── reports/            # Report cambiamenti
    └── changes_YYYYMMDD.json
```

## File Principali

### `current/games.db`
Database SQLite con:
- Tabella `games` - stato attuale di tutti i giochi
- Tabella `price_history` - storico cambiamenti prezzi
- Tabella `availability_history` - storico disponibilità
- Tabella `wishlist` - giochi tracciati per notifiche

### `history/YYYY-MM-snapshot.csv.gz`
Backup mensile completo (primo giorno del mese).
Compresso con gzip per risparmiare spazio.

### `reports/changes_YYYYMMDD.json`
Report giornaliero con:
- Nuovi giochi aggiunti
- Cambiamenti di prezzo
- Cambiamenti di disponibilità
- Timestamp dell'analisi

## Retention Policy

- Database: conservato indefinitamente
- Reports: ultimi 30 giorni (poi archiviati)
- History: tutti i backup mensili
