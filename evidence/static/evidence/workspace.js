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
