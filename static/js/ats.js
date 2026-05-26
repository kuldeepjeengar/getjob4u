// ATS scanner client — supports role-based and JD-based scoring.
(function () {
  const form = document.getElementById('atsForm');
  const fileInput = document.getElementById('fileInput');
  const dropzone = document.getElementById('dropzone');
  const fileName = document.getElementById('fileName');
  const scanBtn = document.getElementById('scanBtn');
  const placeholder = document.getElementById('atsPlaceholder');
  const resultBox = document.getElementById('atsResult');
  const modeButtons = document.querySelectorAll('.ats-mode-toggle .med-btn');
  const rolePanel = document.querySelector('[data-panel="role"]');
  const jdPanel = document.querySelector('[data-panel="jd"]');
  const jdText = document.getElementById('jdText');

  let mode = 'role';

  modeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      mode = btn.dataset.mode;
      modeButtons.forEach((b) => b.classList.toggle('active', b === btn));
      rolePanel.hidden = mode !== 'role';
      jdPanel.hidden = mode !== 'jd';
    });
  });

  const MAX_FILE_BYTES = Math.floor(2.5 * 1024 * 1024);

  function validateFile(f) {
    if (!f) return true;
    if (f.size > MAX_FILE_BYTES) {
      alert('File is too large. Maximum size is 2.5 MB.');
      fileInput.value = '';
      fileName.textContent = '';
      return false;
    }
    return true;
  }

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0] && validateFile(fileInput.files[0])) {
      fileName.textContent = fileInput.files[0].name;
    }
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
    if (e.dataTransfer.files[0] && validateFile(e.dataTransfer.files[0])) {
      fileInput.files = e.dataTransfer.files;
      fileName.textContent = e.dataTransfer.files[0].name;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) {
      alert('Please upload a resume file first.');
      return;
    }
    if (mode === 'jd' && (!jdText.value || jdText.value.trim().length < 30)) {
      alert('Paste a job description (30+ characters) to use JD match mode.');
      return;
    }

    scanBtn.disabled = true;
    scanBtn.textContent = 'Scanning…';
    try {
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      let endpoint = '/api/ats/scan';
      if (mode === 'jd') {
        endpoint = '/api/ats/scan-jd';
        fd.append('jd_text', jdText.value);
      } else {
        fd.append('target_role', document.getElementById('targetRole').value);
      }
      const r = await fetch(endpoint, { method: 'POST', body: fd });
      if (r.status === 413) {
        // Reverse proxy (nginx / ALB / CloudFront) rejected the upload before it reached FastAPI.
        throw new Error('Your resume is too large for the server. Please upload a file under 2.5 MB.');
      }
      const raw = await r.text();
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        // server returned HTML / plain text instead of JSON — surface the real status
        const snippet = raw.slice(0, 120).replace(/\s+/g, ' ').trim();
        throw new Error(`Server returned ${r.status} ${r.statusText || ''} (not JSON). ${snippet ? 'Preview: ' + snippet : ''}`);
      }
      if (!r.ok) throw new Error(data.detail || `Scan failed (${r.status})`);
      renderResult(data);
      if (window.g4uKeyEvent) {
        window.g4uKeyEvent('ats_scan_success', {
          event_category: 'ats_scanner',
          mode: mode,
          target_role: data.target_role,
          score: Math.round(data.overall_score),
          grade: data.grade,
        });
      }
    } catch (err) {
      alert('Scan failed: ' + err.message);
    } finally {
      scanBtn.disabled = false;
      scanBtn.textContent = 'Scan resume';
    }
  });

  function renderResult(data) {
    // Belt-and-suspenders: set both the hidden attribute AND an inline display
    // so stale cached CSS (older builds where `.placeholder { display: flex }`
    // outranks `[hidden]`) can't keep the box visible.
    placeholder.hidden = true;
    placeholder.style.display = 'none';
    resultBox.hidden = false;
    resultBox.style.display = '';

    document.getElementById('scoreNum').textContent = Math.round(data.overall_score);
    document.getElementById('scoreGrade').textContent = data.grade;
    const targetLabel = data.target_role === 'custom_jd'
      ? 'custom job description'
      : data.target_role.replace(/_/g, ' ');
    document.getElementById('scoreSub').textContent =
      `${data.word_count} words · matched against: ${targetLabel}`;

    const circle = document.getElementById('scoreCircle');
    const color = data.overall_score >= 70 ? '#00d4b4' : data.overall_score >= 50 ? '#ffaa3c' : '#ff5a6b';
    circle.style.background = `conic-gradient(${color} ${data.overall_score}%, var(--bg-soft) 0%)`;

    const bd = document.getElementById('breakdown');
    bd.innerHTML = '';
    const labels = {
      keywords: data.target_role === 'custom_jd' ? 'JD keywords' : 'Role keywords',
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
