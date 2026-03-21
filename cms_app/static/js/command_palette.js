document.addEventListener('DOMContentLoaded', function() {
  const modalEl = document.getElementById('commandPaletteModal');
  const inputEl = document.getElementById('commandPaletteInput');
  const resultsEl = document.getElementById('commandPaletteResults');
  const dataEl = document.getElementById('commandPaletteActions');
  if (!modalEl || !inputEl || !resultsEl || !dataEl) return;

  let modal = null;
  try {
    modal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });
  } catch (e) {
    modal = null;
  }
  if (!modal) return;

  let ACTIONS = [];
  try {
    ACTIONS = JSON.parse(dataEl.textContent || '[]') || [];
  } catch (e) {
    ACTIONS = [];
  }

  let activeIdx = -1;
  let currentItems = [];
  let debounceTimer = null;
  let lastFetchToken = 0;
  let actionsLoadPromise = null;

  function normalize(s) {
    return (s || '').toString().trim().toLowerCase();
  }

  function clearResults() {
    resultsEl.innerHTML = '';
    activeIdx = -1;
    currentItems = [];
  }

  function setActive(idx) {
    activeIdx = idx;
    const nodes = resultsEl.querySelectorAll('[data-cmd-idx]');
    nodes.forEach(n => {
      const i = Number(n.getAttribute('data-cmd-idx'));
      if (i === activeIdx) n.classList.add('active');
      else n.classList.remove('active');
    });
  }

  function render(items) {
    currentItems = items || [];
    resultsEl.innerHTML = '';
    activeIdx = -1;
    if (!currentItems.length) {
      const empty = document.createElement('div');
      empty.className = 'list-group-item text-muted';
      empty.textContent = 'No matches.';
      resultsEl.appendChild(empty);
      return;
    }
    currentItems.forEach((it, idx) => {
      const a = document.createElement('a');
      a.href = it.url || '#';
      a.className = 'list-group-item list-group-item-action';
      a.setAttribute('data-cmd-idx', String(idx));
      a.innerHTML = `<div class="d-flex justify-content-between align-items-center">
        <div>
          <div class="fw-semibold">${it.label || ''}</div>
          ${it.hint ? `<div class="small text-muted">${it.hint}</div>` : ''}
        </div>
        ${it.badge ? `<span class="badge text-bg-secondary">${it.badge}</span>` : ''}
      </div>`;
      a.addEventListener('mouseenter', () => setActive(idx));
      a.addEventListener('click', (e) => {
        if (!it.url) {
          e.preventDefault();
          return;
        }
        try { modal.hide(); } catch (err) {}
      });
      resultsEl.appendChild(a);
    });
    setActive(0);
  }

  function scoreAction(action, q) {
    const hay = normalize(`${action.label || ''} ${action.hint || ''} ${(action.tags || []).join(' ')}`);
    if (!hay) return 0;
    if (!q) return 1;
    if (hay === q) return 100;
    if (hay.startsWith(q)) return 80;
    if (hay.includes(q)) return 50;
    return 0;
  }

  function filterActions(q) {
    const query = normalize(q);
    const scored = ACTIONS.map(a => ({ a, s: scoreAction(a, query) })).filter(x => x.s > 0);
    scored.sort((x, y) => y.s - x.s);
    return scored.slice(0, 12).map(x => x.a);
  }

  function ensureActionsLoaded() {
    if (ACTIONS && ACTIONS.length) return Promise.resolve(ACTIONS);
    if (actionsLoadPromise) return actionsLoadPromise;
    actionsLoadPromise = fetch(`${window.location.origin}/api/command-palette/actions`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(body => {
        const items = (body && body.data && body.data.items) ? body.data.items : [];
        if (Array.isArray(items)) ACTIONS = items;
        return ACTIONS;
      })
      .catch(() => ACTIONS)
      .finally(() => { actionsLoadPromise = null; });
    return actionsLoadPromise;
  }

  function studentsUrl(enrollmentNo) {
    const params = new URLSearchParams({ enrollment_no: enrollmentNo, status: 'all' });
    return `${window.location.origin}/students?` + params.toString();
  }

  function fetchStudents(term) {
    const q = normalize(term);
    if (q.length < 2) return Promise.resolve([]);
    const token = ++lastFetchToken;
    const params = new URLSearchParams({ q: q, include_inactive: '1' });
    return fetch(`${window.location.origin}/api/students/search?` + params.toString())
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(body => {
        if (token !== lastFetchToken) return [];
        const items = (body && body.data && body.data.items) ? body.data.items : [];
        return (items || []).map(s => ({
          label: `${s.enrollment_no} — ${s.name || ''}`,
          hint: `${s.program_name || ''}${s.semester ? ` · Sem ${s.semester}` : ''}`,
          url: studentsUrl(s.enrollment_no),
          badge: 'Student'
        }));
      })
      .catch(() => []);
  }

  function buildResults(q) {
    const raw = (q || '').toString();
    const query = normalize(raw);
    return ensureActionsLoaded().then(() => {
      const actions = filterActions(query);
      if (query.startsWith('stu ') || query.startsWith('student ')) {
        const term = raw.replace(/^student\s+/i, '').replace(/^stu\s+/i, '').trim();
        return fetchStudents(term).then(stuItems => render([...stuItems, ...actions]));
      }
      if (query.startsWith('staff ') || query.startsWith('user ')) {
        const term = raw.replace(/^staff\s+/i, '').replace(/^user\s+/i, '').trim();
        const url = `${window.location.origin}/faculty?q=` + encodeURIComponent(term);
        const staffItem = term ? [{ label: `Search staff: ${term}`, hint: 'Opens Staff directory', url, badge: 'Staff' }] : [];
        render([...staffItem, ...actions]);
        return Promise.resolve();
      }
      render(actions);
      return Promise.resolve();
    });
  }

  function open() {
    try { modal.show(); } catch (e) {}
    setTimeout(() => { try { inputEl.focus(); inputEl.select(); } catch (e) {} }, 50);
    buildResults(inputEl.value || '');
  }

  try { window.openCommandPalette = open; } catch (e) {}

  function isTypingTarget(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    return Boolean(el.isContentEditable);
  }

  document.addEventListener('keydown', function(e) {
    const key = (e.key || '').toLowerCase();
    const isK = key === 'k';
    const hasCtrl = e.ctrlKey || e.metaKey;
    if (hasCtrl && isK) {
      if (isTypingTarget(document.activeElement)) {
        e.preventDefault();
      } else {
        e.preventDefault();
      }
      open();
      return;
    }
    if (key === 'escape') {
      try { modal.hide(); } catch (err) {}
    }
  });

  document.querySelectorAll('[data-action="open-command-palette"]').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      open();
    });
  });

  inputEl.addEventListener('input', function() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { buildResults(inputEl.value || ''); }, 120);
  });

  modalEl.addEventListener('shown.bs.modal', function() {
    try { inputEl.focus(); inputEl.select(); } catch (e) {}
  });

  modalEl.addEventListener('hidden.bs.modal', function() {
    inputEl.value = '';
    clearResults();
  });

  inputEl.addEventListener('keydown', function(e) {
    const key = (e.key || '').toLowerCase();
    if (key === 'arrowdown') {
      e.preventDefault();
      const next = Math.min((activeIdx < 0 ? 0 : activeIdx + 1), currentItems.length - 1);
      setActive(next);
      return;
    }
    if (key === 'arrowup') {
      e.preventDefault();
      const prev = Math.max((activeIdx < 0 ? 0 : activeIdx - 1), 0);
      setActive(prev);
      return;
    }
    if (key === 'enter') {
      e.preventDefault();
      const item = currentItems[activeIdx];
      if (item && item.url) {
        window.location.href = item.url;
        try { modal.hide(); } catch (err) {}
      }
      return;
    }
  });
});
