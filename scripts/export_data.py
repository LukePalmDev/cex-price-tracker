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
    return db.export_to_json(output_path)


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
