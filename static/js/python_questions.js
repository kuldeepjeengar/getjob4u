// Python interview questions page — tabs (coding/theory), filter, search, copy.
(function () {
  'use strict';

  // -------- Shared utilities --------

  function buildFilter(scope) {
    // `scope` is "coding" or "theory" — drives a self-contained filter setup
    // for a single panel.
    const cfg = scope === 'theory'
      ? { list: 'pyqTheoryList', empty: 'pyqTheoryEmpty',
          count: 'pyqTheoryCount', search: 'pyqTheorySearch',
          noun: 'theory question', plural: 'theory questions' }
      : { list: 'pyqList', empty: 'pyqEmpty',
          count: 'pyqCount', search: 'pyqSearch',
          noun: 'question', plural: 'questions' };

    const listEl = document.getElementById(cfg.list);
    if (!listEl) return null;

    const cards = Array.from(listEl.querySelectorAll('.pyq-card'));
    const emptyEl = document.getElementById(cfg.empty);
    const countEl = document.getElementById(cfg.count);
    const searchEl = document.getElementById(cfg.search);
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
      countEl.textContent = visible + ' ' + (visible === 1 ? cfg.noun : cfg.plural);
      emptyEl.hidden = visible !== 0;
    }

    // Filter-chip groups scoped to this panel
    document.querySelectorAll('.filter-chips[data-scope="' + scope + '"]').forEach((group) => {
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
    if (searchEl) {
      searchEl.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          state.q = searchEl.value;
          apply();
          if (state.q && window.g4uTrack) {
            window.g4uTrack('pyq_search', {
              event_category: 'python_questions',
              event_label: scope + ':' + state.q.slice(0, 40),
            });
          }
        }, 180);
      });
    }

    return { apply, listEl };
  }

  // -------- Initialize both panels --------
  const coding = buildFilter('coding');
  const theory = buildFilter('theory');
  if (!coding && !theory) return;

  // -------- Tab switching --------
  const tabs = document.querySelectorAll('.pyq-tab');
  const panels = document.querySelectorAll('.pyq-panel');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      tabs.forEach((t) => {
        const active = t === tab;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      panels.forEach((p) => {
        const match = p.dataset.panel === target;
        p.classList.toggle('is-active', match);
        p.hidden = !match;
      });
    });
  });

  // -------- Copy-solution buttons (shared across both panels) --------
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.pyq-copy-btn');
    if (!btn) return;
    e.preventDefault();
    const card = btn.closest('.pyq-card');
    const code = card && card.querySelector('pre.pyq-code code');
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

  // -------- Inline Run buttons --------
  // First click on a card's Run swaps the static <pre> for a CodeMirror
  // editor, lazy-loads Pyodide, runs the code, and shows output below.
  // Subsequent clicks just re-run the current editor contents.
  const cardState = new WeakMap();   // card -> { editor, panel, output, status, originalCode }

  function setRunUi(card, running) {
    const btn = card.querySelector('.pyq-run-btn');
    if (!btn) return;
    btn.disabled = running;
    btn.classList.toggle('is-running', running);
    const text = btn.querySelector('.pyq-run-text');
    if (text) text.textContent = running ? 'Running…' : 'Run';
  }

  function setStatus(card, msg, kind) {
    const status = card.querySelector('.pyq-run-status');
    if (!status) return;
    status.textContent = msg;
    status.classList.remove('is-ok', 'is-err', 'is-busy');
    if (kind) status.classList.add('is-' + kind);
  }

  function appendOutput(outEl, text, kind) {
    if (!text) return;
    const span = document.createElement('span');
    if (kind) span.className = 'out-' + kind;
    span.textContent = text;
    outEl.appendChild(span);
    outEl.appendChild(document.createTextNode('\n'));
    outEl.scrollTop = outEl.scrollHeight;
  }

  async function initCard(card) {
    const pre = card.querySelector('pre.pyq-code');
    const codeEl = pre && pre.querySelector('code');
    const panel = card.querySelector('.pyq-run-panel');
    if (!pre || !codeEl || !panel) return null;

    const originalCode = codeEl.innerText;

    // Replace the <pre> with a <textarea> so CodeMirror can attach.
    const ta = document.createElement('textarea');
    ta.className = 'pyq-run-editor';
    ta.spellcheck = false;
    ta.value = originalCode;
    pre.replaceWith(ta);

    panel.hidden = false;
    const output = panel.querySelector('.pyq-run-output');

    let editor = null;
    try {
      editor = await G4UPython.attachEditor(ta);
      editor.setOption('extraKeys', Object.assign({}, editor.getOption('extraKeys') || {}, {
        'Ctrl-Enter': () => doRun(card),
        'Cmd-Enter':  () => doRun(card),
      }));
    } catch (err) {
      // Editor failed to load — fall back to textarea
      setStatus(card, 'Editor failed; using plain textarea', 'err');
    }

    const state = { editor, panel, output, originalCode };
    cardState.set(card, state);
    return state;
  }

  async function doRun(card) {
    let state = cardState.get(card);
    if (!state) state = await initCard(card);
    if (!state) return;

    const code = state.editor ? state.editor.getValue() : card.querySelector('.pyq-run-editor').value;
    setRunUi(card, true);
    setStatus(card, 'Loading runtime…', 'busy');

    try {
      await G4UPython.ensureReady((msg) => setStatus(card, msg, 'busy'));
      setStatus(card, 'Running…', 'busy');
      const t0 = performance.now();
      const { stdout, stderr } = await G4UPython.run(code);
      const elapsed = (performance.now() - t0).toFixed(0);

      if (state.output.textContent.trim()) {
        const sep = document.createElement('span');
        sep.className = 'out-sep';
        sep.textContent = '─'.repeat(40) + '\n';
        state.output.appendChild(sep);
      }
      if (stdout) appendOutput(state.output, stdout, 'stdout');
      if (stderr) appendOutput(state.output, stderr, 'stderr');
      if (!stdout && !stderr) {
        appendOutput(state.output, '(no output — the snippet defines code but does not call it. Add a function call and print() the result.)', 'muted');
      }
      setStatus(card, `Done in ${elapsed} ms` + (stderr ? ' · with error' : ''), stderr ? 'err' : 'ok');
    } catch (err) {
      appendOutput(state.output, err && err.message ? err.message : String(err), 'stderr');
      setStatus(card, 'Runtime error', 'err');
    } finally {
      setRunUi(card, false);
    }
  }

  document.body.addEventListener('click', (e) => {
    const runBtn = e.target.closest('.pyq-run-btn');
    if (runBtn) {
      e.preventDefault();
      const card = runBtn.closest('.pyq-card');
      if (card) doRun(card);
      return;
    }
    const closeBtn = e.target.closest('.pyq-run-close');
    if (closeBtn) {
      const panel = closeBtn.closest('.pyq-run-panel');
      if (panel) panel.hidden = true;
    }
  });
})();
