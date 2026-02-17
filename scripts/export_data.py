"""
CEX Price Tracker - Export Data
Esporta i dati dal database SQLite in JSON per la dashboard web.
Può essere eseguito standalone o chiamato da GitHub Actions.

Uso:
    python export_data.py
    python export_data.py --db ../data/current/games.db --out ../dashboard/data/games.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Aggiungi la cartella scraper al path
sys.path.insert(0, str(Path(__file__).parent.parent / "scraper"))

from database_manager import DatabaseManager


def export_games(db_path: str, output_path: str) -> int:
    """
    Esporta tutti i giochi + metadati in un file JSON per la dashboard.

    Returns:
        Numero di giochi esportati
    """
    db = DatabaseManager(db_path)

    # Recupera giochi e statistiche
    games = db.get_all_games()
    stats = db.get_statistics()

    # Per ogni gioco, aggiunge la variazione prezzo degli ultimi 7 giorni
    # (usata dalla dashboard per indicatori tendenza)
    enriched = []
    for g in games:
        entry = dict(g)

        # Recupera storico prezzi ultimi 30 giorni
        history = db.get_price_history(g['id'], days=30)
        entry['price_history_30d'] = [
            {
                'old_price': h['old_price'],
                'new_price': h['new_price'],
                'changed_at': h['changed_at'],
            }
            for h in history
        ]

        # Calcola tendenza prezzo (ultima variazione %)
        if len(history) >= 2:
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

    # Recupera wishlist per la dashboard
    wishlist_items = db.get_wishlist()
    wishlist_ids = {item['game_id'] for item in wishlist_items}

    # Carica report odierno se esiste
    today = datetime.now().strftime('%Y%m%d')
    report_path = Path(db_path).parent.parent / "reports" / f"changes_{today}.json"
    daily_summary = None
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            daily_report = json.load(f)
            daily_summary = daily_report.get('summary')

    # Struttura JSON finale
    output = {
        'metadata': {
            'exported_at':   datetime.now().isoformat(),
            'total_games':   len(enriched),
            'version':       '1.0',
        },
        'statistics': {
            **stats,
            'daily_summary': daily_summary,
        },
        'games': enriched,
    }

    # Salva file JSON
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    return len(enriched)


def main():
    parser = argparse.ArgumentParser(description='Esporta dati DB → JSON per dashboard')
    parser.add_argument(
        '--db',
        default='../data/current/games.db',
        help='Percorso database SQLite (default: ../data/current/games.db)'
    )
    parser.add_argument(
        '--out',
        default='../dashboard/data/games.json',
        help='Percorso output JSON (default: ../dashboard/data/games.json)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("📤 CEX PRICE TRACKER - Export Dashboard Data")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"\n📂 Database:  {args.db}")
    print(f"📄 Output:    {args.out}")
    print("\n🔄 Esportazione in corso...")

    try:
        count = export_games(args.db, args.out)
        size_kb = Path(args.out).stat().st_size / 1024
        print(f"\n✅ Esportati {count} giochi → {args.out}")
        print(f"   Dimensione file: {size_kb:.1f} KB")
        print("\n" + "=" * 60)
        print("✅ EXPORT COMPLETATO")
        print("=" * 60 + "\n")
        return 0
    except Exception as e:
        print(f"\n❌ Errore durante l'export: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
