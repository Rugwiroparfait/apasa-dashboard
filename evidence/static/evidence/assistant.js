'use strict';
export function initAssistant(panel) {
  if (!panel) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const form = panel.querySelector('.assistant-form');
  const field = form.querySelector('textarea');
  const send = form.querySelector('button[type=submit]');
  const sendMarkup = send.innerHTML;
  const thread = panel.querySelector('.assistant-thread');
  const log = panel.querySelector('.assistant-conversation');
  const status = panel.querySelector('.assistant-status');
  const thinking = panel.querySelector('.assistant-thinking');
  const retry = panel.querySelector('.assistant-retry');
  const enabled = panel.dataset.enabled === 'true';
  let busy = false;
  let failedQuestion = '';
  let failedTurn = null;

  function bottom(smooth = true) {
    thread.scrollTo({top: thread.scrollHeight, behavior: smooth && !reducedMotion.matches ? 'smooth' : 'auto'});
  }
  const say = (message, error = false) => {
    status.textContent = message;
    status.classList.toggle('is-error', error);
  };
  const paragraph = (text, className) => {
    const element = document.createElement('p');
    element.className = className; element.textContent = text;
    return element;
  };
  field.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (enabled && !busy) form.requestSubmit();
    }
  });
  retry.addEventListener('click', () => {
    if (!enabled || busy) return;
    field.value = failedQuestion; form.requestSubmit();
  });
  panel.querySelectorAll('[data-assistant-question]').forEach(button => button.addEventListener('click', () => {
    if (!enabled || busy) return;
    field.value = button.dataset.assistantQuestion; form.requestSubmit();
  }));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!enabled || busy || !form.reportValidity()) return;
    const question = field.value.trim();
    if (question.length < 10) { say('Ask a question of 10–1,500 characters.', true); field.focus(); return; }
    const data = new FormData(form);
    data.set('question', question);
    busy = true;
    panel.dataset.state = 'sending';
    retry.hidden = true;
    field.readOnly = true;
    const controls = [...panel.querySelectorAll('.assistant-quick button,.assistant-form button')];
    controls.forEach(button => button.disabled = true);
    send.setAttribute('aria-busy', 'true'); send.textContent = 'Sending…';
    log.querySelector('.assistant-empty')?.remove();
    if (failedTurn && failedQuestion === question) failedTurn.remove();
    failedTurn = null;
    const turn = document.createElement('article'); turn.className = 'assistant-turn';
    turn.append(paragraph(question, 'assistant-question')); log.append(turn);
    panel.classList.add('has-conversation');
    log.setAttribute('aria-busy', 'true');
    thinking.hidden = false;
    say('Sending your question…'); bottom();
    const thinkingTimer = setTimeout(() => {
      panel.dataset.state = 'thinking'; send.textContent = 'Thinking…';
      say('Reviewing the published evidence and its limitations…');
    }, 400);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, credentials: 'same-origin',
        headers: {'Accept': 'application/json'}, signal: controller.signal,
      });
      if (!(response.headers.get('content-type') || '').includes('application/json')) {
        throw new Error('The assistant could not be reached. Your session may have expired; refresh and sign in again.');
      }
      const result = await response.json();
      if (!response.ok) {
        const message = result.error || 'The assistant is unavailable. No AI answer was generated.';
        panel.dataset.state = response.status === 429 || /limit|budget|quota/i.test(message) ? 'rate-limit' : result.unavailable ? 'unavailable' : 'error';
        throw new Error(message);
      }
      if (typeof result.answer !== 'string' || !result.answer.trim()) {
        panel.dataset.state = 'empty';
        throw new Error('The assistant returned an empty response. No answer is available. You can retry this question.');
      }
      panel.dataset.state = 'idle';
      turn.append(paragraph(result.label || 'APASA · AI explanation · unreviewed', 'assistant-response-label'));
      const responseBody = document.createElement('div'); responseBody.className = 'assistant-response';
      responseBody.append(paragraph(result.answer, 'assistant-answer'));
      if (Array.isArray(result.sources) && result.sources.some(Boolean)) {
        const sources = document.createElement('details'); sources.className = 'assistant-sources';
        const summary = document.createElement('summary'); summary.textContent = 'Source references'; sources.append(summary);
        const list = document.createElement('ul');
        result.sources.filter(Boolean).forEach(source => {
          const item = document.createElement('li'); item.textContent = source; list.append(item);
        });
        sources.append(list); responseBody.append(sources);
      }
      if (result.url) {
        const url = new URL(result.url, window.location.href);
        if (url.origin === window.location.origin) {
          const link = document.createElement('a'); link.href = url.href;
          link.textContent = 'Saved explanation and sources'; responseBody.append(link);
        }
      }
      responseBody.append(paragraph('Check the cited evidence and comparison limits before use.', 'assistant-answer-note'));
      turn.append(responseBody);
      while (log.children.length > 4) log.firstElementChild.remove();
      field.value = ''; failedQuestion = '';
      say('Response received. AI wording is unreviewed.');
    } catch (error) {
      failedQuestion = question; failedTurn = turn; retry.hidden = false;
      if (['sending', 'thinking'].includes(panel.dataset.state)) panel.dataset.state = 'error';
      say(error.name === 'AbortError' ? 'The request timed out. No response is claimed. You can retry this question.' : error.message, true);
    } finally {
      clearTimeout(timeout); clearTimeout(thinkingTimer);
      thinking.hidden = true; busy = false; field.readOnly = false;
      send.innerHTML = sendMarkup; send.removeAttribute('aria-busy');
      controls.forEach(button => button.disabled = false);
      log.setAttribute('aria-busy', 'false'); bottom();
    }
  });
}
