#!/usr/bin/env python3
"""
CEX Price Tracker - Main Scraper (v2 - Algolia)
Orchestratore principale: scraping Algolia → database → report cambiamenti

Sostituisce la versione precedente basata su Selenium.
Da eseguire dalla cartella 'scraper/':
    python main_scraper.py

Tempo atteso: ~10-30 secondi (vs 29 minuti con Selenium)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from database_manager import DatabaseManager
from changes_analyzer import ChangesAnalyzer
from algolia_scraper import scrape_all_consoles


# ============================================================================
# CONFIGURAZIONE PERCORSI
# ============================================================================

DB_PATH        = "../data/current/games.db"
REPORTS_DIR    = "../data/reports"
DASHBOARD_JSON = "../dashboard/data/games.json"


# ============================================================================
# NORMALIZZAZIONE PRODOTTO
# ============================================================================

def normalize_product(product: dict) -> dict:
    """
    Converte un prodotto dal formato Algolia al formato DatabaseManager.

    Input (da algolia_scraper):
        {
            'Type': 'Videogame', 'Platform': 'Xbox 360',
            'Title': 'Halo 3',  'Price': 4.0,
            'Buyable': True,    'ID': 'xbx3halo3',
            'URL': 'https://...', '_console_group': 'Xbox'
        }

    Output (per DatabaseManager.upsert_game):
        {
            'title': 'Halo 3',       'console': 'Xbox',
            'category': 'Xbox 360',  'current_price': 4.0,
            'is_available': True,    'url': 'https://...'
        }
    """
    return {
        "title":         product.get("Title", "").strip(),
        "console":       product.get("_console_group", product.get("Platform", "")),
        "category":      product.get("Platform", ""),
        "current_price": product.get("Price"),
        "is_available":  bool(product.get("Buyable", False)),
        "url":           product.get("URL", ""),
    }


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    start_time = datetime.now()

    print("\n" + "=" * 60)
    print("🎮 CEX PRICE TRACKER - Main Scraper v2 (Algolia)")
    print(f"📅 {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # --- 1. DATABASE ---
    print("\n💾 Connessione al database...")
    db = DatabaseManager(DB_PATH)
    db.init_database()
    print(f"   ✅ Database: {DB_PATH}")

    # --- 2. SCRAPING VIA ALGOLIA ---
    print("\n🌐 Avvio scraping via Algolia...")
    try:
        raw_products = scrape_all_consoles()
    except Exception as e:
        print(f"\n❌ Errore durante lo scraping: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if not raw_products:
        print("⚠️  Nessun prodotto trovato. Controlla la connessione o le credenziali Algolia.")
        return 1

    print(f"✅ Scraping completato: {len(raw_products)} prodotti trovati")

    # --- 3. SALVATAGGIO + RILEVAMENTO CAMBIAMENTI ---
    print("\n💾 Aggiornamento database e rilevamento cambiamenti...")

    analyzer = ChangesAnalyzer()
    stats = {
        "new_games":              0,
        "price_changes":          0,
        "availability_changes":   0,
        "unchanged":              0,
        "errors":                 [],
    }

    total = len(raw_products)
    for i, raw in enumerate(raw_products, 1):

        # Progress ogni 500 prodotti
        if i % 500 == 0 or i == total:
            pct = i / total * 100
            print(f"   📥 {i}/{total} ({pct:.0f}%)...")

        try:
            game_data = normalize_product(raw)

            if not game_data["title"]:
                continue

            # Leggi stato precedente PRIMA dell'upsert (per ChangesAnalyzer)
            existing = db.get_game_by_title_console(
                game_data["title"], game_data["console"]
            ) if hasattr(db, "get_game_by_title_console") else None

            old_price = existing["current_price"] if existing else None
            old_avail = existing["is_available"]  if existing else None

            game_id, price_changed, avail_changed = db.upsert_game(game_data)

            # Marca nuovo se non esisteva
            if old_price is None and old_avail is None:
                analyzer.mark_new(game_id, game_data)
                stats["new_games"] += 1
            else:
                analyzer.record(
                    game_id, game_data,
                    price_changed, avail_changed,
                    old_price, old_avail,
                )
                if price_changed:
                    stats["price_changes"] += 1
                elif avail_changed:
                    stats["availability_changes"] += 1
                else:
                    stats["unchanged"] += 1

        except Exception as e:
            stats["errors"].append({
                "product": raw.get("Title", "?"),
                "error":   str(e),
            })

    print(f"   ✅ Database aggiornato")

    # --- 4. REPORT CAMBIAMENTI ---
    report_dir = Path(REPORTS_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    today      = datetime.now().strftime("%Y%m%d")
    report_path = report_dir / f"changes_{today}.json"

    report = analyzer.build_report(stats, len(raw_products), start_time)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📄 Report salvato: {report_path}")

    # --- 5. EXPORT JSON PER DASHBOARD ---
    print("\n📤 Export JSON per dashboard...")
    try:
        db.export_to_json(DASHBOARD_JSON)
        print(f"   ✅ Dashboard aggiornata: {DASHBOARD_JSON}")
    except Exception as e:
        print(f"   ⚠️  Export dashboard fallito: {e}")

    # --- 6. RIEPILOGO FINALE ---
    elapsed  = (datetime.now() - start_time).total_seconds()
    db_stats = db.get_statistics()

    print("\n" + "=" * 60)
    print("📊 RIEPILOGO FINALE")
    print("=" * 60)
    print(f"⏱️  Durata:               {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"🎮 Prodotti scrappati:    {len(raw_products)}")
    print(f"🗄️  Giochi in database:   {db_stats['total_games']}")
    print(f"✅ Disponibili:           {db_stats['available_games']}")
    print(f"🆕 Nuovi giochi:          {stats['new_games']}")
    print(f"💰 Cambiamenti prezzo:    {stats['price_changes']}")
    print(f"📦 Cambiamenti disponib.: {stats['availability_changes']}")
    print(f"⏸️  Invariati:             {stats['unchanged']}")

    if stats["errors"]:
        print(f"\n⚠️  Errori ({len(stats['errors'])}):")
        for err in stats["errors"][:5]:
            print(f"   - {err['product']}: {err['error']}")
        if len(stats["errors"]) > 5:
            print(f"   ... e altri {len(stats['errors']) - 5}")

    print("=" * 60)
    print("✨ COMPLETATO!")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrotto dall'utente.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Errore critico: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
