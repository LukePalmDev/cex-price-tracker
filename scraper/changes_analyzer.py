"""
CEX Price Tracker - Changes Analyzer
Raccoglie e formatta i cambiamenti rilevati durante lo scraping giornaliero.
"""

from datetime import datetime
from typing import Dict, List, Optional


class ChangesAnalyzer:
    """Raccoglie i cambiamenti durante lo scraping e genera il report finale."""

    def __init__(self):
        self._new_games: List[Dict] = []
        self._price_changes: List[Dict] = []
        self._availability_changes: List[Dict] = []
        # Stato precedente necessario per costruire il diff:
        # viene fornito da DatabaseManager prima dell'upsert → passiamo i dati grezzi
        self._records: List[Dict] = []

    def record(
        self,
        game_id: int,
        game_data: dict,
        price_changed: bool,
        avail_changed: bool,
        old_price: Optional[float] = None,
        old_avail: Optional[bool] = None,
    ):
        """
        Registra il risultato dell'upsert di un singolo gioco.

        Args:
            game_id:       ID nel database (intero)
            game_data:     dizionario normalizzato passato a upsert_game()
            price_changed: True se il prezzo è cambiato
            avail_changed: True se la disponibilità è cambiata
            old_price:     Prezzo precedente (opzionale, per calcolare la variazione)
            old_avail:     Disponibilità precedente (opzionale)
        """
        self._records.append({
            'game_id':      game_id,
            'game_data':    game_data,
            'price_changed': price_changed,
            'avail_changed': avail_changed,
            'old_price':    old_price,
            'old_avail':    old_avail,
        })

        if price_changed:
            entry = {
                'game_id': game_id,
                'title':   game_data['title'],
                'console': game_data['console'],
                'new_price': game_data.get('current_price'),
            }
            if old_price is not None:
                entry['old_price'] = old_price
                if old_price and old_price != 0:
                    entry['variation_pct'] = round(
                        (game_data['current_price'] - old_price) / old_price * 100, 2
                    )
            self._price_changes.append(entry)

        if avail_changed:
            new_avail = game_data.get('is_available', False)
            entry = {
                'game_id':    game_id,
                'title':      game_data['title'],
                'console':    game_data['console'],
                'new_status': 'Disponibile' if new_avail else 'Esaurito',
            }
            if old_avail is not None:
                entry['old_status'] = 'Disponibile' if old_avail else 'Esaurito'
            self._availability_changes.append(entry)

    def mark_new(self, game_id: int, game_data: dict):
        """Marca esplicitamente un gioco come nuovo (primo inserimento)."""
        self._new_games.append({
            'game_id': game_id,
            'title':   game_data['title'],
            'console': game_data['console'],
            'price':   game_data.get('current_price'),
        })

    def build_report(
        self,
        stats: dict,
        total_scraped: int,
        start_time: datetime,
    ) -> dict:
        """
        Costruisce il dizionario del report finale da salvare in JSON.

        Args:
            stats:         dict con contatori new_games/price_changes/...
            total_scraped: numero totale di prodotti scrappati
            start_time:    datetime di inizio esecuzione

        Returns:
            Dict pronto per json.dump()
        """
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        report = {
            'metadata': {
                'generated_at':  end_time.isoformat(),
                'date':          end_time.strftime('%Y-%m-%d'),
                'duration_sec':  round(elapsed, 1),
                'total_scraped': total_scraped,
            },
            'summary': {
                'new_games':             stats.get('new_games', 0),
                'price_changes':         stats.get('price_changes', 0),
                'availability_changes':  stats.get('availability_changes', 0),
                'unchanged':             stats.get('unchanged', 0),
                'errors':                len(stats.get('errors', [])),
            },
            'new_games':             self._new_games,
            'price_changes':         self._price_changes,
            'availability_changes':  self._availability_changes,
            'errors':                stats.get('errors', []),
        }

        self._print_summary(report['summary'])
        return report

    def _print_summary(self, summary: dict):
        """Stampa il riepilogo a console."""
        print("\n" + "=" * 60)
        print("📊 RIEPILOGO CAMBIAMENTI")
        print("=" * 60)
        print(f"🆕 Nuovi giochi:           {summary['new_games']}")
        print(f"💰 Cambiamenti prezzo:     {summary['price_changes']}")
        print(f"📦 Cambiamenti disponib.:  {summary['availability_changes']}")
        print(f"⏸️  Nessun cambiamento:     {summary['unchanged']}")
        if summary['errors']:
            print(f"⚠️  Errori:                 {summary['errors']}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Proprietà di sola lettura (utili per i test)
    # ------------------------------------------------------------------
    @property
    def new_games(self) -> List[Dict]:
        return list(self._new_games)

    @property
    def price_changes(self) -> List[Dict]:
        return list(self._price_changes)

    @property
    def availability_changes(self) -> List[Dict]:
        return list(self._availability_changes)


# ============================================================================
# FUNZIONE STANDALONE (usata da GitHub Actions / notify.yml)
# ============================================================================

def load_latest_report(reports_dir: str = "../data/reports") -> Optional[Dict]:
    """
    Carica il report del giorno corrente (o il più recente disponibile).

    Returns:
        Dict del report, oppure None se non trovato.
    """
    from pathlib import Path

    dir_path = Path(reports_dir)
    if not dir_path.exists():
        return None

    today = datetime.now().strftime('%Y%m%d')
    today_file = dir_path / f"changes_{today}.json"

    if today_file.exists():
        import json
        with open(today_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Fallback: prendi il file più recente
    reports = sorted(dir_path.glob("changes_*.json"), reverse=True)
    if reports:
        import json
        with open(reports[0], 'r', encoding='utf-8') as f:
            return json.load(f)

    return None
