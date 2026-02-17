"""
CEX Price Tracker - Database Initialization
Script per inizializzare il database SQLite
"""

from database_manager import DatabaseManager
from pathlib import Path


def main():
    """Inizializza il database e verifica la creazione"""
    print("="*60)
    print("🎮 CEX PRICE TRACKER - DATABASE INITIALIZATION")
    print("="*60)
    
    # Verifica che la directory data/current esista
    db_path = Path("../data/current")
    if not db_path.exists():
        print(f"📁 Creazione directory: {db_path}")
        db_path.mkdir(parents=True, exist_ok=True)
    
    # Inizializza database
    print("\n🔧 Inizializzazione database...")
    db = DatabaseManager("../data/current/games.db")
    db.init_database()
    
    # Verifica creazione
    db_file = Path("../data/current/games.db")
    if db_file.exists():
        size_kb = db_file.stat().st_size / 1024
        print(f"✅ Database creato: {db_file}")
        print(f"   Dimensione: {size_kb:.2f} KB")
    else:
        print("❌ Errore: database non creato!")
        return 1
    
    # Mostra statistiche iniziali
    print("\n📊 Statistiche iniziali:")
    stats = db.get_statistics()
    print(f"   Totale giochi: {stats['total_games']}")
    print(f"   Disponibili: {stats['available_games']}")
    print(f"   Console trackate: {len(stats['by_console'])}")
    
    if stats['by_console']:
        print("\n   Giochi per console:")
        for console, count in stats['by_console'].items():
            print(f"   - {console}: {count}")
    
    print("\n" + "="*60)
    print("✅ INIZIALIZZAZIONE COMPLETATA!")
    print("="*60)
    
    print("\n💡 Prossimi passi:")
    print("   1. Esegui scraper per popolare il database")
    print("   2. Controlla: ../data/current/games.db")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
