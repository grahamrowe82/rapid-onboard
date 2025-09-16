(function () {
  if (typeof window === 'undefined' || typeof window.initialSections === 'undefined') {
    return;
  }

  const sectionField = document.getElementById('section-data');
  const copyButton = document.getElementById('copy-brief');
  const copyFeedback = document.getElementById('copy-feedback');
  const downloadForm = document.getElementById('download-form');

  let sections;
  try {
    sections = JSON.parse(JSON.stringify(window.initialSections || {}));
  } catch (err) {
    sections = {};
  }

  const SECTION_ORDER = [
    ['context', 'Context'],
    ['goals', 'Goals'],
    ['constraints', 'Constraints'],
    ['stakeholders', 'Stakeholders'],
    ['unknowns', 'Unknowns'],
    ['risks', 'Risks'],
    ['week1_plan', 'Week 1 Plan'],
  ];

  function syncField() {
    if (!sectionField) {
      return;
    }
    sectionField.value = JSON.stringify(sections);
  }

  function ensureArray(key) {
    if (!Array.isArray(sections[key])) {
      sections[key] = [];
    }
    return sections[key];
  }

  document.querySelectorAll('[data-section-list]').forEach((list) => {
    const key = list.getAttribute('data-section-key');
    if (!key) {
      return;
    }
    const items = list.querySelectorAll('li[contenteditable="true"]');
    items.forEach((item) => {
      const index = parseInt(item.dataset.index || '0', 10);
      const values = ensureArray(key);
      if (typeof values[index] === 'undefined') {
        values[index] = item.textContent.trim();
      }
      const updateFromContent = () => {
        const text = item.textContent.trim();
        values[index] = text || '—';
        if (!text) {
          item.textContent = '—';
          item.dataset.placeholder = 'true';
        } else if (item.dataset.placeholder) {
          delete item.dataset.placeholder;
        }
        syncField();
      };
      item.addEventListener('blur', updateFromContent);
      item.addEventListener('input', () => {
        const text = item.textContent;
        values[index] = text.trim();
        syncField();
      });
    });
  });

  function buildMarkdown(data) {
    const clone = Object.assign({}, data);
    const lines = [`# ${clone.title || 'Onboarding Brief'}`, ''];
    SECTION_ORDER.forEach(([key, label]) => {
      lines.push(`## ${label}`);
      lines.push('');
      if (key === 'context') {
        const context = (clone.context || '').toString().trim();
        lines.push(context || '—');
      } else {
        const items = Array.isArray(clone[key]) ? clone[key] : [];
        if (!items.length || items.every((item) => !item || !item.toString().trim())) {
          lines.push('- —');
        } else {
          items.forEach((item) => {
            const value = (item || '').toString().trim();
            lines.push(`- ${value || '—'}`);
          });
        }
      }
      lines.push('');
    });
    return lines.join('\n').trim() + '\n';
  }

  async function copyMarkdown() {
    const markdown = buildMarkdown(sections);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(markdown);
        if (copyFeedback) {
          copyFeedback.classList.add('visible');
          setTimeout(() => copyFeedback.classList.remove('visible'), 1600);
        }
        return;
      } catch (err) {
        // fall through to textarea copy
      }
    }
    const temp = document.createElement('textarea');
    temp.value = markdown;
    temp.setAttribute('readonly', 'true');
    temp.style.position = 'absolute';
    temp.style.left = '-9999px';
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    if (copyFeedback) {
      copyFeedback.classList.add('visible');
      setTimeout(() => copyFeedback.classList.remove('visible'), 1600);
    }
  }

  if (copyButton) {
    copyButton.addEventListener('click', copyMarkdown);
  }

  if (downloadForm) {
    downloadForm.addEventListener('submit', syncField);
  }

  syncField();
})();
