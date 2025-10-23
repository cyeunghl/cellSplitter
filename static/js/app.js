const MODE_CONFLUENCY = 'confluency';
const MODE_DILUTION = 'dilution';

function formatCells(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)} B`;
  }
  if (absolute >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)} M`;
  }
  if (absolute >= 1_000) {
    return `${(value / 1_000).toFixed(2)} K`;
  }
  return value.toFixed(0);
}

function buildSeedingSummary(data) {
  const segments = [];
  if (data.mode === MODE_DILUTION) {
    segments.push(
      `<p><strong>Dilute to ${data.final_concentration_formatted} cells/mL</strong> in ${data.total_volume_formatted} total volume.</p>`
    );
    segments.push(
      `<p>Use <strong>${data.slurry_volume_formatted}</strong> of culture at ${formatCells(
        data.cell_concentration
      )} cells/mL with <strong>${data.media_volume_formatted}</strong> of media.</p>`
    );
    segments.push(
      `<p class="meta">Cells delivered: ${data.cells_needed_formatted} total.</p>`
    );
  } else {
    segments.push(
      `<p><strong>Seed ${data.required_cells_formatted} cells per ${data.vessel} (${data.vessel_area_cm2} cm²)</strong> × ${data.vessels_used} vessel(s) (<strong>${data.required_cells_total_formatted}</strong> total).</p>`
    );
    segments.push(
      `<p>Aim for ${data.target_confluency.toFixed(1)}% confluency in ${data.hours.toFixed(
        1
      )} hours (${(data.hours / 24).toFixed(2)} days) with a doubling time of ${data.doubling_time_used.toFixed(
        2
      )} h.</p>`
    );
    if (data.volume_needed_formatted) {
      const totalVolume = data.volume_needed_total_formatted
        ? ` (total <strong>${data.volume_needed_total_formatted}</strong>)`
        : '';
      segments.push(
        `<p>At ${formatCells(data.cell_concentration)} cells/mL, seed <strong>${data.volume_needed_formatted}</strong> per vessel${totalVolume}.</p>`
      );
    } else {
      segments.push(
        '<p class="note">Enter a valid cell concentration to get a recommended seeding volume.</p>'
      );
    }
    segments.push(
      `<p class="meta">Projected final yield: ${data.final_cells_total_formatted} cells across ${data.vessels_used} vessel(s) (${data.growth_cycles.toFixed(
        2
      )} doublings).</p>`
    );
  }
  if (data.note_suggestion) {
    segments.push(`<p class="note">${data.note_suggestion}</p>`);
  }
  return segments.join('\n');
}

function attachMediaCheckboxHandler() {
  const checkbox = document.querySelector('#use-previous-media');
  const mediaField = document.querySelector('#media-field');
  if (!checkbox || !mediaField || checkbox.disabled) {
    return;
  }
  const previousMedia = checkbox.dataset.media || '';
  checkbox.addEventListener('change', () => {
    if (checkbox.checked) {
      mediaField.value = previousMedia;
    }
  });
}

function fillPassageFormFromSeeding(data, { submit = false } = {}) {
  const passageForm = document.querySelector('[data-passage-form]');
  if (!passageForm) {
    return;
  }

  const vesselInput = passageForm.querySelector('#passage-vessel-id');
  if (vesselInput) {
    if (data.vessel_id !== undefined) {
      vesselInput.value = data.vessel_id ?? '';
    } else {
      vesselInput.value = '';
    }
  }

  const vesselsUsedInput = passageForm.querySelector('#passage-vessels-used');
  if (vesselsUsedInput) {
    if (data.vessels_used !== undefined) {
      vesselsUsedInput.value = data.vessels_used ?? '';
    } else {
      vesselsUsedInput.value = '';
    }
  }

  const seededCellsInput = passageForm.querySelector('#passage-seeded-cells');
  if (seededCellsInput) {
    if (data.mode === MODE_DILUTION) {
      seededCellsInput.value = data.cells_needed ?? '';
    } else {
      seededCellsInput.value = data.required_cells_total ?? '';
    }
  }

  const notesField = passageForm.querySelector('#notes-field');
  if (notesField && data.note_suggestion) {
    const suggestion = data.note_suggestion;
    const existingGenerated = notesField.dataset.generatedNote || '';
    if (!notesField.value || notesField.value === existingGenerated) {
      notesField.value = suggestion;
      notesField.dataset.generatedNote = suggestion;
    } else if (!notesField.value.includes(suggestion)) {
      notesField.value = `${notesField.value}\n\n${suggestion}`;
      notesField.dataset.generatedNote = suggestion;
    }
  }

  const mediaCheckbox = passageForm.querySelector('#use-previous-media');
  if (mediaCheckbox && !mediaCheckbox.disabled && !mediaCheckbox.checked && mediaCheckbox.dataset.media) {
    mediaCheckbox.checked = true;
    mediaCheckbox.dispatchEvent(new Event('change'));
  }

  if (submit) {
    passageForm.submit();
  } else {
    passageForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (notesField) {
      notesField.focus();
    }
  }
}

