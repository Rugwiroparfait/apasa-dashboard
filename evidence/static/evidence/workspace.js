'use strict';
// Progressive enhancement: links, filters and the text download work without JS.
document.querySelectorAll('[data-copy-note]').forEach(button => {
  button.addEventListener('click', async () => {
    const note = document.getElementById('evidence-note');
    const status = document.getElementById('copy-status');
    if (!note || !status) return;
    try {
      await navigator.clipboard.writeText(note.textContent);
      status.textContent = 'Evidence note copied, including source details and any mock-data warning.';
    } catch (_) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(document.querySelector('.note-preview'));
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Note selected. Use your device’s copy command, or download the text file.';
    }
  });
});

// Submit canonical GET selections, keeping focus and recovering cleanly from back/forward cache.
function autoNavigateFilters(form, changedName, status) {
  if (form.dataset.loading === 'true') return;
  const parameters = new URLSearchParams(new FormData(form));
  form.querySelectorAll('select[name]').forEach(select => parameters.set(select.name, select.value));
  form.dataset.loading = 'true';
  form.setAttribute('aria-busy', 'true');
  if (status) status.textContent = 'Updating selections…';
  try { sessionStorage.setItem('apasa-filter-focus', JSON.stringify({path: location.pathname, name: changedName})); } catch (_) {}
  window.location.assign(location.pathname + '?' + parameters.toString());
}
const districtFilters = document.querySelector('[data-district-filters]');
const nationalFilters = document.querySelector('[data-national-filters]');
if (districtFilters) {
  const province = districtFilters.querySelector('[name=province]');
  const district = districtFilters.querySelector('[name=district]');
  const crop = districtFilters.querySelector('[name=crop]');
  districtFilters.addEventListener('change', event => {
    const field = event.target;
    if (!(field instanceof HTMLSelectElement)) return;
    if (field === province) { district.value = ''; crop.value = ''; }
    if (field === district) crop.value = '';
    autoNavigateFilters(districtFilters, field.name, document.querySelector('[data-filter-status]'));
  });
}
if (nationalFilters) {
  nationalFilters.addEventListener('change', event => {
    if (event.target instanceof HTMLSelectElement) {
      autoNavigateFilters(nationalFilters, event.target.name, document.querySelector('[data-national-status]'));
    }
  });
}
if (districtFilters || nationalFilters) {
  window.addEventListener('pageshow', event => {
    if (event.persisted) { window.location.reload(); return; }
    try {
      const saved = JSON.parse(sessionStorage.getItem('apasa-filter-focus') || 'null');
      sessionStorage.removeItem('apasa-filter-focus');
      if (saved?.path === location.pathname) {
        const control = (districtFilters || nationalFilters).elements.namedItem(saved.name);
        if (control && !control.disabled) control.focus({preventScroll: true});
      }
    } catch (_) {}
  });
}

const goalFilters = document.querySelector('[data-goal-filters]');
if (goalFilters) {
  goalFilters.querySelector('[name=scope]').addEventListener('change', () => {
    goalFilters.querySelector('[name=geography]').value = '';
    goalFilters.requestSubmit();
  });
}

// Browser guidance mirrors server-side conditional URL/origin validation.
const syntheticUpload = document.querySelector('#id_synthetic_demo');
if (syntheticUpload) {
  const sourceURL = document.querySelector('#id_source_url');
  const origin = document.querySelector('#id_origin');
  const updateOriginRequirements = () => {
    sourceURL.required = !syntheticUpload.checked;
    origin.required = syntheticUpload.checked;
  };
  syntheticUpload.addEventListener('change', updateOriginRequirements);
  updateOriginRequirements();
}

const syntheticTarget = document.querySelector('#id_is_mocked');
const targetSourceURL = document.querySelector('#id_source_url');
if (!syntheticUpload && syntheticTarget && targetSourceURL) {
  const updateTargetURL = () => { targetSourceURL.required = !syntheticTarget.checked; };
  syntheticTarget.addEventListener('change', updateTargetURL);
  updateTargetURL();
}
