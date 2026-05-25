// Generic "copy from a node" buttons. Trigger via .copy-resume[data-target="id"].
(function () {
  document.querySelectorAll('.copy-resume').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.target;
      const node = document.getElementById(id);
      if (!node) return;
      navigator.clipboard.writeText(node.innerText).then(() => {
        const old = btn.textContent;
        btn.textContent = '✓ Copied';
        setTimeout(() => (btn.textContent = old), 1500);
        if (window.g4uKeyEvent) {
          window.g4uKeyEvent('resume_copy', {
            event_category: 'sample_resumes',
            resume_id: id,
          });
        }
      });
    });
  });
})();
