function formatNumber(n) {
  try {
    return new Intl.NumberFormat().format(Number(n || 0));
  } catch {
    return String(n || 0);
  }
}

function getApiBase() {
  if (typeof window !== 'undefined' && window.NNBOM_API_BASE) return window.NNBOM_API_BASE;
  try {
    const host = window.location && window.location.hostname ? window.location.hostname : 'localhost';
    const proto = window.location && window.location.protocol ? window.location.protocol : 'http:';
    return `${proto}//${host}:5001`;
  } catch {
    return 'http://localhost:5001';
  }
}

function formatUpdatedTime(value) {
  if (!value) return '-';
  if (typeof value === 'string') {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) {
      const iso = d.toISOString();
      return iso.replace('T', ' ').replace('.000Z', ' UTC');
    }
    return value;
  }
  return String(value);
}

function shortName(value) {
  if (!value) return '-';
  const s = String(value);
  if (s.length <= 28) return s;
  return s.slice(0, 16) + '…' + s.slice(-9);
}

function githubUrlFromFullName(fullName) {
  if (!fullName) return null;
  const s = String(fullName);
  let owner = null;
  let repo = null;
  if (s.includes('__')) [owner, repo] = s.split('__', 2);
  else if (s.includes('/')) [owner, repo] = s.split('/', 2);
  if (!owner || !repo) return null;
  return `https://github.com/${owner}/${repo}`;
}

