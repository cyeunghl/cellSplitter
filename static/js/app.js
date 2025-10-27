const MODE_CONFLUENCY = 'confluency';
const MODE_DILUTION = 'dilution';

function parseNumericInput(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'boolean') {
    return null;
  }
  const cleaned = String(value).trim();
  if (!cleaned) {
    return null;
  }
  const normalized = cleaned.replace(/,/g, '').replace(/\s+/g, '').toUpperCase();
  let multiplier = 1;
  let numericPortion = normalized;
  if (numericPortion.endsWith('K')) {
    multiplier = 1_000;
    numericPortion = numericPortion.slice(0, -1);
  } else if (numericPortion.endsWith('M')) {
    multiplier = 1_000_000;
    numericPortion = numericPortion.slice(0, -1);
  } else if (numericPortion.endsWith('B')) {
    multiplier = 1_000_000_000;
    numericPortion = numericPortion.slice(0, -1);
  }
  let parsed = Number.parseFloat(numericPortion);
  if (Number.isNaN(parsed)) {
    parsed = Number.parseFloat(numericPortion.replace(/E/g, 'e'));
  }
  if (Number.isNaN(parsed)) {
    return null;
  }
  const numericValue = parsed * multiplier;
  if (!Number.isFinite(numericValue)) {
    return null;
  }
  return numericValue;
}

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

function parseJSONScript(id) {
  const script = document.getElementById(id);
  if (!script) {
    return null;
  }
  try {
    const content = script.textContent || script.innerText || '';
    if (!content.trim()) {
      return null;
    }
    return JSON.parse(content);
  } catch (error) {
    return null;
  }
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

function attachHarvestTabs() {
  const tabContainer = document.querySelector('[data-harvest-tabs]');
  if (!tabContainer) {
    return;
  }
  const root = tabContainer.closest('[data-harvest-container]') || tabContainer.parentElement;
  if (!root) {
    return;
  }
  const tabs = Array.from(tabContainer.querySelectorAll('[data-harvest-tab]'));
  if (!tabs.length) {
    return;
  }
  const sections = new Map();
  tabs.forEach((tab) => {
    const target = tab.dataset.harvestTab;
    if (!target) {
      return;
    }
    const section = root.querySelector(`[data-harvest-section="${target}"]`);
    if (section) {
      sections.set(target, section);
    }
  });
  if (!sections.size) {
    return;
  }

  const setActive = (targetName) => {
    let resolved = targetName;
    if (!resolved || !sections.has(resolved)) {
      resolved = tabs[0]?.dataset.harvestTab;
    }
    if (!resolved || !sections.has(resolved)) {
      return;
    }
    tabs.forEach((tab) => {
      const isActive = tab.dataset.harvestTab === resolved;
      tab.classList.toggle('is-active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      tab.setAttribute('tabindex', isActive ? '0' : '-1');
    });
    sections.forEach((section, key) => {
      const isActive = key === resolved;
      section.hidden = !isActive;
      section.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    });
  };

  const defaultTab = tabContainer.dataset.defaultTab || tabs[0]?.dataset.harvestTab;
  setActive(defaultTab);

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      setActive(tab.dataset.harvestTab);
    });
  });
}

function attachMediaCheckboxHandler() {
  const checkbox = document.querySelector('#use-previous-media');
  const mediaField = document.querySelector('#media-field');
  if (!checkbox || !mediaField || checkbox.disabled) {
    return;
  }
  const previousMedia = checkbox.dataset.media || '';
  if (previousMedia) {
    checkbox.checked = true;
    if (!mediaField.value) {
      mediaField.value = previousMedia;
    }
  }
  checkbox.addEventListener('change', () => {
    if (checkbox.checked) {
      mediaField.value = previousMedia;
    }
  });
}

async function copyLabelFromPassageForm() {
  const passageForm = document.querySelector('[data-passage-form]');
  if (!passageForm) {
    return;
  }

  const cultureName = passageForm.dataset.cultureName || '';
  const nextPassage = passageForm.dataset.nextPassage || '';
  const dateInput = passageForm.querySelector('input[name="date"]');
  const dateValue = dateInput && dateInput.value ? dateInput.value : new Date().toISOString().slice(0, 10);
  const seededInput = passageForm.querySelector('#passage-seeded-cells');
  const seededRaw = seededInput ? seededInput.value : '';

  let seededDisplay = '—';
  if (seededRaw) {
    const seededNumber = Number(seededRaw);
    if (Number.isFinite(seededNumber)) {
      seededDisplay = formatCellsForLabel(seededNumber);
    } else {
      seededDisplay = seededRaw;
    }
  }

  const parts = [];
  if (cultureName) {
    parts.push(`Culture: ${cultureName}`);
  }
  parts.push(`Date: ${dateValue}`);
  if (nextPassage) {
    const normalized = String(nextPassage).startsWith('P') ? String(nextPassage) : `P${nextPassage}`;
    parts.push(`Passage: ${normalized}`);
  }
  parts.push(`Cells seeded: ${seededDisplay}`);

  await copyPlainText(parts.join('\n'));
}

