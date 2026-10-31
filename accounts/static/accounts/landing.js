'use strict';
// The page remains complete without JavaScript or its decorative image.
document.querySelectorAll('[data-image-fallback]').forEach(image => {
  const fallback = () => {
    image.parentElement.classList.add('image-unavailable');
    image.alt = '';
  };
  image.addEventListener('error', fallback, {once: true});
  if (image.complete && !image.naturalWidth) fallback();
});
// Public section links expose the current section without changing navigation.
const sectionLinks = [...document.querySelectorAll('.public-header nav a')];
if ('IntersectionObserver' in window && document.getElementById('features')) {
  const observer = new IntersectionObserver(entries => {
    entries.filter(entry => entry.isIntersecting).forEach(entry => {
      sectionLinks.forEach(link => {
        if (new URL(link.href).hash === '#' + entry.target.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    });
  }, {rootMargin: '-10% 0px -55% 0px'});
  ['about', 'features', 'how-it-works'].forEach(id => observer.observe(document.getElementById(id)));
}

// Reveal sections once, with a short stagger for cards in the same group.
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const revealTargets = [...document.querySelectorAll([
  '.public-about > div', '.public-feature', '.public-section-title',
  '.public-audiences > div', '.public-how > .public-eyebrow', '.public-how > h2',
  '.public-steps > li', '.public-principles-heading', '.public-principles li',
  '.public-closing > div', '.public-closing > .ui-button',
].join(','))];
let revealObserver;
const reveal = element => {
  element.removeAttribute('data-reveal-pending');
  element.classList.add('is-revealed');
  revealObserver?.unobserve(element);
};
document.querySelectorAll('.public-feature-grid,.public-audiences,.public-steps,.public-principles ul').forEach(group => {
  [...group.children].forEach((child, index) => {
    child.style.setProperty('--reveal-delay', `${Math.min(index, 3) * 80}ms`);
  });
});
if (!reducedMotion.matches && 'IntersectionObserver' in window) {
  revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => { if (entry.isIntersecting) reveal(entry.target); });
  }, {threshold: .12, rootMargin: '0px 0px -32px 0px'});
  revealTargets.forEach(element => {
    element.classList.add('scroll-reveal');
    // Do not hide above-the-fold content, restored scroll positions or focused links.
    if (element.getBoundingClientRect().top < window.innerHeight - 24) reveal(element);
    else { element.setAttribute('data-reveal-pending', ''); revealObserver.observe(element); }
  });
}
document.addEventListener('focusin', event => {
  const target = event.target.closest('[data-reveal-pending]');
  if (target) { target.style.setProperty('--reveal-delay', '0ms'); reveal(target); }
});

// One animation frame per scroll update; no perpetual JavaScript render loop.
const scene = document.querySelector('.hero-scene');
let scrollFrame = 0;
let lastProgress = -1;
function updateScenery() {
  scrollFrame = 0;
  if (!scene || reducedMotion.matches) return;
  const bounds = scene.getBoundingClientRect();
  const progress = Math.max(0, Math.min(1, -bounds.top / bounds.height));
  if (Math.abs(progress - lastProgress) < .0005) return;
  lastProgress = progress;
  // Mobile travels toward the center so the tractor stays within the existing crop.
  const distance = bounds.width <= 600 ? -Math.min(bounds.width * .2, 80) : Math.min(bounds.width * .2, 260);
  scene.style.setProperty('--tractor-scroll-x', `${(progress * distance).toFixed(2)}px`);
  scene.style.setProperty('--tractor-scroll-y', `${(progress * 24).toFixed(2)}px`);
  scene.style.setProperty('--tractor-scroll-rotation', `${(progress * .8).toFixed(3)}deg`);
  scene.style.setProperty('--wordmark-scroll-y', `${(-progress * 28).toFixed(2)}px`);
}
function scheduleScenery() {
  if (!scrollFrame && !document.hidden) scrollFrame = requestAnimationFrame(updateScenery);
}
function motionPreferenceChanged() {
  if (reducedMotion.matches) {
    revealTargets.forEach(reveal);
    revealObserver?.disconnect();
    if (scene) {
      ['--tractor-scroll-x', '--tractor-scroll-y', '--tractor-scroll-rotation', '--wordmark-scroll-y'].forEach(name => scene.style.removeProperty(name));
    }
  }
  lastProgress = -1;
  scheduleScenery();
}
if (scene) {
  window.addEventListener('scroll', scheduleScenery, {passive: true});
  window.addEventListener('resize', () => { lastProgress = -1; scheduleScenery(); }, {passive: true});
  document.addEventListener('visibilitychange', scheduleScenery);
  scheduleScenery();
}
reducedMotion.addEventListener('change', motionPreferenceChanged);
