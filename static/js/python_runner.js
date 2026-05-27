// Shared Python-runner module.
//
// Lazy-loads Pyodide + CodeMirror 5 from CDN on first use. Exposes a tiny
// API used by both the standalone /python-playground page and the inline
// "Run" buttons on each coding solution card.
//
// Usage:
//   await G4UPython.ensureReady(onProgress);
//   const editor = G4UPython.attachEditor(textareaEl);
//   const { stdout, stderr } = await G4UPython.run(editor.getValue());

(function () {
  'use strict';

  // ----- CDN URLs -----
  const PYODIDE_VERSION = 'v0.26.4';
  const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`;
  const PYODIDE_JS = `${PYODIDE_INDEX_URL}pyodide.js`;

  const CM_VERSION = '5.65.18';
  const CM_BASE = `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${CM_VERSION}`;
  const CM_RESOURCES = [
    { type: 'css', href: `${CM_BASE}/codemirror.min.css` },
    { type: 'css', href: `${CM_BASE}/theme/dracula.min.css` },
    { type: 'js',  src:  `${CM_BASE}/codemirror.min.js` },
    { type: 'js',  src:  `${CM_BASE}/mode/python/python.min.js` },
    { type: 'js',  src:  `${CM_BASE}/addon/edit/matchbrackets.min.js` },
    { type: 'js',  src:  `${CM_BASE}/addon/edit/closebrackets.min.js` },
    { type: 'js',  src:  `${CM_BASE}/addon/comment/comment.min.js` },
  ];

  // ----- State -----
  let pyodide = null;
  let pyodideLoadingPromise = null;
  let cmLoadingPromise = null;

  // ----- Internal: dynamic CSS / JS loading -----
  function loadCss(href) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`link[href="${href}"]`)) return resolve();
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.onload = resolve;
      link.onerror = () => reject(new Error(`failed to load CSS: ${href}`));
      document.head.appendChild(link);
    });
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) return resolve();
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error(`failed to load script: ${src}`));
      document.head.appendChild(script);
    });
  }

  // ----- Public: ensureCodeMirror -----
  function ensureCodeMirror() {
    if (window.CodeMirror && window.CodeMirror.modes && window.CodeMirror.modes.python) {
      return Promise.resolve(window.CodeMirror);
    }
    if (cmLoadingPromise) return cmLoadingPromise;

    cmLoadingPromise = (async () => {
      // CSS in parallel; JS sequentially because addons depend on the core.
      await Promise.all(CM_RESOURCES.filter(r => r.type === 'css').map(r => loadCss(r.href)));
      for (const r of CM_RESOURCES.filter(r => r.type === 'js')) {
        await loadScript(r.src);
      }
      return window.CodeMirror;
    })();
    return cmLoadingPromise;
  }

  // ----- Public: ensureReady (Pyodide) -----
  function ensureReady(onProgress) {
    if (pyodide) return Promise.resolve(pyodide);
    if (pyodideLoadingPromise) {
      if (onProgress) onProgress('attaching');
      return pyodideLoadingPromise;
    }

    pyodideLoadingPromise = (async () => {
      if (onProgress) onProgress('Loading Pyodide runtime…');
      await loadScript(PYODIDE_JS);
      if (onProgress) onProgress('Initializing Python interpreter (one-time, ~5s)…');
      // `loadPyodide` is attached to window by pyodide.js
      pyodide = await window.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
      if (onProgress) onProgress('Ready.');
      return pyodide;
    })().catch((err) => {
      pyodideLoadingPromise = null;
      throw err;
    });

    return pyodideLoadingPromise;
  }

  // ----- Public: run -----
  async function run(code) {
    if (!pyodide) {
      throw new Error('Pyodide not initialized — call ensureReady() first.');
    }
    let stdout = '';
    let stderr = '';
    pyodide.setStdout({ batched: (t) => { stdout += t + '\n'; } });
    pyodide.setStderr({ batched: (t) => { stderr += t + '\n'; } });
    let value;
    try {
      // Use async runner so users can `await` if they want
      value = await pyodide.runPythonAsync(code);
    } catch (err) {
      // PythonError exposes message; surface the traceback as stderr
      stderr += (err && err.message) ? err.message : String(err);
    }
    // Reset to defaults so other code on the page isn't affected
    pyodide.setStdout({});
    pyodide.setStderr({});
    return {
      stdout: stdout.replace(/\n+$/, ''),
      stderr: stderr.replace(/\n+$/, ''),
      value: value !== undefined && value !== null ? String(value) : '',
    };
  }

  // ----- Public: attachEditor -----
  // Replaces a <textarea> with a CodeMirror instance configured for Python.
  // Returns the CodeMirror handle.
  async function attachEditor(textarea, options) {
    const CM = await ensureCodeMirror();
    const opts = Object.assign({
      mode: 'python',
      theme: 'dracula',
      lineNumbers: true,
      matchBrackets: true,
      autoCloseBrackets: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      lineWrapping: true,
      extraKeys: {
        Tab: (cm) => cm.replaceSelection('    ', 'end'),
        'Ctrl-Enter': () => { /* handler set by caller */ },
        'Cmd-Enter':  () => { /* handler set by caller */ },
      },
    }, options || {});
    return CM.fromTextArea(textarea, opts);
  }

  // ----- Expose -----
  window.G4UPython = { ensureReady, ensureCodeMirror, attachEditor, run };
})();
