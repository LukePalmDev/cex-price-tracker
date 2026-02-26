#!/usr/bin/env python3
"""
CEX Price Tracker - Algolia Scraper
Sostituisce completamente Selenium usando l'API Algolia di WeBuy.

Vantaggi rispetto al vecchio scraper:
- Zero dipendenze da Chrome/Selenium
- Nessun wait/sleep necessario
- ceil(totale/1000) richieste per categoria (minimo assoluto)
- Tempo stimato: 5-15 secondi invece di 29 minuti

Credenziali Algolia (pubbliche, estratte dal browser):
- Endpoint:   https://search.webuy.io
- App ID:     LNNFEEWZVA
- API Key:    variabile d'ambiente ALGOLIA_API_KEY

Uso:
    from algolia_scraper import scrape_all_consoles
    products = scrape_all_consoles()

Author: Claude
Version: 1.2 (offset-based pagination + env var)
"""

import os
import math
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURAZIONE ALGOLIA
# ============================================================================

ALGOLIA_ENDPOINT = "https://search.webuy.io/1/indexes/*/queries"
ALGOLIA_APP_ID   = "LNNFEEWZVA"
# La API key viene letta dall'ambiente — mai hardcoded nel codice
# In locale: export ALGOLIA_API_KEY=bf79f2b6699e60a18ae330a1248b452c
# Su GitHub Actions: secret ALGOLIA_API_KEY
ALGOLIA_API_KEY  = os.environ.get("ALGOLIA_API_KEY", "")
ALGOLIA_INDEX    = "prod_cex_it_box_name_asc"

HITS_PER_PAGE = 1000   # massimo consentito da Algolia
REQUEST_PAUSE = 0.3    # secondi di cortesia tra richieste

HEADERS = {
    "Content-Type": "application/json",
    "Origin":       "https://it.webuy.com",
    "Referer":      "https://it.webuy.com/",
    "User-Agent":   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/26.3 Safari/605.1.15",
}

PRODUCT_URL = "https://it.webuy.com/product-detail/?id="

ATTRIBUTES_TO_RETRIEVE = [
    "boxId", "boxName", "sellPrice",
    "ecomQuantity", "collectionQuantity",
    "categoryFriendlyName", "categoryName",
    "superCatFriendlyName", "discontinued",
    "priceLastChanged", "rating",
]

# ============================================================================
# CONSOLE DA MONITORARE
# ============================================================================

CONSOLES_TO_TRACK = {
    "Xbox": [
        {"name": "Xbox",          "id": 1020},
        {"name": "Xbox 360",      "id": 827},
        {"name": "Xbox One",      "id": 1002},
        {"name": "Xbox CrossGen", "id": 1088},
        {"name": "Xbox Series",   "id": 1091},
    ],
    "PS4": [
        {"name": "PSP",  "id": 862},
        {"name": "PS4",  "id": 1001},
    ],
    "Wii": [
        {"name": "Wii",  "id": 831},
    ],
    "Switch": [
        {"name": "Switch", "id": 1037},
    ],
}


# ============================================================================
# FUNZIONI CORE
# ============================================================================

