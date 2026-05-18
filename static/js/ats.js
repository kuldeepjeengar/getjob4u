// ATS scanner client.
(function () {
  const form = document.getElementById('atsForm');
  const fileInput = document.getElementById('fileInput');
  const dropzone = document.getElementById('dropzone');
  const fileName = document.getElementById('fileName');
  const scanBtn = document.getElementById('scanBtn');
  const placeholder = document.getElementById('atsPlaceholder');
  const resultBox = document.getElementById('atsResult');

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) fileName.textContent = fileInput.files[0].name;
  });

  ['dragenter', 'dragover'].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    })
  );
  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files[0]) {
      fileInput.files = e.dataTransfer.files;
      fileName.textContent = e.dataTransfer.files[0].name;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return;
    scanBtn.disabled = true;
    scanBtn.textContent = 'Scanning…';
    try {
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('target_role', document.getElementById('targetRole').value);
      const r = await fetch('/api/ats/scan', { method: 'POST', body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Scan failed');
      renderResult(data);
    } catch (err) {
      alert('Scan failed: ' + err.message);
    } finally {
      scanBtn.disabled = false;
      scanBtn.textContent = 'Scan resume';
    }
  });

  function renderResult(data) {
    placeholder.hidden = true;
    resultBox.hidden = false;

    document.getElementById('scoreNum').textContent = Math.round(data.overall_score);
    document.getElementById('scoreGrade').textContent = data.grade;
    document.getElementById('scoreSub').textContent = `${data.word_count} words · target role: ${data.target_role.replace('_', ' ')}`;

    const circle = document.getElementById('scoreCircle');
    const color = data.overall_score >= 70 ? '#00d4b4' : data.overall_score >= 50 ? '#ffaa3c' : '#ff5a6b';
    circle.style.background = `conic-gradient(${color} ${data.overall_score}%, var(--bg-soft) 0%)`;

    const bd = document.getElementById('breakdown');
    bd.innerHTML = '';
    const labels = {
      keywords: 'Role keywords',
      sections: 'Resume sections',
      contact: 'Contact info',
      action_verbs: 'Action verbs',
      quantification: 'Quantified impact',
      length: 'Length',
    };
    Object.entries(data.breakdown).forEach(([key, val]) => {
      const row = document.createElement('div');
      row.className = 'bd-row';
      row.innerHTML = `
        <div>
          <div class="bd-name">${labels[key] || key}</div>
          <div class="bd-meta">${val.label}</div>
        </div>
        <div class="bd-meta"><strong>${Math.round(val.score)}</strong>/100</div>
        <div class="bd-bar"><div class="bd-bar-fill" style="width:${val.score}%"></div></div>
      `;
      bd.appendChild(row);
    });

    const sug = document.getElementById('suggestions');
    sug.innerHTML = '';
    data.suggestions.forEach((s) => {
      const li = document.createElement('li');
      li.textContent = s;
      sug.appendChild(li);
    });

    const matched = document.getElementById('matchedKw');
    const missing = document.getElementById('missingKw');
    matched.innerHTML = '';
    missing.innerHTML = '';
    data.matched_keywords.forEach((k) => {
      const s = document.createElement('span');
      s.textContent = k;
      matched.appendChild(s);
    });
    data.missing_keywords.forEach((k) => {
      const s = document.createElement('span');
      s.textContent = k;
      missing.appendChild(s);
    });

    resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
})();
