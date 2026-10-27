/* Shared teaching widgets. All feedback is local; no model or evaluation pipeline runs. */
(() => {
  const root = document.documentElement;
  let saved;
  try { saved = localStorage.getItem('procurement-learning-theme'); } catch (_) {}
  const theme = new URLSearchParams(location.search).get('theme');
  root.dataset.theme = ['light','dark'].includes(theme) ? theme : saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  if (['light','dark'].includes(theme)) {
    try { localStorage.setItem('procurement-learning-theme', theme); } catch (_) {}
  }
  const toggle = document.querySelector('[data-theme-toggle]');
  function labelTheme() { if (toggle) toggle.textContent = root.dataset.theme === 'dark' ? 'Light theme' : 'Dark theme'; }
  labelTheme();
  toggle?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('procurement-learning-theme', root.dataset.theme); } catch (_) {}
    labelTheme();
  });
  document.querySelector('[data-print]')?.addEventListener('click', () => window.print());
  document.querySelectorAll('[data-quiz]').forEach(quiz => {
    quiz.addEventListener('change', () => {
      const selected = quiz.querySelector('input:checked');
      if (!selected) return;
      const correct = selected.value === quiz.dataset.answer;
      const feedback = quiz.querySelector('[data-feedback]');
      feedback.dataset.correct = String(correct);
      feedback.textContent = (correct ? 'Correct. ' : 'Try again. ') + (correct ? quiz.dataset.explanation : (quiz.dataset.hint || 'Locate the earliest failing step in this example, then choose its owner.'));
    });
  });
  document.querySelectorAll('[data-walkthrough]').forEach(walkthrough => {
    const buttons = walkthrough.querySelectorAll('[data-step-button]');
    const panels = walkthrough.querySelectorAll('[data-step-panel]');
    buttons.forEach(button => button.addEventListener('click', () => {
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      panels.forEach(panel => { panel.hidden = panel.dataset.stepPanel !== button.dataset.stepButton; });
    }));
  });
  const lab = document.querySelector('[data-retrieval-lab]');
  if (lab) {
    const update = () => {
      const selected = [...lab.querySelectorAll('input:checked')];
      const hits = selected.filter(input => input.dataset.relevant === 'true').length;
      lab.querySelector('[data-precision]').textContent = selected.length ? `${hits}/${selected.length} = ${Math.round(hits / selected.length * 100)}%` : '— (no results)';
      lab.querySelector('[data-recall]').textContent = `${hits}/2 = ${Math.round(hits / 2 * 100)}%`;
      lab.querySelector('[data-k]').textContent = selected.length;
      lab.querySelectorAll('input:not(:checked)').forEach(input => { input.disabled = selected.length >= 3; });
    };
    lab.addEventListener('change', update); update();
  }
})();
