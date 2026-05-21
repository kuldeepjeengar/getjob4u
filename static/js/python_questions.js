// Python coding questions page — filter, search, copy.
(function () {
  'use strict';

  const list = document.getElementById('pyqList');
  if (!list) return;

  const cards = Array.from(list.querySelectorAll('.pyq-card'));
  const empty = document.getElementById('pyqEmpty');
  const countEl = document.getElementById('pyqCount');
  const search = document.getElementById('pyqSearch');

  const state = { difficulty: 'all', category: 'all', q: '' };

  function apply() {
    let visible = 0;
    const q = state.q.trim().toLowerCase();
    cards.forEach((card) => {
      const okDiff = state.difficulty === 'all' || card.dataset.difficulty === state.difficulty;
      const okCat  = state.category   === 'all' || card.dataset.category   === state.category;
      const okQ    = !q || card.dataset.search.includes(q);
      const show = okDiff && okCat && okQ;
      card.hidden = !show;
      if (show) visible += 1;
    });
    countEl.textContent = visible + (visible === 1 ? ' question' : ' questions');
    empty.hidden = visible !== 0;
  }

  // Filter-chip groups
  document.querySelectorAll('.filter-chips').forEach((group) => {
    const filter = group.dataset.filter; // "difficulty" | "category"
    group.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-chip');
      if (!btn) return;
      group.querySelectorAll('.filter-chip').forEach((b) => b.classList.toggle('is-active', b === btn));
      state[filter] = btn.dataset.value;
      apply();
    });
  });

  // Live search
  let searchTimer = null;
  search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.q = search.value;
      apply();
      if (state.q && window.g4uTrack) {
        window.g4uTrack('pyq_search', { event_category: 'python_questions', event_label: state.q.slice(0, 40) });
      }
    }, 180);
  });

  // Copy-solution buttons
  list.addEventListener('click', (e) => {
    const btn = e.target.closest('.pyq-copy-btn');
    if (!btn) return;
    e.preventDefault();
    const card = btn.closest('.pyq-card');
    const code = card.querySelector('pre.pyq-code code');
    if (!code || !navigator.clipboard) return;
    navigator.clipboard.writeText(code.innerText).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copied ✓';
      btn.classList.add('is-copied');
      setTimeout(() => {
        btn.textContent = orig;
        btn.classList.remove('is-copied');
      }, 1400);
    }).catch(() => { /* clipboard blocked — silent */ });
  });
})();
