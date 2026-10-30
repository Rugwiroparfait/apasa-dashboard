'use strict';
(() => {
  const panel = document.getElementById('apasa-assistant');
  if (!panel) return;
  const toggle = document.querySelector('.assistant-toggle');
  const close = panel.querySelector('.assistant-close');
  const backdrop = document.querySelector('.assistant-backdrop');
  const narrow = window.matchMedia('(max-width: 1199px)');
  const form = panel.querySelector('.assistant-form');
  const field = form.querySelector('textarea');
  const log = panel.querySelector('.assistant-conversation');
  const status = panel.querySelector('.assistant-status');
  let open = !narrow.matches;
  let busy = false;
  function show(value, focus = false) {
    open = value;
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('assistant-collapsed', !open);
    document.body.classList.toggle('assistant-drawer-open', open && narrow.matches);
    backdrop.hidden = !open || !narrow.matches;
    panel.setAttribute('role', narrow.matches ? 'dialog' : 'complementary');
    if (narrow.matches && open) panel.setAttribute('aria-modal', 'true');
    else panel.removeAttribute('aria-modal');
    if (focus) (open ? close : toggle).focus();
  }
  show(open);
  toggle.addEventListener('click', () => show(!open, true));
  close.addEventListener('click', () => show(false, true));
  backdrop.addEventListener('click', () => show(false, true));
  narrow.addEventListener('change', () => show(!narrow.matches, panel.contains(document.activeElement))); 
  document.addEventListener('keydown', e => {
    if (!open) return;
    if (e.key === 'Escape') { e.preventDefault(); show(false, true); }
    if (e.key === 'Tab' && narrow.matches) {
      const focusable = [...panel.querySelectorAll('button:not(:disabled),textarea:not(:disabled),a[href],summary')].filter(e => e.getClientRects().length);
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  const say = (message, error = false) => { status.textContent = message; status.classList.toggle('is-error', error); };
  const paragraph = (text, className) => { const el = document.createElement('p'); el.className = className; el.textContent = text; return el; };
  panel.querySelectorAll('[data-assistant-question]').forEach(button => button.addEventListener('click', () => {
    if (busy) return;
    field.value = button.dataset.assistantQuestion;
    form.requestSubmit();
  }));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || !form.reportValidity()) return;
    busy = true;
    const question = field.value.trim();
    const data = new FormData(form);
    const buttons = [...panel.querySelectorAll('.assistant-quick button,.assistant-form button')];
    buttons.forEach(b => b.disabled = true);
    log.setAttribute('aria-busy', 'true');
    say('Asking about the current evidence…');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetch(form.action, {method: 'POST', body: data, credentials: 'same-origin', headers: {'Accept':'application/json'}, signal:controller.signal});
      const type = response.headers.get('content-type') || '';
      if (!type.includes('application/json')) throw new Error('The assistant could not be reached. Your session may have expired; refresh and sign in again.');
      const result = await response.json();
      if (!response.ok || !result.answer) throw new Error(result.error || 'The assistant is unavailable. No AI answer was generated.');
      const turn = document.createElement('article'); turn.className = 'assistant-turn';
      turn.append(paragraph(question, 'assistant-question'), paragraph(result.label || 'AI explanation · unreviewed', 'assistant-response-label'), paragraph(result.answer, 'assistant-answer'));
      if (result.url) { const link = document.createElement('a'); link.href=result.url; link.textContent='Open saved explanation and sources'; turn.append(link); }
      log.append(turn);
      while (log.children.length > 4) log.firstElementChild.remove();
      field.value = '';
      say('Uses the context and source details below. Check all AI wording before use.');
      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) turn.scrollIntoView({behavior:'smooth',block:'nearest'});
    } catch (error) {
      say(error.name === 'AbortError' ? 'The assistant timed out. No response is claimed. You can try again.' : error.message, true);
    } finally {
      clearTimeout(timeout); busy=false; buttons.forEach(b => b.disabled=false); log.setAttribute('aria-busy','false');
    }
  });
})();
