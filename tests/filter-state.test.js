const test = require('node:test');
const assert = require('node:assert/strict');
const F = require('../dashboard/filter-state.js');

const MERLATA = 'Merlata Bloom';
const REGGIO = 'Reggio Emilia San Pietro';

function game(overrides) {
  return Object.assign({
    id: 1,
    title: 'Zelda',
    console: 'Switch',
    current_price: 20,
    price_trend_pct: null,
    is_available: 1,
    out_of_stock_stores: [],
  }, overrides);
}

test('catalog lists the 12 store ids from the data, including the two user stores', () => {
  assert.equal(F.STORE_CATALOG.length, 12);
  assert.equal(new Set(F.STORE_IDS).size, 12);
  assert.ok(F.STORE_IDS.includes(MERLATA));
  assert.ok(F.STORE_IDS.includes(REGGIO));
  assert.equal(F.storeLabel(MERLATA), 'Milano Merlata Bloom');
  assert.equal(F.storeLabel(REGGIO), REGGIO);
  for (const preset of F.STORE_PRESETS) {
    assert.deepEqual(F.normalizeStores(preset.stores), preset.stores);
  }
});

test('empty query is the default view and round-trips', () => {
  const state = F.parseFilterState('');
  assert.deepEqual(state, {
    q: '',
    console: '',
    avail: '',
    trend: '',
    stores: [],
    min: null,
    max: null,
    sort: 'title',
    dir: 'asc',
    wl: false,
    page: 1,
  });
  assert.equal(F.serializeFilterState(state), '');
  assert.equal(F.sameQuery('', ''), true);
});

test('query round-trip keeps search, console, stores, price, availability, trend, sort, wishlist and page', () => {
  const original = '?q=zelda&console=Switch&avail=1&trend=down&stores=Reggio+Emilia+San+Pietro,Merlata+Bloom&min=5&max=30,5&sort=current_price&dir=desc&wl=1&page=3';
  const state = F.parseFilterState(original);
  assert.equal(state.q, 'zelda');
  assert.equal(state.console, 'Switch');
  assert.equal(state.avail, '1');
  assert.equal(state.trend, 'down');
  assert.deepEqual(state.stores, [MERLATA, REGGIO]);
  assert.equal(state.min, 5);
  assert.equal(state.max, 30.5);
  assert.equal(state.sort, 'current_price');
  assert.equal(state.dir, 'desc');
  assert.equal(state.wl, true);
  assert.equal(state.page, 3);
  const again = F.parseFilterState(F.serializeFilterState(state));
  assert.deepEqual(again, state);
});

test('unknown and hostile params are ignored and never serialized as raw markup', () => {
  const raw = [
    '?q=<script>alert(1)</script>',
    'console="><img src=x onerror=alert(1)>',
    'stores=<script>,Merlata Bloom,Nope',
    'sort=<script>',
    'dir=DESC',
    'avail=<img src=x onerror=alert(1)>',
    'trend=<script>',
    'min=<script>',
    'max=-5',
    'page=0',
    'wl=<script>',
    'evil=<script>alert(1)</script>',
  ].join('&');
  const state = F.parseFilterState(raw);
  assert.equal(state.q, '<script>alert(1)</script>');
  assert.equal(state.console, '');
  assert.deepEqual(state.stores, [MERLATA]);
  assert.equal(state.sort, 'title');
  assert.equal(state.dir, 'asc');
  assert.equal(state.avail, '');
  assert.equal(state.trend, '');
  assert.equal(state.min, null);
  assert.equal(state.max, null);
  assert.equal(state.page, 1);
  assert.equal(state.wl, false);
  const serialized = F.serializeFilterState(state, { evil: '<script>' });
  assert.equal(serialized.includes('<'), false);
  assert.equal(serialized.includes('>'), false);
  assert.equal(serialized.includes('evil'), false);
  const again = F.parseFilterState(serialized);
  assert.equal(again.q, state.q);
  assert.deepEqual(again.stores, [MERLATA]);
});

test('price bounds accept comma decimals and reject junk', () => {
  assert.equal(F.parsePrice('10,5'), 10.5);
  assert.equal(F.parsePrice('10.'), 10);
  assert.equal(F.parsePrice('0'), 0);
  assert.equal(F.parsePrice(''), null);
  assert.equal(F.parsePrice('1e2'), null);
  assert.equal(F.parsePrice('+10'), null);
  assert.equal(F.parsePrice('-1'), null);
  assert.equal(F.parsePrice('10.999'), null);
  assert.equal(F.parsePrice('<script>'), null);
  assert.equal(F.parsePrice(100001), null);
});

test('api is preserved encoded and other extra keys are dropped', () => {
  const serialized = F.serializeFilterState({ q: 'mario' }, {
    api: 'http://127.0.0.1:8787',
    next: '/admin',
  });
  const params = new URLSearchParams(serialized.slice(1));
  assert.equal(params.get('q'), 'mario');
  assert.equal(params.get('api'), 'http://127.0.0.1:8787');
  assert.equal(params.get('next'), null);
  assert.equal(serialized.includes('<'), false);
});

test('sameQuery treats space encodings as equal', () => {
  assert.equal(F.sameQuery('?q=a+b&stores=Merlata+Bloom', '?q=a%20b&stores=Merlata%20Bloom'), true);
  assert.equal(F.sameQuery('?q=a', '?q=b'), false);
});

