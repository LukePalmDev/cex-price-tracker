"""
CEX Price Tracker - CSV Import Test
Script per importare dati da CSV esistente nel nuovo database (solo per testing)
"""

import csv
import sys
from pathlib import Path
from database_manager import DatabaseManager


def parse_price(price_str):
    """Converte stringa prezzo in float"""
    if not price_str or price_str == '':
        return None
    try:
        # Rimuovi simbolo € e spazi, converti in float
        price_str = price_str.replace('€', '').replace(',', '.').strip()
        return float(price_str)
    except (ValueError, AttributeError):
        return None


def parse_availability(buyable_str):
    """Converte stringa disponibilità in boolean"""
    if isinstance(buyable_str, bool):
        return buyable_str
    if isinstance(buyable_str, str):
        return buyable_str.lower() in ['true', 'sì', 'si', 'yes', '1']
    return False


def import_csv_to_database(csv_path: str, db_path: str = "../data/current/games.db"):
    """Importa dati da CSV nel database"""
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ File CSV non trovato: {csv_path}")
        return 1
    
    print("="*60)
    print("📥 CEX PRICE TRACKER - CSV IMPORT")
    print("="*60)
    print(f"\n📄 File CSV: {csv_file.name}")
    
    # Inizializza database
    db = DatabaseManager(db_path)
    db.init_database()
    
    # Leggi CSV
    imported = 0
    errors = 0
    price_changes = 0
    availability_changes = 0
    
    print("\n🔄 Importazione in corso...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Mappa console (Type nel CSV)
                console_map = {
                    'Xbox': 'Xbox',
                    'PS4': 'PS4',
                    'PSP': 'PSP',
                    'Wii': 'Wii',
                    'Switch': 'Switch'
                }
                
                console_type = row.get('Type', '').strip()
                console = console_map.get(console_type, console_type)
                
                if not console:
                    continue
                
                # Prepara dati gioco
                game_data = {
                    'title': row.get('Title', '').strip(),
                    'console': console,
                    'category': row.get('Platform', '').strip() if 'Platform' in row else None,
                    'current_price': parse_price(row.get('Price')),
                    'is_available': parse_availability(row.get('Buyable', True)),
                    'url': row.get('URL', '').strip() if 'URL' in row else None,
                }
                
                if not game_data['title']:
                    continue
                
                # Inserisci/aggiorna nel database
                game_id, price_chg, avail_chg = db.upsert_game(game_data)
                
                imported += 1
                if price_chg:
                    price_changes += 1
                if avail_chg:
                    availability_changes += 1
                
                # Progress indicator
                if imported % 100 == 0:
                    print(f"   Processati: {imported} giochi...", end='\r')
                    
            except Exception as e:
                errors += 1
                if errors < 5:  # Mostra solo i primi 5 errori
                    print(f"\n⚠️  Errore riga {reader.line_num}: {e}")
    
    print(f"\n\n✅ Importazione completata!")
    print(f"   Giochi importati: {imported}")
    print(f"   Cambiamenti prezzo: {price_changes}")
    print(f"   Cambiamenti disponibilità: {availability_changes}")
    if errors > 0:
        print(f"   Errori: {errors}")
    
    # Mostra statistiche finali
    print("\n📊 Statistiche database:")
    stats = db.get_statistics()
    print(f"   Totale giochi: {stats['total_games']}")
    print(f"   Disponibili: {stats['available_games']}")
    print(f"   Non disponibili: {stats['unavailable_games']}")
    print(f"   Prezzo medio: €{stats['average_price']}")
    
    print("\n   Giochi per console:")
    for console, count in stats['by_console'].items():
        print(f"   - {console}: {count}")
    
    # Esporta JSON per dashboard
    print("\n📤 Export JSON per dashboard...")
    db.export_to_json("../dashboard/data/games.json")
    
    print("\n" + "="*60)
    print("✅ IMPORT COMPLETATO!")
    print("="*60)
    
    return 0


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Uso: python test_import_csv.py <percorso_csv>")
        print("\nEsempio:")
        print("  python test_import_csv.py /percorso/al/file.csv")
        return 1
    
    csv_path = sys.argv[1]
    return import_csv_to_database(csv_path)


if __name__ == "__main__":
    sys.exit(main())
