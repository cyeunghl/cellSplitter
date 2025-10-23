# cellSplitter

A lightweight Flask web app for tracking tissue culture passages, media history, and
seeding plans. Create a culture journal, log each passage, and calculate how many cells to
seed toward a desired confluency using built-in doubling times and vessel capacity data.

## Features

- 📓 **Culture journal** – Record each passage with media, cell concentrations, doubling
  times, and notes.
- 🔁 **Auto-numbered passages** – Passage numbers increment automatically (P1, P2, …).
- 🧪 **Media reuse** – Pull forward the previous passage's media with a single checkbox.
- 📈 **Seeding planner** – Calculate required cell numbers and seeding volumes based on
  target confluency, time to split, vessel size, and doubling time, or plan dilutions to
  reach a specific concentration and total volume, then push the plan directly into the
  passage log.
- 📁 **Archive cultures** – Mark cultures as ended to move them into an archived list
  while preserving full passage history.
- ✏️ **Edit or remove passages** – Correct typos or delete errant entries without touching
  the surrounding history.
- 🧬 **Doubling-time library** – Preloaded database of common cell lines with editable
  doubling-time ranges and references.
- 🧮 **Tissue culture vessel data** – Uses surface areas and cell capacities curated from
  ThermoFisher’s “Cell Culture Useful Numbers” reference to estimate final cell yields.
- 🏷️ **One-click labels** – Generate printer-friendly label text from the seeding planner
  and copy it straight to the clipboard.
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

- When creating a culture, the initial passage (P1) is recorded automatically with any
  media, doubling-time, or concentration values you supply.
- The seeding planner defaults to the average doubling time of the selected cell line but
  lets you override it for passage-specific behavior. Switch to *Concentration to dilute*
  mode to compute how much cell slurry and media are needed to reach a desired final
  concentration and volume.
- Cell concentration inputs accept plain numbers as well as shorthand such as `300K`,
  `1.5e6`, or `2.3M` cells/mL.
- Use the “Use previous passage media” checkbox when logging a passage to keep media
  formulations consistent.
- Apply seeding planner results to the passage form—or save them outright—to capture
  vessel usage, seeded cells, and planning notes without retyping.
- Copy the generated label text after a seeding or dilution calculation to print or share
  culture labels with consistent naming.
- End a culture when you are finished working with it to tuck it into the archived list;
  you can reactivate it later if needed. Active culture cards include a quick “End
  culture” button, while the culture detail page offers both end and reactivate options.
- Need to fix a mistake? Open any passage entry to edit or delete it without affecting the
  rest of the log.
- Use the “Export active cultures (CSV)” button atop the dashboard to download the current
  state of all in-progress cultures.
- To keep a copy of the database, back up `cellsplitter.db` or point `SQLALCHEMY_DATABASE_URI`
  to your preferred database engine.

## Data sources

Default cell lines and vessel capacities are seeded from the JSON files in `data/`. The
values mirror publicly available vendor catalogs (ATCC, ThermoFisher) for convenience—verify
against your lab’s validated growth rates when planning experiments.

## License

This project is provided as-is under the MIT license.
