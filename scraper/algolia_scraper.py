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
- Categoria >  1000 prodotti → split ricorsivo su sellPrice
  (i filtri disponibile/esaurito non bastano: alcuni sottoinsiemi
  superano comunque 1000 e Algolia tronca i risultati in silenzio)

Credenziali Algolia:
- Endpoint:   https://search.webuy.io
- App ID:     LNNFEEWZVA
- API Key:    variabile d'ambiente ALGOLIA_API_KEY (secret GitHub Actions)

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
import json
import subprocess
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
REQUEST_PAUSE = 1.0    # secondi tra richieste (più prudente per evitare blocchi Cloudflare)
MAX_RETRIES   = 4      # tentativi per singola richiesta in caso di risposta vuota/errore
RETRY_BACKOFF = 2.0    # secondi di attesa iniziale tra retry (cresce: 2s, 4s, 8s...)

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

# ============================================================================
# ECCEZIONI
# ============================================================================

class ScrapeIncompleteError(Exception):
    """
    Sollevata quando una o più categorie non vengono scaricate correttamente
    (es. blocco Cloudflare). Serve come safety guard: impedisce a uno scraping
    parziale di sovrascrivere il dataset completo nel database/dashboard.
    """
    def __init__(self, failed_categories: List[str]):
        self.failed_categories = failed_categories
        super().__init__(
            f"Scraping incompleto: {len(failed_categories)} categorie fallite "
            f"({', '.join(failed_categories)})"
        )


# ============================================================================
# FUNZIONI CORE
# ============================================================================

def fetch_query(
    session: requests.Session,
    category_id: int,
    extra_filter: str = "",
    hits_per_page: int = HITS_PER_PAGE,
) -> Optional[Dict]:
    """
    Esegue una singola richiesta POST ad Algolia tramite curl.

    La chiave resta negli header della richiesta e non viene scritta
    nei messaggi di errore (l'eccezione di subprocess include gli argv).
    `session` è ignorato e tenuto per compatibilità con i chiamanti.
    """
    if not ALGOLIA_API_KEY:
        raise EnvironmentError(
            "ALGOLIA_API_KEY non trovata. Impostala nell'ambiente "
            "(su GitHub Actions: secret ALGOLIA_API_KEY)."
        )

    base_filter = f"boxVisibilityOnWeb=1 AND boxSaleAllowed=1 AND categoryId:{category_id}"
    full_filter = f"{base_filter} AND ({extra_filter})" if extra_filter else base_filter

    params_str = "&".join([
        f"attributesToRetrieve={','.join(ATTRIBUTES_TO_RETRIEVE)}",
        f"filters={full_filter}",
        f"hitsPerPage={hits_per_page}",
        "query=",
    ])

    payload = {
        "requests": [{"indexName": ALGOLIA_INDEX, "params": params_str}]
    }

    cmd = [
        "curl",
        "-s",
        "--max-time", "20",
        "-X", "POST",
        ALGOLIA_ENDPOINT,
        "-H", "Content-Type: application/json",
        "-H", "Origin: https://it.webuy.com",
        "-H", "Referer: https://it.webuy.com/",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-H", f"X-Algolia-Application-Id: {ALGOLIA_APP_ID}",
        "-H", f"X-Algolia-API-Key: {ALGOLIA_API_KEY}",
        "-d", json.dumps(payload),
    ]

    # Retry con backoff esponenziale: Cloudflare può bloccare richieste
    # ravvicinate restituendo un corpo vuoto. Riproviamo prima di arrenderci.
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=True)
            if not result.stdout.strip():
                raise ValueError("risposta vuota")
            resp_data = json.loads(result.stdout)
            if "results" not in resp_data:
                raise ValueError(resp_data.get("message") or "risposta Algolia senza risultati")
            return resp_data["results"][0]
        except subprocess.TimeoutExpired:
            last_err = "timeout"
        except subprocess.CalledProcessError as e:
            last_err = f"curl exit {e.returncode}"
        except json.JSONDecodeError:
            last_err = "risposta non JSON"
        except ValueError as e:
            last_err = str(e)
        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF * (2 ** (attempt - 1))
            print(f"    ⏳ Tentativo {attempt}/{MAX_RETRIES} fallito ({last_err}); riprovo tra {wait:.0f}s...")
            time.sleep(wait)

    print(f"    ❌ Errore curl dopo {MAX_RETRIES} tentativi: {last_err}")
    return None


def _dedupe_hits(hits: List[Dict]) -> List[Dict]:
    """Tiene un solo hit per boxId (l'ultimo visto)."""
    by_id: Dict[str, Dict] = {}
    order: List[str] = []
    for hit in hits:
        box_id = str(hit.get("boxId") or "")
        key = box_id or f"anon:{len(order)}"
        if key not in by_id:
            order.append(key)
        by_id[key] = hit
    return [by_id[k] for k in order]


