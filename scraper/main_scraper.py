"""
CEX Price Tracker - Main Scraper
Orchestratore principale: scraping → database → report cambiamenti

Integra cex_selenium_scraper.py esistente con DatabaseManager.
Da eseguire dalla cartella 'scraper/':
    python main_scraper.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Aggiungi la cartella scraper al path
sys.path.insert(0, str(Path(__file__).parent))

from database_manager import DatabaseManager
from changes_analyzer import ChangesAnalyzer


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# Categorie da monitorare con i loro ID CEX
CONSOLES_TO_TRACK = {
    "Xbox": [
        {"name": "Xbox",        "id": 1020},
        {"name": "Xbox 360",    "id": 827},
        {"name": "Xbox One",    "id": 1002},
        {"name": "Xbox CrossGen","id": 1088},
        {"name": "Xbox Series", "id": 1091},
    ],
    "PS4": [
        {"name": "PS4",         "id": 1000},
    ],
    "PSP": [
        {"name": "PSP",         "id": 613},
    ],
    "Wii": [
        {"name": "Wii",         "id": 641},
        {"name": "Wii U",       "id": 945},
    ],
    "Switch": [
        {"name": "Switch",      "id": 1064},
    ],
}

DB_PATH = "../data/current/games.db"
REPORTS_DIR = "../data/reports"
DASHBOARD_JSON = "../dashboard/data/games.json"


# ============================================================================
# IMPORTA FUNZIONI SCRAPER
# ============================================================================

def import_scraper():
    """
    Importa le funzioni necessarie dallo scraper esistente.
    Supporta sia il file originale che una versione headless-forzata.
    """
    try:
        # Importa le funzioni dallo scraper originale
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cex_selenium_scraper",
            Path(__file__).parent / "cex_selenium_scraper.py"
        )
        mod = importlib.util.load_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        print(f"❌ Impossibile importare cex_selenium_scraper.py: {e}")
        print("   Assicurati che il file sia nella cartella 'scraper/'")
        sys.exit(1)


# ============================================================================
# FUNZIONI SCRAPING
# ============================================================================

def scrape_all_consoles(headless: bool = True) -> list:
    """
    Esegue lo scraping di tutte le console configurate.
    
    Returns:
        Lista di tutti i prodotti trovati
    """
    mod = import_scraper()
    
    # Crea driver Selenium in modalità headless
    print(f"\n🚀 Avvio browser Chrome ({'headless' if headless else 'visibile'})...")
    driver = mod.CexSeleniumDriver(headless=headless)
    
    all_products = []
    total_consoles = sum(len(cats) for cats in CONSOLES_TO_TRACK.values())
    processed = 0
    
    try:
        for console_group, categories in CONSOLES_TO_TRACK.items():
            print(f"\n📦 Console: {console_group}")
            
            for cat in categories:
                processed += 1
                print(f"\n  [{processed}/{total_consoles}] 🎮 {cat['name']} (id={cat['id']})...")
                
                try:
                    products = mod.scrape_category(
                        driver=driver,
                        category_name=cat['name'],
                        category_id=cat['id'],
                        availability=mod.AVAILABILITY_ALL  # Tutti: disponibili + esauriti
                    )
                    
                    # Normalizza il campo console_group (tutti i tipi Xbox → 'Xbox')
                    for p in products:
                        p['_console_group'] = console_group
                    
                    all_products.extend(products)
                    print(f"  ✅ {len(products)} prodotti trovati")
                    
                except Exception as e:
                    print(f"  ❌ Errore scraping {cat['name']}: {e}")
                    continue
    
    finally:
        driver.quit()
    
    return all_products


def normalize_product(product: dict) -> dict:
    """
    Normalizza un prodotto dallo scraper al formato DatabaseManager.
    
    Input (formato scraper esistente):
        {
            'Type': 'Xbox', 'Platform': 'Xbox 360',
            'Title': 'Halo 3', 'Price': 4.0,
            'Buyable': True, 'ID': 'xbx3halo3',
            'URL': 'https://...',
            '_console_group': 'Xbox'
        }
    
    Output (formato DatabaseManager):
        {
            'title': 'Halo 3', 'console': 'Xbox',
            'category': 'Xbox 360', 'current_price': 4.0,
            'is_available': True, 'url': 'https://...'
        }
    """
    # Il console_group raggruppa tutti i tipi Xbox sotto 'Xbox', ecc.
    console_group = product.get('_console_group') or product.get('Type', '')
    
    return {
        'title':         product.get('Title', '').strip(),
        'console':       console_group,
        'category':      product.get('Platform') or product.get('Type'),
        'current_price': product.get('Price'),
        'is_available':  bool(product.get('Buyable', False)),
        'url':           product.get('URL'),
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    start_time = datetime.now()
    
    print("=" * 60)
    print("🎮 CEX PRICE TRACKER - Scraping Giornaliero")
    print(f"📅 {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # --- 1. INIZIALIZZA DATABASE ---
    print("\n🔧 Inizializzazione database...")
    db = DatabaseManager(DB_PATH)
    db.init_database()
    print("✅ Database pronto")
    
    # --- 2. SCRAPING ---
    print("\n🌐 Avvio scraping CEX Italia...")
    try:
        raw_products = scrape_all_consoles(headless=True)
    except Exception as e:
        print(f"\n❌ Errore durante lo scraping: {e}")
        return 1
    
    print(f"\n✅ Scraping completato: {len(raw_products)} prodotti trovati in totale")
    
    if not raw_products:
        print("⚠️  Nessun prodotto trovato. Controlla il browser e riprova.")
        return 1
    
    # --- 3. SALVA NEL DATABASE + RILEVA CAMBIAMENTI ---
    print("\n💾 Aggiornamento database e rilevamento cambiamenti...")
    
    analyzer = ChangesAnalyzer()
    stats = {
        'new_games': 0,
        'price_changes': 0,
        'availability_changes': 0,
        'unchanged': 0,
        'errors': []
    }
    
    for raw in raw_products:
        try:
            game_data = normalize_product(raw)
            
            if not game_data['title']:
                continue
            
            game_id, price_changed, avail_changed = db.upsert_game(game_data)
            analyzer.record(game_id, game_data, price_changed, avail_changed)
            
            if price_changed:
                stats['price_changes'] += 1
            elif avail_changed:
                stats['availability_changes'] += 1
            else:
                stats['unchanged'] += 1
                
        except Exception as e:
            stats['errors'].append({'product': raw.get('Title', '?'), 'error': str(e)})
    
    # --- 4. REPORT CAMBIAMENTI ---
    report_dir = Path(REPORTS_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now().strftime('%Y%m%d')
    report_path = report_dir / f"changes_{today}.json"
    
    report = analyzer.build_report(stats, len(raw_products), start_time)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Report salvato: {report_path}")
    
    # --- 5. EXPORT JSON PER DASHBOARD ---
    print("\n📤 Export JSON per dashboard...")
    exported = db.export_to_json(DASHBOARD_JSON)
    
    # --- 6. RIEPILOGO FINALE ---
    elapsed = (datetime.now() - start_time).total_seconds()
    db_stats = db.get_statistics()
    
    print("\n" + "=" * 60)
    print("📊 RIEPILOGO FINALE")
    print("=" * 60)
    print(f"⏱️  Durata:               {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"🎮 Prodotti scrappati:    {len(raw_products)}")
    print(f"🗄️  Giochi in database:   {db_stats['total_games']}")
    print(f"✅ Disponibili:           {db_stats['available_games']}")
    print(f"🆕 Nuovi giochi:          {stats['new_games']}")
    print(f"💰 Cambiamenti prezzo:    {stats['price_changes']}")
    print(f"📦 Cambiamenti disponib.: {stats['availability_changes']}")
    print(f"⏸️  Invariati:             {stats['unchanged']}")
    if stats['errors']:
        print(f"⚠️  Errori:               {len(stats['errors'])}")
    print("=" * 60)
    print("✅ SCRAPING COMPLETATO CON SUCCESSO")
    print("=" * 60 + "\n")
    
    return 0 if not stats['errors'] else 1


if __name__ == "__main__":
    sys.exit(main())
