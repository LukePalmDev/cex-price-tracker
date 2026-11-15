/**
 * Stato filtri della dashboard: parsing/serializzazione della query string
 * e regole di disponibilità per negozio.
 *
 * Un titolo è in stock in un negozio quando `is_available` è truthy e
 * l'id del negozio non compare in `out_of_stock_stores`. È la stessa regola
 * del filtro singolo precedente.
 *
 * I 12 id sono quelli presenti in dashboard/data/games.json.
 * "Milano Merlata Bloom" nel testo dell'interfaccia corrisponde all'id
 * "Merlata Bloom". "Reggio Emilia San Pietro" coincide con l'id nel dato.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.CexFilters = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STORE_CATALOG = [
    { id: 'Bologna Amendola', label: 'Bologna Amendola', abbr: 'B.A.' },
    { id: 'Bologna San Felice', label: 'Bologna San Felice', abbr: 'B.S.F.' },
    { id: 'Gran Roma', label: 'Gran Roma', abbr: 'R.G.' },
    { id: 'IT Ecommerce', label: 'IT Ecommerce', abbr: 'Ecom' },
    { id: 'La Romanina', label: 'La Romanina', abbr: 'R.L.' },
    { id: 'Le Corti Venete', label: 'Le Corti Venete', abbr: 'L.C.V.' },
    { id: 'Merlata Bloom', label: 'Milano Merlata Bloom', abbr: 'Merlata' },
    { id: 'Milano Viale Tunisia', label: 'Milano Viale Tunisia', abbr: 'M.' },
    { id: 'Parma Repubblica', label: 'Parma Repubblica', abbr: 'P.' },
    { id: 'Reggio Emilia San Pietro', label: 'Reggio Emilia San Pietro', abbr: 'Reggio' },
    { id: 'RMA CENTRE', label: 'RMA Centre', abbr: 'RMA' },
    { id: 'The Wow Side', label: 'The Wow Side', abbr: 'R.W.' },
  ];

  const STORE_PRESETS = [
    { id: 'merlata', label: 'Milano Merlata Bloom', stores: ['Merlata Bloom'] },
    { id: 'reggio', label: 'Reggio Emilia San Pietro', stores: ['Reggio Emilia San Pietro'] },
    { id: 'miei', label: 'I miei negozi', stores: ['Merlata Bloom', 'Reggio Emilia San Pietro'] },
  ];

  const STORE_BY_ID = new Map(STORE_CATALOG.map(store => [store.id, store]));
  const STORE_IDS = STORE_CATALOG.map(store => store.id);

  const CONSOLES = [
    'Xbox', 'Xbox 360', 'Xbox One', 'Xbox CrossGen', 'Xbox Series',
    'PS2', 'PS3', 'PSP', 'PS4', 'PS5',
    'GameCube', 'Wii', 'Wii U', 'DS', '3DS', 'Switch',
  ];
  const CONSOLE_SET = new Set(CONSOLES);

  const SORT_KEYS = ['title', 'console', 'current_price', 'price_trend_pct', 'is_available'];
  const SORT_SET = new Set(SORT_KEYS);

  const QUERY_MAX = 200;
  const PRICE_MAX = 100000;
  const PAGE_MAX = 100000;

  function cleanQuery(raw) {
    return String(raw ?? '').replace(/[\u0000-\u001F\u007F]/g, '').trim().slice(0, QUERY_MAX);
  }

  function normalizeConsole(value) {
    const name = String(value ?? '');
    return CONSOLE_SET.has(name) ? name : '';
  }

  function normalizeAvail(value) {
    return value === '0' || value === '1' ? value : '';
  }

  function normalizeTrend(value) {
    return value === 'down' || value === 'up' ? value : '';
  }

  function normalizeSort(value) {
    const key = String(value ?? '');
    return SORT_SET.has(key) ? key : 'title';
  }

  function splitStores(raw) {
    if (raw == null || raw === '') return [];
    return String(raw).split(',');
  }

  function normalizeStores(ids) {
    const wanted = new Set();
    const list = Array.isArray(ids) ? ids : splitStores(ids);
    list.forEach(value => {
      const id = String(value ?? '').trim();
      if (STORE_BY_ID.has(id)) wanted.add(id);
    });
    return STORE_CATALOG.filter(store => wanted.has(store.id)).map(store => store.id);
  }

  function parsePrice(raw) {
    if (raw == null) return null;
    if (typeof raw === 'number') {
      if (!Number.isFinite(raw) || raw < 0 || raw > PRICE_MAX) return null;
      return Math.round(raw * 100) / 100;
    }
    let text = String(raw).trim().replace(',', '.');
    if (text === '') return null;
    if (!/^\d+(\.\d{0,2})?$/.test(text)) return null;
    if (text.endsWith('.')) text = text.slice(0, -1);
    if (text === '') return null;
    const value = Number(text);
    if (!Number.isFinite(value) || value < 0 || value > PRICE_MAX) return null;
    return Math.round(value * 100) / 100;
  }

  function formatPrice(value) {
    const rounded = Math.round(Number(value) * 100) / 100;
    return String(rounded);
  }

  function parsePage(raw) {
    if (typeof raw === 'number') {
      if (!Number.isSafeInteger(raw) || raw < 1 || raw > PAGE_MAX) return 1;
      return raw;
    }
    if (raw == null || raw === '') return 1;
    const text = String(raw).trim();
    if (!/^[1-9]\d*$/.test(text)) return 1;
    const page = Number(text);
    if (!Number.isSafeInteger(page) || page > PAGE_MAX) return 1;
    return page;
  }

  function toParams(search) {
    if (search instanceof URLSearchParams) return search;
    const raw = String(search ?? '');
    return new URLSearchParams(raw.startsWith('?') ? raw.slice(1) : raw);
  }

  function parseFilterState(search) {
    const params = toParams(search);
    return {
      q: cleanQuery(params.get('q')),
      console: normalizeConsole(params.get('console')),
      avail: normalizeAvail(params.get('avail')),
      trend: normalizeTrend(params.get('trend')),
      stores: normalizeStores(params.get('stores')),
      min: parsePrice(params.get('min')),
      max: parsePrice(params.get('max')),
      sort: normalizeSort(params.get('sort')),
      dir: params.get('dir') === 'desc' ? 'desc' : 'asc',
      wl: params.get('wl') === '1',
      page: parsePage(params.get('page')),
    };
  }

  function serializeFilterState(state, extra) {
    const source = state || {};
    const q = cleanQuery(source.q);
    const consoleName = normalizeConsole(source.console);
    const avail = normalizeAvail(source.avail);
    const trend = normalizeTrend(source.trend);
    const stores = normalizeStores(source.stores);
    const min = parsePrice(source.min);
    const max = parsePrice(source.max);
    const sort = normalizeSort(source.sort);
    const dir = source.dir === 'desc' ? 'desc' : 'asc';
    const page = parsePage(source.page);
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (consoleName) params.set('console', consoleName);
    if (avail) params.set('avail', avail);
    if (trend) params.set('trend', trend);
    if (stores.length) params.set('stores', stores.join(','));
    if (min != null) params.set('min', formatPrice(min));
    if (max != null) params.set('max', formatPrice(max));
    if (sort !== 'title') params.set('sort', sort);
    if (dir === 'desc') params.set('dir', 'desc');
    if (source.wl) params.set('wl', '1');
    if (page > 1) params.set('page', String(page));
    if (extra && typeof extra.api === 'string' && extra.api && extra.api.length <= QUERY_MAX) {
      params.set('api', extra.api);
    }
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  function sameQuery(a, b) {
    const left = toParams(a);
    const right = toParams(b);
    const keys = new Set([...left.keys(), ...right.keys()]);
    for (const key of keys) {
      if (left.getAll(key).join('\u0000') !== right.getAll(key).join('\u0000')) return false;
    }
    return true;
  }

  function storesInStock(game, storeIds) {
    if (!game || !game.is_available) return [];
    const outOfStock = Array.isArray(game.out_of_stock_stores) ? game.out_of_stock_stores : [];
    const seen = new Set();
    const found = [];
    normalizeStores(storeIds).forEach(id => {
      if (seen.has(id) || outOfStock.includes(id)) return;
      seen.add(id);
      found.push(id);
    });
    return found;
  }

  function matchesGame(game, state, wishlistIds) {
    if (!game || typeof game !== 'object') return false;
    const source = state || {};
    const q = cleanQuery(source.q).toLowerCase();
    if (q && !String(game.title || '').toLowerCase().includes(q)) return false;
    const consoleName = normalizeConsole(source.console);
    if (consoleName && game.console !== consoleName) return false;
    const avail = normalizeAvail(source.avail);
    if (avail !== '' && String(game.is_available) !== avail) return false;
    const trend = normalizeTrend(source.trend);
    if (trend === 'down' && !(game.price_trend_pct < 0)) return false;
    if (trend === 'up' && !(game.price_trend_pct > 0)) return false;
    if (source.wl) {
      const ids = Array.isArray(wishlistIds) ? wishlistIds : [];
      if (!ids.includes(game.id)) return false;
    }
    const stores = normalizeStores(source.stores);
    if (stores.length && storesInStock(game, stores).length === 0) return false;
    const min = parsePrice(source.min);
    const max = parsePrice(source.max);
    if (min != null || max != null) {
      if (game.current_price == null || game.current_price === '') return false;
      const price = Number(game.current_price);
      if (!Number.isFinite(price)) return false;
      if (min != null && price < min) return false;
      if (max != null && price > max) return false;
    }
    return true;
  }

  function filterAndSort(games, state, wishlistIds) {
    const source = state || {};
    const sortKey = normalizeSort(source.sort);
    const sign = source.dir === 'desc' ? -1 : 1;
    const filtered = (Array.isArray(games) ? games : []).filter(game => matchesGame(game, source, wishlistIds));
    filtered.sort((a, b) => {
      const va = a[sortKey] ?? '';
      const vb = b[sortKey] ?? '';
      if (typeof va === 'string') return va.localeCompare(vb) * sign;
      return (va - vb) * sign;
    });
    return filtered;
  }

  function storeById(id) {
    return STORE_BY_ID.get(id) || null;
  }

  function storeLabel(id) {
    const store = storeById(id);
    return store ? store.label : '';
  }

  function storeAbbr(id) {
    const store = storeById(id);
    return store ? store.abbr : '';
  }

  return {
    STORE_CATALOG,
    STORE_PRESETS,
    STORE_IDS,
    CONSOLES,
    SORT_KEYS,
    parseFilterState,
    serializeFilterState,
    sameQuery,
    parsePrice,
    cleanQuery,
    normalizeStores,
    storesInStock,
    matchesGame,
    filterAndSort,
    storeById,
    storeLabel,
    storeAbbr,
  };
});