def _price_pivot(session: requests.Session, category_id: int, extra_filter: str, total: int) -> Optional[float]:
    """Trova un prezzo che spezza il risultato in due parti non vuote."""
    lo, hi = 0.0, 2000.0
    best = None
    best_balance = None
    for _ in range(14):
        mid = round((lo + hi) / 2, 2)
        if mid <= lo or mid >= hi:
            break
        clause = f"sellPrice < {mid:.2f}"
        probe_filter = f"{extra_filter} AND {clause}" if extra_filter else clause
        probe = fetch_query(session, category_id, probe_filter, hits_per_page=0)
        if probe is None:
            return best
        left = int(probe.get("nbHits") or 0)
        if 0 < left < total:
            balance = abs(left - (total / 2))
            if best is None or balance < best_balance:
                best = mid
                best_balance = balance
            if left < total / 2:
                lo = mid
            else:
                hi = mid
            if left <= HITS_PER_PAGE and (total - left) <= HITS_PER_PAGE:
                return mid
        elif left == 0:
            lo = mid
        else:
            hi = mid
        time.sleep(0.25)
    return best


def fetch_all_hits(
    session: requests.Session,
    category_id: int,
    extra_filter: str = "",
    _depth: int = 0,
) -> Optional[List[Dict]]:
    """
    Scarica tutti gli hit di un filtro, spezzando su sellPrice se superano
    il limite Algolia di 1000. Ritorna None se una richiesta fallisce o lo
    split non copre nbHits (così il chiamante può abortire senza perdere dati).
    """
    if _depth > 12:
        print("    ❌ Split prezzo troppo profondo")
        return None

    result = fetch_query(session, category_id, extra_filter)
    if result is None:
        return None

    total = int(result.get("nbHits") or 0)
    hits = result.get("hits") or []
    if total <= HITS_PER_PAGE:
        if len(hits) < total:
            print(f"    ❌ Risposta parziale: {len(hits)}/{total}")
            return None
        return hits

    pivot = _price_pivot(session, category_id, extra_filter, total)
    if pivot is None:
        print(f"    ❌ Impossibile dividere {total} risultati (filtro: {extra_filter or 'tutti'})")
        return None

    print(f"    ↳ {total} > {HITS_PER_PAGE}, split su sellPrice {pivot:.2f}")
    time.sleep(REQUEST_PAUSE)
    left_filter = f"sellPrice < {pivot:.2f}"
    right_filter = f"sellPrice >= {pivot:.2f}"
    if extra_filter:
        left_filter = f"{extra_filter} AND {left_filter}"
        right_filter = f"{extra_filter} AND {right_filter}"

    left = fetch_all_hits(session, category_id, left_filter, _depth + 1)
    if left is None:
        return None
    time.sleep(REQUEST_PAUSE)
    right = fetch_all_hits(session, category_id, right_filter, _depth + 1)
    if right is None:
        return None

    merged = _dedupe_hits(left + right)
    if len(merged) < total:
        print(f"    ❌ Split incompleto: {len(merged)}/{total}")
        return None
    return merged


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
    Scarica tutti i prodotti di una categoria.

    Sopra i 1000 risultati Algolia tronca la risposta: lo split ricorsivo
    su sellPrice recupera il catalogo intero invece di perderne una coda.
    """
    print(f"\n  🔍 {category_name} (id={category_id})...")

    hits = fetch_all_hits(session, category_id)
    if hits is None:
        print(f"    ❌ Impossibile scaricare {category_name} per intero")
        raise ScrapeIncompleteError([category_name])

    products = [parse_hit(h, category_name, console_group) for h in hits]
    deduped = {}
    for product in products:
        deduped[product.get("ID") or id(product)] = product
    products = list(deduped.values())
    print(f"    ✅ {len(products)} prodotti")
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
    failed_cats  = []
    total_cats   = sum(len(cats) for cats in CONSOLES_TO_TRACK.values())
    processed    = 0

    with requests.Session() as session:
        for console_group, categories in CONSOLES_TO_TRACK.items():
            print(f"\n📦 Gruppo: {console_group}")
            for cat in categories:
                processed += 1
                print(f"\n  [{processed}/{total_cats}]", end="")
                try:
                    products = scrape_category(
                        session=session,
                        category_name=cat["name"],
                        category_id=cat["id"],
                        console_group=console_group,
                    )
                    all_products.extend(products)
                except ScrapeIncompleteError as e:
                    # Accumula e prosegui, così a fine ciclo abbiamo l'elenco completo
                    failed_cats.extend(e.failed_categories)
                if processed < total_cats:
                    time.sleep(REQUEST_PAUSE)

    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print(f"✅ Scraping completato!")
    print(f"⏱️  Tempo: {elapsed:.1f} secondi")
    print(f"🎮 Prodotti totali: {len(all_products)}")
    print("=" * 60 + "\n")

    # SAFETY GUARD: se anche una sola categoria è fallita, lo scraping è
    # incompleto. Solleviamo l'eccezione per impedire che dati parziali
    # sovrascrivano il dataset completo in database/dashboard.
    if failed_cats:
        raise ScrapeIncompleteError(failed_cats)

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