function prepareSeedingResultActions(container, data) {
  const passageForm = document.querySelector('[data-passage-form]');
  const actionRow = document.createElement('div');
  actionRow.className = 'form-actions';

  if (passageForm && data.mode === MODE_CONFLUENCY) {
    const fillButton = document.createElement('button');
    fillButton.type = 'button';
    fillButton.className = 'button secondary';
    fillButton.textContent = 'Fill passage form';
    fillButton.addEventListener('click', () => {
      fillPassageFormFromSeeding(data, { submit: false });
    });

    const commitButton = document.createElement('button');
    commitButton.type = 'button';
    commitButton.className = 'button primary';
    commitButton.textContent = 'Save as new passage';
    commitButton.addEventListener('click', () => {
      const confirmed = window.confirm('Save this seeding plan as a new passage?');
      if (!confirmed) {
        return;
      }
      fillPassageFormFromSeeding(data, { submit: true });
    });

    actionRow.append(fillButton, commitButton);
  }

  const labelButton = document.createElement('button');
  labelButton.type = 'button';
  labelButton.className = 'button ghost';
  labelButton.textContent = 'Copy label text';
  labelButton.addEventListener('click', () => {
    copyLabelToClipboard(data);
  });
  actionRow.append(labelButton);

  container.appendChild(actionRow);
}

function attachSeedingFormHandler() {
  const form = document.querySelector('#seeding-form');
  if (!form) {
    return;
  }
  const resultContainer = document.querySelector('#seeding-result');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!resultContainer) {
      return;
    }
    resultContainer.textContent = 'Calculating…';

    const formData = new FormData(form);
    const mode = form.querySelector('input[name="mode"]:checked')?.value || MODE_CONFLUENCY;

    const payload = {
      culture_id: form.dataset.cultureId,
      mode,
      cell_concentration: formData.get('cell_concentration'),
    };

    if (mode === MODE_CONFLUENCY) {
      const targetDays = Number(formData.get('target_days') || 0);
      const additionalHours = Number(formData.get('additional_hours') || 0);
      const totalHours = targetDays * 24 + additionalHours;
      payload.vessel_id = formData.get('vessel_id');
      payload.target_confluency = formData.get('target_confluency');
      payload.target_hours = totalHours;
      payload.doubling_time_override = formData.get('doubling_time_override');
      payload.vessels_used = Number(formData.get('vessels_used') || 1);
    } else {
      payload.final_concentration = formData.get('final_concentration');
      payload.total_volume_ml = formData.get('total_volume_ml');
    }

    try {
      const response = await fetch('/api/calc-seeding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        resultContainer.innerHTML = `<p class="error">${data.error || 'Calculation failed.'}</p>`;
        return;
      }
      resultContainer.innerHTML = buildSeedingSummary(data);
      prepareSeedingResultActions(resultContainer, data);
    } catch (error) {
      resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
    }
  });
}

async function copyLabelToClipboard(data) {
  const form = document.querySelector('#seeding-form');
  if (!form) {
    return;
  }

  const mediaField = document.querySelector('#media-field');
  const media = mediaField ? mediaField.value.trim() : '';
  const today = form.dataset.today || new Date().toISOString().slice(0, 10);
  const cultureName = form.dataset.cultureName || '';
  const cellLineName = form.dataset.cellLineName || cultureName;

  const cellsText =
    data.mode === MODE_DILUTION
      ? data.cells_needed_formatted || formatCells(data.cells_needed)
      : data.required_cells_formatted || formatCells(data.required_cells);

  const parts = [];
  if (cultureName) {
    parts.push(`Culture: ${cultureName}`);
  }
  parts.push(`Cell line: ${cellLineName}`);
  parts.push(`Date: ${today}`);
  parts.push(`Media: ${media || '—'}`);

  let cellsSegment = `Cells seeded: ${cellsText} cells`;
  if (data.mode === MODE_CONFLUENCY && data.vessel) {
    const vesselCount = data.vessels_used || 1;
    cellsSegment += ` (${vesselCount} × ${data.vessel})`;
  }
  parts.push(cellsSegment);

  const labelText = parts.join(' | ');

  const fallbackCopy = () => {
    const textarea = document.createElement('textarea');
    textarea.value = labelText;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (successful) {
        window.alert('Label text copied to clipboard.');
      } else {
        window.prompt('Copy the label text below:', labelText);
      }
    } catch (error) {
      document.body.removeChild(textarea);
      window.prompt('Copy the label text below:', labelText);
    }
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(labelText);
      window.alert('Label text copied to clipboard.');
    } catch (error) {
      fallbackCopy();
    }
  } else {
    fallbackCopy();
  }
}

function attachModeSwitcher() {
  const form = document.querySelector('#seeding-form');
  if (!form) {
    return;
  }
  const radios = form.querySelectorAll('input[name="mode"]');

  const update = () => {
    const selected = form.querySelector('input[name="mode"]:checked');
    const mode = selected ? selected.value : MODE_CONFLUENCY;
    form.dataset.mode = mode;
    const sections = form.querySelectorAll('[data-mode-section]');
    sections.forEach((section) => {
      section.hidden = section.dataset.modeSection !== mode;
    });
    const conditionalFields = form.querySelectorAll('[data-required-when]');
    conditionalFields.forEach((field) => {
      field.required = field.dataset.requiredWhen === mode;
    });
    const labels = form.querySelectorAll('.mode-toggle label');
    labels.forEach((label) => {
      const input = label.querySelector('input[type="radio"]');
      if (!input) {
        return;
      }
      label.classList.toggle('is-selected', input.checked);
    });
  };

  radios.forEach((radio) => {
    radio.addEventListener('change', update);
  });

  update();
}

document.addEventListener('DOMContentLoaded', () => {
  attachMediaCheckboxHandler();
  attachModeSwitcher();
  attachSeedingFormHandler();
});
