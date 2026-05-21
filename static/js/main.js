// Site-wide JS — nav toggle, year, daily question refresh.
(function () {
  document.getElementById('year').textContent = new Date().getFullYear();

  const toggle = document.getElementById('navToggle');
  const nav = document.getElementById('primaryNav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => nav.classList.toggle('open'));
  }

  const dqBtn = document.getElementById('newQuestionBtn');
  const dq = document.getElementById('dailyQuestion');
  if (dqBtn && dq) {
    dqBtn.addEventListener('click', async () => {
      dqBtn.disabled = true;
      try {
        const r = await fetch('/api/daily-question');
        const data = await r.json();
        dq.textContent = data.question;
      } catch (e) {
        /* silent */
      } finally {
        dqBtn.disabled = false;
      }
    });
  }

  // Copy share link to clipboard (home hero share row)
  const copyLinkBtn = document.getElementById('copyLinkBtn');
  if (copyLinkBtn && navigator.clipboard) {
    copyLinkBtn.addEventListener('click', (e) => {
      e.preventDefault();
      navigator.clipboard.writeText('https://getjob4u.com').then(() => {
        const original = copyLinkBtn.textContent;
        copyLinkBtn.textContent = '✓';
        setTimeout(() => { copyLinkBtn.textContent = original; }, 1400);
      }).catch(() => { /* clipboard blocked — silent */ });
    });
  }

  // ATS scanner demo animation (home page)
  const demoStage = document.getElementById('atsDemoStage');
  if (demoStage) {
    const resumeMock = document.getElementById('resumeMock');
    const chips = demoStage.querySelectorAll('.kw-chip');
    const bars = resumeMock.querySelectorAll('.rb-line');
    const steps = demoStage.querySelectorAll('.demo-step');
    const scoreBadge = document.getElementById('atsScoreBadge');
    const scoreNum = scoreBadge.querySelector('.score-ring-num');
    const liveChip = document.getElementById('liveScoreChip');
    const liveNum = document.getElementById('liveScoreNum');
    const demoLabel = document.getElementById('demoLabel');
    const status = document.getElementById('demoStatus');
    const statusText = document.getElementById('demoStatusText');
    const sparkleBurst = document.getElementById('sparkleBurst');

    const START_SCORE = 42;
    const FINAL_SCORE = 98;
    let timers = [];
    let running = false;
    let liveScore = START_SCORE;

    function clearTimers() {
      timers.forEach((t) => clearTimeout(t));
      timers = [];
    }

    function setStep(idx) {
      steps.forEach((s, i) => {
        s.classList.toggle('is-active', i === idx);
        s.classList.toggle('is-done', i < idx);
      });
    }

    function setStatus(html, flash) {
      statusText.innerHTML = html;
      if (flash) {
        status.classList.remove('is-flash');
        // force reflow so animation can restart
        void status.offsetWidth;
        status.classList.add('is-flash');
      }
    }

    function bumpLiveScore(to) {
      const from = liveScore;
      const target = Math.min(FINAL_SCORE, to);
      const dur = 500;
      const start = performance.now();
      liveChip.classList.remove('is-pop');
      void liveChip.offsetWidth;
      liveChip.classList.add('is-pop');
      function tick(now) {
        const t = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - t, 3);
        liveNum.textContent = Math.round(from + (target - from) * eased);
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      liveScore = target;
    }

    function animateFinalScore(target, duration) {
      const start = performance.now();
      function tick(now) {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3);
        scoreNum.textContent = Math.round(eased * target);
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }

    function buildSparkles() {
      sparkleBurst.innerHTML = '';
      const count = 22;
      for (let i = 0; i < count; i++) {
        const s = document.createElement('span');
        s.className = 'sparkle';
        const angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
        const dist = 110 + Math.random() * 80;
        s.style.setProperty('--sx', `${Math.cos(angle) * dist}px`);
        s.style.setProperty('--sy', `${Math.sin(angle) * dist}px`);
        s.style.animationDelay = `${Math.random() * 0.12}s`;
        // alternate colors
        if (i % 3 === 0) {
          s.style.background = '#7c5cff';
          s.style.boxShadow = '0 0 10px rgba(124,92,255,0.9)';
        } else if (i % 3 === 1) {
          s.style.background = '#ffaa3c';
          s.style.boxShadow = '0 0 10px rgba(255,170,60,0.9)';
        }
        sparkleBurst.appendChild(s);
      }
    }

    function fireSparkles() {
      buildSparkles();
      sparkleBurst.classList.remove('is-bursting');
      void sparkleBurst.offsetWidth;
      sparkleBurst.classList.add('is-bursting');
    }

    function resetDemo() {
      clearTimers();
      demoStage.classList.remove('is-scanning', 'is-done');
      resumeMock.classList.remove('is-scanning');
      chips.forEach((c) => c.classList.remove('is-visible'));
      bars.forEach((b) => b.classList.remove('is-matched'));
      scoreBadge.classList.remove('is-visible');
      scoreNum.textContent = '0';
      steps.forEach((s) => s.classList.remove('is-active', 'is-done'));
      sparkleBurst.classList.remove('is-bursting');
      sparkleBurst.innerHTML = '';
      status.classList.remove('is-success');
      liveScore = START_SCORE;
      liveNum.textContent = String(START_SCORE);
      demoLabel.textContent = 'Live · scanning resume';
      setStatus('Initializing scan…');
    }

    function runDemo() {
      if (running) return;
      running = true;
      resetDemo();

      // Step 1 — scanning
      setStep(0);
      demoStage.classList.add('is-scanning');
      resumeMock.classList.add('is-scanning');
      timers.push(setTimeout(() => setStatus('Parsing sections, contact, and skills…'), 400));
      timers.push(setTimeout(() => setStatus(`Initial ATS score: <span class="pt">${START_SCORE}</span> · gaps detected`, true), 1500));

      // Step 2 — keyword chips land one-by-one with score bumps + bar flashes
      const chipStart = 2300;
      const chipGap = 380;
      timers.push(setTimeout(() => {
        setStep(1);
        demoLabel.textContent = 'Live · suggesting keywords';
      }, chipStart - 80));

      chips.forEach((chip, i) => {
        const pts = parseInt(chip.dataset.pts || '8', 10);
        const targetIdx = parseInt(chip.dataset.target || '-1', 10);
        const kw = chip.dataset.kw || 'keyword';
        timers.push(setTimeout(() => {
          chip.classList.add('is-visible');
          if (targetIdx >= 0 && bars[targetIdx]) {
            bars[targetIdx].classList.add('is-matched');
          }
          bumpLiveScore(liveScore + pts);
          setStatus(`Found <span class="pt">${kw}</span> · <span class="pt">+${pts}</span> pts`, true);
        }, chipStart + i * chipGap));
      });

      // Step 3 — applying changes
      const applyAt = chipStart + chips.length * chipGap + 200;
      timers.push(setTimeout(() => {
        setStep(2);
        resumeMock.classList.remove('is-scanning');
        demoLabel.textContent = 'Live · applying changes';
        setStatus('Rewriting bullets · quantifying impact…', true);
      }, applyAt));

      // Step 4 — final score reveal + sparkle burst
      const finalAt = applyAt + 1100;
      timers.push(setTimeout(() => {
        setStep(3);
        demoStage.classList.add('is-done');
        scoreBadge.classList.add('is-visible');
        animateFinalScore(FINAL_SCORE, 1100);
        fireSparkles();
        demoLabel.textContent = 'Optimized · max ATS score';
        status.classList.add('is-success');
        setStatus(`<span class="pt">Max ATS score 98/100</span> · Boost +${FINAL_SCORE - START_SCORE}`, true);
      }, finalAt));

      // Loop the demo
      timers.push(setTimeout(() => {
        running = false;
        runDemo();
      }, finalAt + 4200));
    }

    // Start only when scrolled into view (and respect reduced motion)
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      // Show the final state statically.
      chips.forEach((c) => c.classList.add('is-visible'));
      bars.forEach((b) => b.classList.add('is-matched'));
      steps.forEach((s) => s.classList.add('is-done'));
      scoreBadge.classList.add('is-visible');
      scoreNum.textContent = String(FINAL_SCORE);
      liveNum.textContent = String(FINAL_SCORE);
      demoStage.classList.add('is-done');
      demoLabel.textContent = 'Optimized · max ATS score';
      status.classList.add('is-success');
      setStatus(`<span class="pt">Max ATS score ${FINAL_SCORE}/100</span> · Boost +${FINAL_SCORE - START_SCORE}`);
    } else if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            runDemo();
          } else {
            running = false;
            clearTimers();
          }
        });
      }, { threshold: 0.3 });
      io.observe(demoStage);
    } else {
      runDemo();
    }
  }
})();
