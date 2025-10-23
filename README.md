# cellSplitter

A lightweight Flask web app for tracking tissue culture passages, media history, and
seeding plans. Create a culture journal, log each passage, and calculate how many cells to
seed toward a desired confluency using built-in doubling times and vessel capacity data.

## Features

- 📓 **Culture journal** – Record each passage with media, cell concentrations, doubling
  times, and notes.
- 🔁 **Auto-numbered passages** – Passage numbers increment automatically (P1, P2, …).
- 🧪 **Media shortcuts** – Copy media recipes from the previous passage with a click.
- 📈 **Seeding planner** – Calculate required cell numbers and seeding volumes based on
  target confluency, time to split, vessel size, and doubling time.
- 🧬 **Doubling-time library** – Preloaded database of common cell lines with editable
  doubling-time ranges and references.
- 🧮 **Tissue culture vessel data** – Uses surface areas and cell capacities curated from
  ThermoFisher’s “Cell Culture Useful Numbers” reference to estimate final cell yields.

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
  lets you override it for passage-specific behavior.
- Cell concentration inputs accept plain numbers as well as shorthand such as `300K`,
  `1.5e6`, or `2.3M` cells/mL.
- To keep a copy of the database, back up `cellsplitter.db` or point `SQLALCHEMY_DATABASE_URI`
  to your preferred database engine.

## Data sources

Default cell lines and vessel capacities are seeded from the JSON files in `data/`. The
values mirror publicly available vendor catalogs (ATCC, ThermoFisher) for convenience—verify
against your lab’s validated growth rates when planning experiments.

## License

This project is provided as-is under the MIT license.
