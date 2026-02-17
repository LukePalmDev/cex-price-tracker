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
                    category TEXT,
                    current_price REAL,
                    is_available BOOLEAN DEFAULT 1,
                    condition TEXT,
                    url TEXT,
                    first_seen DATE NOT NULL,
                    last_updated DATE NOT NULL,
                    last_price_change DATE,
                    last_availability_change DATE,
                    image_url TEXT,
                    UNIQUE(title, console)
                )
            """)
            
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
            
            # Controlla se il gioco esiste già
            cursor.execute(
                "SELECT id, current_price, is_available FROM games WHERE title = ? AND console = ?",
                (game_data['title'], game_data['console'])
            )
            existing = cursor.fetchone()
            
            today = date.today().isoformat()
            price_changed = False
            availability_changed = False
            
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
                
                # Aggiorna gioco
                cursor.execute("""
                    UPDATE games 
                    SET current_price = ?,
                        is_available = ?,
                        category = ?,
                        condition = ?,
                        url = ?,
                        image_url = ?,
                        last_updated = ?,
                        last_price_change = CASE WHEN ? THEN ? ELSE last_price_change END,
                        last_availability_change = CASE WHEN ? THEN ? ELSE last_availability_change END
                    WHERE id = ?
                """, (
                    new_price, new_availability, game_data.get('category'),
                    game_data.get('condition'), game_data.get('url'),
                    game_data.get('image_url'), today,
                    price_changed, today,
                    availability_changed, today,
                    game_id
                ))
                
            else:
                # Nuovo gioco - inserisci
                cursor.execute("""
                    INSERT INTO games (
                        title, console, category, current_price, is_available,
                        condition, url, image_url, first_seen, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_data['title'], game_data['console'], game_data.get('category'),
                    game_data.get('current_price'), game_data.get('is_available', 1),
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
            
            # Totale giochi
            cursor.execute("SELECT COUNT(*) as total FROM games")
            total = cursor.fetchone()['total']
            
            # Giochi disponibili
            cursor.execute("SELECT COUNT(*) as available FROM games WHERE is_available = 1")
            available = cursor.fetchone()['available']
            
            # Giochi per console
            cursor.execute("""
                SELECT console, COUNT(*) as count 
                FROM games 
                GROUP BY console 
                ORDER BY count DESC
            """)
            by_console = {row['console']: row['count'] for row in cursor.fetchall()}
            
            # Prezzo medio
            cursor.execute("SELECT AVG(current_price) as avg_price FROM games WHERE current_price IS NOT NULL")
            avg_price = cursor.fetchone()['avg_price']
            
            # Ultimo aggiornamento
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
    
    def export_to_json(self, output_path: str):
        """Esporta tutti i giochi in formato JSON per la dashboard"""
        games = self.get_all_games()
        stats = self.get_statistics()
        
        data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_games': len(games),
                'statistics': stats
            },
            'games': games
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Esportati {len(games)} giochi in {output_path}")
        return len(games)


if __name__ == "__main__":
    # Test rapido
    db = DatabaseManager()
    db.init_database()
    stats = db.get_statistics()
    print(f"\n📊 Statistiche database:")
    print(f"   Totale giochi: {stats['total_games']}")
    print(f"   Disponibili: {stats['available_games']}")
    print(f"   Prezzo medio: €{stats['average_price']}")
