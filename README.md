# cellSplitter

A lightweight Flask web app for tracking tissue culture passages, media history, and
seeding plans. Create a culture journal, log each passage, and calculate how many cells to
seed toward a desired confluency using built-in doubling times and vessel capacity data.

## Features

- 📓 **Culture journal** – Record each passage with media, cell concentrations, doubling
  times, and notes.
- 🔁 **Auto-numbered passages** – Choose the starting passage (defaults to P1) and let the
  app increment numbers automatically (P1, P2, …).
- 🧪 **Media reuse** – Pull forward the previous passage's media with a single checkbox.
- 📈 **Seeding planner** – Split the culture or run a combined seed-and-split workflow:
  calculate required cells and volumes toward a target confluency or dilute a portion to a
  desired concentration and volume, then push the plan straight into the passage log.
- 📊 **Harvest tracking** – Record measured harvest concentrations, volumes, and
  viability so the seeding planner and passage form always start with the latest
  suspension data.
- 🌱 **Pre-split confluency** – Capture the observed confluence before harvesting so the
  next passage form and history both reflect how dense the culture was.
- 🧫 **Bulk harvest & passages** – Select multiple cultures to capture confluency,
  harvest measurements, plan seeding, and commit new passages (plus labels) in one
  workflow.
- 📁 **Archive cultures** – Mark cultures as ended to move them into an archived list
  while preserving full passage history, or permanently delete ended cultures when
  they are no longer needed.
- 🔔 **Culture reminders** – Highlight stale cultures and configure the passage-number
  threshold that triggers a “time to refresh” reminder.
- ♻️ **Media refresh logging** – Append a dated “media refreshed” note to the latest
  passage with a single click.
- ✏️ **Edit or remove passages** – Correct typos or delete errant entries without touching
  the surrounding history.
- 🧬 **Doubling-time library** – Preloaded database of common cell lines with editable
  doubling-time ranges and references.
- 🧮 **Tissue culture vessel data** – Uses surface areas and cell capacities curated from
  ThermoFisher’s “Cell Culture Useful Numbers” reference to estimate final cell yields.
- 🏷️ **One-click labels** – Generate printer-friendly label text from the seeding planner
  and copy it straight to the clipboard.
- 🧾 **Myco label run** – Grab a dashboard table of today’s labels for every active
  culture—preformatted with the date and CY initials for quick mycoplasma testing.
- 📤 **CSV export** – Download an overview of all active cultures—including the most
  recent passage details—for external reporting.

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the development server**

   ```bash
   flask --app app run --debug
   ```

   The app stores data in a local SQLite database (`cellsplitter.db`).

3. **Open the interface** at <http://127.0.0.1:5000> to create cultures, log passages, and
   plan seeding densities.

## Usage notes

- When creating a culture, you can set the initial passage number (defaults to P1) and
  record any starting media, doubling-time, or concentration values alongside it.
- The seeding planner defaults to the average doubling time of the selected cell line but
  lets you override it for passage-specific behavior. Switch to *Concentration to dilute*
  mode to compute how much cell slurry and media are needed to reach a desired final
  concentration and volume.
- Cultures default to a T75 flask in the target confluency planner—swap the vessel if you
  are planning for a different format.
- Log the measured suspension concentration and total harvest volume in the culture detail
- Record pre-split confluency and viability just before harvest—the values auto-fill the
  passage form and are saved with the resulting passage entry for future reference.
- Cell concentration inputs accept plain numbers as well as shorthand such as `300K`,
  `1.5e6`, or `2.3M` cells/mL.
- Use the “Use previous passage media” checkbox when logging a passage to keep media
  formulations consistent.
- Apply seeding planner results to the passage form—or save them outright—to capture
  vessel usage, seeded cells, and planning notes without retyping. Switch to *Seed & split*
  mode when a portion of the harvest needs to be diluted separately (e.g. for QC assays).
- Copy the generated label text after a seeding or dilution calculation to print or share
  culture labels with consistent naming.
- Need a quick mycoplasma check run? Use the dashboard’s Myco test labels table to copy
  today’s culture/date/CY label text in bulk.
- Use the bulk processing card on the dashboard to record confluence, harvest measurements,
  planner inputs, and passage saves for several cultures at once.
- Adjust the passage reminder threshold in the dashboard header to customize when the
  “time to refresh” warning appears, and watch for stale-culture highlights after four
  days without activity.
- End a culture when you are finished working with it to tuck it into the archived list;
  you can reactivate it later if needed, or permanently delete archived cultures from the
  dashboard when their records are no longer required.
- Provide a reason when ending a culture to keep archival notes alongside the record, and
  use the “Refresh media” action to append dated maintenance notes without logging a new
  passage.
- Need to fix a mistake? Open any passage entry to edit or delete it without affecting the
  rest of the log.
- Use the export control atop the dashboard to download active cultures, ended cultures,
  or a combined CSV snapshot in a single click.
- To keep a copy of the database, back up `cellsplitter.db` or point `SQLALCHEMY_DATABASE_URI`
  to your preferred database engine.

## Data sources

Default cell lines and vessel capacities are seeded from the JSON files in `data/`. The
values mirror publicly available vendor catalogs (ATCC, ThermoFisher) for convenience—verify
against your lab’s validated growth rates when planning experiments.

## License

This project is provided as-is under the MIT license.
