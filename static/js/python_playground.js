// Standalone /python-playground page logic.
// Wires up CodeMirror editor, the Run button, presets, and output panel
// against the shared G4UPython runner.
(function () {
  'use strict';

  const ta = document.getElementById('playgroundEditor');
  if (!ta) return;

  const runBtn = document.getElementById('runBtn');
  const resetBtn = document.getElementById('resetBtn');
  const clearBtn = document.getElementById('clearOutputBtn');
  const presetSel = document.getElementById('presetSelect');
  const outEl = document.getElementById('playgroundOutput');
  const statusEl = document.getElementById('runStatus');
  const spinner = runBtn.querySelector('.run-spinner');
  const runText = runBtn.querySelector('.run-text');

  const INITIAL_CODE = ta.value;
  const STORAGE_KEY = 'g4u.playground.code';

  // ----- Presets -----
  const PRESETS = {
    hello:
`print("Hello, World!")
name = "Ada"
print(f"My name is {name} and I am {len(name) * 4} years old (not really).")`,

    fib:
`# Fibonacci generator — O(1) memory
def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

from itertools import islice
print(list(islice(fib(), 15)))
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]`,

    fizzbuzz:
`# Classic FizzBuzz
for n in range(1, 21):
    if n % 15 == 0:
        print("FizzBuzz")
    elif n % 3 == 0:
        print("Fizz")
    elif n % 5 == 0:
        print("Buzz")
    else:
        print(n)`,

    twosum:
`# Two Sum — return indices of the two numbers that add up to target
def twoSum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i

print(twoSum([2, 7, 11, 15], 9))   # [0, 1]
print(twoSum([3, 2, 4], 6))         # [1, 2]
print(twoSum([3, 3], 6))            # [0, 1]`,

    counter:
`# Word frequency with collections.Counter
from collections import Counter

text = """the quick brown fox jumps over the lazy dog
the lazy dog sleeps while the quick fox watches"""

words = text.lower().split()
print("Total words:", len(words))
print("Unique words:", len(set(words)))
print("Top 5:", Counter(words).most_common(5))`,

    deepcopy:
`# The mutable default argument trap — a classic Python gotcha
def buggy(item, bag=[]):       # BAD: bag is shared across calls!
    bag.append(item)
    return bag

print(buggy(1))   # [1]
print(buggy(2))   # [1, 2]  -- surprise!
print(buggy(3))   # [1, 2, 3]

def fixed(item, bag=None):
    if bag is None:
        bag = []          # fresh list each call
    bag.append(item)
    return bag

print("---")
print(fixed(1))   # [1]
print(fixed(2))   # [2]
print(fixed(3))   # [3]`,

    dataclass:
`from dataclasses import dataclass, field
from typing import List

@dataclass
class Cart:
    owner: str
    items: List[str] = field(default_factory=list)   # safe mutable default
    discount: float = 0.0

c = Cart("Ada")
c.items.append("apple")
c.items.append("banana")
print(c)
# Cart(owner='Ada', items=['apple', 'banana'], discount=0.0)`,

    decorator:
`# A simple timing decorator
import time
from functools import wraps

def timed(fn):
    @wraps(fn)
    def wrap(*a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"  ⏱ {fn.__name__} took {elapsed:.3f} ms")
    return wrap

@timed
def slow_sum(n):
    return sum(i * i for i in range(n))

print("result =", slow_sum(1_000_000))`,
  };

  // ----- Editor (lazy: only create when CodeMirror is loaded) -----
  let cm = null;
  function getCode() { return cm ? cm.getValue() : ta.value; }
  function setCode(s) {
    if (cm) cm.setValue(s);
    else    ta.value = s;
  }

  // Initialize CodeMirror in the background so the editor is upgraded
  // even before the user clicks "Run" (snappier feel, ~150 KB).
  G4UPython.attachEditor(ta).then((editor) => {
    cm = editor;
    cm.setOption('extraKeys', Object.assign({}, cm.getOption('extraKeys'), {
      'Ctrl-Enter': () => runCode(),
      'Cmd-Enter':  () => runCode(),
    }));
    // Persisted draft
    const draft = localStorage.getItem(STORAGE_KEY);
    if (draft && draft.trim()) cm.setValue(draft);
    cm.on('change', () => {
      try { localStorage.setItem(STORAGE_KEY, cm.getValue()); } catch (e) {}
    });
  }).catch((err) => {
    setStatus('Editor load failed — using plain textarea: ' + err.message, 'err');
  });

  // ----- UI helpers -----
  function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.classList.remove('is-ok', 'is-err', 'is-busy');
    if (kind) statusEl.classList.add('is-' + kind);
  }
  function setRunning(yes) {
    runBtn.disabled = yes;
    spinner.hidden = !yes;
    runText.textContent = yes ? 'Running…' : 'Run';
  }
  function appendOutput(text, kind) {
    if (!text) return;
    const span = document.createElement('span');
    if (kind) span.className = 'out-' + kind;
    span.textContent = text;
    outEl.appendChild(span);
    outEl.appendChild(document.createTextNode('\n'));
    outEl.scrollTop = outEl.scrollHeight;
  }

  // ----- Run -----
  async function runCode() {
    const code = getCode();
    if (!code.trim()) {
      setStatus('Nothing to run', 'err');
      return;
    }
    setRunning(true);
    setStatus('Loading runtime…', 'busy');
    try {
      await G4UPython.ensureReady((msg) => setStatus(msg, 'busy'));
      const t0 = performance.now();
      setStatus('Running…', 'busy');
      const { stdout, stderr } = await G4UPython.run(code);
      const elapsed = (performance.now() - t0).toFixed(0);

      // Separator between runs
      if (outEl.textContent.trim()) {
        const sep = document.createElement('span');
        sep.className = 'out-sep';
        sep.textContent = '─'.repeat(48) + '\n';
        outEl.appendChild(sep);
      }
      if (stdout) appendOutput(stdout, 'stdout');
      if (stderr) appendOutput(stderr, 'stderr');
      if (!stdout && !stderr) appendOutput('(no output)', 'muted');

      setStatus(`Done in ${elapsed} ms` + (stderr ? ' · with error' : ''), stderr ? 'err' : 'ok');
      if (window.g4uTrack) {
        window.g4uTrack('playground_run', { event_category: 'playground', event_label: stderr ? 'error' : 'ok' });
      }
    } catch (err) {
      appendOutput(err && err.message ? err.message : String(err), 'stderr');
      setStatus('Runtime error', 'err');
    } finally {
      setRunning(false);
    }
  }

  runBtn.addEventListener('click', runCode);
  resetBtn.addEventListener('click', () => {
    setCode(INITIAL_CODE);
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
    setStatus('Reset to initial code', 'ok');
  });
  clearBtn.addEventListener('click', () => {
    outEl.textContent = '';
    setStatus('Output cleared', 'ok');
  });
  presetSel.addEventListener('change', (e) => {
    const key = e.target.value;
    if (!key) return;
    const snippet = PRESETS[key];
    if (snippet) {
      setCode(snippet);
      setStatus(`Loaded "${e.target.selectedOptions[0].text}"`, 'ok');
    }
    e.target.value = '';
  });
})();
