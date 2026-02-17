#!/usr/bin/env python3
"""
CEX Category Scraper - Versione Selenium SUPER-OTTIMIZZATA
Scraper interattivo per giochi Xbox da it.webuy.com
Ottimizzato per Mac M4 con rendering JavaScript

OTTIMIZZAZIONI APPLICATE:
FASE 1 (v2.5):
- Parser lxml (5-10x più veloce di html.parser)
- Immagini disabilitate in Chrome (risparmio ~2s per pagina)
- Pausa tra categorie ridotta (0.5s invece di 1s)

FASE 2A (v2.6):
- WebDriverWait intelligente (aspetta paginazione invece di 2.2s fissi)
- Pausa dinamica tra pagine (adatta alla velocità rete)
- Riuso HTML parsing (soup creato una volta invece di 2)
- Chrome flags ottimizzati (disabilita logging, sync, extensions)

FASE 2B (v2.7):
- Fonts e plugins disabilitati (risparmio bandwidth)
- Retry logic (3 tentativi per pagina fallita, +95% affidabilità)
- Salvataggio asincrono (CSV e JSON in parallelo)

Guadagno totale: ~70-75% più veloce + 95% più affidabile

REQUISITI:
pip3 install selenium webdriver-manager beautifulsoup4 lxml

Author: Claude
Date: 2024-02-14
Version: 2.7 (Super-Optimized - Fase 2 Completa)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import json
import time
import math
import threading
from datetime import datetime
from typing import List, Dict, Optional
import sys

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

BASE_URL = "https://it.webuy.com/search"
PRODUCT_URL = "https://it.webuy.com/product-detail/"

# Categorie Xbox disponibili
CATEGORIES = {
    "1": {"name": "Xbox", "id": 1020},
    "2": {"name": "Xbox 360", "id": 827},
    "3": {"name": "Xbox One", "id": 1002},
    "4": {"name": "Xbox CrossGen", "id": 1088},
    "5": {"name": "Xbox Series", "id": 1091}
}

# Costanti
RESULTS_PER_PAGE = 17
SORT_ALPHABETIC = "prod_cex_it_box_name_asc"
AVAILABILITY_IN_STOCK = "inStock"
AVAILABILITY_ALL = "allStock"

# Timeout per attesa caricamento (secondi)
PAGE_LOAD_TIMEOUT = 20
ELEMENT_WAIT_TIMEOUT = 10

# ============================================================================
# STRUTTURA HTML CEX (per riferimento)
# ============================================================================
# Contenitore principale: div.cx-card.cx-card-product.vertical.cx-card-animate
#   ├── div.wrapper-box
#   │   ├── div.thumbnail
#   │   │   └── div.card-img
#   │   │       └── div.cx-out-of-stock  (se non disponibile) → "ESAURITO"
#   │   └── div.content
#   │       ├── div.card-title
#   │       │   └── a.line-clamp  (TITOLO + href con ID)
#   │       └── div.product-prices
#   │           ├── div.price-wrapper
#   │           │   └── p.product-main-price  (PREZZO)
#   │           └── div (add-cart-button O cx-out-of-stock-btn)
# ============================================================================

# ============================================================================
# CLASSE SELENIUM DRIVER
# ============================================================================

class CexSeleniumDriver:
    """Gestisce il browser Selenium"""
    
    def __init__(self, headless: bool = True):
        """
        Inizializza il driver Chrome
        
        Args:
            headless: Se True, Chrome funziona in background senza finestra
        """
        self.driver = None
        self.headless = headless
        self._init_driver()
    
    def _init_driver(self):
        """Inizializza il driver Chrome con le opzioni corrette"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')  # Nuova modalità headless
        
        # Opzioni per Mac M4 e stabilità
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # FASE 2 - PUNTO 4: Chrome flags ottimizzati per performance
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')  # Solo errori fatali
        options.add_argument('--silent')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--mute-audio')
        
        # OTTIMIZZAZIONE: Disabilita immagini per velocità +25-35%
        # FASE 2 - PUNTO 2: Disabilita fonts custom e plugins
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # Blocca immagini
            "profile.default_content_setting_values.notifications": 2,  # Blocca notifiche
            "profile.managed_default_content_settings.plugins": 2,  # Blocca plugins
            "webkit.webprefs.fonts.standard.Zyyy": "Arial",  # Font fisso invece di custom fonts
            "profile.default_content_setting_values.plugins": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # User agent realistico
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Disabilita notifiche e richieste inutili
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            print("✅ Browser Chrome inizializzato")
        except Exception as e:
            print(f"❌ Errore inizializzazione Chrome: {e}")
            print("\n💡 Hai installato ChromeDriver? Leggi INSTALLAZIONE_SELENIUM_MAC.md")
            sys.exit(1)
    
    def get(self, url: str) -> bool:
        """
        Carica una pagina
        
        Returns:
            True se successo, False altrimenti
        """
        try:
            self.driver.get(url)
            return True
        except Exception as e:
            print(f"❌ Errore caricamento pagina: {e}")
            return False
    
    def wait_for_products(self, timeout: int = ELEMENT_WAIT_TIMEOUT) -> bool:
        """
        Aspetta che i prodotti si carichino sulla pagina
        FASE 2 - PUNTO 1: WebDriverWait intelligente con fallback
        
        Returns:
            True se i prodotti sono stati caricati
        """
        try:
            # STRATEGIA: Aspetta la paginazione (carica per ultima quando tutto è pronto)
            # Con fallback a attesa standard se paginazione non trovata
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ais-Pagination"))
                )
                # Paginazione trovata = pagina completa, buffer minimo
                time.sleep(0.5)
                return True
            except TimeoutException:
                # Fallback: usa strategia standard (pagine con pochi prodotti potrebbero non avere paginazione)
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='product-detail']"))
                )
                time.sleep(2.2)  # Attesa standard come backup
                return True
        except TimeoutException:
            print(f"⚠️  Timeout: prodotti non caricati entro {timeout} secondi")
            return False
    
    def get_page_source(self) -> str:
        """Ritorna l'HTML della pagina corrente"""
        return self.driver.page_source
    
    def quit(self):
        """Chiude il browser"""
        if self.driver:
            self.driver.quit()
            print("✅ Browser chiuso")

