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
        <div class="placeholder-title">Queued (prototype)</div>
        <div class="placeholder-sub">Repo: <strong>${url}</strong><br/>Next: connect this to backend analysis and render results here.</div>
      `;
    }
    toast('Saved. Prototype output updated.');
  };

  if (btnRun) btnRun.addEventListener('click', run);
  if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
  if (btnDemo) btnDemo.addEventListener('click', () => {
    if (input) input.value = 'https://github.com/pytorch/vision';
    toast('Demo filled.');
  });
});

