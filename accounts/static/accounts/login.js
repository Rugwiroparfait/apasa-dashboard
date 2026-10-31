'use strict';
(() => {
  const form = document.querySelector('.signin-form');
  if (!form) return;
  const password = form.querySelector('#id_password');
  const toggle = form.querySelector('.password-toggle');
  const submit = form.querySelector('.signin-submit');
  const initialSubmit = submit.innerHTML;
  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    toggle.textContent = visible ? 'Hide' : 'Show';
    toggle.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    toggle.setAttribute('aria-pressed', String(visible));
  });
  form.addEventListener('submit', event => {
    if (submit.disabled) { event.preventDefault(); return; }
    submit.disabled = true;
    submit.textContent = 'Signing in…';
    form.querySelector('.signin-status').textContent = 'Signing in…';
  });
  window.addEventListener('pageshow', () => { submit.disabled = false; submit.innerHTML = initialSubmit; });
})();