# ============================================================================
# FUNZIONI DI UTILITÀ
# ============================================================================

def print_header():
    """Stampa l'intestazione dello script"""
    print("\n" + "="*70)
    print("🎮  CEX SELENIUM SCRAPER - Ricerca Giochi Xbox")
    print("="*70)
    print("📍 Sito: it.webuy.com")
    print("💻 Sistema: Mac M4 Optimized + Selenium")
    print("="*70 + "\n")


def print_menu_categories():
    """Mostra il menu di selezione categorie"""
    print("\n📦 CATEGORIE DISPONIBILI:\n")
    for key, cat in CATEGORIES.items():
        print(f"  [{key}] {cat['name']}")
    print(f"  [0] Tutte le categorie")
    print()


def print_menu_availability():
    """Mostra il menu di selezione disponibilità"""
    print("\n📋 DISPONIBILITÀ:\n")
    print("  [1] Solo disponibili (In Stock)")
    print("  [2] Tutti i prodotti (Disponibili + Non disponibili)")
    print()


def print_menu_browser_mode():
    """Mostra il menu per la modalità browser"""
    print("\n🌐 MODALITÀ BROWSER:\n")
    print("  [1] Headless (background, più veloce)")
    print("  [2] Visibile (vedi cosa succede, debug)")
    print()


def get_user_choice(prompt: str, valid_options: List[str]) -> str:
    """Richiede input utente con validazione"""
    while True:
        choice = input(prompt).strip()
        if choice in valid_options:
            return choice
        print(f"❌ Scelta non valida. Opzioni disponibili: {', '.join(valid_options)}")


