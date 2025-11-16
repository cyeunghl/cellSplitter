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
- 🔔 **Culture reminders** – Highlight stale cultures and configure reminder thresholds for
  both passage numbers and days since the last handling.
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
- 🗂️ **Label library** – Maintain a reusable collection of clipboard-ready label snippets
  and copy or prune them in bulk.
- 🔀 **Clone cultures** – Spin up a new culture from the latest passage of an active
  line, keeping the media and notes intact while choosing a new name, vessel, and seeded
  cell count from a dialog.
- 🧼 **Mycoplasma status** – Update each culture’s current Myco state (untested, tested,
  free, or contaminated) right from the dashboard or passage history—contaminated
  cultures are highlighted automatically.
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

## Multi-user journal + API blueprint

The repository now includes a production-minded Flask blueprint under
`journal_app/` that upgrades the single-user journal to a multi-user API with
per-user isolation, secure password hashing, email/password-reset flows, and
RESTful CRUD endpoints.

### Highlights

- **User management** – `journal_app/models.py` defines `User` and
  `JournalEntry` models (SQLAlchemy) with password + security-answer hashing,
  reset-token helpers, and a one-to-many relationship.
- **Session handling** – `journal_app/security.py` provides a lightweight
  session-based auth layer that mirrors Flask-Login's API so you can swap in the
  official extension simply by installing `Flask-Login` and updating imports if
  desired. Routes in `journal_app/auth.py` expose sign-up, login, logout, and
  rate-limit aware flows.
- **Password reset** – Email-based token resets use `itsdangerous` plus a
  pluggable mail backend (`Flask-Mail` or the included shim). Optional security
  question fallback endpoints are provided.
- **Journal isolation** – `journal_app/journals.py` exposes CRUD endpoints that
  always scope queries to the authenticated user via the `@owner_required`
  decorator.
- **CSRF & rate limiting guidance** – `journal_app/extensions.py` wires up
  `CSRFProtect` (or a shim) and documents where to drop in `Flask-Limiter` or
  Redis-backed counters for brute-force mitigation.
- **Migrations** – Run `flask --app journal_app:create_app db upgrade` after
  installing `Flask-Migrate`, or use the included `create-db` CLI helper for
  quick SQLite tests.
- **Email delivery** – Configure SMTP/Mailtrap credentials through environment
  variables in `journal_app/config.py`. The included mail shim allows tests to
  run without outbound SMTP; production deployments should install
  `Flask-Mail`.

### Running the API locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # installs Flask-Mail, Flask-WTF, Flask-Migrate
flask --app journal_app:create_app run
```

### Testing

Pytest coverage for the auth + journal flows lives in `tests/test_journal_app.py`.
Run the suite with an in-memory SQLite database via:

```bash
pytest -q
```

The tests monkeypatch SMTP delivery, assert rate-limit counter increments, and
confirm token expiration + security-question fallback behavior.

3. **Open the interface** at <http://127.0.0.1:5000> to create cultures, log passages, and
   plan seeding densities.

## Usage notes

- When creating a culture, you can set the initial passage number (defaults to P1) and
  record starting media, doubling times, plus either a starting concentration or the
  total cells seeded alongside it.
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
  vessel usage, seeded cells, and planning notes without retyping. The passage form now
  lives directly beneath the planner so the workflow stays in one place. Switch to
  *Seed & split* mode when a portion of the harvest needs to be diluted separately
  (e.g. for QC assays). Choosing *Seed everything* works even without a measured harvest;
  the passage is saved with a “seeded everything” note so you can log the workflow
  immediately and backfill numbers later if desired.
- Copy the generated label text after a seeding or dilution calculation to print or share
  culture labels with consistent naming.
- Need a quick mycoplasma check run? Use the dashboard’s Myco test labels table to copy
  culture labels and optionally append today’s date or extra text using the same controls
  as the label library.
- Use the Myco status dropdowns beside each culture (or the passage history header) to
  flag cultures as Myco-free, tested, untested, or contaminated as you progress through
  QC.
- Click **Clone culture** in any journal header to branch a new culture from the latest
  passage—rename it, pick a vessel, and set the seeded cells from a dialog without
  re-entering media or notes.
- Use the bulk processing card on the dashboard to record confluence, harvest measurements,
  planner inputs, and passage saves for several cultures at once.
- Adjust the passage reminder threshold and the “last handled” day cutoff from the
  dashboard header to customize when warnings appear for long-running cultures.
- Use the collapsible label library at the bottom of the dashboard to keep reagent or
  workflow snippets handy—toggle today’s date on with a button, append optional freeform
  text, select specific entries, or copy them all in one click.
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
