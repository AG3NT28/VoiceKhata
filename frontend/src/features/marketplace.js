import {
  marketplaceSearch,
  marketplaceProviders,
  marketplaceRedirect,
  marketplaceImport,
  marketplaceStars,
  marketplaceStar,
  marketplaceUnstar,
} from '../services/api.js';

function money(rupees) {
  if (rupees == null || Number.isNaN(Number(rupees))) return '—';
  return `₹${Number(rupees).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function deltaLabel(deltaRupees) {
  const n = Number(deltaRupees) || 0;
  if (n === 0) return '<span class="mkt-delta flat">No change</span>';
  if (n < 0) return `<span class="mkt-delta down">↓ ${money(Math.abs(n))} cheaper</span>`;
  return `<span class="mkt-delta up">↑ ${money(n)} higher</span>`;
}

let starredIds = new Set();

function offerCard(offer) {
  const incomplete = offer.price_complete ? '' : '<span class="mkt-flag">Estimated</span>';
  const isStarred = starredIds.has(String(offer.offer_id));
  return `
    <article class="mkt-offer" data-offer-id="${offer.offer_id}">
      <div class="mkt-offer-top">
        <div>
          <h3>${offer.title}</h3>
          <p class="mkt-meta">${[offer.brand, offer.supplier_name || offer.provider_name].filter(Boolean).join(' · ')}</p>
        </div>
        <button type="button" class="mkt-star-btn" data-offer-id="${offer.offer_id}" aria-pressed="${isStarred}" title="${isStarred ? 'Unstar' : 'Star to monitor fare'}">${isStarred ? '★' : '☆'}</button>
      </div>
      <dl class="mkt-stats">
        <div><dt>Pack</dt><dd>${offer.package_quantity} ${offer.unit}</dd></div>
        <div><dt>MOQ</dt><dd>${offer.moq}</dd></div>
        <div><dt>Base</dt><dd>${money(offer.base_price_rupees)}</dd></div>
        <div><dt>Unit landed</dt><dd>${money(offer.effective_unit_rupees)}/${offer.unit} ${incomplete}</dd></div>
        <div><dt>Delivery</dt><dd>${offer.delivery_estimate_days != null ? `${offer.delivery_estimate_days}d` : '—'} · ${money(offer.delivery_charges_rupees)}</dd></div>
        <div><dt>Stock</dt><dd>${offer.stock_status}</dd></div>
      </dl>
      <div class="mkt-actions">
        <button type="button" class="mkt-redirect" data-offer-id="${offer.offer_id}" ${offer.has_redirect ? '' : 'disabled'}>
          Open supplier
        </button>
      </div>
    </article>
  `;
}

function starCard(star) {
  return `
    <article class="mkt-star-card" data-offer-id="${star.offer_id}">
      <div class="mkt-offer-top">
        <div>
          <h3>${star.title}</h3>
          <p class="mkt-meta">${[star.brand, star.supplier_name].filter(Boolean).join(' · ')} · ${star.package_quantity} ${star.unit}</p>
        </div>
        <button type="button" class="mkt-star-btn" data-offer-id="${star.offer_id}" aria-pressed="true" title="Unstar">★</button>
      </div>
      <dl class="mkt-stats">
        <div><dt>Watched</dt><dd>${money(star.starred_price_rupees)}</dd></div>
        <div><dt>Now</dt><dd>${money(star.current_price_rupees)}</dd></div>
        <div><dt>Change</dt><dd>${deltaLabel(star.delta_rupees)}</dd></div>
        <div><dt>Status</dt><dd>${star.stock_status}</dd></div>
      </dl>
      <button type="button" class="secondary mkt-watch-search" data-q="${(star.brand ? star.brand + ' ' : '')}${star.title}">Compare</button>
    </article>
  `;
}

export function mountMarketplace(root) {
  if (!root) return;
  root.innerHTML = `
    <div class="card mkt-card">
      <div class="inv-bar">
        <div>
          <h3 data-i18n="marketplace">Marketplace</h3>
          <p class="mkt-sub">Search wholesale fares. Star items to monitor price changes.</p>
        </div>
      </div>

      <section id="mktStarsSection" class="mkt-stars-section" aria-label="Starred fares">
        <div class="mkt-section-head">
          <h4>★ Starred fares</h4>
          <p>Watch staples and spot when rates move.</p>
        </div>
        <div id="mktStars" class="mkt-stars-grid"></div>
      </section>

      <form id="mktSearchForm" class="mkt-search">
        <input id="mktQuery" type="search" placeholder="Search — oil, atta, dal…" required enterkeyhint="search" />
        <button type="submit">Search</button>
      </form>
      <p id="mktNotice" class="form-notice" role="status" aria-live="polite" hidden></p>
      <div id="mktRankings" class="mkt-rankings" hidden></div>
      <div id="mktResults" class="mkt-results"></div>
      <details class="mkt-import">
        <summary>Import catalogue (CSV)</summary>
        <form id="mktImportForm" class="mkt-import-form">
          <input id="mktSupplierName" type="text" placeholder="Supplier name" value="Local Wholesaler" />
          <input id="mktImportFile" type="file" accept=".csv,.xlsx,.xls" required />
          <button type="submit" class="secondary">Upload</button>
        </form>
      </details>
    </div>
  `;

  const notice = root.querySelector('#mktNotice');
  const results = root.querySelector('#mktResults');
  const rankingsEl = root.querySelector('#mktRankings');
  const starsEl = root.querySelector('#mktStars');

  function setNotice(msg, isError = false) {
    notice.textContent = msg || '';
    notice.hidden = !msg;
    notice.classList.toggle('error', Boolean(isError && msg));
  }

  async function loadStars() {
    try {
      const stars = await marketplaceStars();
      starredIds = new Set((stars || []).map((s) => String(s.offer_id)));
      starsEl.innerHTML = stars?.length
        ? stars.map(starCard).join('')
        : '<p class="empty-state">No starred stock yet. Search and tap ★.</p>';
    } catch (err) {
      starsEl.innerHTML = `<p class="empty-state">${err.message}</p>`;
    }
  }

  function renderSearch(data) {
    const offers = data.offers || [];
    setNotice(`${offers.length} offers for “${data.query}”.`, false);
    const ranks = data.rankings || {};
    const pick = (arr) => (arr && arr[0] ? arr[0].title : '—');
    rankingsEl.hidden = offers.length === 0;
    rankingsEl.innerHTML = `
      <div class="mkt-rank-card"><span>Lowest unit</span><strong>${pick(ranks.lowest_unit_price)}</strong></div>
      <div class="mkt-rank-card"><span>Best bulk</span><strong>${pick(ranks.best_bulk_deal)}</strong></div>
      <div class="mkt-rank-card"><span>Fastest</span><strong>${pick(ranks.fastest_delivery)}</strong></div>
    `;
    results.innerHTML = offers.length
      ? offers.map((o) => offerCard(o)).join('')
      : '<p class="empty-state">No matching offers. Try oil, atta, dal, rice…</p>';
  }

  root.querySelector('#mktSearchForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = root.querySelector('#mktQuery').value.trim();
    if (!query) return;
    setNotice('Searching…');
    results.innerHTML = '';
    rankingsEl.hidden = true;
    try {
      const data = await marketplaceSearch(query);
      renderSearch(data);
    } catch (err) {
      const msg = /failed to fetch/i.test(err.message || '')
        ? 'Cannot reach server. Check backend is running on port 8000.'
        : err.message;
      setNotice(msg, true);
    }
  });

  async function toggleStar(offerId) {
    const id = String(offerId);
    try {
      if (starredIds.has(id)) {
        await marketplaceUnstar(id);
        starredIds.delete(id);
      } else {
        await marketplaceStar(id);
        starredIds.add(id);
      }
      await loadStars();
      results.querySelectorAll('.mkt-star-btn').forEach((btn) => {
        const on = starredIds.has(String(btn.dataset.offerId));
        btn.setAttribute('aria-pressed', String(on));
        btn.textContent = on ? '★' : '☆';
      });
    } catch (err) {
      setNotice(err.message, true);
    }
  }

  root.addEventListener('click', async (event) => {
    const starBtn = event.target.closest('.mkt-star-btn');
    if (starBtn) {
      event.preventDefault();
      await toggleStar(starBtn.dataset.offerId);
      return;
    }
    const watchSearch = event.target.closest('.mkt-watch-search');
    if (watchSearch) {
      root.querySelector('#mktQuery').value = watchSearch.dataset.q || '';
      root.querySelector('#mktSearchForm').requestSubmit();
      return;
    }
    const redirectBtn = event.target.closest('.mkt-redirect');
    if (redirectBtn && !redirectBtn.disabled) {
      try {
        const data = await marketplaceRedirect(redirectBtn.dataset.offerId);
        window.open(data.destination_url, '_blank', 'noopener,noreferrer');
        setNotice(data.notice || 'Opened supplier listing.', false);
      } catch (err) {
        setNotice(err.message, true);
      }
    }
  });

  root.querySelector('#mktImportForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const file = root.querySelector('#mktImportFile').files?.[0];
    const supplierName = root.querySelector('#mktSupplierName').value.trim() || 'Imported Supplier';
    if (!file) return;
    try {
      const report = await marketplaceImport(file, supplierName);
      setNotice(`Imported ${report.imported}, rejected ${report.rejected}.`, report.rejected > 0 && report.imported === 0);
    } catch (err) {
      setNotice(err.message, true);
    }
  });

  results.innerHTML = '';
  loadStars();
  // Warm provider list quietly (non-blocking)
  marketplaceProviders().catch(() => {});
}

export function applyMarketplaceVoiceResult(marketplacePayload) {
  const section = document.getElementById('marketplace');
  if (!section) return;
  const query = marketplacePayload?.query || marketplacePayload?.parsed?.raw_query;
  const input = section.querySelector('#mktQuery');
  if (input && query) input.value = query;
  const results = section.querySelector('#mktResults');
  const rankingsEl = section.querySelector('#mktRankings');
  const notice = section.querySelector('#mktNotice');
  if (!results) return;
  const offers = marketplacePayload?.offers || [];
  if (notice) {
    notice.hidden = false;
    notice.textContent = `Voice search: ${offers.length} offers.`;
  }
  if (rankingsEl) rankingsEl.hidden = offers.length === 0;
  results.innerHTML = offers.length
    ? offers.map((o) => offerCard(o)).join('')
    : '<p class="empty-state">No offers from voice search.</p>';
}
