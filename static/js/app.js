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

function formatWithSignificantDigits(value, digits = 2) {
  if (!Number.isFinite(value)) {
    return null;
  }
  if (value === 0) {
    return '0';
  }
  const formatted = Number.parseFloat(value.toPrecision(digits));
  return Number.isInteger(formatted) ? formatted.toString() : formatted.toString();
}

function formatCellsForLabel(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return '—';
  }
  if (numericValue === 0) {
    return '0';
  }

  const sign = numericValue < 0 ? '-' : '';
  const absolute = Math.abs(numericValue);

  if (absolute >= 1_000_000) {
    const millions = absolute / 1_000_000;
    const formatted = formatWithSignificantDigits(millions, 2);
    return formatted ? `${sign}${formatted}M` : '—';
  }

  if (absolute >= 1_000) {
    const thousands = absolute / 1_000;
    const formatted = formatWithSignificantDigits(thousands, 2);
    if (!formatted) {
      return '—';
    }
    const thousandsNumeric = Number(formatted);
    if (Number.isFinite(thousandsNumeric) && thousandsNumeric >= 1000) {
      const millionsFormatted = formatWithSignificantDigits(thousandsNumeric / 1000, 2);
      return millionsFormatted ? `${sign}${millionsFormatted}M` : '—';
    }
    return `${sign}${formatted}K`;
  }

  const formatted = formatWithSignificantDigits(absolute, 2);
  return formatted ? `${sign}${formatted}` : '—';
}