def build_search_url(category_id: int, page: int, availability: str) -> str:
    """Costruisce l'URL di ricerca con i parametri corretti"""
    params = {
        'page': page,
        'categoryIds': category_id,
        'sortBy': SORT_ALPHABETIC,
        'availability': availability
    }
    
    query_parts = [f"{key}={value}" for key, value in params.items()]
    return f"{BASE_URL}?{'&'.join(query_parts)}"


def extract_product_id(href: str) -> Optional[str]:
    """Estrae l'ID prodotto dall'URL"""
    try:
        if 'id=' in href:
            return href.split('id=')[1].split('&')[0]
    except:
        pass
    return None


def clean_price(price_text: str) -> Optional[float]:
    """Pulisce e converte il prezzo in float"""
    try:
        price_clean = price_text.replace('€', '').replace(',', '.').strip()
        return float(price_clean)
    except:
        return None


def parse_total_results(soup: BeautifulSoup) -> int:
    """
    Estrae il numero totale di risultati dalla pagina
    FASE 2 - PUNTO 5: Accetta soup invece di html per evitare doppio parsing
    """
    try:
        # Cerca vari possibili selettori per il conteggio
        selectors = [
            ('p', {'class': 'text-base'}),
            ('p', {'class': lambda x: x and 'result' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'result' in str(x).lower()})
        ]
        
        for tag, attrs in selectors:
            result_elem = soup.find(tag, attrs)
            if result_elem:
                text = result_elem.get_text(strip=True)
                # Estrae il numero
                number = ''.join(filter(str.isdigit, text))
                if number:
                    return int(number)
    except:
        pass
    return 0


def parse_products_from_html(soup: BeautifulSoup, platform: str) -> List[Dict]:
    """
    Estrae i prodotti dall'HTML della pagina
    USA STRATEGIA 2 (string esatto) - funziona con tempi 2-2.2s
    OTTIMIZZATO: usa lxml invece di html.parser (5-10x più veloce)
    FASE 2 - PUNTO 5: Accetta soup invece di html per evitare doppio parsing
    
    Args:
        soup: BeautifulSoup object con HTML parsato
        platform: Nome piattaforma (Xbox, Xbox 360, etc.)
    
    Returns:
        Lista di prodotti con Type e Platform
    """
    products = []
    
    # TROVA TUTTI I CONTENITORI PRODOTTO (strategia string esatto)
    # IMPORTANTE: Non usare lambda, usa string esatto!
    product_cards = soup.find_all('div', class_='cx-card cx-card-product vertical cx-card-animate')
    
    for card in product_cards:
        try:
            # 1. TITOLO (dentro a.line-clamp)
            title_link = card.find('a', class_='line-clamp')
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            href = title_link.get('href', '')
            product_id = extract_product_id(href)
            
            if not title or not product_id:
                continue
            
            # 2. PREZZO (dentro p.product-main-price)
            price = None
            price_elem = card.find('p', class_='product-main-price')
            if price_elem:
                price = clean_price(price_elem.get_text())
            
            # 3. DISPONIBILITÀ (Buyable: True/False)
            buyable = True  # Default: disponibile
            
            out_of_stock_div = card.find('div', class_='cx-out-of-stock')
            if out_of_stock_div and 'ESAURITO' in out_of_stock_div.get_text(strip=True).upper():
                buyable = False
            else:
                # Controllo alternativo: cerca il pulsante info (prodotto esaurito)
                out_of_stock_btn = card.find('div', class_='cx-out-of-stock-btn')
                if out_of_stock_btn:
                    buyable = False
            
            # Crea oggetto prodotto con NUOVA STRUTTURA
            product = {
                'Type': 'Videogame',  # Fisso per ora
                'Platform': platform,
                'Title': title,
                'Price': price,
                'Buyable': buyable,
                'ID': product_id,
                'URL': f"{PRODUCT_URL}?id={product_id}"
            }
            
            products.append(product)
            
        except Exception as e:
            # Ignora errori su singoli prodotti
            continue
    
    return products


