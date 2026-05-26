"""
CEX Price Tracker - Database Manager
Gestisce tutte le operazioni sul database SQLite
"""

import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """Gestisce il database SQLite per il tracking dei prezzi"""
    
    def __init__(self, db_path: str = "data/current/games.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    @contextmanager
    def get_connection(self):
        """Context manager per gestire le connessioni al database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permette accesso per nome colonna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Inizializza il database con lo schema completo"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabella principale: games
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    console TEXT NOT NULL,
                    category TEXT NOT NULL,
                    current_price REAL,
                    cash_price REAL,
                    exchange_price REAL,
                    ecom_quantity INTEGER DEFAULT 0,
                    collection_quantity INTEGER DEFAULT 0,
                    out_of_stock_stores TEXT DEFAULT '[]',
                    is_available BOOLEAN DEFAULT 1,
                    condition TEXT,
                    url TEXT,
                    first_seen DATE NOT NULL,
                    last_updated DATE NOT NULL,
                    last_price_change DATE,
                    last_availability_change DATE,
                    image_url TEXT,
                    UNIQUE(title, console, category)
                )
            """)

            # Migrazione schema legacy
            self._migrate_games_table_if_needed(cursor)
            # Aggiunta colonne nuove su DB esistenti
            self._add_new_columns_if_missing(cursor)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_console ON games(console)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_price ON games(current_price)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_available ON games(is_available)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_last_updated ON games(last_updated)")
            
            # Tabella storico prezzi
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    old_price REAL,
                    new_price REAL NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_game ON price_history(game_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(changed_at)")
            
            # Tabella storico disponibilità
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS availability_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    old_status BOOLEAN,
                    new_status BOOLEAN NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_availability_history_game ON availability_history(game_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_availability_history_date ON availability_history(changed_at)")
            
            # Tabella wishlist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    target_price REAL,
                    notify_on_availability BOOLEAN DEFAULT 1,
                    notes TEXT,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                    UNIQUE(game_id)
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_game ON wishlist(game_id)")
            
            print("✅ Database schema inizializzato con successo!")
        
        # Esegue la pulizia automatica dei duplicati
        self.clean_duplicates()

    def clean_duplicates(self) -> int:
        """
        Identifica ed elimina i record duplicati (stesso titolo e stessa console).
        Mantiene solo il record con il prezzo corrente più alto (current_price DESC).
        Se i prezzi sono identici, mantiene quello aggiornato più di recente.
        """
        print("🧹 Avvio verifica e pulizia duplicati nel database...")
        deleted_count = 0
        
        # Trova i titoli e console che hanno duplicati
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, console, COUNT(*) as cnt
                FROM games
                GROUP BY title, console
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if not duplicates:
                print("   ✅ Nessun titolo duplicato trovato nel database.")
                return 0
                
            print(f"   ⚠️  Trovati {len(duplicates)} titoli duplicati. Rimozione copie con prezzo inferiore...")
            
            for row in duplicates:
                title = row['title']
                console = row['console']
                
                # Ottiene tutti i record per questo specifico duplicato, ordinati
                # per prezzo decrescente, data aggiornamento decrescente ed ID decrescente.
                cursor.execute("""
                    SELECT id, current_price, last_updated, category
                    FROM games
                    WHERE title = ? AND console = ?
                    ORDER BY current_price DESC, last_updated DESC, id DESC
                """, (title, console))
                records = cursor.fetchall()
                
                if len(records) <= 1:
                    continue
                
                # Il primo record è il "winner" (prezzo più alto / aggiornato più di recente)
                winner_id = records[0]['id']
                to_delete = records[1:]
                
                for r in to_delete:
                    gid = r['id']
                    # Rimuove in cascata per sicurezza da tutte le tabelle correlate
                    cursor.execute("DELETE FROM wishlist WHERE game_id = ?", (gid,))
                    cursor.execute("DELETE FROM price_history WHERE game_id = ?", (gid,))
                    cursor.execute("DELETE FROM availability_history WHERE game_id = ?", (gid,))
                    cursor.execute("DELETE FROM games WHERE id = ?", (gid,))
                    deleted_count += 1
                    
        print(f"   🧹 Pulizia completata: eliminati {deleted_count} record doppi non ottimali.")
        return deleted_count

    def _add_new_columns_if_missing(self, cursor):
        """Aggiunge le nuove colonne se non esistono (ALTER TABLE safe)."""
        cursor.execute("PRAGMA table_info(games)")
        existing_cols = {row['name'] for row in cursor.fetchall()}

        new_cols = [
            ("cash_price",          "REAL",    "NULL"),
            ("exchange_price",      "REAL",    "NULL"),
            ("ecom_quantity",       "INTEGER", "0"),
            ("collection_quantity", "INTEGER", "0"),
            ("out_of_stock_stores", "TEXT",    "'[]'"),
        ]
        for col_name, col_type, default in new_cols:
            if col_name not in existing_cols:
                cursor.execute(
                    f"ALTER TABLE games ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                )
                print(f"   ✅ Colonna aggiunta: games.{col_name}")

    def _migrate_games_table_if_needed(self, cursor):
        """Aggiorna la tabella games al vincolo UNIQUE(title, console, category)."""
        cursor.execute("PRAGMA table_info(games)")
        columns = cursor.fetchall()
        if not columns:
            return

        category_info = next((c for c in columns if c['name'] == 'category'), None)
        category_not_null = bool(category_info and category_info['notnull'])

        has_target_unique = False
        has_legacy_unique = False

        cursor.execute("PRAGMA index_list(games)")
        for idx in cursor.fetchall():
            if not idx['unique']:
                continue
            idx_name = idx['name']
            cursor.execute(f"PRAGMA index_info('{idx_name}')")
            idx_cols = [row['name'] for row in cursor.fetchall()]
            if idx_cols == ['title', 'console', 'category']:
                has_target_unique = True
            elif idx_cols == ['title', 'console']:
                has_legacy_unique = True

        if has_target_unique and category_not_null and not has_legacy_unique:
            return

        print("🔄 Migrazione tabella games: UNIQUE(title, console, category)")
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("""
            CREATE TABLE games_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                console TEXT NOT NULL,
                category TEXT NOT NULL,
                current_price REAL,
                cash_price REAL,
                exchange_price REAL,
                ecom_quantity INTEGER DEFAULT 0,
                collection_quantity INTEGER DEFAULT 0,
                out_of_stock_stores TEXT DEFAULT '[]',
                is_available BOOLEAN DEFAULT 1,
                condition TEXT,
                url TEXT,
                first_seen DATE NOT NULL,
                last_updated DATE NOT NULL,
                last_price_change DATE,
                last_availability_change DATE,
                image_url TEXT,
                UNIQUE(title, console, category)
            )
        """)
        cursor.execute("""
            INSERT INTO games_new (
                id, title, console, category, current_price, is_available,
                condition, url, first_seen, last_updated,
                last_price_change, last_availability_change, image_url
            )
            SELECT
                id, title, console, COALESCE(NULLIF(category, ''), console),
                current_price, is_available, condition, url, first_seen, last_updated,
                last_price_change, last_availability_change, image_url
            FROM games
            ORDER BY id
        """)
        cursor.execute("DROP TABLE games")
        cursor.execute("ALTER TABLE games_new RENAME TO games")
        cursor.execute("PRAGMA foreign_keys = ON")
        print("✅ Migrazione games completata")

    def upsert_game(self, game_data: Dict) -> Tuple[int, bool, bool]:
        """
        Inserisce o aggiorna un gioco nel database.
        Traccia automaticamente i cambiamenti di prezzo e disponibilità.
        
        Returns:
            (game_id, price_changed, availability_changed)
        
        Note:
            Per ottenere anche old_price/old_avail (utili per ChangesAnalyzer)
            chiama get_game_by_id(game_id) PRIMA di chiamare questo metodo.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            category = (game_data.get('category') or game_data.get('console') or '').strip()
            if not category:
                raise ValueError("Campo 'category' mancante")
            
            # Controlla se il gioco esiste già
            cursor.execute(
                "SELECT id, current_price, is_available FROM games WHERE title = ? AND console = ? AND category = ?",
                (game_data['title'], game_data['console'], category)
            )
            existing = cursor.fetchone()
            
            today = date.today().isoformat()
            price_changed = False
            availability_changed = False

            # Campi nuovi comuni INSERT/UPDATE
            cash_price          = game_data.get('cash_price')
            exchange_price      = game_data.get('exchange_price')
            ecom_quantity       = game_data.get('ecom_quantity', 0)
            collection_quantity = game_data.get('collection_quantity', 0)
            out_of_stock_stores = json.dumps(game_data.get('out_of_stock_stores') or [])
            
            if existing:
                # Gioco esistente - aggiorna
                game_id = existing['id']
                old_price = existing['current_price']
                old_availability = existing['is_available']
                
                new_price = game_data.get('current_price')
                new_availability = game_data.get('is_available', 1)
                
                # Controlla cambiamenti prezzo
                if old_price != new_price and new_price is not None:
                    price_changed = True
                    cursor.execute("""
                        INSERT INTO price_history (game_id, old_price, new_price)
                        VALUES (?, ?, ?)
                    """, (game_id, old_price, new_price))
                
                # Controlla cambiamenti disponibilità
                if old_availability != new_availability:
                    availability_changed = True
                    cursor.execute("""
                        INSERT INTO availability_history (game_id, old_status, new_status)
                        VALUES (?, ?, ?)
                    """, (game_id, old_availability, new_availability))
                
                # Aggiorna gioco (con nuovi campi)
                cursor.execute("""
                    UPDATE games SET
                        current_price        = ?,
                        cash_price           = ?,
                        exchange_price       = ?,
                        ecom_quantity        = ?,
                        collection_quantity  = ?,
                        out_of_stock_stores  = ?,
                        is_available         = ?,
                        category             = ?,
                        condition            = ?,
                        url                  = ?,
                        image_url            = ?,
                        last_updated         = ?,
                        last_price_change    = CASE WHEN ? THEN ? ELSE last_price_change END,
                        last_availability_change = CASE WHEN ? THEN ? ELSE last_availability_change END
                    WHERE id = ?
                """, (
                    new_price, cash_price, exchange_price,
                    ecom_quantity, collection_quantity, out_of_stock_stores,
                    new_availability, category,
                    game_data.get('condition'), game_data.get('url'),
                    game_data.get('image_url'), today,
                    price_changed, today,
                    availability_changed, today,
                    game_id
                ))
                
            else:
                # Nuovo gioco - inserisci (con nuovi campi)
                cursor.execute("""
                    INSERT INTO games (
                        title, console, category, current_price,
                        cash_price, exchange_price, ecom_quantity, collection_quantity,
                        out_of_stock_stores,
                        is_available, condition, url, image_url, first_seen, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_data['title'], game_data['console'], category,
                    game_data.get('current_price'),
                    cash_price, exchange_price, ecom_quantity, collection_quantity,
                    out_of_stock_stores,
                    game_data.get('is_available', 1),
                    game_data.get('condition'), game_data.get('url'),
                    game_data.get('image_url'), today, today
                ))
                
                game_id = cursor.lastrowid
                
                # Registra primo prezzo in history
                if game_data.get('current_price') is not None:
                    cursor.execute("""
                        INSERT INTO price_history (game_id, old_price, new_price)
                        VALUES (?, NULL, ?)
                    """, (game_id, game_data.get('current_price')))
                
                # Registra prima disponibilità
                cursor.execute("""
                    INSERT INTO availability_history (game_id, old_status, new_status)
                    VALUES (?, NULL, ?)
                """, (game_id, game_data.get('is_available', 1)))
            
            return game_id, price_changed, availability_changed
    
    def get_all_games(self, console: Optional[str] = None) -> List[Dict]:
        """Recupera tutti i giochi, opzionalmente filtrati per console"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if console:
                cursor.execute("SELECT * FROM games WHERE console = ? ORDER BY title", (console,))
            else:
                cursor.execute("SELECT * FROM games ORDER BY console, title")
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """Recupera un singolo gioco per ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_game_by_title_console(self, title: str, console: str) -> Optional[Dict]:
        """Recupera un gioco per titolo e console (prende il primo se ci sono più categorie)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM games WHERE title = ? AND console = ? LIMIT 1",
                (title, console)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def count_games_by_title_console(self, title: str, console: str) -> int:
        """Conta i record per la coppia (title, console), indipendentemente dalla categoria."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM games WHERE title = ? AND console = ?",
                (title, console)
            )
            return int(cursor.fetchone()['cnt'])

    def reset_history_for_games(self, game_ids: List[int]) -> int:
        """
        Resetta lo storico prezzo/disponibilità per una lista di game_id e
        reinserisce un singolo snapshot iniziale con i valori correnti.
        """
        normalized = []
        seen = set()
        for gid in game_ids or []:
            try:
                val = int(gid)
            except (TypeError, ValueError):
                continue
            if val > 0 and val not in seen:
                seen.add(val)
                normalized.append(val)

        if not normalized:
            return 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(normalized))
            cursor.execute(
                f"SELECT id, current_price, is_available FROM games WHERE id IN ({placeholders})",
                normalized
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                return 0

            ids = [int(r['id']) for r in rows]
            ph = ",".join(["?"] * len(ids))
            cursor.execute(f"DELETE FROM price_history WHERE game_id IN ({ph})", ids)
            cursor.execute(f"DELETE FROM availability_history WHERE game_id IN ({ph})", ids)

            for row in rows:
                gid = int(row['id'])
                if row.get('current_price') is not None:
                    cursor.execute(
                        "INSERT INTO price_history (game_id, old_price, new_price) VALUES (?, NULL, ?)",
                        (gid, row['current_price'])
                    )
                cursor.execute(
                    "INSERT INTO availability_history (game_id, old_status, new_status) VALUES (?, NULL, ?)",
                    (gid, row['is_available'])
                )
            return len(ids)

    def get_price_history(self, game_id: int, days: int = 30) -> List[Dict]:
        """Recupera lo storico prezzi di un gioco"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_history
                WHERE game_id = ?
                AND changed_at >= datetime('now', '-{} days')
                ORDER BY changed_at DESC
            """.format(days), (game_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_availability_history(self, game_id: int, days: int = 30) -> List[Dict]:
        """Recupera lo storico disponibilità di un gioco"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM availability_history
                WHERE game_id = ?
                AND changed_at >= datetime('now', '-{} days')
                ORDER BY changed_at DESC
            """.format(days), (game_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Calcola statistiche generali del database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM games")
            total = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as available FROM games WHERE is_available = 1")
            available = cursor.fetchone()['available']
            
            cursor.execute("""
                SELECT console, COUNT(*) as count
                FROM games
                GROUP BY console
                ORDER BY count DESC
            """)
            by_console = {row['console']: row['count'] for row in cursor.fetchall()}
            
            cursor.execute("SELECT AVG(current_price) as avg_price FROM games WHERE current_price IS NOT NULL")
            avg_price = cursor.fetchone()['avg_price']
            
            cursor.execute("SELECT MAX(last_updated) as last_update FROM games")
            last_update = cursor.fetchone()['last_update']
            
            return {
                'total_games': total,
                'available_games': available,
                'unavailable_games': total - available,
                'by_console': by_console,
                'average_price': round(avg_price, 2) if avg_price else 0,
                'last_update': last_update
            }
    
    def add_to_wishlist(self, game_id: int, target_price: Optional[float] = None,
                       notes: Optional[str] = None) -> bool:
        """Aggiunge un gioco alla wishlist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO wishlist (game_id, target_price, notes)
                    VALUES (?, ?, ?)
                """, (game_id, target_price, notes))
                return True
        except sqlite3.IntegrityError:
            return False  # Gioco già in wishlist
    
    def remove_from_wishlist(self, game_id: int) -> bool:
        """Rimuove un gioco dalla wishlist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM wishlist WHERE game_id = ?", (game_id,))
            return cursor.rowcount > 0
    
    def get_wishlist(self) -> List[Dict]:
        """Recupera tutti i giochi in wishlist con i loro dettagli"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    w.*,
                    g.title, g.console, g.current_price, g.is_available, g.url
                FROM wishlist w
                JOIN games g ON w.game_id = g.id
                ORDER BY w.added_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_wishlist_ids(self) -> List[int]:
        """Recupera solo gli ID dei giochi in wishlist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT game_id FROM wishlist ORDER BY added_at DESC")
            return [int(row['game_id']) for row in cursor.fetchall()]

    def set_wishlist_ids(self, game_ids: List[int]) -> Dict[str, int]:
        """
        Sostituisce la wishlist con una nuova lista di game_id.
        Restituisce un riepilogo su quanti ID sono stati salvati/scartati.
        """
        normalized = []
        seen = set()
        for gid in game_ids or []:
            try:
                val = int(gid)
            except (TypeError, ValueError):
                continue
            if val > 0 and val not in seen:
                seen.add(val)
                normalized.append(val)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            valid_ids = []

            if normalized:
                placeholders = ",".join(["?"] * len(normalized))
                cursor.execute(
                    f"SELECT id FROM games WHERE id IN ({placeholders})",
                    normalized
                )
                valid_set = {int(row['id']) for row in cursor.fetchall()}
                valid_ids = [gid for gid in normalized if gid in valid_set]

            cursor.execute("DELETE FROM wishlist")
            if valid_ids:
                cursor.executemany(
                    "INSERT INTO wishlist (game_id) VALUES (?)",
                    [(gid,) for gid in valid_ids]
                )

        return {
            'requested': len(normalized),
            'saved': len(valid_ids),
            'ignored': len(normalized) - len(valid_ids)
        }

    def export_to_json(self, output_path: str):
        """Esporta tutti i giochi in formato JSON per la dashboard"""
        games = self.get_all_games()
        stats = self.get_statistics()
        report_date = (stats.get('last_update') or datetime.now().strftime('%Y-%m-%d')).replace('-', '')
        report_path = self.db_path.parent.parent / "reports" / f"changes_{report_date}.json"
        daily_summary = None
        if report_path.exists():
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    daily_report = json.load(f)
                    daily_summary = daily_report.get('summary')
            except Exception:
                daily_summary = None

        # Recupera tutto lo storico prezzi degli ultimi 30 giorni in una sola query (Risoluzione N+1)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT game_id, old_price, new_price, changed_at
                FROM price_history
                WHERE changed_at >= datetime('now', '-30 days')
                ORDER BY game_id, changed_at DESC
            """)
            history_rows = cursor.fetchall()

        history_map = {}
        for r in history_rows:
            gid = int(r['game_id'])
            if gid not in history_map:
                history_map[gid] = []
            history_map[gid].append({
                'old_price': r['old_price'],
                'new_price': r['new_price'],
                'changed_at': r['changed_at']
            })

        enriched = []
        for g in games:
            entry = dict(g)

            # Deserializza out_of_stock_stores da stringa JSON a lista Python
            raw_oos = entry.get("out_of_stock_stores") or "[]"
            if isinstance(raw_oos, str):
                try:
                    entry["out_of_stock_stores"] = json.loads(raw_oos)
                except Exception:
                    entry["out_of_stock_stores"] = []

            history = history_map.get(g['id'], [])
            entry['price_history_30d'] = history
            if history:
                last = history[0]
                if last['old_price'] and last['old_price'] != 0:
                    entry['price_trend_pct'] = round(
                        (last['new_price'] - last['old_price']) / last['old_price'] * 100, 2
                    )
                else:
                    entry['price_trend_pct'] = None
            else:
                entry['price_trend_pct'] = None
            enriched.append(entry)

        statistics = {
            **stats,
            'daily_summary': daily_summary,
        }
        
        exported_at = datetime.now().isoformat()
        version_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        data = {
            'metadata': {
                'exported_at': exported_at,
                'total_games': len(enriched),
                'version': version_str,
                'statistics': statistics
            },
            'statistics': statistics,
            'games': enriched
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Scrive games.json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Scrive last_update.json per caching lato client (Miglioria 3)
        last_update_file = output_file.parent / "last_update.json"
        last_update_data = {
            "version": version_str,
            "exported_at": exported_at,
            "total_games": len(enriched),
            "statistics": statistics
        }
        with open(last_update_file, 'w', encoding='utf-8') as f:
            json.dump(last_update_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Esportati {len(enriched)} giochi in {output_path}")
        print(f"✅ Generato file di versione in {last_update_file}")
        return len(enriched)



if __name__ == "__main__":
    # Test rapido
    db = DatabaseManager()
    db.init_database()
    stats = db.get_statistics()
    print(f"\n📊 Statistiche database:")
    print(f"   Totale giochi: {stats['total_games']}")
    print(f"   Disponibili: {stats['available_games']}")
    print(f"   Prezzo medio: €{stats['average_price']}")