async function fetchJson(path) {
  const res = await fetch(`${getApiBase()}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Network error ' + res.status);
  const data = await res.json();
  if (!data || data.success === false) throw new Error((data && data.message) || 'Backend error');
  return data;
}

function el(id) {
  return document.getElementById(id);
}

let charts = { tpl: null, ptm: null, mod: null };
let moduleListCache = [];

function destroyChart(name) {
  try {
    if (charts[name]) charts[name].destroy();
  } catch {}
  charts[name] = null;
}

function renderMiniList(containerEl, rows, onClick) {
  if (!containerEl) return;
  if (!rows || rows.length === 0) {
    containerEl.innerHTML = `<div class="mini-row" style="cursor:default"><div class="mini-name">No data</div><div class="mini-val">-</div></div>`;
    return;
  }
  containerEl.innerHTML = rows
    .map((r) => {
      const name = r && r.name ? String(r.name) : '-';
      const val = formatNumber(r && r.repo_count != null ? r.repo_count : r.value);
      return `<div class="mini-row" data-name="${encodeURIComponent(name)}"><div class="mini-name" title="${name}">${name}</div><div class="mini-val">${val}</div></div>`;
    })
    .join('');
  containerEl.querySelectorAll('.mini-row[data-name]').forEach((row) => {
    row.addEventListener('click', () => {
      const name = decodeURIComponent(row.getAttribute('data-name') || '');
      if (onClick) onClick(name);
    });
  });
}

function renderBarChart(canvasEl, rows, color, onClickLabel) {
  if (!canvasEl) return null;
  const labels = (rows || []).map((r) => shortName(r.name));
  const rawLabels = (rows || []).map((r) => String(r.name || ''));
  const values = (rows || []).map((r) => Number(r.repo_count || 0));

  const ctx = canvasEl.getContext('2d');
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Repo count',
          data: values,
          backgroundColor: color,
          borderColor: 'rgba(100,255,218,0.45)',
          borderWidth: 1,
          borderRadius: 8,
          maxBarThickness: 48,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              const idx = items && items[0] ? items[0].dataIndex : 0;
              return rawLabels[idx] || '';
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: 'rgba(204,214,246,0.85)' },
          grid: { color: 'rgba(100,255,218,0.08)' },
        },
        y: {
          ticks: { color: 'rgba(204,214,246,0.85)' },
          grid: { color: 'rgba(100,255,218,0.08)' },
        },
      },
      onClick: (_evt, elements) => {
        if (!elements || elements.length === 0) return;
        const idx = elements[0].index;
        const name = rawLabels[idx];
        if (name && onClickLabel) onClickLabel(name);
      },
    },
  });
}

function openModal(title, meta, bodyHtml) {
  const modal = el('detail-modal');
  if (!modal) return;
  el('modal-title').textContent = title || 'Detail';
  el('modal-meta').textContent = meta || '';
  el('modal-body').innerHTML = bodyHtml || '';
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const modal = el('detail-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

function renderDetailRepos(items, opts) {
  const withOccurrences = Boolean(opts && opts.withOccurrences);
  if (!items || items.length === 0) return `<div class="detail-grid"><div class="detail-row" style="cursor:default"><div class="detail-repo">No repositories found</div><div class="detail-num">-</div></div></div>`;

  const rows = items
    .map((r) => {
      const fullName = r.full_name || '-';
      const stars = formatNumber(r.stars || 0);
      const occ = formatNumber(r.occurrences || 0);
      const url = githubUrlFromFullName(fullName);
      const clickAttr = url ? `data-url="${encodeURIComponent(url)}"` : '';
      return `<div class="detail-row" ${clickAttr} title="${url ? 'Open on GitHub' : fullName}">
        <div class="detail-repo">${fullName}</div>
        <div class="detail-num"><strong>${stars}</strong> ★</div>
        ${withOccurrences ? `<div class="detail-num"><strong>${occ}</strong> occ</div>` : ''}
      </div>`;
    })
    .join('');

  return `<div class="detail-grid">${rows}</div>`;
}

function wireDetailRepoClicks() {
  const body = el('modal-body');
  if (!body) return;
  body.querySelectorAll('.detail-row[data-url]').forEach((row) => {
    row.addEventListener('click', () => {
      const url = decodeURIComponent(row.getAttribute('data-url') || '');
      if (url) window.open(url, '_blank', 'noopener');
    });
  });
}

async function showModuleDetail(name) {
  try {
    openModal(name, 'Loading module detail…', `<div class="loading-stack"><div class="spin-loader"></div><p>Loading…</p></div>`);
    const data = await fetchJson(`/api/analytics/module/detail?name=${encodeURIComponent(name)}&limit=30`);
    const mod = data.module || {};
    const meta = `Repos: ${formatNumber(mod.repo_count)}  ·  Total occurrences: ${formatNumber(mod.total_occurrences)}`;
    const html = renderDetailRepos(data.top_repos || [], { withOccurrences: true });
    openModal(name, meta, html);
    wireDetailRepoClicks();
  } catch (err) {
    openModal(name, 'Failed to load', `<div class="content-section" style="margin:0">Error: ${String(err.message || err)}</div>`);
  }
}

async function showComponentDetail(type, name) {
  try {
    const label = type === 'tpl' ? 'TPL' : 'PTM';
    openModal(`${label}: ${name}`, 'Loading…', `<div class="loading-stack"><div class="spin-loader"></div><p>Loading…</p></div>`);
    const data = await fetchJson(`/api/analytics/component/detail?type=${encodeURIComponent(type)}&name=${encodeURIComponent(name)}&limit=30`);
    const comp = data.component || {};
    const meta = `Repos containing it: ${formatNumber(comp.repo_count)}`;
    const html = renderDetailRepos(data.top_repos || [], { withOccurrences: false });
    openModal(`${label}: ${name}`, meta, html);
    wireDetailRepoClicks();
  } catch (err) {
    openModal(name, 'Failed to load', `<div class="content-section" style="margin:0">Error: ${String(err.message || err)}</div>`);
  }
}

function applyModuleFilter(q) {
  const query = (q || '').trim().toLowerCase();
  const filtered = !query
    ? moduleListCache
    : moduleListCache.filter((r) => String(r.name || '').toLowerCase().includes(query));
  const list = el('list-mod');
  renderMiniList(list, filtered.slice(0, 60), (name) => showModuleDetail(name));
}

async function loadAll() {
  destroyChart('tpl');
  destroyChart('ptm');
  destroyChart('mod');

  el('kpi-repos').textContent = '…';
  el('kpi-tpl-uniq').textContent = '…';
  el('kpi-ptm-uniq').textContent = '…';
  el('kpi-mod-uniq').textContent = '…';

  renderMiniList(el('list-tpl'), [], null);
  renderMiniList(el('list-ptm'), [], null);
  renderMiniList(el('list-mod'), [], null);

  try {
    const [summary, tpl, ptm, modTop, modList] = await Promise.all([
      fetchJson('/api/analytics/summary'),
      fetchJson('/api/analytics/top_tpls?limit=14'),
      fetchJson('/api/analytics/top_ptms?limit=14'),
      fetchJson('/api/analytics/top_modules?limit=12'),
      fetchJson('/api/analytics/top_modules?limit=80'),
    ]);

    const s = summary.summary || {};
    el('kpi-repos').textContent = formatNumber(s.total_repos);
    el('kpi-tpl-uniq').textContent = formatNumber(s.unique_tpl);
    el('kpi-ptm-uniq').textContent = formatNumber(s.unique_ptm);
    el('kpi-mod-uniq').textContent = formatNumber(s.unique_module);
    el('stat-updated').textContent = formatUpdatedTime(s.last_updated);

    const tplRows = (tpl.items || []).map((r) => ({ name: r.name, repo_count: r.repo_count }));
    const ptmRows = (ptm.items || []).map((r) => ({ name: r.name, repo_count: r.repo_count }));
    const modRows = (modTop.items || []).map((r) => ({ name: r.name, repo_count: r.repo_count }));

    renderMiniList(el('list-tpl'), tplRows, (name) => showComponentDetail('tpl', name));
    renderMiniList(el('list-ptm'), ptmRows, (name) => showComponentDetail('ptm', name));

    moduleListCache = (modList.items || []).map((r) => ({
      name: r.name,
      repo_count: r.repo_count,
      occurrences: r.occurrences,
    }));
    applyModuleFilter(el('module-filter').value);

    charts.tpl = renderBarChart(el('chart-tpl'), tplRows, 'rgba(100,255,218,0.35)', (name) => showComponentDetail('tpl', name));
    charts.ptm = renderBarChart(el('chart-ptm'), ptmRows, 'rgba(136,146,176,0.45)', (name) => showComponentDetail('ptm', name));
    charts.mod = renderBarChart(el('chart-mod'), modRows, 'rgba(100,255,218,0.25)', (name) => showModuleDetail(name));
  } catch (err) {
    console.error(err);
    openModal('Analytics', 'Failed to load analytics', `<div class="content-section" style="margin:0">Error: ${String(err.message || err)}</div>`);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const closeBtn = el('modal-close');
  const backdrop = el('modal-backdrop');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  const refresh = el('btn-refresh');
  if (refresh) refresh.addEventListener('click', loadAll);

  const modFilter = el('module-filter');
  if (modFilter) modFilter.addEventListener('input', (e) => applyModuleFilter(e.target.value));

  loadAll();
});

