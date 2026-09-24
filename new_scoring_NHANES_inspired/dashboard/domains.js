'use strict';
// Extend this registry and add a matching panel as each domain becomes ready.
// Unspecified future domains deliberately have no invented names or scores.
const domainRegistry = [
  {id: 'metabolism', label: '01 · Metabolism'},
  {id: 'organ-stress', label: '02 · Organ stress'},
  {id: 'inflammation', label: '03 · Inflammation markers'},
  {id: 'nutrition', label: '04 · Nutrition markers'},
  {id: 'system-stability', label: '05 · System Stability'},
];
for (const domain of domainRegistry) {
  const button = document.createElement('button');
  button.type = 'button'; button.id = `nav-${domain.id}`;
  button.textContent = domain.label; button.disabled = !!domain.pending;
  if (!domain.pending) {
    button.setAttribute('aria-controls', `domain-${domain.id}`);
    button.setAttribute('aria-pressed', String(domain.id === 'metabolism'));
    button.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('domain-focus', {detail: {id: domain.id}}));
    });
  }
  document.getElementById('domain-nav').append(button);
}
