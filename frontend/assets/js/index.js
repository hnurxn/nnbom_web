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
      const iso = d.toISOString(); // always UTC
      return iso.replace('T', ' ').replace('.000Z', ' UTC');
    }
    return value;
  }
  return String(value);
}

async function loadSnapshotStats() {
  try {
    const res = await fetch(`${getApiBase()}/api/stats/summary`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Network error ' + res.status);
    const data = await res.json();
    if (!data.success) throw new Error(data.message || 'Backend error');

    const stats = data.stats || {};
    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };

    setText('stat-tpl', formatNumber(stats.total_tpl));
    setText('stat-ptm', formatNumber(stats.total_ptm));
    setText('stat-mod', formatNumber(stats.total_module));
    setText('stat-dep', formatNumber(stats.total_dependency));
    setText('stat-updated', formatUpdatedTime(stats.last_updated));
  } catch (err) {
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded', loadSnapshotStats);
