const STORAGE_KEY = 'voicekhata.priceCompare';

const DEFAULT_ROWS = [
  {
    item: 'Rice 5kg',
    yourPrice: 320,
    sources: { jumbotail: 305, flipkart: 339, amazon: 349 },
  },
  {
    item: 'Wheat Flour 5kg',
    yourPrice: 450,
    sources: { jumbotail: 429, flipkart: 460, amazon: 475 },
  },
  {
    item: 'Cooking Oil 1L',
    yourPrice: 180,
    sources: { jumbotail: 169, flipkart: 185, amazon: 192 },
  },
];

export function loadPriceRows() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return structuredClone(DEFAULT_ROWS);
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length ? parsed : structuredClone(DEFAULT_ROWS);
  } catch {
    return structuredClone(DEFAULT_ROWS);
  }
}

export function savePriceRows(rows) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
}

export function bestSource(row) {
  const entries = Object.entries(row.sources || {});
  if (!entries.length) return null;
  return entries.reduce((best, cur) => (cur[1] < best[1] ? cur : best));
}

export function sourceLabel(key) {
  return (
    {
      jumbotail: 'JumboTail',
      flipkart: 'Flipkart',
      amazon: 'Amazon',
    }[key] || key
  );
}
