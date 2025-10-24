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
      const cellLine = button.getAttribute('data-cell-line') || '';
      const passageNumber = button.getAttribute('data-passage-number') || '';
      const dateString =
        button.getAttribute('data-date') || new Date().toISOString().slice(0, 10);
      const seededCells = button.getAttribute('data-seeded') || '';
      const media = button.getAttribute('data-media') || '';
      const parts = [];
      if (cellLine) {
        parts.push(cellLine);
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

      const snapshot = parts.join(' · ');
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
      cultureMap.set(id, entry);
    }
  });

  if (!cultureMap.size) {
    return;
  }

  const today = bulkCard.dataset.today || new Date().toISOString().slice(0, 10);
  const selectAllButton = bulkCard.querySelector('[data-bulk-select-all]');
  const copyButton = bulkCard.querySelector('[data-bulk-generate-copy]');
  const prepareButton = bulkCard.querySelector('[data-bulk-prepare-passages]');
  const labelsButton = bulkCard.querySelector('[data-bulk-copy-labels]');
  const copyOutput = bulkCard.querySelector('#bulk-copy-output');
  const labelOutput = bulkCard.querySelector('#bulk-label-output');
  const form = bulkCard.querySelector('[data-bulk-form]');
  const statusNode = bulkCard.querySelector('[data-bulk-status]');
  const rows = form ? Array.from(form.querySelectorAll('tr[data-bulk-row]')) : [];
  const rowsById = new Map();
  rows.forEach((row) => {
    const id = Number.parseInt(row.dataset.cultureId, 10);
    if (!Number.isNaN(id)) {
      rowsById.set(id, row);
    }
  });

  const clearElement = (node) => {
    if (node) {
      node.innerHTML = '';
    }
  };

  const showStatus = (message, type = 'info') => {
    if (!statusNode) {
      return;
    }
    statusNode.textContent = message || '';
    statusNode.classList.toggle('error', type === 'error');
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

  const buildSnapshot = (options) => {
    const parts = [];
    if (options.cellLine) {
      parts.push(options.cellLine);
    }
    if (options.date) {
      parts.push(options.date);
    }
    if (options.passage) {
      const passageString = String(options.passage);
      parts.push(passageString.startsWith('P') ? passageString : `P${passageString}`);
    }
    if (options.seeded && options.seeded !== '—') {
      parts.push(`${options.seeded} cells`);
    }
    if (options.media) {
      parts.push(options.media);
    }
    return parts.join(' · ');
  };

  const renderCopyTable = (ids) => {
    if (!copyOutput) {
      return;
    }
    clearElement(copyOutput);
    if (!ids.length) {
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

    ids.forEach((id) => {
      const culture = cultureMap.get(id);
      if (!culture) {
        return;
      }
      const snapshot = buildSnapshot({
        cellLine: culture.cell_line,
        date: culture.latest_passage_date || today,
        passage: culture.latest_passage_number,
        seeded: culture.latest_seeded_display,
        media: culture.latest_media,
      });
      if (!snapshot) {
        return;
      }
      lines.push(snapshot);
      const row = tbody.insertRow();
      const cultureCell = row.insertCell();
      cultureCell.textContent = culture.name || culture.cell_line || '';
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
      copyRowButton.addEventListener('click', () => {
        copyPlainText(snapshot);
      });
      actionsCell.appendChild(copyRowButton);
    });

    if (!lines.length) {
      copyOutput.innerHTML =
        '<p class="form-hint">No copy text is available yet for the selected cultures.</p>';
      copyOutput.hidden = false;
      return;
    }

    tableWrapper.appendChild(table);
    copyOutput.appendChild(tableWrapper);

    if (lines.length) {
      const copyAllButton = document.createElement('button');
      copyAllButton.type = 'button';
      copyAllButton.className = 'button secondary';
      copyAllButton.textContent = 'Copy all';
      copyAllButton.addEventListener('click', () => {
        copyPlainText(lines.join('\n'));
      });
      copyOutput.appendChild(copyAllButton);
    }

    copyOutput.hidden = false;
  };

  const updateModeSections = (row) => {
    const modeSelect = row.querySelector('.bulk-mode');
    const mode = modeSelect ? modeSelect.value : 'confluency';
    row.dataset.mode = mode;
    const sections = row.querySelectorAll('.bulk-mode-section');
    sections.forEach((section) => {
      const active = section.dataset.bulkModeSection === mode;
      section.hidden = !active;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !active;
      });
    });
  };

  const updateDilutionSections = (row) => {
    const radios = row.querySelectorAll('input[data-bulk-dilution-mode]');
    let mode = 'concentration';
    radios.forEach((radio) => {
      if (radio.checked) {
        mode = radio.value;
      }
    });
    row.dataset.dilutionMode = mode;
    const sections = row.querySelectorAll('[data-bulk-dilution-section]');
    sections.forEach((section) => {
      const active = section.dataset.bulkDilutionSection === mode;
      section.hidden = !active;
      const inputs = section.querySelectorAll('input, select, textarea');
      inputs.forEach((input) => {
        input.disabled = !active;
      });
    });
  };

  const appendNoteSuggestion = (notesField, suggestion) => {
    if (!notesField || !suggestion) {
      return;
    }
    const existingGenerated = notesField.dataset.generatedNote || '';
    if (!notesField.value || notesField.value === existingGenerated) {
      notesField.value = suggestion;
      notesField.dataset.generatedNote = suggestion;
    } else if (!notesField.value.includes(suggestion)) {
      notesField.value = `${notesField.value}\n\n${suggestion}`;
      notesField.dataset.generatedNote = suggestion;
    }
  };

  const calculateSeedingForRow = async (row, cultureId) => {
    const culture = cultureMap.get(cultureId);
    if (!culture) {
      return;
    }
    const resultContainer = row.querySelector('[data-bulk-result]');
    if (resultContainer) {
      resultContainer.textContent = 'Calculating…';
    }

    const modeSelect = row.querySelector('.bulk-mode');
    const mode = modeSelect ? modeSelect.value : 'confluency';
    const cellConcentrationInput = row.querySelector('.bulk-cell-concentration');
    const cellConcentration = cellConcentrationInput
      ? cellConcentrationInput.value.trim()
      : '';
    if (!cellConcentration) {
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
      const targetConfluencyInput = row.querySelector('.bulk-target-confluency');
      const hoursInput = row.querySelector('.bulk-hours');
      const vesselsUsedInput = row.querySelector('.bulk-vessels-used');
      const doublingInput = row.querySelector('.bulk-doubling-override');

      if (!vesselSelect || !vesselSelect.value) {
        if (resultContainer) {
          resultContainer.innerHTML =
            '<p class="error">Select a vessel before calculating the seeding plan.</p>';
        }
        return;
      }

      payload.vessel_id = Number.parseInt(vesselSelect.value, 10);
      payload.target_confluency = targetConfluencyInput
        ? targetConfluencyInput.value
        : '';
      payload.target_hours = hoursInput ? hoursInput.value : '';
      payload.vessels_used = vesselsUsedInput ? vesselsUsedInput.value : '';
      if (doublingInput && doublingInput.value) {
        payload.doubling_time_override = doublingInput.value;
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
      const data = await response.json();
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
        data.mode === MODE_DILUTION
          ? data.cells_needed
          : data.required_cells_total;
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

  const toggleRows = (ids) => {
    if (!form) {
      return;
    }
    rows.forEach((row) => {
      const id = Number.parseInt(row.dataset.cultureId, 10);
      row.hidden = !ids.includes(id);
    });
    form.hidden = !ids.length;
  };

  const gatherEntries = (ids) => {
    return ids
      .map((id) => {
        const row = rowsById.get(id);
        if (!row || row.hidden) {
          return null;
        }
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
        return {
          culture_id: id,
          measured_cell_concentration: readValue('.bulk-measured-concentration'),
          measured_slurry_volume_ml: readValue('.bulk-measured-volume'),
          measured_yield_millions: readValue('.bulk-measured-yield'),
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
      })
      .filter((entry) => entry !== null);
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
      const row = rowsById.get(cultureId);
      if (row) {
        row.dataset.savedPassageNumber = record.passage_number;
        row.dataset.savedDate = record.date;
        if (record.seeded_cells !== undefined && record.seeded_cells !== null) {
          row.dataset.savedSeeded = record.seeded_cells;
          row.dataset.savedSeededDisplay =
            record.seeded_cells_formatted || formatCells(record.seeded_cells);
        }
        row.dataset.nextPassage = record.passage_number + 1;
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
      }
    });
  };

  const buildLabelText = (cultureId) => {
    const culture = cultureMap.get(cultureId);
    if (!culture) {
      return '';
    }
    const row = rowsById.get(cultureId);
    const lines = [];
    lines.push(`Culture: ${culture.name}`);
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
    } else if (culture.latest_passage_number) {
      passageNumber = culture.latest_passage_number;
    }
    if (passageNumber !== undefined && passageNumber !== null) {
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
    } else if (culture.latest_seeded_cells) {
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
    if (!ids.length) {
      labelOutput.innerHTML =
        '<p class="form-hint">Select cultures to prepare label text.</p>';
      labelOutput.hidden = false;
      return;
    }

    const lines = [];
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'table-wrapper';
    const table = document.createElement('table');
    table.className = 'table bulk-label-table';
    const thead = table.createTHead();
    const headRow = thead.insertRow();
    headRow.innerHTML =
      '<th scope="col">Culture</th><th scope="col">Label text</th><th scope="col" class="actions-column">Actions</th>';
    const tbody = table.createTBody();

    ids.forEach((id) => {
      const labelText = buildLabelText(id);
      if (!labelText) {
        return;
      }
      lines.push(labelText);
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
      copyRowButton.addEventListener('click', () => {
        copyPlainText(labelText);
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

    if (lines.length) {
      const copyAllButton = document.createElement('button');
      copyAllButton.type = 'button';
      copyAllButton.className = 'button secondary';
      copyAllButton.textContent = 'Copy all labels';
      copyAllButton.addEventListener('click', () => {
        copyPlainText(lines.join('\n\n'));
      });
      labelOutput.appendChild(copyAllButton);
    }

    labelOutput.hidden = false;
  };

  rows.forEach((row) => {
    updateModeSections(row);
    updateDilutionSections(row);
    const modeSelect = row.querySelector('.bulk-mode');
    if (modeSelect) {
      modeSelect.addEventListener('change', () => {
        updateModeSections(row);
      });
    }
    const dilutionRadios = row.querySelectorAll('input[data-bulk-dilution-mode]');
    dilutionRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        updateDilutionSections(row);
      });
    });
    const mediaCheckbox = row.querySelector('.bulk-use-previous');
    if (mediaCheckbox) {
      const mediaField = row.querySelector('.bulk-media');
      mediaCheckbox.addEventListener('change', () => {
        if (mediaCheckbox.checked && mediaField) {
          mediaField.value = mediaCheckbox.dataset.media || '';
        }
      });
    }
    const calcButton = row.querySelector('.bulk-calc');
    if (calcButton) {
      calcButton.addEventListener('click', () => {
        const id = Number.parseInt(row.dataset.cultureId, 10);
        if (!Number.isNaN(id)) {
          calculateSeedingForRow(row, id);
        }
      });
    }
  });

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

  if (prepareButton) {
    prepareButton.addEventListener('click', () => {
      const ids = getSelectedIds();
      toggleRows(ids);
      if (!ids.length) {
        showStatus('Select at least one culture to prepare passages.', 'error');
      } else {
        showStatus('Fill in the visible rows and save when ready.');
      }
    });
  }

  if (labelsButton) {
    labelsButton.addEventListener('click', () => {
      const ids = getSelectedIds();
      renderLabelTable(ids);
    });
  }

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const ids = getSelectedIds();
      if (!ids.length) {
        showStatus('Select at least one culture before saving.', 'error');
        return;
      }
      const entries = gatherEntries(ids);
      if (!entries.length) {
        showStatus('Add passage details before saving.', 'error');
        return;
      }

      showStatus('Saving passages…');
      try {
        const response = await fetch('/api/bulk-passages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entries }),
        });
        const data = await response.json();
        if (!response.ok) {
          showStatus(data.error || 'Failed to save passages.', 'error');
          return;
        }
        updateRowsFromResponse(data.passages);
        showStatus(`Saved ${data.created} passage${data.created === 1 ? '' : 's'}.`);
        renderCopyTable(ids);
        renderLabelTable(ids);
      } catch (error) {
        showStatus(error.message, 'error');
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  attachMediaCheckboxHandler();
  attachModeSwitcher();
  attachDilutionModeSwitcher();
  attachSeedingFormHandler();
  attachMycoSelectAllHandlers();
  attachMycoTableCopyHandlers();
  attachCulturePrintHandlers();
  initBulkProcessing();
});
