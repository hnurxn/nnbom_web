function toast(message) {
  const old = document.querySelector('.toast');
  if (old) old.remove();
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = message;
  document.body.appendChild(t);
  setTimeout(() => {
    try { t.remove(); } catch {}
  }, 3200);
}

function normalizeRepoLine(line) {
  const v = (line || '').trim();
  if (!v) return null;
  // accept owner/repo or github url
  if (v.startsWith('http')) {
    try {
      const u = new URL(v);
      if (u.hostname !== 'github.com') return null;
      const parts = u.pathname.split('/').filter(Boolean);
      if (parts.length < 2) return null;
      return `${parts[0]}/${parts[1]}`;
    } catch {
      return null;
    }
  }
  const m = v.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
  if (!m) return null;
  return `${m[1]}/${m[2]}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('repo-list');
  const out = document.getElementById('output');
  const btnRun = document.getElementById('btn-run');
  const btnDemo = document.getElementById('btn-demo');

  try {
    const saved = localStorage.getItem('nnbom_tool_evolution_repo_list');
    if (saved && input) input.value = saved;
  } catch {}

  const run = () => {
    const raw = (input && input.value) || '';
    const lines = raw.split('\n').map(normalizeRepoLine).filter(Boolean);
    const unique = Array.from(new Set(lines));
    if (unique.length === 0) {
      toast('<strong>Empty</strong> list. Add at least one repo like owner/repo');
      return;
    }
    try {
      localStorage.setItem('nnbom_tool_evolution_repo_list', raw);
    } catch {}
    if (out) {
      out.innerHTML = `
        <div class="placeholder-title">Example report (placeholder)</div>
        <div class="placeholder-sub">Input accepted: <strong>${unique.length}</strong> repos. Replace this example with local execution results later.</div>
        <div class="example-figure" aria-label="Example figure">
          <svg viewBox="0 0 640 180" role="img" aria-label="Example: new components introduced by a batch of repositories">
            <defs>
              <linearGradient id="g2_dyn" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#64ffda" stop-opacity="0.45"/>
                <stop offset="1" stop-color="#64ffda" stop-opacity="0.12"/>
              </linearGradient>
            </defs>
            <rect x="12" y="14" width="616" height="152" rx="14" fill="rgba(10,25,47,0.25)" stroke="rgba(100,255,218,0.14)"/>
            <text x="28" y="44" fill="rgba(204,214,246,0.92)" font-size="14" font-weight="700">New components introduced (example)</text>
            <text x="28" y="70" fill="rgba(136,146,176,0.92)" font-size="12">New TPLs</text>
            <rect x="120" y="60" width="210" height="12" rx="6" fill="url(#g2_dyn)"/>
            <text x="616" y="70" text-anchor="end" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">94</text>

            <text x="28" y="98" fill="rgba(136,146,176,0.92)" font-size="12">New PTMs</text>
            <rect x="120" y="88" width="98" height="12" rx="6" fill="rgba(136,146,176,0.35)"/>
            <text x="616" y="98" text-anchor="end" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">44</text>

            <text x="28" y="126" fill="rgba(136,146,176,0.92)" font-size="12">New Modules</text>
            <rect x="120" y="116" width="420" height="12" rx="6" fill="url(#g2_dyn)"/>
            <text x="616" y="126" text-anchor="end" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">6,545</text>
          </svg>
        </div>
        <div class="example-report">
          <p><strong>Example (multi-repository analysis):</strong> We examine repositories added in <strong>December 2024</strong> using the NNBOM constructed from data before <strong>November 2024</strong>. The tool identifies <strong>94</strong> previously unseen TPLs, <strong>44</strong> new PTMs, and <strong>6,545</strong> new Modules introduced by these repositories.</p>
          <p>Among a total of <strong>14,467</strong> Modules in this batch, <strong>45.2%</strong> are original creations, highlighting a notable level of innovation.</p>
        </div>
      `;
    }
    toast('Saved. Example output updated.');
  };

  if (btnRun) btnRun.addEventListener('click', run);
  if (btnDemo) btnDemo.addEventListener('click', () => {
    if (!input) return;
    input.value = ['pytorch/vision', 'tensorflow/models', 'huggingface/transformers', 'ultralytics/ultralytics'].join('\n');
    toast('Demo filled.');
  });
});