function buildSeedingSummary(data) {
  const segments = [];
  if (data.mode === MODE_DILUTION) {
    const isCellsMode = data.dilution_input_mode === 'cells';
    const volumeSummary = data.total_volume_formatted
      ? ` in ${data.total_volume_formatted} total volume`
      : '';
    const perPortionSummary =
      isCellsMode && data.cells_to_seed_formatted && data.volume_per_seed_formatted
        ? ` (${data.cells_to_seed_formatted} in ${data.volume_per_seed_formatted})`
        : '';
    segments.push(
      `<p><strong>Dilute to ${data.final_concentration_formatted} cells/mL</strong>${perPortionSummary}${volumeSummary}.</p>`
    );
    segments.push(
      `<p>Use <strong>${data.slurry_volume_formatted}</strong> of culture at ${formatCells(
        data.cell_concentration
      )} cells/mL with <strong>${data.media_volume_formatted}</strong> of media.</p>`
    );
    if (isCellsMode && data.volume_per_seed_formatted && data.cells_to_seed_formatted) {
      const portionCount =
        Number.isFinite(data.portions_prepared) && data.portions_prepared > 0
          ? ` (~${formatWithSignificantDigits(data.portions_prepared, 2)} portion(s))`
          : '';
      segments.push(
        `<p class="meta">Per portion: ${data.cells_to_seed_formatted} cells in ${data.volume_per_seed_formatted}${portionCount}.</p>`
      );
    }
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

  const cellConcentrationField = passageForm.querySelector('#cell-concentration-field');
  if (cellConcentrationField) {
    let concentrationValue = data.cell_concentration;
    if (data.mode === MODE_DILUTION && data.final_concentration !== undefined) {
      concentrationValue = data.final_concentration;
    }
    if (
      (typeof concentrationValue === 'number' && Number.isFinite(concentrationValue)) ||
      (typeof concentrationValue === 'string' && concentrationValue.trim() !== '')
    ) {
      cellConcentrationField.value = concentrationValue;
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

async function copyPlainText(text) {
  const labelText = text != null ? String(text) : '';
  if (!labelText.trim()) {
    return;
  }

  const fallbackCopy = () => {
    const textarea = document.createElement('textarea');
    textarea.value = labelText;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    let copied = false;
    try {
      copied = document.execCommand('copy');
    } catch (error) {
      copied = false;
    }
    document.body.removeChild(textarea);
    if (!copied) {
      window.prompt('Copy the label text below:', labelText);
    }
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(labelText);
      return;
    } catch (error) {
      // Fall through to fallback copy handling below.
    }
  }

  fallbackCopy();
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
    if (typeof form.reportValidity === 'function' && !form.reportValidity()) {
      resultContainer.innerHTML =
        '<p class="error">Please resolve the highlighted fields before calculating.</p>';
      return;
    }
    resultContainer.textContent = 'Calculating…';

    const formData = new FormData(form);
    const mode = form.querySelector('input[name="mode"]:checked')?.value || MODE_CONFLUENCY;
    const cellConcentrationInput = (formData.get('cell_concentration') || '').trim();
    if (!cellConcentrationInput) {
      resultContainer.innerHTML =
        '<p class="error">Enter the starting cell concentration (e.g. 1e6 cells/mL) before calculating.</p>';
      return;
    }

    const payload = {
      culture_id: form.dataset.cultureId,
      mode,
      cell_concentration: cellConcentrationInput,
    };

    if (mode === MODE_CONFLUENCY) {
      const vesselId = formData.get('vessel_id');
      const targetConfluency = Number.parseFloat(formData.get('target_confluency'));
      const targetDays = Number(formData.get('target_days') || 0);
      const additionalHours = Number(formData.get('additional_hours') || 0);
      const totalHours = targetDays * 24 + additionalHours;
      if (!vesselId) {
        resultContainer.innerHTML =
          '<p class="error">Select a vessel before calculating the seeding plan.</p>';
        return;
      }
      if (!Number.isFinite(targetConfluency) || targetConfluency <= 0) {
        resultContainer.innerHTML =
          '<p class="error">Enter a valid target confluency above 0%.</p>';
        return;
      }
      if (!Number.isFinite(totalHours) || totalHours <= 0) {
        resultContainer.innerHTML =
          '<p class="error">Specify a time horizon greater than zero.</p>';
        return;
      }
      const vesselIdNumber = Number.parseInt(vesselId, 10);
      if (Number.isNaN(vesselIdNumber)) {
        resultContainer.innerHTML =
          '<p class="error">Select a valid vessel before calculating the seeding plan.</p>';
        return;
      }
      payload.vessel_id = vesselIdNumber;
      payload.target_confluency = targetConfluency;
      payload.target_hours = totalHours;
      payload.doubling_time_override = formData.get('doubling_time_override');
      payload.vessels_used = Number(formData.get('vessels_used') || 1);
    } else {
      const dilutionMode =
        form.querySelector('input[name="dilution_input_mode"]:checked')?.value || 'concentration';
      payload.dilution_input_mode = dilutionMode;
      if (dilutionMode === 'cells') {
        payload.cells_to_seed = formData.get('cells_to_seed');
        payload.volume_per_seed_ml = formData.get('volume_per_seed_ml');
      } else {
        payload.final_concentration = formData.get('final_concentration');
      }
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

  const today = form.dataset.today || new Date().toISOString().slice(0, 10);
  const cultureName = form.dataset.cultureName || '';
  const nextPassageRaw = form.dataset.nextPassage || '';
  let cellsText = '—';
  if (data.mode === MODE_DILUTION) {
    cellsText = formatCellsForLabel(data.cells_needed);
  } else {
    const candidates = [
      data.required_cells_total,
      data.required_cells,
      data.final_cells_total,
    ];
    for (const candidate of candidates) {
      const formatted = formatCellsForLabel(candidate);
      if (formatted !== '—') {
        cellsText = formatted;
        break;
      }
    }
  }

  if (cellsText === '—') {
    cellsText =
      data.cells_needed_formatted ||
      data.required_cells_total_formatted ||
      data.required_cells_formatted ||
      data.cells_needed ||
      data.required_cells_total ||
      data.required_cells ||
      '—';
  }

  const parts = [];
  if (cultureName) {
    parts.push(`Culture: ${cultureName}`);
  }
  parts.push(`Date: ${today}`);

  if (nextPassageRaw) {
    const normalized = String(nextPassageRaw).startsWith('P')
      ? String(nextPassageRaw)
      : `P${nextPassageRaw}`;
    parts.push(`Passage: ${normalized}`);
  }

  parts.push(`Cells seeded: ${cellsText}`);

  const labelText = parts.join('\n');
  await copyPlainText(labelText);
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

function attachDilutionModeSwitcher() {
  const form = document.querySelector('#seeding-form');
  if (!form) {
    return;
  }

  const radios = form.querySelectorAll('input[name="dilution_input_mode"]');
  if (!radios.length) {
    return;
  }

  const update = () => {
    const selected = form.querySelector('input[name="dilution_input_mode"]:checked');
    const mode = selected ? selected.value : 'concentration';
    form.dataset.dilutionInputMode = mode;

    const sections = form.querySelectorAll('[data-dilution-section]');
    sections.forEach((section) => {
      const isActive = section.dataset.dilutionSection === mode;
      section.hidden = !isActive;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !isActive;
        const requiredWhen = input.dataset.requiredWhenDilution;
        if (requiredWhen) {
          input.required = isActive && requiredWhen === mode;
        }
      });
    });
  };

  radios.forEach((radio) => {
    radio.addEventListener('change', update);
  });

  update();
}

function attachMycoTableCopyHandler() {
  const button = document.querySelector('.copy-myco-table');
  if (!button) {
    return;
  }

  const tableId = button.dataset.tableId;
  if (!tableId) {
    return;
  }

  const table = document.getElementById(tableId);
  if (!table) {
    return;
  }

  button.addEventListener('click', async () => {
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const lines = rows
      .map((row) => {
        const label = row.querySelector('.label-snippet');
        const culture = row.querySelector('.myco-culture');
        const labelText = label ? label.textContent.trim() : '';
        const cultureText = culture ? culture.textContent.trim() : '';
        if (!labelText && !cultureText) {
          return '';
        }
        if (!cultureText) {
          return labelText;
        }
        return `${labelText}\t${cultureText}`;
      })
      .filter((line) => line);

    const tableText = lines.join('\n');
    if (tableText) {
      await copyPlainText(tableText);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  attachMediaCheckboxHandler();
  attachModeSwitcher();
  attachDilutionModeSwitcher();
  attachSeedingFormHandler();
  attachMycoTableCopyHandler();
});
