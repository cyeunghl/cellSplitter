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
    segments.push(
      `<p>At ${formatCells(data.cell_concentration)} cells/mL, seed <strong>${data.volume_needed_formatted}</strong>.</p>`
    );
  } else {
    segments.push(
      '<p class="note">Enter a valid cell concentration to get a recommended seeding volume.</p>'
    );
  }
  segments.push(
    `<p class="meta">Projected final yield: ${formatCells(data.final_cells)} cells (${data.growth_cycles.toFixed(
      2
    )} doublings).</p>`
  );
  return segments.join('\n');
}

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

    const payload = {
      culture_id: form.dataset.cultureId,
      vessel_id: vesselId,
      target_confluency: targetConfluency,
      target_hours: totalHours,
      cell_concentration: formData.get('cell_concentration'),
      doubling_time_override: formData.get('doubling_time_override'),
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
    } catch (error) {
      resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  attachCopyMediaHandler();
  attachSeedingFormHandler();
});
