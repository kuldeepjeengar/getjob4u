// Cold email + LinkedIn DM generator client.
(function () {
  const templates = window.__TEMPLATES__;
  const select = document.getElementById('templateKey');
  const form = document.getElementById('emailForm');
  const msgBox = document.getElementById('msgBox');
  const actions = document.getElementById('outputActions');
  const copyBtn = document.getElementById('copyBtn');
  const regenerateBtn = document.getElementById('regenerateBtn');
  const medButtons = document.querySelectorAll('.med-btn');
  let currentMedium = 'email';
  let lastPayload = null;

  function refreshTemplates() {
    select.innerHTML = '';
    templates[currentMedium].forEach((t) => {
      const opt = document.createElement('option');
      opt.value = t.value;
      opt.textContent = t.label;
      select.appendChild(opt);
    });
    document.querySelectorAll('.alumni-field').forEach((f) => (f.hidden = true));
    document.querySelectorAll('.recruiter-field').forEach((f) => (f.hidden = true));
  }

  select.addEventListener('change', () => {
    const v = select.value;
    document.querySelectorAll('.alumni-field').forEach((f) => (f.hidden = v !== 'alumni_outreach'));
    document.querySelectorAll('.recruiter-field').forEach((f) => (f.hidden = v !== 'recruiter_response'));
  });

  medButtons.forEach((b) =>
    b.addEventListener('click', () => {
      medButtons.forEach((x) => x.classList.toggle('active', x === b));
      currentMedium = b.dataset.medium;
      refreshTemplates();
    })
  );

  refreshTemplates();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = { medium: currentMedium };
    fd.forEach((v, k) => (payload[k] = v));
    lastPayload = payload;
    await generate(payload);
  });

  regenerateBtn.addEventListener('click', () => {
    if (lastPayload) generate(lastPayload);
  });

  async function generate(payload) {
    try {
      const r = await fetch('/api/email/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Failed to generate');
      renderMessage(data);
    } catch (err) {
      alert(err.message);
    }
  }

  function renderMessage(data) {
    if (data.medium === 'email') {
      msgBox.innerHTML = '';
      const subj = document.createElement('div');
      subj.className = 'msg-subject';
      subj.textContent = 'Subject: ' + data.subject;
      msgBox.appendChild(subj);
      const body = document.createElement('div');
      body.textContent = data.body;
      msgBox.appendChild(body);
    } else {
      msgBox.textContent = data.message;
    }
    actions.hidden = false;
  }

  copyBtn.addEventListener('click', () => {
    const text = msgBox.innerText;
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = '✓ Copied';
      setTimeout(() => (copyBtn.textContent = '📋 Copy'), 1500);
    });
  });
})();