test('store filter keeps titles in stock at one or more selected stores', () => {
  const atMerlata = game({
    id: 1,
    title: 'In Merlata',
    out_of_stock_stores: [REGGIO, 'Bologna Amendola'],
  });
  const atReggio = game({
    id: 2,
    title: 'In Reggio',
    out_of_stock_stores: [MERLATA],
  });
  const atBoth = game({ id: 3, title: 'In both', out_of_stock_stores: ['Gran Roma'] });
  const atNeither = game({
    id: 4,
    title: 'Nowhere',
    out_of_stock_stores: [MERLATA, REGGIO],
  });
  const unavailable = game({
    id: 5,
    title: 'Unavailable but not listed',
    is_available: 0,
    out_of_stock_stores: [],
  });
  const games = [atMerlata, atReggio, atBoth, atNeither, unavailable];

  assert.deepEqual(F.storesInStock(atMerlata, [MERLATA, REGGIO]), [MERLATA]);
  assert.deepEqual(F.storesInStock(atReggio, [MERLATA, REGGIO]), [REGGIO]);
  assert.deepEqual(F.storesInStock(atBoth, [MERLATA, REGGIO]), [MERLATA, REGGIO]);
  assert.deepEqual(F.storesInStock(unavailable, [MERLATA]), []);
  assert.deepEqual(F.storesInStock(atMerlata, ['<script>', 'Nope']), []);

  const merlataOnly = F.filterAndSort(games, { stores: [MERLATA] });
  assert.deepEqual(merlataOnly.map(item => item.id), [3, 1]);

  const either = F.filterAndSort(games, { stores: [REGGIO, MERLATA] });
  assert.deepEqual(either.map(item => item.id).sort(), [1, 2, 3]);

  const untouched = F.filterAndSort(games, { stores: [] });
  assert.equal(untouched.length, games.length);
  assert.notEqual(untouched, games);
});

test('no store selection preserves the other filters, including unavailable titles', () => {
  const games = [
    game({ id: 1, title: 'Alpha', is_available: 0, console: 'PS4', current_price: 8 }),
    game({ id: 2, title: 'Beta', is_available: 1, console: 'PS5', current_price: 40, price_trend_pct: -2 }),
    game({ id: 3, title: 'Gamma', is_available: 1, console: 'PS5', current_price: 12, price_trend_pct: 3 }),
  ];
  const result = F.filterAndSort(games, {
    q: 'a',
    console: 'PS5',
    avail: '1',
    trend: 'up',
    min: 10,
    max: 15,
    stores: [],
  });
  assert.deepEqual(result.map(item => item.id), [3]);
});

test('price range is inclusive and drops a title with no price when a bound is set', () => {
  const games = [
    game({ id: 1, title: 'Cheap', current_price: 5 }),
    game({ id: 2, title: 'Edge', current_price: 10 }),
    game({ id: 3, title: 'Top', current_price: 20 }),
    game({ id: 4, title: 'Missing', current_price: null }),
  ];
  assert.deepEqual(F.filterAndSort(games, { min: 10, max: 20 }).map(item => item.id), [2, 3]);
  assert.deepEqual(F.filterAndSort(games, { min: 0 }).map(item => item.id).sort(), [1, 2, 3]);
  assert.deepEqual(F.filterAndSort(games, { min: '<script>' }).map(item => item.id).sort(), [1, 2, 3, 4]);
});

test('real catalog: Merlata and Reggio stock matches the out-of-stock lists', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../dashboard/data/games.json'), 'utf8'));
  const games = data.games;
  assert.ok(games.length > 1000);
  const ids = new Set();
  games.forEach(item => (item.out_of_stock_stores || []).forEach(id => ids.add(id)));
  for (const id of F.STORE_IDS) assert.ok(ids.has(id), id);

  function count(storeId) {
    return games.filter(item => {
      if (!item.is_available) return false;
      const outOfStock = Array.isArray(item.out_of_stock_stores) ? item.out_of_stock_stores : [];
      return !outOfStock.includes(storeId);
    }).length;
  }

  const merlata = F.filterAndSort(games, { stores: [MERLATA] });
  const reggio = F.filterAndSort(games, { stores: [REGGIO] });
  const either = F.filterAndSort(games, { stores: [MERLATA, REGGIO] });
  assert.equal(merlata.length, count(MERLATA));
  assert.equal(reggio.length, count(REGGIO));
  assert.equal(either.length, count(MERLATA) + count(REGGIO) - games.filter(item =>
    F.storesInStock(item, [MERLATA, REGGIO]).length === 2
  ).length);
  merlata.forEach(item => {
    assert.deepEqual(F.storesInStock(item, [MERLATA, REGGIO]).includes(MERLATA), true);
    assert.equal(item.out_of_stock_stores.includes(MERLATA), false);
  });
  assert.equal(F.filterAndSort(games, {}).length, games.length);
});

test('wishlist and sort stay optional and do not mutate the source list', () => {
  const games = [
    game({ id: 2, title: 'B' }),
    game({ id: 1, title: 'A' }),
  ];
  const copy = games.map(item => Object.assign({}, item));
  const wished = F.filterAndSort(games, { wl: true, sort: 'title', dir: 'asc' }, [2]);
  assert.deepEqual(wished.map(item => item.id), [2]);
  assert.deepEqual(games, copy);
  const byPrice = F.filterAndSort([
    game({ id: 1, title: 'A', current_price: 30 }),
    game({ id: 2, title: 'B', current_price: 5 }),
  ], { sort: 'current_price', dir: 'desc' });
  assert.deepEqual(byPrice.map(item => item.id), [1, 2]);
});