def fetch_page(
    session: requests.Session,
    category_id: int,
    offset: int = 0,
) -> Optional[Dict]:
    """
    Esegue una singola richiesta POST ad Algolia con offset.

    Args:
        session:     requests.Session riusabile
        category_id: ID categoria CEX
        offset:      Indice del primo risultato (0, 1000, 2000...)

    Returns:
        Dict con i risultati Algolia, oppure None in caso di errore
    """
    if not ALGOLIA_API_KEY:
        raise EnvironmentError(
            "ALGOLIA_API_KEY non trovata. "
            "Esegui: export ALGOLIA_API_KEY=bf79f2b6699e60a18ae330a1248b452c"
        )

    filters = (
        f"boxVisibilityOnWeb=1 AND boxSaleAllowed=1 "
        f"AND categoryId:{category_id}"
    )

    params_str = "&".join([
        f"attributesToRetrieve={','.join(ATTRIBUTES_TO_RETRIEVE)}",
        f"filters={filters}",
        f"hitsPerPage={HITS_PER_PAGE}",
        f"offset={offset}",
        "query=",
    ])

    payload = {
        "requests": [{"indexName": ALGOLIA_INDEX, "params": params_str}]
    }

    url = (
        f"{ALGOLIA_ENDPOINT}"
        f"?x-algolia-api-key={ALGOLIA_API_KEY}"
        f"&x-algolia-application-id={ALGOLIA_APP_ID}"
    )

    try:
        resp = session.post(url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()["results"][0]
    except requests.exceptions.Timeout:
        print(f"    ⚠️  Timeout (offset={offset})")
        return None
    except Exception as e:
        print(f"    ❌ Errore: {e}")
        return None


def parse_hit(hit: Dict, platform: str, console_group: str) -> Dict:
    """Converte un hit Algolia nel formato DatabaseManager."""
    box_id  = hit.get("boxId", "")
    buyable = (
        (hit.get("ecomQuantity") or 0) > 0
        or (hit.get("collectionQuantity") or 0) > 0
    )
    return {
        "Type":           "Videogame",
        "Platform":       platform,
        "Title":          hit.get("boxName", ""),
        "Price":          hit.get("sellPrice"),
        "Buyable":        buyable,
        "ID":             box_id,
        "URL":            f"{PRODUCT_URL}{box_id}",
        "_console_group": console_group,
    }


def scrape_category(
    session: requests.Session,
    category_name: str,
    category_id: int,
    console_group: str,
) -> List[Dict]:
    """
    Scarica TUTTI i prodotti di una categoria con il minimo di richieste.

    Logica:
    1. Prima richiesta (offset=0) → scopre nbHits totali
    2. Calcola quante richieste servono: ceil(nbHits / 1000)
    3. Richieste successive con offset=1000, 2000...
    """
    print(f"\n  🔍 {category_name} (id={category_id})...")

    result = fetch_page(session, category_id, offset=0)
    if result is None:
        print(f"    ❌ Impossibile contattare Algolia per {category_name}")
        return []

    nb_hits        = result.get("nbHits", 0)
    total_requests = math.ceil(nb_hits / HITS_PER_PAGE)

    print(f"    📊 {nb_hits} prodotti → {total_requests} richiesta/e")

    products = [parse_hit(h, category_name, console_group) for h in result.get("hits", [])]

    for i, offset in enumerate(range(HITS_PER_PAGE, nb_hits, HITS_PER_PAGE), start=2):
        time.sleep(REQUEST_PAUSE)
        print(f"    📄 Richiesta {i}/{total_requests} (offset={offset})...")

        result = fetch_page(session, category_id, offset=offset)
        if result is None:
            print(f"    ⚠️  Richiesta {i} saltata per errore")
            continue

        products.extend(
            parse_hit(h, category_name, console_group)
            for h in result.get("hits", [])
        )

    print(f"    ✅ {len(products)}/{nb_hits} prodotti scaricati")
    return products


def scrape_all_consoles() -> List[Dict]:
    """Entry point principale: scarica tutti i prodotti di tutte le console."""
    print("\n" + "=" * 60)
    print("🚀 CEX ALGOLIA SCRAPER - Avvio")
    print("=" * 60)
    print(f"⚡ Endpoint: {ALGOLIA_ENDPOINT}")
    print(f"📦 Console:  {', '.join(CONSOLES_TO_TRACK.keys())}")
    print("=" * 60)

    start_time   = datetime.now()
    all_products = []
    total_cats   = sum(len(cats) for cats in CONSOLES_TO_TRACK.values())
    processed    = 0

    with requests.Session() as session:
        for console_group, categories in CONSOLES_TO_TRACK.items():
            print(f"\n📦 Gruppo: {console_group}")
            for cat in categories:
                processed += 1
                print(f"\n  [{processed}/{total_cats}]", end="")
                products = scrape_category(
                    session=session,
                    category_name=cat["name"],
                    category_id=cat["id"],
                    console_group=console_group,
                )
                all_products.extend(products)
                if processed < total_cats:
                    time.sleep(REQUEST_PAUSE)

    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print(f"✅ Scraping completato!")
    print(f"⏱️  Tempo: {elapsed:.1f} secondi")
    print(f"🎮 Prodotti totali: {len(all_products)}")
    print("=" * 60 + "\n")

    return all_products


# ============================================================================
# TEST RAPIDO
# ============================================================================

if __name__ == "__main__":
    print("🧪 Test rapido — PS4 (categoryId=1001)...\n")

    with requests.Session() as session:
        products = scrape_category(
            session=session,
            category_name="PS4",
            category_id=1001,
            console_group="PS4",
        )

    disponibili = sum(1 for p in products if p["Buyable"])
    esauriti    = sum(1 for p in products if not p["Buyable"])

    print(f"\n✅ Prodotti PS4: {len(products)}")
    print(f"   Disponibili: {disponibili}")
    print(f"   Esauriti:    {esauriti}")
    if products:
        print(f"\n   Esempio: {products[0]['Title']} — €{products[0]['Price']}")
