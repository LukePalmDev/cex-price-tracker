#!/usr/bin/env python3
"""
CEX Price Tracker - Algolia Scraper
Sostituisce completamente Selenium usando l'API Algolia di WeBuy.

NOTA SUL LIMITE ALGOLIA:
Algolia impone un hard limit: (page * hitsPerPage) <= 1000.
Anche con offset, il totale non può superare 1000 per query.
L'unico modo per ottenere >1000 risultati da una categoria è
dividere in sottoinsiemi disgiunti che restano ognuno sotto 1000.

STRATEGIA:
- Categoria <= 1000 prodotti → 1 query sola
- Categoria >  1000 prodotti → 2 query disgiunte:
    query 1: disponibili  (inStockStore=1 OR inStockOnline=1)
    query 2: esauriti     (inStockStore=0 AND inStockOnline=0)
  Disponibili + esauriti = tutti i prodotti, senza sovrapposizioni.
  Entrambi i subset sono sempre abbondantemente sotto 1000.

Credenziali Algolia (pubbliche, estratte dal browser):
- Endpoint:   https://search.webuy.io
- App ID:     LNNFEEWZVA
- API Key:    variabile d'ambiente ALGOLIA_API_KEY

Uso:
    from algolia_scraper import scrape_all_consoles
    products = scrape_all_consoles()

Author: Claude
Version: 1.4 (aggiunge outOfStock, cashPriceCalculated, exchangePriceCalculated)
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
ALGOLIA_API_KEY  = os.environ.get("ALGOLIA_API_KEY", "")
ALGOLIA_INDEX    = "prod_cex_it_box_name_asc"

HITS_PER_PAGE = 1000   # massimo per query
REQUEST_PAUSE = 0.3    # secondi tra richieste

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
    "cashPriceCalculated", "exchangePriceCalculated",
    "ecomQuantity", "collectionQuantity",
    "outOfStock",
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
    "PlayStation": [
        {"name": "PS2",  "id": 824},
        {"name": "PS3",  "id": 1013},
        {"name": "PSP",  "id": 862},
        {"name": "PS4",  "id": 1001},
        {"name": "PS5",  "id": 1094},
    ],
    "Nintendo": [
        {"name": "GameCube", "id": 1029},
        {"name": "Wii",      "id": 831},
        {"name": "Wii U",    "id": 996},
        {"name": "DS",       "id": 834},
        {"name": "3DS",      "id": 977},
        {"name": "Switch",   "id": 1037},
    ],
}

# Filtri disponibilità
FILTER_AVAILABLE   = "(inStockStore=1 OR inStockOnline=1)"
FILTER_UNAVAILABLE = "(inStockStore=0 AND inStockOnline=0)"


# ============================================================================
# FUNZIONI CORE
# ============================================================================

def fetch_query(
    session: requests.Session,
    category_id: int,
    extra_filter: str = "",
) -> Optional[Dict]:
    """
    Esegue una singola richiesta POST ad Algolia.

    Args:
        session:      requests.Session riusabile
        category_id:  ID categoria CEX
        extra_filter: filtro aggiuntivo da appendere (es. disponibili/esauriti)

    Returns:
        Dict con i risultati Algolia, oppure None in caso di errore
    """
    if not ALGOLIA_API_KEY:
        raise EnvironmentError(
            "ALGOLIA_API_KEY non trovata.\n"
            "Esegui: export ALGOLIA_API_KEY=bf79f2b6699e60a18ae330a1248b452c"
        )

    base_filter = f"boxVisibilityOnWeb=1 AND boxSaleAllowed=1 AND categoryId:{category_id}"
    full_filter = f"{base_filter} AND {extra_filter}" if extra_filter else base_filter

    params_str = "&".join([
        f"attributesToRetrieve={','.join(ATTRIBUTES_TO_RETRIEVE)}",
        f"filters={full_filter}",
        f"hitsPerPage={HITS_PER_PAGE}",
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
        print(f"    ⚠️  Timeout")
        return None
    except Exception as e:
        print(f"    ❌ Errore: {e}")
        return None


def parse_hit(hit: Dict, platform: str, console_group: str) -> Dict:
    """Converte un hit Algolia nel formato DatabaseManager."""
    box_id         = hit.get("boxId", "")
    ecom_qty       = hit.get("ecomQuantity") or 0
    collection_qty = hit.get("collectionQuantity") or 0
    buyable        = ecom_qty > 0 or collection_qty > 0

    return {
        "Type":               "Videogame",
        "Platform":           platform,
        "Title":              hit.get("boxName", ""),
        "Price":              hit.get("sellPrice"),
        "CashPrice":          hit.get("cashPriceCalculated"),
        "ExchangePrice":      hit.get("exchangePriceCalculated"),
        "EcomQuantity":       ecom_qty,
        "CollectionQuantity": collection_qty,
        "OutOfStock":         hit.get("outOfStock") or [],   # lista negozi esauriti
        "Buyable":            buyable,
        "ID":                 box_id,
        "URL":                f"{PRODUCT_URL}{box_id}",
        "_console_group":     console_group,
    }


def scrape_category(
    session: requests.Session,
    category_name: str,
    category_id: int,
    console_group: str,
) -> List[Dict]:
    """
    Scarica TUTTI i prodotti di una categoria.

    Strategia automatica:
    - <= 1000 prodotti → 1 query (tutti insieme)
    - >  1000 prodotti → 2 query disgiunte: disponibili + esauriti
      I due subset non si sovrappongono mai e restano sempre sotto 1000.
    """
    print(f"\n  🔍 {category_name} (id={category_id})...")

    # Sonda iniziale: quanti prodotti ci sono?
    probe = fetch_query(session, category_id)
    if probe is None:
        print(f"    ❌ Impossibile contattare Algolia per {category_name}")
        return []

    nb_hits = probe.get("nbHits", 0)
    print(f"    📊 {nb_hits} prodotti totali")

    # --- Categoria piccola: query unica ---
    if nb_hits <= HITS_PER_PAGE:
        products = [parse_hit(h, category_name, console_group) for h in probe.get("hits", [])]
        print(f"    ✅ {len(products)} prodotti (query singola)")
        return products

    # --- Categoria grande: 2 query disgiunte ---
    print(f"    ⚡ >1000 prodotti → 2 query (disponibili + esauriti)")
    time.sleep(REQUEST_PAUSE)

    # Query 1: disponibili
    r_avail = fetch_query(session, category_id, FILTER_AVAILABLE)
    n_avail = r_avail.get("nbHits", 0) if r_avail else 0
    products_avail = [parse_hit(h, category_name, console_group)
                      for h in (r_avail.get("hits", []) if r_avail else [])]
    print(f"      → disponibili: {n_avail} prodotti")

    time.sleep(REQUEST_PAUSE)

    # Query 2: esauriti
    r_unavail = fetch_query(session, category_id, FILTER_UNAVAILABLE)
    n_unavail = r_unavail.get("nbHits", 0) if r_unavail else 0
    products_unavail = [parse_hit(h, category_name, console_group)
                        for h in (r_unavail.get("hits", []) if r_unavail else [])]
    print(f"      → esauriti:    {n_unavail} prodotti")

    products = products_avail + products_unavail
    print(f"    ✅ {len(products)}/{nb_hits} prodotti (attesi: {nb_hits})")

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
        p = products[0]
        print(f"\n   Esempio: {p['Title']} — €{p['Price']}")
        print(f"   Cash: €{p['CashPrice']} | Voucher: €{p['ExchangePrice']}")
        print(f"   OutOfStock stores: {p['OutOfStock'][:3]}")
