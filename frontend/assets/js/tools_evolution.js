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
        <div class="placeholder-title">Queued (prototype)</div>
        <div class="placeholder-sub">Repos: <strong>${unique.length}</strong><br/>${unique.slice(0, 10).join('<br/>')}${unique.length > 10 ? '<br/>…' : ''}<br/><br/>Next: connect to analytics aggregation for this subset.</div>
      `;
    }
    toast('Saved. Prototype output updated.');
  };

  if (btnRun) btnRun.addEventListener('click', run);
  if (btnDemo) btnDemo.addEventListener('click', () => {
    if (!input) return;
    input.value = ['pytorch/vision', 'tensorflow/models', 'huggingface/transformers', 'ultralytics/ultralytics'].join('\n');
    toast('Demo filled.');
  });
});

