"""
CEX Price Tracker - Notification Manager
Invia notifiche Telegram per cambiamenti rilevanti nella wishlist.

Uso:
    TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python notification_manager.py

Viene chiamato automaticamente da GitHub Actions (notify.yml) dopo ogni scraping.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Aggiungi cartella scraper al path per importare DatabaseManager
sys.path.insert(0, str(Path(__file__).parent.parent / "scraper"))
from database_manager import DatabaseManager


# ============================================================================
# TELEGRAM NOTIFIER
# ============================================================================

class TelegramNotifier:
    """Gestisce l'invio di messaggi via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Invia un messaggio Telegram. Ritorna True se successo."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Errore invio Telegram: {e}")
            return False

    def test_connection(self) -> bool:
        """Verifica che il bot sia raggiungibile."""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get('ok'):
                bot_name = data['result'].get('username', '?')
                print(f"✅ Bot connesso: @{bot_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ Errore connessione bot: {e}")
            return False


# ============================================================================
# CARICAMENTO DATI
# ============================================================================

def load_changes_report(reports_dir: str = "../data/reports") -> Optional[Dict]:
    """Carica il report dei cambiamenti di oggi (o il più recente)."""
    dir_path = Path(reports_dir)
    if not dir_path.exists():
        return None

    today = datetime.now().strftime('%Y%m%d')
    today_file = dir_path / f"changes_{today}.json"

    if today_file.exists():
        with open(today_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Fallback: prendi il più recente
    reports = sorted(dir_path.glob("changes_*.json"), reverse=True)
    if reports:
        with open(reports[0], 'r', encoding='utf-8') as f:
            return json.load(f)

    return None


def load_wishlist(db_path: str = "../data/current/games.db") -> List[Dict]:
    """Carica la wishlist dal database."""
    try:
        db = DatabaseManager(db_path)
        return db.get_wishlist()
    except Exception as e:
        print(f"⚠️  Errore caricamento wishlist: {e}")
        return []


def load_database_stats(db_path: str = "../data/current/games.db") -> Dict:
    """Carica le statistiche correnti del database."""
    try:
        db = DatabaseManager(db_path)
        return db.get_statistics()
    except Exception as e:
        print(f"⚠️  Errore caricamento statistiche DB: {e}")
        return {}


# ============================================================================
# RICERCA CAMBIAMENTI WISHLIST
# ============================================================================

def find_wishlist_notifications(changes: Dict, wishlist: List[Dict]) -> Dict:
    """
    Trova cambiamenti che riguardano giochi nella wishlist.

    Returns:
        Dict con liste di: price_drops, price_rises, back_in_stock, out_of_stock
    """
    # Crea un dizionario wishlist per ricerca rapida
    # key: game_id, value: wishlist entry
    wishlist_by_id = {item['game_id']: item for item in wishlist}
    # key: title.lower(), value: wishlist entry (per match su nome)
    wishlist_by_title = {item['title'].lower(): item for item in wishlist}

    notifications = {
        'price_drops':   [],   # Prezzo sceso (specialmente sotto target)
        'price_rises':   [],   # Prezzo salito
        'back_in_stock': [],   # Tornato disponibile
        'out_of_stock':  [],   # Diventato esaurito
    }

    # --- Cambiamenti prezzo ---
    for change in changes.get('price_changes', []):
        title_lower = change.get('title', '').lower()
        game_id = change.get('game_id')

        wishlist_item = wishlist_by_id.get(game_id) or wishlist_by_title.get(title_lower)
        if not wishlist_item:
            continue

        new_price = change.get('new_price') or 0
        old_price = change.get('old_price') or 0
        target_price = wishlist_item.get('target_price')
        variation_pct = change.get('variation_pct', 0)

        entry = {
            'title':         change.get('title'),
            'console':       change.get('console'),
            'old_price':     old_price,
            'new_price':     new_price,
            'variation_pct': variation_pct,
            'target_price':  target_price,
            'url':           wishlist_item.get('url', ''),
            'hit_target':    target_price and new_price <= target_price,
        }

        if new_price < old_price:
            notifications['price_drops'].append(entry)
        else:
            notifications['price_rises'].append(entry)

    # --- Cambiamenti disponibilità ---
    for change in changes.get('availability_changes', []):
        title_lower = change.get('title', '').lower()
        game_id = change.get('game_id')

        wishlist_item = wishlist_by_id.get(game_id) or wishlist_by_title.get(title_lower)
        if not wishlist_item:
            continue

        if not wishlist_item.get('notify_on_availability', True):
            continue

        entry = {
            'title':   change.get('title'),
            'console': change.get('console'),
            'url':     wishlist_item.get('url', ''),
            'price':   wishlist_item.get('current_price'),
        }

        new_status = change.get('new_status', '')
        if 'Disponibile' in new_status:
            notifications['back_in_stock'].append(entry)
        else:
            notifications['out_of_stock'].append(entry)

    return notifications


# ============================================================================
# FORMATTAZIONE MESSAGGI
# ============================================================================

def format_notification_message(notifications: Dict, summary: Dict) -> Optional[str]:
    """
    Formatta il messaggio Telegram in HTML.
    Ritorna None se non c'è nulla di rilevante da notificare.
    """
    has_content = any(notifications.values())
    if not has_content:
        return None

    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    msg = f"🔔 <b>CEX Price Tracker</b> — {now}\n"
    msg += "─" * 30 + "\n\n"

    # 🔥 Prezzi scesi (specialmente con target raggiunto)
    if notifications['price_drops']:
        msg += "💰 <b>RIBASSI DI PREZZO:</b>\n"
        for g in notifications['price_drops']:
            target_tag = " 🎯 <b>TARGET RAGGIUNTO!</b>" if g.get('hit_target') else ""
            msg += f"• <b>{g['title']}</b> ({g['console']}){target_tag}\n"
            msg += f"  {g['old_price']:.2f}€ → <b>{g['new_price']:.2f}€</b>"
            if g['variation_pct']:
                msg += f" ({g['variation_pct']:+.1f}%)"
            if g.get('target_price'):
                msg += f" | Target: {g['target_price']:.2f}€"
            msg += "\n\n"

    # ✅ Tornati disponibili
    if notifications['back_in_stock']:
        msg += "✅ <b>TORNATI DISPONIBILI:</b>\n"
        for g in notifications['back_in_stock']:
            price_str = f" — {g['price']:.2f}€" if g.get('price') else ""
            msg += f"• <b>{g['title']}</b> ({g['console']}){price_str}\n\n"

    # ❌ Diventati esauriti
    if notifications['out_of_stock']:
        msg += "❌ <b>ESAURITI:</b>\n"
        for g in notifications['out_of_stock']:
            msg += f"• <b>{g['title']}</b> ({g['console']})\n\n"

    # 📈 Prezzi saliti (meno urgenti, inclusi solo se non ci sono altri alert)
    if notifications['price_rises'] and not any([
        notifications['price_drops'],
        notifications['back_in_stock'],
        notifications['out_of_stock']
    ]):
        msg += "📈 <b>PREZZI AUMENTATI:</b>\n"
        for g in notifications['price_rises'][:5]:  # Max 5 per non spammare
            msg += f"• <b>{g['title']}</b> ({g['console']}): "
            msg += f"{g['old_price']:.2f}€ → {g['new_price']:.2f}€\n\n"

    # Footer con statistiche giornaliere
    if summary:
        msg += "─" * 30 + "\n"
        msg += f"📊 Oggi: {summary.get('price_changes', 0)} camb. prezzo"
        msg += f" | {summary.get('availability_changes', 0)} camb. disponib."
        msg += f" | {summary.get('new_games', 0)} nuovi"

    return msg


def format_daily_summary_message(summary: Dict) -> str:
    """Messaggio di riepilogo giornaliero (inviato sempre, anche senza wishlist)."""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    msg = f"🤖 <b>CEX Scraping completato</b> — {now}\n\n"
    msg += f"🕸️ Prodotti scrappati: <b>{summary.get('total_scraped', '?')}</b>\n"
    if summary.get('total_games') is not None:
        msg += f"🗄️ Giochi unici nel DB: <b>{summary.get('total_games')}</b>\n"
    msg += f"💰 Cambiamenti prezzo: <b>{summary.get('price_changes', 0)}</b>\n"
    msg += f"📦 Cambiamenti disponibilità: <b>{summary.get('availability_changes', 0)}</b>\n"
    msg += f"🆕 Nuovi giochi: <b>{summary.get('new_games', 0)}</b>\n"
    if summary.get('errors', 0):
        msg += f"⚠️  Errori: <b>{summary['errors']}</b>\n"
    return msg


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("📬 CEX PRICE TRACKER - Notification Manager")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Leggi configurazione
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("❌ Variabili TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID non configurate")
        print("   Esegui: export TELEGRAM_BOT_TOKEN=xxx && export TELEGRAM_CHAT_ID=yyy")
        return 1

    notifier = TelegramNotifier(bot_token, chat_id)

    # 2. Verifica connessione bot
    print("\n🔗 Verifica connessione bot...")
    if not notifier.test_connection():
        print("❌ Impossibile connettersi al bot. Verifica il token.")
        return 1

    # 3. Carica report
    print("\n📥 Caricamento report cambiamenti...")
    changes = load_changes_report()
    if not changes:
        print("⚠️  Nessun report trovato")
        return 0

    summary = changes.get('summary', {})
    metadata = changes.get('metadata', {})
    print(f"✅ Report del {metadata.get('date', '?')} caricato")
    print(f"   Cambiamenti: {summary.get('price_changes', 0)} prezzi, "
          f"{summary.get('availability_changes', 0)} disponibilità")

    # 4. Carica wishlist
    print("\n⭐ Caricamento wishlist...")
    wishlist = load_wishlist()
    print(f"   {len(wishlist)} giochi in wishlist")
    db_stats = load_database_stats()

    # 5. Invia sempre il riepilogo giornaliero
    daily_msg = format_daily_summary_message({
        **summary,
        'total_scraped': metadata.get('total_scraped', '?'),
        'total_games': db_stats.get('total_games')
    })
    notifier.send_message(daily_msg)
    print("✅ Riepilogo giornaliero inviato")

    # 6. Notifiche wishlist
    if wishlist:
        print("\n🔍 Ricerca cambiamenti wishlist...")
        notifications = find_wishlist_notifications(changes, wishlist)

        total = sum(len(v) for v in notifications.values())
        print(f"   Trovati {total} aggiornamenti rilevanti")

        if total > 0:
            msg = format_notification_message(notifications, summary)
            if msg:
                success = notifier.send_message(msg)
                if success:
                    print("✅ Notifica wishlist inviata!")
                else:
                    print("❌ Errore invio notifica wishlist")
                    return 1
    else:
        print("\nℹ️  Wishlist vuota — aggiungi giochi dalla dashboard")

    print("\n" + "=" * 60)
    print("✅ NOTIFICATION MANAGER COMPLETATO")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
