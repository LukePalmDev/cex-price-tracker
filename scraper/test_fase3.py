"""
CEX Price Tracker - Test Fase 3
Verifica che main_scraper.py, changes_analyzer.py e export_data.py
funzionino correttamente usando dati simulati (senza Selenium).

Eseguire dalla cartella 'scraper/':
    python test_fase3.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from database_manager import DatabaseManager
from changes_analyzer import ChangesAnalyzer

# ============================================================================
# DATI DI TEST (simulano l'output dello scraper)
# ============================================================================

FAKE_PRODUCTS = [
    # PS4
    {'title': 'God of War',         'console': 'PS4',    'category': 'PS4',    'current_price': 29.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=sgodofwar'},
    {'title': 'Spider-Man',          'console': 'PS4',    'category': 'PS4',    'current_price': 19.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=sspiderman'},
    {'title': 'The Last of Us',      'console': 'PS4',    'category': 'PS4',    'current_price': None,  'is_available': False, 'url': 'https://it.webuy.com/product-detail/?id=slastofus'},
    # Xbox
    {'title': 'Halo Infinite',       'console': 'Xbox',   'category': 'Xbox Series', 'current_price': 39.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=xhaloinf'},
    {'title': 'Forza Horizon 5',     'console': 'Xbox',   'category': 'Xbox Series', 'current_price': 34.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=xforzah5'},
    {'title': 'Halo 3',              'console': 'Xbox',   'category': 'Xbox 360',    'current_price': 4.00,  'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=xhalo3'},
    # Switch
    {'title': 'Zelda: BOTW',         'console': 'Switch', 'category': 'Switch', 'current_price': 44.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=nzeldabotw'},
    {'title': 'Mario Kart 8 Deluxe', 'console': 'Switch', 'category': 'Switch', 'current_price': 49.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=nmk8d'},
    # Wii
    {'title': 'Wii Sports',          'console': 'Wii',    'category': 'Wii',    'current_price': 7.00,  'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=wwsports'},
    # PSP
    {'title': 'God of War: Chains',  'console': 'PSP',    'category': 'PSP',    'current_price': 5.00,  'is_available': False, 'url': 'https://it.webuy.com/product-detail/?id=pgowch'},
]

# Secondo set: prezzi/disponibilità cambiati per simulare il secondo scraping
FAKE_PRODUCTS_V2 = [
    {'title': 'God of War',         'console': 'PS4',    'category': 'PS4',    'current_price': 24.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=sgodofwar'},   # ← prezzo sceso
    {'title': 'Spider-Man',          'console': 'PS4',    'category': 'PS4',    'current_price': 19.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=sspiderman'},   # invariato
    {'title': 'The Last of Us',      'console': 'PS4',    'category': 'PS4',    'current_price': 12.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=slastofus'},   # ← tornato disponibile
    {'title': 'Halo Infinite',       'console': 'Xbox',   'category': 'Xbox Series', 'current_price': 39.99, 'is_available': False, 'url': 'https://it.webuy.com/product-detail/?id=xhaloinf'}, # ← esaurito
    {'title': 'Forza Horizon 5',     'console': 'Xbox',   'category': 'Xbox Series', 'current_price': 34.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=xforzah5'}, # invariato
    {'title': 'Halo 3',              'console': 'Xbox',   'category': 'Xbox 360',    'current_price': 3.00,  'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=xhalo3'},    # ← prezzo sceso
    {'title': 'Zelda: BOTW',         'console': 'Switch', 'category': 'Switch', 'current_price': 44.99, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=nzeldabotw'}, # invariato
    {'title': 'Mario Kart 8 Deluxe', 'console': 'Switch', 'category': 'Switch', 'current_price': 55.00, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=nmk8d'},       # ← prezzo salito
    {'title': 'Wii Sports',          'console': 'Wii',    'category': 'Wii',    'current_price': 7.00,  'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=wwsports'},    # invariato
    {'title': 'God of War: Chains',  'console': 'PSP',    'category': 'PSP',    'current_price': 5.00,  'is_available': False, 'url': 'https://it.webuy.com/product-detail/?id=pgowch'},      # invariato
    {'title': 'Cyberpunk 2077',      'console': 'PS4',    'category': 'PS4',    'current_price': 15.00, 'is_available': True,  'url': 'https://it.webuy.com/product-detail/?id=scyber'},      # ← NUOVO gioco
]


# ============================================================================
# FUNZIONE DI TEST
# ============================================================================

def run_test(db_path: str, products: list, label: str):
    """Simula un ciclo di scraping sul database."""
    
    print(f"\n{'='*60}")
    print(f"🔄 Simulazione: {label}")
    print(f"{'='*60}")
    
    db = DatabaseManager(db_path)
    db.init_database()
    
    analyzer = ChangesAnalyzer()
    stats = {'new_games': 0, 'price_changes': 0, 'availability_changes': 0, 'unchanged': 0, 'errors': []}
    
    for game_data in products:
        try:
            game_id, price_changed, avail_changed = db.upsert_game(game_data)
            analyzer.record(game_id, game_data, price_changed, avail_changed)
            
            if price_changed:
                stats['price_changes'] += 1
                print(f"  💰 Prezzo cambiato: {game_data['title']} → €{game_data['current_price']}")
            elif avail_changed:
                stats['availability_changes'] += 1
                status = "✅ Disponibile" if game_data['is_available'] else "❌ Esaurito"
                print(f"  📦 Disponibilità: {game_data['title']} → {status}")
            else:
                stats['unchanged'] += 1
                
        except Exception as e:
            stats['errors'].append({'product': game_data.get('title', '?'), 'error': str(e)})
            print(f"  ⚠️  Errore: {game_data.get('title')} - {e}")
    
    db_stats = db.get_statistics()
    report = analyzer.build_report(stats, len(products), datetime.now())
    
    print(f"\n📊 Database: {db_stats['total_games']} giochi | "
          f"Disponibili: {db_stats['available_games']} | "
          f"Prezzo medio: €{db_stats['average_price']}")
    
    return report


def main():
    # Usa database temporaneo per il test
    db_path = "../data/current/test_fase3.db"
    
    print("=" * 60)
    print("🧪 CEX PRICE TRACKER - Test Fase 3")
    print("=" * 60)
    
    # --- TEST 1: Primo scraping ---
    report1 = run_test(db_path, FAKE_PRODUCTS, "PRIMO SCRAPING (inserimento iniziale)")
    
    # --- TEST 2: Secondo scraping con cambiamenti ---
    report2 = run_test(db_path, FAKE_PRODUCTS_V2, "SECONDO SCRAPING (rilevamento cambiamenti)")
    
    # --- TEST 3: Export JSON ---
    print("\n" + "=" * 60)
    print("🧪 Test Export JSON")
    print("=" * 60)
    
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    try:
        from export_data import export_games
        count = export_games(db_path, "../dashboard/data/test_games.json")
        print(f"✅ Export OK: {count} giochi esportati")
        print(f"   File: ../dashboard/data/test_games.json")
    except Exception as e:
        print(f"❌ Export fallito: {e}")
    
    # --- PULIZIA ---
    import os
    try:
        os.remove(db_path)
        print(f"\n🧹 Database di test rimosso: {db_path}")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("✅ TEST FASE 3 COMPLETATO!")
    print("=" * 60)
    print("\nSe tutti i test sono ✅ puoi procedere alla Fase 4 (GitHub Actions)")
    print("oppure fare un test reale con: python main_scraper.py\n")


if __name__ == "__main__":
    main()
