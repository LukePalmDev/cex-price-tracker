"""
CEX Price Tracker - Monthly Snapshot
Crea un backup mensile compresso del database.
"""

import sqlite3
import csv
import gzip
import shutil
from pathlib import Path
from datetime import datetime


def main():
    db_path = Path("data/current/games.db")
    history_dir = Path("data/history")
    history_dir.mkdir(parents=True, exist_ok=True)

    month = datetime.now().strftime('%Y-%m')
    snapshot_path = history_dir / f"{month}-snapshot.csv.gz"

    print(f"📸 Creazione snapshot mensile: {month}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games ORDER BY console, title")
    rows = cursor.fetchall()
    conn.close()

    with gzip.open(snapshot_path, 'wt', encoding='utf-8', newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows([dict(r) for r in rows])

    size_kb = snapshot_path.stat().st_size / 1024
    print(f"✅ Snapshot salvato: {snapshot_path} ({size_kb:.1f} KB)")
    print(f"   Giochi inclusi: {len(rows)}")


if __name__ == "__main__":
    main()
