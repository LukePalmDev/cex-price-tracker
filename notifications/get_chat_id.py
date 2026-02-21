"""
CEX Price Tracker - Get Telegram Chat ID
Script per trovare il tuo Chat ID Telegram.

Uso:
    python get_chat_id.py
"""

import sys
import requests


def get_chat_id(bot_token: str):
    """Recupera il chat_id dal primo messaggio ricevuto dal bot."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    print(f"\n🔍 Controllo aggiornamenti bot...")
    response = requests.get(url, timeout=10)
    data = response.json()

    if not data.get('ok'):
        print(f"❌ Errore: {data.get('description', 'Token non valido')}")
        return None

    updates = data.get('result', [])

    if not updates:
        print("\n⚠️  Nessun messaggio trovato!")
        print("   → Apri Telegram, cerca il tuo bot e invia /start")
        print("   → Poi riesegui questo script")
        return None

    # Prendi l'ultimo messaggio
    last_update = updates[-1]
    message = last_update.get('message') or last_update.get('channel_post')

    if not message:
        print("❌ Nessun messaggio valido trovato")
        return None

    chat = message.get('chat', {})
    chat_id = chat.get('id')
    chat_type = chat.get('type', '?')
    chat_name = chat.get('first_name') or chat.get('title') or '?'

    print(f"\n✅ Chat trovata!")
    print(f"   Tipo:    {chat_type}")
    print(f"   Nome:    {chat_name}")
    print(f"   Chat ID: {chat_id}")

    return chat_id


def main():
    print("=" * 50)
    print("🤖 CEX Price Tracker - Get Chat ID")
    print("=" * 50)

    token = input("\nIncolla il tuo Bot Token: ").strip()
    if not token:
        print("❌ Token vuoto")
        return 1

    # Test connessione
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if not data.get('ok'):
            print(f"❌ Token non valido: {data.get('description')}")
            return 1
        bot_name = data['result'].get('username', '?')
        print(f"\n✅ Bot trovato: @{bot_name}")
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return 1

    chat_id = get_chat_id(token)

    if chat_id:
        print("\n" + "=" * 50)
        print("📋 SALVA QUESTI VALORI PER GITHUB SECRETS:")
        print("=" * 50)
        print(f"\nTELEGRAM_BOT_TOKEN = {token}")
        print(f"TELEGRAM_CHAT_ID   = {chat_id}")
        print("\nVai su:")
        print("https://github.com/LukePalmDev/cex-price-tracker/settings/secrets/actions")
        print("e aggiungi entrambi come Repository Secrets")
        print("=" * 50 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
