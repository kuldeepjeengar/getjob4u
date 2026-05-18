// Generic tabs. Buttons with data-tab="X" reveal panels with id="tab-X".
(function () {
  document.querySelectorAll('.tab-bar').forEach((bar) => {
    const buttons = bar.querySelectorAll('.tab');
    const container = bar.parentElement;
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        buttons.forEach((b) => b.classList.toggle('active', b === btn));
        container.querySelectorAll('.tip-panel').forEach((p) => {
          p.classList.toggle('active', p.id === `tab-${target}`);
        });
      });
    });
  });
})();