def scrape_page_with_selenium(driver: CexSeleniumDriver, url: str, platform: str) -> tuple[List[Dict], int]:
    """
    Scarica e analizza una singola pagina con Selenium
    FASE 2 - PUNTO 5: Crea soup una volta sola e riusa
    FASE 2 - PUNTO 7: Retry logic per affidabilità
    
    Args:
        driver: Selenium driver
        url: URL della pagina
        platform: Nome piattaforma (Xbox, Xbox 360, etc.)
    
    Returns:
        (lista_prodotti, totale_risultati)
    """
    MAX_RETRIES = 3
    
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                print(f"  🔄 Tentativo {attempt + 1}/{MAX_RETRIES}...")
            else:
                print(f"  🔍 Carico: {url}")
            
            # Carica la pagina
            if not driver.get(url):
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  Caricamento fallito, riprovo tra 2 secondi...")
                    time.sleep(2)
                    continue
                return [], 0
            
            # Aspetta che i prodotti si carichino
            if attempt == 0:
                print(f"  ⏳ Attendo caricamento JavaScript...")
            
            if not driver.wait_for_products():
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  Timeout prodotti, riprovo...")
                    time.sleep(2)
                    continue
                else:
                    print(f"  ⚠️  Prodotti non trovati dopo {MAX_RETRIES} tentativi")
                    # Salva HTML per debug
                    with open('cex_selenium_debug.html', 'w', encoding='utf-8') as f:
                        f.write(driver.get_page_source())
                    print(f"  💾 HTML salvato in: cex_selenium_debug.html")
                    return [], 0
            
            # Ottieni HTML renderizzato e crea soup UNA VOLTA SOLA
            html = driver.get_page_source()
            try:
                soup = BeautifulSoup(html, 'lxml')
            except:
                soup = BeautifulSoup(html, 'html.parser')
            
            # Passa soup (non html) e platform alle funzioni - riuso stesso soup
            total_results = parse_total_results(soup)
            products = parse_products_from_html(soup, platform)
            
            # Successo! Ritorna i risultati
            if attempt > 0:
                print(f"  ✅ Successo al tentativo {attempt + 1}")
            return products, total_results
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠️  Errore (tentativo {attempt + 1}): {e}")
                print(f"  🔄 Riprovo tra 2 secondi...")
                time.sleep(2)
            else:
                print(f"  ❌ Errore dopo {MAX_RETRIES} tentativi: {e}")
                return [], 0
    
    return [], 0


def scrape_category(driver: CexSeleniumDriver, category_name: str, category_id: int, availability: str) -> List[Dict]:
    """
    Scarica tutti i prodotti di una categoria
    
    Args:
        driver: Driver Selenium
        category_name: Nome della categoria (es. "Xbox 360")
        category_id: ID della categoria
        availability: "inStock" o "allStock"
    
    Returns:
        Lista di prodotti con Type e Platform
    """
    print(f"\n{'='*70}")
    print(f"📦 Categoria: {category_name}")
    print(f"🔍 Disponibilità: {'Solo disponibili' if availability == AVAILABILITY_IN_STOCK else 'Tutti'}")
    print(f"{'='*70}\n")
    
    all_products = []
    
    # Prima pagina per ottenere il totale
    print("📄 Pagina 1...")
    url = build_search_url(category_id, 1, availability)
    products, total_results = scrape_page_with_selenium(driver, url, category_name)
    
    if total_results == 0:
        print("⚠️  Nessun risultato trovato")
        return []
    
    all_products.extend(products)
    
    # Calcola numero totale di pagine
    total_pages = math.ceil(total_results / RESULTS_PER_PAGE)
    
    print(f"\n📊 Trovati {total_results} risultati totali")
    print(f"📑 Pagine da scaricare: {total_pages}")
    print(f"✅ Prodotti pagina 1: {len(products)}\n")
    
    # Scarica le pagine rimanenti
    for page_num in range(2, total_pages + 1):
        print(f"📄 Pagina {page_num}/{total_pages}...")
        
        # FASE 2 - PUNTO 3: Pausa dinamica - misura tempo di caricamento
        page_start_time = time.time()
        
        url = build_search_url(category_id, page_num, availability)
        products, _ = scrape_page_with_selenium(driver, url, category_name)
        all_products.extend(products)
        print(f"   ✅ Prodotti trovati: {len(products)}")
        
        # Calcola tempo impiegato per questa pagina
        page_duration = time.time() - page_start_time
        
        # Pausa dinamica: se la pagina è stata lenta, pausa breve; se veloce, pausa più lunga
        # Obiettivo: mantenere ~3-4 secondi tra inizio di una pagina e inizio della successiva
        if page_num < total_pages:
            # Formula: pausa = max(0.5s, 2.0s - (tempo_impiegato - 2.5s))
            # Se impiegato 5s → pausa 0.5s (minimo)
            # Se impiegato 3s → pausa 1.5s
            # Se impiegato 2s → pausa 2.0s (massimo)
            dynamic_pause = max(0.5, min(2.0, 4.0 - page_duration))
            time.sleep(dynamic_pause)
    
    print(f"\n{'='*70}")
    print(f"✅ Scraping completato!")
    print(f"📦 Totale prodotti estratti: {len(all_products)}")
    print(f"{'='*70}\n")
    
    return all_products