function attachPassageLabelCopyHandler() {
  const button = document.querySelector('[data-copy-passage-label]');
  if (!button) {
    return;
  }
  button.addEventListener('click', async () => {
    await copyLabelFromPassageForm();
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

  const cellConcentrationHidden = passageForm.querySelector('#passage-cell-concentration');
  if (cellConcentrationHidden) {
    let concentrationValue = data.cell_concentration;
    if (data.mode === MODE_DILUTION && data.final_concentration !== undefined) {
      concentrationValue = data.final_concentration;
    }
    if (
      (typeof concentrationValue === 'number' && Number.isFinite(concentrationValue)) ||
      (typeof concentrationValue === 'string' && concentrationValue.trim() !== '')
    ) {
      cellConcentrationHidden.value = concentrationValue;
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

async function parseJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    const parseError = new Error('INVALID_JSON_RESPONSE');
    parseError.rawText = text;
    throw parseError;
  }
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
      let data;
      try {
        data = await parseJsonResponse(response);
      } catch (parseError) {
        console.error('Failed to parse seeding response', parseError);
        resultContainer.innerHTML =
          '<p class="error">Server returned an unexpected response. Please try again.</p>';
        return;
      }
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
      const isActive = section.dataset.modeSection === mode;
      section.hidden = !isActive;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !isActive;
      });
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

function attachMycoTableCopyHandlers() {
  const buttons = document.querySelectorAll('.copy-myco-table');
  if (!buttons.length) {
    return;
  }

  buttons.forEach((button) => {
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
      if (!rows.length) {
        return;
      }

      const selectedRows = rows.filter((row) => {
        const checkbox = row.querySelector('.label-select');
        return checkbox ? checkbox.checked : false;
      });

      const rowsToCopy = selectedRows.length ? selectedRows : rows;
      const lines = rowsToCopy
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
  });
}

function attachMycoSelectAllHandlers() {
  const buttons = document.querySelectorAll('.copy-myco-select-all');
  if (!buttons.length) {
    return;
  }

  buttons.forEach((button) => {
    const tableId = button.dataset.tableId;
    if (!tableId) {
      return;
    }

    const table = document.getElementById(tableId);
    if (!table) {
      return;
    }

    button.addEventListener('click', () => {
      const checkboxes = Array.from(
        table.querySelectorAll('tbody .label-select')
      );
      if (!checkboxes.length) {
        return;
      }

      const shouldSelectAll = !checkboxes.every((checkbox) => checkbox.checked);
      checkboxes.forEach((checkbox) => {
        checkbox.checked = shouldSelectAll;
      });
    });
  });
}

function attachCulturePrintHandlers() {
  const buttons = document.querySelectorAll('[data-print-culture]');
  if (!buttons.length) {
    return;
  }

  buttons.forEach((button) => {
    button.addEventListener('click', async () => {
      const cultureName = button.getAttribute('data-culture-name') || '';
      const passageNumber = button.getAttribute('data-passage-number') || '';
      const dateString =
        button.getAttribute('data-date') || new Date().toISOString().slice(0, 10);
      const seededCells = button.getAttribute('data-seeded') || '';
      const media = button.getAttribute('data-media') || '';
      const parts = [];
      if (cultureName) {
        parts.push(cultureName);
      }
      if (dateString) {
        parts.push(dateString);
      }
      if (passageNumber) {
        const formattedPassage = passageNumber.startsWith('P')
          ? passageNumber
          : `P${passageNumber}`;
        parts.push(formattedPassage);
      }
      if (seededCells && seededCells !== '—') {
        parts.push(`${seededCells} cells`);
      }
      if (media) {
        parts.push(media);
      }

      const snapshot = parts.join(' ');
      if (snapshot) {
        await copyPlainText(snapshot);
      }
    });
  });
}


function initBulkProcessing() {
  const bulkCard = document.querySelector('[data-bulk-card]');
  if (!bulkCard) {
    return;
  }

  const cultureData = parseJSONScript('bulk-culture-data');
  if (!Array.isArray(cultureData) || !cultureData.length) {
    return;
  }

  const cultureMap = new Map();
  cultureData.forEach((entry) => {
    if (!entry || entry.id === undefined || entry.id === null) {
      return;
    }
    const id = Number.parseInt(entry.id, 10);
    if (!Number.isNaN(id)) {
      cultureMap.set(id, { ...entry, id });
    }
  });

  if (!cultureMap.size) {
    return;
  }

  const vesselDataRaw = parseJSONScript('bulk-vessel-data');
  const vessels = Array.isArray(vesselDataRaw)
    ? vesselDataRaw
        .map((entry) => {
          if (!entry || entry.id === undefined || entry.id === null) {
            return null;
          }
          const id = Number.parseInt(entry.id, 10);
          if (Number.isNaN(id)) {
            return null;
          }
          return {
            id,
            name: entry.name || `Vessel ${id}`,
            area_cm2: entry.area_cm2,
            cells_at_100_confluency: entry.cells_at_100_confluency,
          };
        })
        .filter(Boolean)
    : [];

  const today = bulkCard.dataset.today || new Date().toISOString().slice(0, 10);
  const selectAllButton = bulkCard.querySelector('[data-bulk-select-all]');
  const copyButton = bulkCard.querySelector('[data-bulk-generate-copy]');
  const startButton = bulkCard.querySelector('[data-bulk-start]');
  const copyOutput = bulkCard.querySelector('#bulk-copy-output');
  const workflow = bulkCard.querySelector('[data-bulk-workflow]');
  const harvestForm = bulkCard.querySelector('[data-bulk-harvest-form]');
  const harvestBody = harvestForm ? harvestForm.querySelector('tbody') : null;
  const plannerForm = bulkCard.querySelector('[data-bulk-planner-form]');
  const plannerBody = plannerForm ? plannerForm.querySelector('tbody') : null;
  const harvestTab = bulkCard.querySelector('[data-bulk-tab="harvest"]');
  const plannerTab = bulkCard.querySelector('[data-bulk-tab="planner"]');
  const statusNode = bulkCard.querySelector('[data-bulk-status]');
  const harvestStatus = bulkCard.querySelector('[data-harvest-status]');
  const plannerStatus = bulkCard.querySelector('[data-planner-status]');
  const labelOutput = bulkCard.querySelector('#bulk-label-output');

  const harvestRowsById = new Map();
  const plannerRowsById = new Map();
  let activeIds = [];
  let harvestSaved = false;

  const clearElement = (node) => {
    if (node) {
      node.innerHTML = '';
    }
  };

  const showStatus = (node, message, type = 'info') => {
    if (!node) {
      return;
    }
    node.textContent = message || '';
    node.classList.toggle('error', type === 'error');
  };

  const resetStatuses = () => {
    showStatus(statusNode, '');
    showStatus(harvestStatus, '');
    showStatus(plannerStatus, '');
  };

  const getSelectedIds = () => {
    const checkboxes = bulkCard.querySelectorAll('.bulk-culture-select:checked');
    const ids = [];
    checkboxes.forEach((checkbox) => {
      const id = Number.parseInt(checkbox.value, 10);
      if (!Number.isNaN(id) && cultureMap.has(id)) {
        ids.push(id);
      }
    });
    return ids;
  };

  const populateVesselOptions = (select, selectedId) => {
    if (!select) {
      return;
    }
    select.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select vessel…';
    select.appendChild(placeholder);
    vessels.forEach((vessel) => {
      const option = document.createElement('option');
      option.value = String(vessel.id);
      option.textContent = vessel.name;
      if (selectedId && Number.parseInt(selectedId, 10) === vessel.id) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  };

  const defaultConcentration = (culture) => {
    if (!culture) {
      return '';
    }
    if (culture.measured_cell_concentration != null) {
      return culture.measured_cell_concentration;
    }
    if (culture.default_cell_concentration != null) {
      return culture.default_cell_concentration;
    }
    return 1000000;
  };

  const defaultSlurryVolume = (culture) => {
    if (!culture) {
      return '';
    }
    if (culture.measured_slurry_volume_ml != null) {
      return culture.measured_slurry_volume_ml;
    }
    if (culture.default_slurry_volume_ml != null) {
      return culture.default_slurry_volume_ml;
    }
    return '';
  };

  const setActiveTab = (tab) => {
    if (!workflow) {
      return;
    }
    const harvestActive = tab === 'harvest';
    const plannerActive = tab === 'planner';
    if (harvestTab) {
      harvestTab.classList.toggle('is-active', harvestActive);
      harvestTab.setAttribute('aria-selected', harvestActive ? 'true' : 'false');
    }
    if (plannerTab) {
      plannerTab.classList.toggle('is-active', plannerActive);
      plannerTab.setAttribute('aria-selected', plannerActive ? 'true' : 'false');
    }
    if (harvestForm) {
      harvestForm.hidden = !harvestActive;
    }
    if (plannerForm) {
      plannerForm.hidden = !plannerActive;
    }
  };

  const ensureWorkflowVisible = (ids) => {
    if (!workflow) {
      return;
    }
    workflow.hidden = !ids.length;
    if (!ids.length) {
      harvestSaved = false;
    }
    if (plannerTab) {
      plannerTab.disabled = !harvestSaved;
    }
    if (!workflow.hidden) {
      setActiveTab(harvestSaved ? 'planner' : 'harvest');
    }
  };

  const renderHarvestRows = (ids) => {
    if (!harvestBody) {
      return;
    }
    harvestBody.innerHTML = '';
    harvestRowsById.clear();
    ids.forEach((id) => {
      const culture = cultureMap.get(id);
      if (!culture) {
        return;
      }
      const row = harvestBody.insertRow();
      row.dataset.cultureId = String(id);
      const cultureCell = row.insertCell();
      const name = document.createElement('strong');
      name.textContent = culture.name || `Culture ${id}`;
      cultureCell.appendChild(name);
      const next = document.createElement('p');
      next.className = 'meta';
      const nextPassage =
        culture.next_passage_number != null ? culture.next_passage_number : 1;
      next.textContent = `Next: P${nextPassage}`;
      cultureCell.appendChild(next);
      if (culture.latest_vessel_name) {
        const vesselMeta = document.createElement('p');
        vesselMeta.className = 'meta';
        vesselMeta.textContent = `Last vessel: ${culture.latest_vessel_name}`;
        cultureCell.appendChild(vesselMeta);
      }

      const confluenceCell = row.insertCell();
      const confluenceLabel = document.createElement('label');
      const confluenceSpan = document.createElement('span');
      confluenceSpan.textContent = 'Pre-split confluence (%)';
      confluenceLabel.appendChild(confluenceSpan);
      const confluenceInput = document.createElement('input');
      confluenceInput.type = 'number';
      confluenceInput.min = '0';
      confluenceInput.max = '100';
      confluenceInput.step = '1';
      confluenceInput.className = 'bulk-harvest-confluence';
      if (culture.pre_split_confluence_percent != null) {
        confluenceInput.value = String(culture.pre_split_confluence_percent);
      }
      confluenceLabel.appendChild(confluenceInput);
      confluenceCell.appendChild(confluenceLabel);

      const concCell = row.insertCell();
      const concLabel = document.createElement('label');
      const concSpan = document.createElement('span');
      concSpan.textContent = 'Measured concentration (cells/mL)';
      concLabel.appendChild(concSpan);
      const concInput = document.createElement('input');
      concInput.type = 'text';
      concInput.className = 'bulk-harvest-concentration';
      const defaultConc = defaultConcentration(culture);
      if (defaultConc !== '') {
        concInput.value = String(defaultConc);
      }
      concLabel.appendChild(concInput);
      concCell.appendChild(concLabel);

      const volumeCell = row.insertCell();
      const volumeLabel = document.createElement('label');
      const volumeSpan = document.createElement('span');
      volumeSpan.textContent = 'Slurry volume (mL)';
      volumeLabel.appendChild(volumeSpan);
      const volumeInput = document.createElement('input');
      volumeInput.type = 'text';
      volumeInput.className = 'bulk-harvest-volume';
      const defaultVolume = defaultSlurryVolume(culture);
      if (defaultVolume !== '') {
        volumeInput.value = String(defaultVolume);
      }
      volumeLabel.appendChild(volumeInput);
      volumeCell.appendChild(volumeLabel);
      if (
        culture.default_slurry_volume_ml != null &&
        culture.measured_slurry_volume_ml == null
      ) {
        const hint = document.createElement('p');
        hint.className = 'form-hint';
        hint.textContent = `Suggested: ${culture.default_slurry_volume_ml} mL`;
        volumeCell.appendChild(hint);
      }
      harvestRowsById.set(id, row);
    });
  };

  const updateModeSections = (row) => {
    if (!row) {
      return;
    }
    const modeSelect = row.querySelector('.bulk-mode');
    const mode = modeSelect ? modeSelect.value : MODE_CONFLUENCY;
    row.dataset.mode = mode;
    const sections = row.querySelectorAll('[data-bulk-mode-section]');
    sections.forEach((section) => {
      const isActive = section.dataset.bulkModeSection === mode;
      section.hidden = !isActive;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !isActive;
      });
    });
  };

  const updateDilutionSections = (row) => {
    if (!row) {
      return;
    }
    const mode = row.dataset.dilutionMode || 'concentration';
    const sections = row.querySelectorAll('[data-bulk-dilution-section]');
    sections.forEach((section) => {
      const isActive = section.dataset.bulkDilutionSection === mode;
      section.hidden = !isActive;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !isActive;
      });
    });
  };

  const appendNoteSuggestion = (notesField, suggestion) => {
    if (!notesField || !suggestion) {
      return;
    }
    const existing = notesField.value || '';
    if (existing.includes(suggestion)) {
      return;
    }
    notesField.value = existing ? `${existing}\n${suggestion}` : suggestion;
  };

  const renderPlannerRows = (ids) => {
    if (!plannerBody) {
      return;
    }
    plannerBody.innerHTML = '';
    plannerRowsById.clear();
    ids.forEach((id) => {
      const culture = cultureMap.get(id);
      if (!culture) {
        return;
      }
      const row = plannerBody.insertRow();
      row.dataset.cultureId = String(id);
      row.dataset.nextPassage =
        culture.next_passage_number != null ? culture.next_passage_number : 1;
      row.dataset.dilutionMode = 'concentration';
      row.dataset.mode = MODE_CONFLUENCY;

      const cultureCell = row.insertCell();
      const strong = document.createElement('strong');
      strong.textContent = culture.name || `Culture ${id}`;
      cultureCell.appendChild(strong);
      const meta = document.createElement('p');
      meta.className = 'meta';
      meta.textContent = `Next: P${row.dataset.nextPassage}`;
      cultureCell.appendChild(meta);
      if (
        culture.measured_cell_concentration != null &&
        culture.measured_slurry_volume_ml != null
      ) {
        const measurementMeta = document.createElement('p');
        measurementMeta.className = 'meta';
        const totalCells =
          culture.measured_cell_concentration * culture.measured_slurry_volume_ml;
        measurementMeta.textContent = `Harvest: ${formatCells(totalCells)} cells`;
        cultureCell.appendChild(measurementMeta);
      }

      const plannerCell = row.insertCell();
      plannerCell.className = 'bulk-cell';
      plannerCell.innerHTML = `
        <div class="field-stack">
          <label>
            <span>Planner mode</span>
            <select class="bulk-mode">
              <option value="confluency">Target confluency</option>
              <option value="dilution">Concentration to dilute</option>
            </select>
          </label>
          <div class="bulk-mode-section" data-bulk-mode-section="confluency">
            <label>
              <span>Vessel</span>
              <select class="bulk-vessel"></select>
            </label>
            <label>
              <span>Target confluency (%)</span>
              <input type="text" class="bulk-target-confluency" />
            </label>
            <label>
              <span>Days until split</span>
              <input type="text" class="bulk-hours" />
            </label>
            <label>
              <span>Vessels used</span>
              <input type="number" min="1" step="1" class="bulk-vessels-used" />
            </label>
            <label>
              <span>Doubling time override (h)</span>
              <input type="text" class="bulk-doubling-override" />
            </label>
          </div>
          <div class="bulk-mode-section" data-bulk-mode-section="dilution" hidden>
            <div class="bulk-dilution-toggle">
              <label class="radio">
                <input type="radio" value="concentration" data-bulk-dilution-mode checked />
                <span>Final concentration</span>
              </label>
              <label class="radio">
                <input type="radio" value="cells" data-bulk-dilution-mode />
                <span>Cells per portion</span>
              </label>
            </div>
            <div class="bulk-dilution-section" data-bulk-dilution-section="concentration">
              <label>
                <span>Final concentration (cells/mL)</span>
                <input type="text" class="bulk-final-concentration" />
              </label>
            </div>
            <div class="bulk-dilution-section" data-bulk-dilution-section="cells" hidden>
              <label>
                <span>Cells to seed (cells)</span>
                <input type="text" class="bulk-cells-to-seed" />
              </label>
              <label>
                <span>Volume per portion (mL)</span>
                <input type="text" class="bulk-volume-per-seed" />
              </label>
            </div>
            <label>
              <span>Total volume (mL)</span>
              <input type="text" class="bulk-total-volume" />
            </label>
          </div>
          <label>
            <span>Starting concentration (cells/mL)</span>
            <input type="text" class="bulk-cell-concentration" />
          </label>
          <div class="form-actions inline">
            <button type="button" class="button secondary small bulk-calc">Calculate</button>
          </div>
          <div class="bulk-result" data-bulk-result>
            Enter planner inputs and calculate to preview guidance.
          </div>
        </div>
      `;

      const passageCell = row.insertCell();
      passageCell.className = 'bulk-cell';
      passageCell.innerHTML = `
        <div class="field-stack">
          <label>
            <span>Date</span>
            <input type="date" class="bulk-date" />
          </label>
          <label>
            <span>Media</span>
            <textarea class="bulk-media" rows="2"></textarea>
          </label>
          <label class="checkbox">
            <input type="checkbox" class="bulk-use-previous" />
            <span>Use previous media</span>
          </label>
          <label>
            <span>Cells seeded (cells)</span>
            <input type="text" class="bulk-seeded" />
          </label>
          <label>
            <span>Doubling time (h)</span>
            <input type="text" class="bulk-doubling" />
          </label>
          <label>
            <span>Notes</span>
            <textarea class="bulk-notes" rows="2"></textarea>
          </label>
        </div>
      `;

      const modeSelect = row.querySelector('.bulk-mode');
      if (modeSelect) {
        modeSelect.value = MODE_CONFLUENCY;
      }
      const vesselSelect = row.querySelector('.bulk-vessel');
      populateVesselOptions(vesselSelect, culture.default_vessel_id);
      const targetInput = row.querySelector('.bulk-target-confluency');
      if (targetInput) {
        targetInput.value = '80';
      }
      const hoursInput = row.querySelector('.bulk-hours');
      if (hoursInput) {
        hoursInput.value = '3';
      }
      const vesselsUsedInput = row.querySelector('.bulk-vessels-used');
      if (vesselsUsedInput) {
        const vesselsValue =
          culture.latest_vessels_used != null && culture.latest_vessels_used > 0
            ? culture.latest_vessels_used
            : 1;
        vesselsUsedInput.value = String(vesselsValue);
      }
      const overrideInput = row.querySelector('.bulk-doubling-override');
      if (overrideInput && culture.default_doubling_time != null) {
        overrideInput.placeholder = `${culture.default_doubling_time}`;
      }
      const finalConcentrationInput = row.querySelector('.bulk-final-concentration');
      if (finalConcentrationInput) {
        finalConcentrationInput.value = '5e5';
      }
      const totalVolumeInput = row.querySelector('.bulk-total-volume');
      if (totalVolumeInput) {
        totalVolumeInput.value = '20';
      }
      const startConcInput = row.querySelector('.bulk-cell-concentration');
      if (startConcInput) {
        const startValue = defaultConcentration(culture);
        if (startValue !== '') {
          startConcInput.value = String(startValue);
        }
      }
      const dilutionRadios = row.querySelectorAll('input[data-bulk-dilution-mode]');
      dilutionRadios.forEach((radio) => {
        radio.name = `bulk-dilution-mode-${id}`;
      });

      const dateInput = row.querySelector('.bulk-date');
      if (dateInput) {
        dateInput.value = today;
      }
      const mediaField = row.querySelector('.bulk-media');
      if (mediaField) {
        mediaField.value = culture.latest_media || '';
      }
      const mediaCheckbox = row.querySelector('.bulk-use-previous');
      if (mediaCheckbox) {
        mediaCheckbox.dataset.media = culture.latest_media || '';
      }
      const seededInput = row.querySelector('.bulk-seeded');
      if (seededInput && culture.latest_seeded_cells != null) {
        seededInput.value = String(culture.latest_seeded_cells);
      }
      const doublingField = row.querySelector('.bulk-doubling');
      if (doublingField && culture.default_doubling_time != null) {
        doublingField.value = String(culture.default_doubling_time);
      }

      updateModeSections(row);
      updateDilutionSections(row);

      if (modeSelect) {
        modeSelect.addEventListener('change', () => {
          updateModeSections(row);
        });
      }
      dilutionRadios.forEach((radio) => {
        radio.addEventListener('change', () => {
          row.dataset.dilutionMode = radio.value;
          updateDilutionSections(row);
        });
      });
      if (mediaCheckbox && mediaField) {
        mediaCheckbox.addEventListener('change', () => {
          if (mediaCheckbox.checked) {
            mediaField.value = mediaCheckbox.dataset.media || '';
          }
        });
      }
      const calcButton = row.querySelector('.bulk-calc');
      if (calcButton) {
        calcButton.addEventListener('click', () => {
          calculateSeedingForRow(row, id);
        });
      }

      plannerRowsById.set(id, row);
    });
  };

  const buildSnapshot = (culture) => {
    if (!culture) {
      return '';
    }
    const parts = [];
    if (culture.name) {
      parts.push(culture.name);
    }
    const snapshotDate = today;
    if (snapshotDate) {
      parts.push(snapshotDate);
    }
    return parts.join(' ');
  };

  const renderCopyTable = (ids) => {
    if (!copyOutput) {
      return;
    }
    clearElement(copyOutput);
    const targetIds = ids && ids.length ? ids : activeIds;
    if (!targetIds.length) {
      copyOutput.innerHTML =
        '<p class="form-hint">Select at least one culture to generate copy text.</p>';
      copyOutput.hidden = false;
      return;
    }

    const lines = [];
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'table-wrapper';
    const table = document.createElement('table');
    table.className = 'table bulk-copy-table';
    const thead = table.createTHead();
    const headRow = thead.insertRow();
    headRow.innerHTML =
      '<th scope="col">Culture</th><th scope="col">Copy text</th><th scope="col" class="actions-column">Actions</th>';
    const tbody = table.createTBody();

    targetIds.forEach((id) => {
      const culture = cultureMap.get(id);
      if (!culture) {
        return;
      }
      const snapshot = buildSnapshot(culture);
      if (!snapshot) {
        return;
      }
      lines.push(snapshot);
      const row = tbody.insertRow();
      const cultureCell = row.insertCell();
      cultureCell.textContent = culture.name || `Culture ${id}`;
      const textCell = row.insertCell();
      const pre = document.createElement('pre');
      pre.className = 'label-snippet';
      pre.textContent = snapshot;
      textCell.appendChild(pre);
      const actionsCell = row.insertCell();
      actionsCell.className = 'actions';
      const copyRowButton = document.createElement('button');
      copyRowButton.type = 'button';
      copyRowButton.className = 'button ghost small';
      copyRowButton.textContent = 'Copy';
      copyRowButton.addEventListener('click', async () => {
        await copyPlainText(snapshot);
      });
      actionsCell.appendChild(copyRowButton);
    });

    if (!lines.length) {
      copyOutput.innerHTML =
        '<p class="form-hint">Add passage details to generate copy text.</p>';
      copyOutput.hidden = false;
      return;
    }

    tableWrapper.appendChild(table);
    copyOutput.appendChild(tableWrapper);
    const copyAllButton = document.createElement('button');
    copyAllButton.type = 'button';
    copyAllButton.className = 'button secondary';
    copyAllButton.textContent = 'Copy all';
    copyAllButton.addEventListener('click', async () => {
      await copyPlainText(lines.join('; '));
    });
    copyOutput.appendChild(copyAllButton);
    copyOutput.hidden = false;
  };

  const buildLabelText = (cultureId) => {
    const culture = cultureMap.get(cultureId);
    if (!culture) {
      return '';
    }
    const row = plannerRowsById.get(cultureId);
    const lines = [];
    lines.push(`Culture: ${culture.name || `Culture ${cultureId}`}`);
    let labelDate = today;
    if (row) {
      labelDate =
        row.dataset.savedDate || row.querySelector('.bulk-date')?.value || today;
    } else if (culture.latest_passage_date) {
      labelDate = culture.latest_passage_date;
    }
    lines.push(`Date: ${labelDate}`);

    let passageNumber = culture.next_passage_number;
    if (row && row.dataset.savedPassageNumber) {
      passageNumber = row.dataset.savedPassageNumber;
    } else if (culture.latest_passage_number != null) {
      passageNumber = culture.latest_passage_number;
    }
    if (passageNumber != null) {
      const normalized = String(passageNumber).startsWith('P')
        ? String(passageNumber)
        : `P${passageNumber}`;
      lines.push(`Passage: ${normalized}`);
    }

    let cellsDisplay = '—';
    if (row) {
      if (row.dataset.savedSeededDisplay) {
        cellsDisplay = row.dataset.savedSeededDisplay;
      } else if (row.dataset.calculatedSeededDisplay) {
        cellsDisplay = row.dataset.calculatedSeededDisplay;
      } else {
        const seededInput = row.querySelector('.bulk-seeded');
        const seededValue = seededInput ? seededInput.value : '';
        const numeric = Number(seededValue);
        if (seededValue && Number.isFinite(numeric)) {
          cellsDisplay = formatCellsForLabel(numeric);
        } else if (seededValue) {
          cellsDisplay = seededValue;
        }
      }
    } else if (culture.latest_seeded_cells != null) {
      cellsDisplay = formatCellsForLabel(culture.latest_seeded_cells);
    } else if (culture.latest_seeded_display) {
      cellsDisplay = culture.latest_seeded_display;
    }
    lines.push(`Cells seeded: ${cellsDisplay}`);
    return lines.join('\n');
  };

  const renderLabelTable = (ids) => {
    if (!labelOutput) {
      return;
    }
    clearElement(labelOutput);
    const targetIds = ids && ids.length ? ids : activeIds;
    if (!targetIds.length) {
      labelOutput.innerHTML =
        '<p class="form-hint">Select cultures to prepare label text.</p>';
      labelOutput.hidden = false;
      return;
    }

    const lines = [];
    const flattenedLines = [];
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'table-wrapper';
    const table = document.createElement('table');
    table.className = 'table bulk-label-table';
    const thead = table.createTHead();
    const headRow = thead.insertRow();
    headRow.innerHTML =
      '<th scope="col">Culture</th><th scope="col">Label text</th><th scope="col" class="actions-column">Actions</th>';
    const tbody = table.createTBody();

    targetIds.forEach((id) => {
      const labelText = buildLabelText(id);
      if (!labelText) {
        return;
      }
      lines.push(labelText);
      flattenedLines.push(labelText.replace(/\s*\n\s*/g, ' '));
      const row = tbody.insertRow();
      const cultureCell = row.insertCell();
      const culture = cultureMap.get(id);
      cultureCell.textContent = culture ? culture.name : `Culture ${id}`;
      const textCell = row.insertCell();
      const pre = document.createElement('pre');
      pre.className = 'label-snippet';
      pre.textContent = labelText;
      textCell.appendChild(pre);
      const actionsCell = row.insertCell();
      actionsCell.className = 'actions';
      const copyRowButton = document.createElement('button');
      copyRowButton.type = 'button';
      copyRowButton.className = 'button ghost small';
      copyRowButton.textContent = 'Copy';
      copyRowButton.addEventListener('click', async () => {
        await copyPlainText(labelText);
      });
      actionsCell.appendChild(copyRowButton);
    });

    if (!lines.length) {
      labelOutput.innerHTML =
        '<p class="form-hint">Add passage details to generate label text.</p>';
      labelOutput.hidden = false;
      return;
    }

    tableWrapper.appendChild(table);
    labelOutput.appendChild(tableWrapper);
    const copyAllButton = document.createElement('button');
    copyAllButton.type = 'button';
    copyAllButton.className = 'button secondary';
    copyAllButton.textContent = 'Copy all labels';
    copyAllButton.addEventListener('click', async () => {
      await copyPlainText(flattenedLines.join('; '));
    });
    labelOutput.appendChild(copyAllButton);
    labelOutput.hidden = false;
  };

  const calculateSeedingForRow = async (row, cultureId) => {
    if (!row) {
      return;
    }
    const resultContainer = row.querySelector('[data-bulk-result]');
    if (resultContainer) {
      resultContainer.textContent = 'Calculating…';
    }
    const modeSelect = row.querySelector('.bulk-mode');
    const mode = modeSelect ? modeSelect.value : MODE_CONFLUENCY;
    row.dataset.mode = mode;
    const cellConcentration = row.querySelector('.bulk-cell-concentration')?.value || '';
    if (!cellConcentration.trim()) {
      if (resultContainer) {
        resultContainer.innerHTML =
          '<p class="error">Enter the starting cell concentration before calculating.</p>';
      }
      return;
    }

    const payload = {
      culture_id: cultureId,
      mode,
      cell_concentration: cellConcentration,
    };

    if (mode === MODE_CONFLUENCY) {
      const vesselSelect = row.querySelector('.bulk-vessel');
      if (!vesselSelect || !vesselSelect.value) {
        if (resultContainer) {
          resultContainer.innerHTML =
            '<p class="error">Select a vessel before calculating the seeding plan.</p>';
        }
        return;
      }
      payload.vessel_id = Number.parseInt(vesselSelect.value, 10);
      const targetConfluencyInput = row.querySelector('.bulk-target-confluency');
      payload.target_confluency = targetConfluencyInput ? targetConfluencyInput.value : '';
      const daysInput = row.querySelector('.bulk-hours');
      if (daysInput && daysInput.value) {
        const days = Number.parseFloat(daysInput.value);
        if (Number.isFinite(days)) {
          payload.target_hours = String(days * 24);
        }
      }
      const vesselsUsedInput = row.querySelector('.bulk-vessels-used');
      payload.vessels_used = vesselsUsedInput ? vesselsUsedInput.value : '';
      const doublingOverride = row.querySelector('.bulk-doubling-override');
      if (doublingOverride && doublingOverride.value) {
        payload.doubling_time_override = doublingOverride.value;
      }
    } else {
      const dilutionMode = row.dataset.dilutionMode || 'concentration';
      payload.dilution_input_mode = dilutionMode;
      const totalVolumeInput = row.querySelector('.bulk-total-volume');
      payload.total_volume_ml = totalVolumeInput ? totalVolumeInput.value : '';
      if (dilutionMode === 'cells') {
        payload.cells_to_seed = row.querySelector('.bulk-cells-to-seed')?.value || '';
        payload.volume_per_seed_ml =
          row.querySelector('.bulk-volume-per-seed')?.value || '';
      } else {
        payload.final_concentration =
          row.querySelector('.bulk-final-concentration')?.value || '';
      }
    }

    try {
      const response = await fetch('/api/calc-seeding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      let data;
      try {
        data = await parseJsonResponse(response);
      } catch (parseError) {
        console.error('Failed to parse bulk seeding response', parseError);
        if (resultContainer) {
          resultContainer.innerHTML =
            '<p class="error">Server returned an unexpected response. Please try again.</p>';
        }
        return;
      }
      if (!response.ok) {
        if (resultContainer) {
          resultContainer.innerHTML = `<p class="error">${
            data.error || 'Calculation failed.'
          }</p>`;
        }
        return;
      }

      if (resultContainer) {
        resultContainer.innerHTML = buildSeedingSummary(data);
      }

      const seededInput = row.querySelector('.bulk-seeded');
      if (seededInput) {
        if (data.mode === MODE_DILUTION) {
          seededInput.value = data.cells_needed ?? '';
        } else {
          seededInput.value = data.required_cells_total ?? '';
        }
      }

      const vesselSelect = row.querySelector('.bulk-vessel');
      if (vesselSelect && data.vessel_id) {
        vesselSelect.value = data.vessel_id;
      }

      const vesselsUsedInput = row.querySelector('.bulk-vessels-used');
      if (vesselsUsedInput && data.vessels_used !== undefined) {
        vesselsUsedInput.value = data.vessels_used ?? '';
      }

      const notesField = row.querySelector('.bulk-notes');
      appendNoteSuggestion(notesField, data.note_suggestion);

      const labelCells =
        data.mode === MODE_DILUTION ? data.cells_needed : data.required_cells_total;
      if (labelCells !== undefined) {
        row.dataset.calculatedSeeded = labelCells;
        row.dataset.calculatedSeededDisplay =
          data.mode === MODE_DILUTION
            ? data.cells_needed_formatted || formatCells(labelCells)
            : data.required_cells_total_formatted || formatCells(labelCells);
      }

      row.dataset.lastCalculation = JSON.stringify(data);
    } catch (error) {
      if (resultContainer) {
        resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
      }
    }
  };

  const gatherPlannerEntries = (ids) => {
    return ids
      .map((id) => {
        const row = plannerRowsById.get(id);
        if (!row) {
          return null;
        }
        const culture = cultureMap.get(id);
        const modeSelect = row.querySelector('.bulk-mode');
        const mode = modeSelect ? modeSelect.value : MODE_CONFLUENCY;
        row.dataset.mode = mode;
        const readValue = (selector) => {
          const element = row.querySelector(selector);
          if (!element) {
            return '';
          }
          if (element.type === 'checkbox') {
            return element.checked ? '1' : '';
          }
          return element.value || '';
        };
        const entry = {
          culture_id: id,
          measured_cell_concentration: culture?.measured_cell_concentration ?? '',
          measured_slurry_volume_ml: culture?.measured_slurry_volume_ml ?? '',
          cell_concentration: readValue('.bulk-cell-concentration'),
          vessel_id: readValue('.bulk-vessel'),
          vessels_used: readValue('.bulk-vessels-used'),
          seeded_cells: readValue('.bulk-seeded'),
          media: readValue('.bulk-media'),
          doubling_time_hours: readValue('.bulk-doubling'),
          notes: readValue('.bulk-notes'),
          date: readValue('.bulk-date'),
          use_previous_media: readValue('.bulk-use-previous') ? 1 : '',
        };
        const daysRaw = readValue('.bulk-hours');
        if (daysRaw) {
          const days = Number.parseFloat(daysRaw);
          if (Number.isFinite(days)) {
            entry.target_hours = String(days * 24);
          }
        }
        const override = readValue('.bulk-doubling-override');
        if (override) {
          entry.doubling_time_override = override;
        }
        const cultureMeasurements = culture;
        if (
          cultureMeasurements?.measured_cell_concentration != null &&
          cultureMeasurements?.measured_slurry_volume_ml != null
        ) {
          const total =
            cultureMeasurements.measured_cell_concentration *
            cultureMeasurements.measured_slurry_volume_ml;
          entry.measured_yield_millions = total / 1_000_000;
        }
        if (mode === MODE_DILUTION) {
          entry.dilution_input_mode = row.dataset.dilutionMode || 'concentration';
          entry.total_volume_ml = readValue('.bulk-total-volume');
          if (entry.dilution_input_mode === 'cells') {
            entry.cells_to_seed = readValue('.bulk-cells-to-seed');
            entry.volume_per_seed_ml = readValue('.bulk-volume-per-seed');
          } else {
            entry.final_concentration = readValue('.bulk-final-concentration');
          }
        }
        return entry;
      })
      .filter((entry) => entry !== null);
  };

  const updateFromHarvestResponse = (records) => {
    if (!Array.isArray(records)) {
      return;
    }
    records.forEach((record) => {
      const id = Number.parseInt(record.culture_id, 10);
      if (Number.isNaN(id)) {
        return;
      }
      const culture = cultureMap.get(id);
      if (culture) {
        culture.measured_cell_concentration = record.measured_cell_concentration;
        culture.measured_slurry_volume_ml = record.measured_slurry_volume_ml;
        if (record.measured_slurry_volume_ml != null) {
          culture.default_slurry_volume_ml = record.measured_slurry_volume_ml;
        }
        if (Object.prototype.hasOwnProperty.call(record, 'pre_split_confluence_percent')) {
          culture.pre_split_confluence_percent = record.pre_split_confluence_percent;
        }
      }
    });
  };

  const updateRowsFromResponse = (records) => {
    if (!Array.isArray(records)) {
      return;
    }
    records.forEach((record) => {
      const cultureId = Number.parseInt(record.culture_id, 10);
      if (Number.isNaN(cultureId)) {
        return;
      }
      const row = plannerRowsById.get(cultureId);
      if (row) {
        row.dataset.savedPassageNumber = record.passage_number;
        row.dataset.savedDate = record.date;
        if (record.seeded_cells !== undefined && record.seeded_cells !== null) {
          row.dataset.savedSeeded = record.seeded_cells;
          row.dataset.savedSeededDisplay =
            record.seeded_cells_formatted || formatCells(record.seeded_cells);
        }
        row.dataset.nextPassage = record.passage_number + 1;
        const metaNodes = row.querySelectorAll('td .meta');
        if (metaNodes.length) {
          metaNodes[0].textContent = `Next: P${record.passage_number + 1}`;
        }
        const dateField = row.querySelector('.bulk-date');
        if (dateField) {
          dateField.value = record.date;
        }
        const mediaField = row.querySelector('.bulk-media');
        if (mediaField) {
          mediaField.value = record.media || '';
        }
        const seededField = row.querySelector('.bulk-seeded');
        if (seededField && record.seeded_cells !== undefined && record.seeded_cells !== null) {
          seededField.value = record.seeded_cells;
        }
      }
      const culture = cultureMap.get(cultureId);
      if (culture) {
        culture.latest_passage_number = record.passage_number;
        culture.latest_passage_date = record.date;
        culture.latest_media = record.media || '';
        culture.latest_seeded_cells = record.seeded_cells ?? null;
        culture.latest_seeded_display =
          record.seeded_cells_formatted ||
          (record.seeded_cells !== undefined && record.seeded_cells !== null
            ? formatCells(record.seeded_cells)
            : culture.latest_seeded_display);
        culture.next_passage_number = record.passage_number + 1;
        culture.measured_cell_concentration = record.measured_cell_concentration;
        culture.measured_slurry_volume_ml = record.measured_slurry_volume_ml;
        if (record.measured_slurry_volume_ml != null) {
          culture.default_slurry_volume_ml = record.measured_slurry_volume_ml;
        }
        culture.pre_split_confluence_percent = null;
      }
    });
  };

  const renderLabelOutput = (ids) => {
    renderLabelTable(ids);
  };

  if (selectAllButton) {
    selectAllButton.addEventListener('click', () => {
      const checkboxes = bulkCard.querySelectorAll('.bulk-culture-select');
      const shouldSelectAll = Array.from(checkboxes).some((checkbox) => !checkbox.checked);
      checkboxes.forEach((checkbox) => {
        checkbox.checked = shouldSelectAll;
      });
    });
  }

  if (copyButton) {
    copyButton.addEventListener('click', () => {
      const ids = getSelectedIds();
      renderCopyTable(ids);
    });
  }

  if (harvestTab) {
    harvestTab.addEventListener('click', () => {
      if (workflow && !workflow.hidden) {
        setActiveTab('harvest');
      }
    });
  }

  if (plannerTab) {
    plannerTab.addEventListener('click', () => {
      if (plannerTab.disabled) {
        showStatus(
          harvestStatus,
          'Save harvest measurements to unlock the planner.',
          'error'
        );
        setActiveTab('harvest');
        return;
      }
      setActiveTab('planner');
    });
  }

  if (startButton) {
    startButton.addEventListener('click', () => {
      const ids = getSelectedIds();
      activeIds = ids;
      resetStatuses();
      if (!ids.length) {
        ensureWorkflowVisible(ids);
        showStatus(statusNode, 'Select at least one culture to begin.', 'error');
        return;
      }
      harvestSaved = false;
      renderHarvestRows(ids);
      renderPlannerRows(ids);
      if (plannerTab) {
        plannerTab.disabled = true;
      }
      ensureWorkflowVisible(ids);
      setActiveTab('harvest');
      showStatus(harvestStatus, 'Record harvest measurements, then save to continue.');
      clearElement(labelOutput);
      if (labelOutput) {
        labelOutput.hidden = true;
      }
      clearElement(copyOutput);
      if (copyOutput) {
        copyOutput.hidden = true;
      }
    });
  }

  if (harvestForm) {
    harvestForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!activeIds.length) {
        showStatus(harvestStatus, 'Select cultures before saving.', 'error');
        return;
      }
      const entries = [];
      let hasError = false;
      activeIds.forEach((id) => {
        const row = harvestRowsById.get(id);
        if (!row) {
          return;
        }
        const culture = cultureMap.get(id);
        const name = culture ? culture.name : `Culture ${id}`;
        const concInput = row.querySelector('.bulk-harvest-concentration');
        const volInput = row.querySelector('.bulk-harvest-volume');
        const confluenceInput = row.querySelector('.bulk-harvest-confluence');
        const concValue = concInput ? concInput.value.trim() : '';
        const volValue = volInput ? volInput.value.trim() : '';
        const confluenceValue = confluenceInput ? confluenceInput.value.trim() : '';
        const concNumber = parseNumericInput(concValue);
        const volNumber = parseNumericInput(volValue);
        let confluenceRounded = null;
        if (confluenceValue) {
          const confluenceNumber = parseNumericInput(confluenceValue);
          if (confluenceNumber === null) {
            hasError = true;
            showStatus(
              harvestStatus,
              `Enter a valid pre-split confluence for ${name}.`,
              'error'
            );
            return;
          }
          const rounded = Math.round(confluenceNumber);
          if (rounded < 0 || rounded > 100) {
            hasError = true;
            showStatus(
              harvestStatus,
              `Pre-split confluence for ${name} should be between 0 and 100%.`,
              'error'
            );
            return;
          }
          confluenceRounded = rounded;
        }
        if (!concValue || concNumber === null || concNumber <= 0) {
          hasError = true;
          showStatus(
            harvestStatus,
            `Enter a valid measured concentration for ${name}.`,
            'error'
          );
          return;
        }
        if (!volValue || volNumber === null || volNumber <= 0) {
          hasError = true;
          showStatus(harvestStatus, `Enter a valid slurry volume for ${name}.`, 'error');
          return;
        }
        const entry = {
          culture_id: id,
          measured_cell_concentration: concNumber,
          measured_slurry_volume_ml: volNumber,
        };
        if (confluenceRounded !== null) {
          entry.pre_split_confluence_percent = confluenceRounded;
        }
        entries.push(entry);
      });
      if (hasError || !entries.length) {
        return;
      }
      showStatus(harvestStatus, 'Saving harvest…');
      try {
        const response = await fetch('/api/bulk-harvest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entries }),
        });
        let data;
        try {
          data = await parseJsonResponse(response);
        } catch (parseError) {
          console.error('Failed to parse bulk harvest response', parseError);
          showStatus(
            harvestStatus,
            'Server returned an unexpected response. Please try again.',
            'error'
          );
          return;
        }
        if (!response.ok) {
          showStatus(harvestStatus, data.error || 'Failed to save harvest.', 'error');
          return;
        }
        harvestSaved = true;
        updateFromHarvestResponse(data.records);
        renderPlannerRows(activeIds);
        if (plannerTab) {
          plannerTab.disabled = false;
        }
        setActiveTab('planner');
        showStatus(harvestStatus, 'Harvest saved. Configure planner inputs next.');
        showStatus(plannerStatus, 'Enter seeding parameters and save to log passages.');
      } catch (error) {
        showStatus(harvestStatus, error.message, 'error');
      }
    });
  }

  if (plannerForm) {
    plannerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!activeIds.length) {
        showStatus(plannerStatus, 'Select cultures before saving.', 'error');
        return;
      }
      if (!harvestSaved) {
        showStatus(plannerStatus, 'Save harvest measurements before logging passages.', 'error');
        setActiveTab('harvest');
        return;
      }
      const entries = gatherPlannerEntries(activeIds);
      if (!entries.length) {
        showStatus(plannerStatus, 'Add passage details before saving.', 'error');
        return;
      }
      const confirmed = window.confirm('Are you sure you want to save?');
      if (!confirmed) {
        return;
      }
      showStatus(plannerStatus, 'Saving passages…');
      try {
        const response = await fetch('/api/bulk-passages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entries }),
        });
        let data;
        try {
          data = await parseJsonResponse(response);
        } catch (parseError) {
          console.error('Failed to parse bulk passage response', parseError);
          showStatus(
            plannerStatus,
            'Server returned an unexpected response. Please try again.',
            'error'
          );
          return;
        }
        if (!response.ok) {
          showStatus(plannerStatus, data.error || 'Failed to save passages.', 'error');
          return;
        }
        updateRowsFromResponse(data.passages);
        showStatus(
          plannerStatus,
          `Saved ${data.created} passage${data.created === 1 ? '' : 's'}.`
        );
        renderCopyTable(activeIds);
        renderLabelOutput(activeIds);
      } catch (error) {
        showStatus(plannerStatus, error.message, 'error');
      }
    });
  }
}


document.addEventListener('DOMContentLoaded', () => {
  attachHarvestTabs();
  attachMediaCheckboxHandler();
  attachPassageLabelCopyHandler();
  attachModeSwitcher();
  attachDilutionModeSwitcher();
  attachSeedingFormHandler();
  attachMycoSelectAllHandlers();
  attachMycoTableCopyHandlers();
  attachCulturePrintHandlers();
  initBulkProcessing();
});
