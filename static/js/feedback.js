// Feedback form.
(function () {
  const form = document.getElementById('feedbackForm');
  const stars = document.querySelectorAll('#ratingStars .star');
  const ratingInput = document.getElementById('ratingInput');
  const status = document.getElementById('formStatus');

  stars.forEach((s) => {
    s.addEventListener('click', () => {
      const val = parseInt(s.dataset.value, 10);
      ratingInput.value = val;
      stars.forEach((x) => x.classList.toggle('active', parseInt(x.dataset.value, 10) <= val));
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    status.className = 'form-status';
    status.textContent = '';
    const fd = new FormData(form);
    const payload = {};
    fd.forEach((v, k) => (payload[k] = v));
    if (!payload.rating) {
      status.className = 'form-status error';
      status.textContent = 'Please pick a rating.';
      return;
    }
    try {
      const r = await fetch('/api/feedback/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Could not submit');
      status.className = 'form-status success';
      status.textContent = data.message;
      if (window.g4uKeyEvent) {
        window.g4uKeyEvent('feedback_submit_success', {
          event_category: 'feedback',
          rating: parseInt(payload.rating, 10) || 0,
        });
      }
      form.reset();
      stars.forEach((x) => x.classList.remove('active'));
    } catch (err) {
      status.className = 'form-status error';
      status.textContent = err.message;
    }
  });
})();
