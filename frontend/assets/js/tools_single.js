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

function normalizeGitHubUrl(input) {
  const v = (input || '').trim();
  if (!v) return null;
  try {
    const u = new URL(v);
    if (u.hostname !== 'github.com') return null;
    const parts = u.pathname.split('/').filter(Boolean);
    if (parts.length < 2) return null;
    return `https://github.com/${parts[0]}/${parts[1]}`;
  } catch {
    // allow owner/repo input
    const m = v.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
    if (m) return `https://github.com/${m[1]}/${m[2]}`;
    return null;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('repo-url');
  const out = document.getElementById('output');
  const btnRun = document.getElementById('btn-run');
  const btnDemo = document.getElementById('btn-demo');

  try {
    const saved = localStorage.getItem('nnbom_tool_single_repo_url');
    if (saved && input) input.value = saved;
  } catch {}

  const run = () => {
    const url = normalizeGitHubUrl(input && input.value);
    if (!url) {
      toast('<strong>Invalid</strong> repo URL. Example: https://github.com/owner/repo');
      return;
    }
    try {
      localStorage.setItem('nnbom_tool_single_repo_url', url);
    } catch {}
    if (out) {
      out.innerHTML = `
        <div class="placeholder-title">Example report (placeholder)</div>
        <div class="placeholder-sub">Input accepted: <strong>${url}</strong>. Replace this example with local execution results later.</div>
        <div class="example-figure" aria-label="Example figure">
          <svg viewBox="0 0 640 180" role="img" aria-label="Example: TPL/PTM/Module composition and new vs reused modules">
            <defs>
              <linearGradient id="g1_dyn" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#64ffda" stop-opacity="0.45"/>
                <stop offset="1" stop-color="#64ffda" stop-opacity="0.12"/>
              </linearGradient>
            </defs>
            <rect x="12" y="14" width="616" height="152" rx="14" fill="rgba(10,25,47,0.25)" stroke="rgba(100,255,218,0.14)"/>
            <text x="28" y="44" fill="rgba(204,214,246,0.92)" font-size="14" font-weight="700">Component composition</text>
            <text x="28" y="64" fill="rgba(136,146,176,0.92)" font-size="12">TPLs</text>
            <rect x="92" y="54" width="250" height="12" rx="6" fill="url(#g1_dyn)"/>
            <text x="350" y="64" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">43</text>
            <text x="28" y="88" fill="rgba(136,146,176,0.92)" font-size="12">PTMs</text>
            <rect x="92" y="78" width="6" height="12" rx="6" fill="rgba(136,146,176,0.35)"/>
            <text x="350" y="88" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">0</text>
            <text x="28" y="112" fill="rgba(136,146,176,0.92)" font-size="12">Modules</text>
            <rect x="92" y="102" width="232" height="12" rx="6" fill="rgba(136,146,176,0.35)"/>
            <text x="350" y="112" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">40</text>

            <text x="410" y="64" fill="rgba(204,214,246,0.92)" font-size="14" font-weight="700">Modules breakdown</text>
            <text x="410" y="88" fill="rgba(136,146,176,0.92)" font-size="12">New</text>
            <rect x="458" y="78" width="150" height="12" rx="6" fill="url(#g1_dyn)"/>
            <text x="616" y="88" text-anchor="end" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">32</text>
            <text x="410" y="112" fill="rgba(136,146,176,0.92)" font-size="12">Reused</text>
            <rect x="458" y="102" width="38" height="12" rx="6" fill="rgba(136,146,176,0.35)"/>
            <text x="616" y="112" text-anchor="end" fill="rgba(204,214,246,0.92)" font-size="12" font-weight="700">8</text>
          </svg>
        </div>
        <div class="example-report">
          <p><strong>Example (single-repository analysis):</strong> Based on the API search for top-recommended repositories created after <strong>January 1, 2025</strong>, the repository <strong>test-time-training/ttt-video-dit</strong> stands out. Created on <strong>April 13, 2025</strong>, it has quickly gained <strong>1.6k stars</strong> and <strong>133 forks</strong>.</p>
          <p>This repository contains <strong>43 TPLs</strong>, <strong>no PTMs</strong>, and <strong>40 modules</strong>, of which <strong>32</strong> are newly created and <strong>8</strong> are reused. Among the reused modules, the oldest dates back to <strong>2020</strong>, while <strong>4</strong> were introduced in <strong>2024</strong>, indicating that reused modules typically originate from the preceding year.</p>
          <p>Notably, it introduces a new TPL, <strong>test-time-training</strong>, released on <strong>February 11, 2025</strong>, which provides support for test-time training kernels. According to our similarity analysis based on module composition, the most similar repository is <strong>Auto1111SDK/Auto1111SDK</strong>.</p>
        </div>
      `;
    }
    toast('Saved. Example output updated.');
  };

  if (btnRun) btnRun.addEventListener('click', run);
  if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
  if (btnDemo) btnDemo.addEventListener('click', () => {
    if (input) input.value = 'https://github.com/pytorch/vision';
    toast('Demo filled.');
  });
});
