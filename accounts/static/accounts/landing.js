/* Optional decorative-motion control; authentication remains an ordinary link. */
(() => {
  const scene = document.querySelector('.hero-scene');
  const button = document.querySelector('.landing-motion');
  if (!scene || !button) return;
  button.hidden = false;
  button.addEventListener('click', () => {
    const paused = button.getAttribute('aria-pressed') !== 'true';
    scene.dataset.motion = paused ? 'paused' : 'running';
    button.setAttribute('aria-pressed', String(paused));
    button.textContent = paused ? 'Resume scenery' : 'Pause scenery';
  });
})();
