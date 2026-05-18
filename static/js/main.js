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
})();