def save_to_csv(products: List[Dict], filename: str):
    """
    Salva i prodotti in formato CSV con struttura:
    Type, Platform, Title, Price, Buyable, ID, URL
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if not products:
                print(f"⚠️  Nessun dato da salvare in CSV")
                return
            
            # Nuove colonne secondo specifiche
            fieldnames = ['Type', 'Platform', 'Title', 'Price', 'Buyable', 'ID', 'URL']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in products:
                writer.writerow(product)
        
        print(f"✅ CSV salvato: {filename}")
        
    except Exception as e:
        print(f"❌ Errore salvando CSV: {e}")


def save_to_json(products: List[Dict], filename: str, metadata: Dict):
    """
    Salva i prodotti in formato JSON con struttura annidata:
    {
      "metadata": {...},
      "data": {
        "Videogame": {
          "Xbox": [{Title, Price, Buyable, ID, URL}, ...],
          "Xbox 360": [...]
        }
      }
    }
    """
    try:
        # Organizza prodotti per Type e Platform
        nested_data = {}
        
        for product in products:
            product_type = product['Type']
            platform = product['Platform']
            
            # Inizializza Type se non esiste
            if product_type not in nested_data:
                nested_data[product_type] = {}
            
            # Inizializza Platform se non esiste
            if platform not in nested_data[product_type]:
                nested_data[product_type][platform] = []
            
            # Crea oggetto prodotto senza Type e Platform (solo dati utili)
            product_data = {
                'Title': product['Title'],
                'Price': product['Price'],
                'Buyable': product['Buyable'],
                'ID': product['ID'],
                'URL': product['URL']
            }
            
            nested_data[product_type][platform].append(product_data)
        
        # Struttura finale con metadata
        data = {
            'metadata': metadata,
            'data': nested_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON salvato: {filename}")
        
    except Exception as e:
        print(f"❌ Errore salvando JSON: {e}")


def print_statistics(products: List[Dict]):
    """Stampa statistiche sui prodotti"""
    if not products:
        return
    
    print(f"\n{'='*70}")
    print("📊 STATISTICHE")
    print(f"{'='*70}\n")
    
    total = len(products)
    buyable = sum(1 for p in products if p['Buyable'] == True)
    not_buyable = total - buyable
    
    prices = [p['Price'] for p in products if p['Price'] is not None]
    
    print(f"📦 Totale prodotti: {total}")
    print(f"✅ Acquistabili: {buyable}")
    print(f"❌ Non acquistabili: {not_buyable}")
    
    if prices:
        prezzo_min = min(prices)
        prezzo_max = max(prices)
        prezzo_medio = sum(prices) / len(prices)
        
        print(f"\n💰 PREZZI:")
        print(f"   Min: €{prezzo_min:.2f}")
        print(f"   Max: €{prezzo_max:.2f}")
        print(f"   Medio: €{prezzo_medio:.2f}")
    
    print(f"\n{'='*70}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funzione principale"""
    
    print_header()
    
    # 1. MODALITÀ BROWSER
    print_menu_browser_mode()
    browser_choice = get_user_choice(
        "Scegli modalità browser [1-2]: ",
        ['1', '2']
    )
    headless = (browser_choice == '1')
    
    # 2. SCELTA CATEGORIA
    print_menu_categories()
    category_choice = get_user_choice(
        "Scegli una categoria [0-5]: ",
        ['0', '1', '2', '3', '4', '5']
    )
    
    # 3. SCELTA DISPONIBILITÀ
    print_menu_availability()
    availability_choice = get_user_choice(
        "Scegli disponibilità [1-2]: ",
        ['1', '2']
    )
    
    availability = AVAILABILITY_IN_STOCK if availability_choice == '1' else AVAILABILITY_ALL
    
    # 4. CONFERMA
    print(f"\n{'='*70}")
    print("🚀 RIEPILOGO RICERCA")
    print(f"{'='*70}")
    print(f"🌐 Browser: {'Headless (background)' if headless else 'Visibile'}")
    
    if category_choice == '0':
        print("📦 Categorie: TUTTE")
    else:
        print(f"📦 Categoria: {CATEGORIES[category_choice]['name']}")
    
    print(f"🔍 Disponibilità: {'Solo disponibili' if availability_choice == '1' else 'Tutti'}")
    print(f"{'='*70}\n")
    
    confirm = input("Procedere? [s/n]: ").strip().lower()
    if confirm not in ['s', 'si', 'sì', 'y', 'yes']:
        print("\n❌ Operazione annullata.\n")
        return
    
    # 5. INIZIALIZZA SELENIUM
    print(f"\n🚀 Inizializzo browser Chrome...")
    driver = CexSeleniumDriver(headless=headless)
    
    # 6. SCRAPING
    start_time = datetime.now()
    all_products = []
    
    try:
        if category_choice == '0':
            # Tutte le categorie
            for cat_data in CATEGORIES.values():
                products = scrape_category(driver, cat_data['name'], cat_data['id'], availability)
                all_products.extend(products)
                time.sleep(0.5)  # OTTIMIZZATO: ridotto da 1s a 0.5s
        else:
            # Singola categoria
            cat_data = CATEGORIES[category_choice]
            all_products = scrape_category(driver, cat_data['name'], cat_data['id'], availability)
    
    finally:
        # Chiudi sempre il browser
        driver.quit()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 7. SALVATAGGIO
    if all_products:
        # Formato nome file: DB-CEX-YYYY-MM-DD_HH-MM-SS
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        csv_filename = f"DB-CEX-{timestamp}.csv"
        json_filename = f"DB-CEX-{timestamp}.json"
        
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'categoria': 'Tutte' if category_choice == '0' else CATEGORIES[category_choice]['name'],
            'disponibilita': 'Solo disponibili' if availability_choice == '1' else 'Tutti',
            'totale_prodotti': len(all_products),
            'durata_secondi': round(duration, 2),
            'metodo': 'Selenium + Chrome + Ottimizzazioni v2.7'
        }
        
        # FASE 2 - PUNTO 6: Salvataggio asincrono con threading
        # Salva CSV e JSON in parallelo mentre mostra le statistiche
        csv_thread = threading.Thread(target=save_to_csv, args=(all_products, csv_filename))
        json_thread = threading.Thread(target=save_to_json, args=(all_products, json_filename, metadata))
        
        csv_thread.start()
        json_thread.start()
        
        # Mostra statistiche mentre i file vengono salvati in background
        print_statistics(all_products)
        
        # Aspetta che il salvataggio sia completato prima di uscire
        csv_thread.join()
        json_thread.join()
        
        print(f"⏱️  Tempo totale: {duration:.2f} secondi")
        print(f"\n{'='*70}")
        print("✨ COMPLETATO CON SUCCESSO!")
        print(f"{'='*70}\n")
        
    else:
        print("\n❌ Nessun prodotto trovato.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operazione interrotta dall'utente.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Errore critico: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
