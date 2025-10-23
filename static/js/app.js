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
  segments.push(
    `<p><strong>Seed ${data.required_cells_formatted} cells per ${data.vessel} (${data.vessel_area_cm2} cm²)</strong> × ${data.vessels_used} vessel(s) (<strong>${data.required_cells_total_formatted}</strong> total).</p>`
    `<p><strong>Seed ${data.required_cells_formatted} cells</strong> into a ${data.vessel}.</p>`
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
    segments.push(
      `<p>At ${formatCells(data.cell_concentration)} cells/mL, seed <strong>${data.volume_needed_formatted}</strong>.</p>`
    );
  } else {
    segments.push(
      '<p class="note">Enter a valid cell concentration to get a recommended seeding volume.</p>'
    );
  }
  segments.push(
    `<p class="meta">Projected final yield: ${data.final_cells_total_formatted} cells across ${data.vessels_used} vessel(s) (${data.growth_cycles.toFixed(
    `<p class="meta">Projected final yield: ${formatCells(data.final_cells)} cells (${data.growth_cycles.toFixed(
      2
    )} doublings).</p>`
  );
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
    vesselInput.value = data.vessel_id ?? '';
  }

  const vesselsUsedInput = passageForm.querySelector('#passage-vessels-used');
  if (vesselsUsedInput) {
    vesselsUsedInput.value = data.vessels_used ?? '';
  }

  const seededCellsInput = passageForm.querySelector('#passage-seeded-cells');
  if (seededCellsInput) {
    seededCellsInput.value = data.required_cells_total ?? '';
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
  if (!passageForm) {
    return;
  }

  const actionRow = document.createElement('div');
  actionRow.className = 'form-actions';

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
  container.appendChild(actionRow);
function attachCopyMediaHandler() {
  const button = document.querySelector('[data-copy-media]');
  if (!button) {
    return;
  }
  const mediaField = document.querySelector('#media-field');
  if (!mediaField) {
    return;
  }
  button.addEventListener('click', () => {
    const media = button.getAttribute('data-media') || '';
    mediaField.value = media;
    mediaField.focus();
  });
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
    const vesselId = formData.get('vessel_id');
    const targetConfluency = formData.get('target_confluency');
    const targetDays = Number(formData.get('target_days') || 0);
    const additionalHours = Number(formData.get('additional_hours') || 0);
    const totalHours = targetDays * 24 + additionalHours;
    const vesselsUsed = Number(formData.get('vessels_used') || 1);

    const payload = {
      culture_id: form.dataset.cultureId,
      vessel_id: vesselId,
      target_confluency: targetConfluency,
      target_hours: totalHours,
      cell_concentration: formData.get('cell_concentration'),
      doubling_time_override: formData.get('doubling_time_override'),
      vessels_used: vesselsUsed,
    };

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

document.addEventListener('DOMContentLoaded', () => {
  attachMediaCheckboxHandler();
  attachCopyMediaHandler();
  attachSeedingFormHandler();
});
