from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cellsplitter.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "cellsplitter-secret-key"

db = SQLAlchemy(app)


class CellLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    doubling_time_min_hours = db.Column(db.Float, nullable=True)
    doubling_time_max_hours = db.Column(db.Float, nullable=True)
    reference_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    cultures = db.relationship("Culture", back_populates="cell_line")

    @property
    def average_doubling_time(self) -> Optional[float]:
        values = [
            value
            for value in (self.doubling_time_min_hours, self.doubling_time_max_hours)
            if value
        ]
        if not values:
            return None
        return sum(values) / len(values)

    def display_doubling_time(self) -> str:
        low = self.doubling_time_min_hours
        high = self.doubling_time_max_hours
        if low and high and low != high:
            return f"{low:g}–{high:g} h"
        if low:
            return f"{low:g} h"
        if high:
            return f"{high:g} h"
        return "Not specified"


class Culture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    cell_line_id = db.Column(db.Integer, db.ForeignKey("cell_line.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text, nullable=True)
    ended_on = db.Column(db.Date, nullable=True)

    cell_line = db.relationship("CellLine", back_populates="cultures")
    passages = db.relationship(
        "Passage",
        back_populates="culture",
        order_by="Passage.passage_number",
        cascade="all, delete-orphan",
    )

    @property
    def latest_passage(self) -> Optional["Passage"]:
        if not self.passages:
            return None
        return max(self.passages, key=lambda passage: passage.passage_number)

    @property
    def next_passage_number(self) -> int:
        latest = self.latest_passage
        if latest is None:
            return 1
        return latest.passage_number + 1

    @property
    def is_active(self) -> bool:
        return self.ended_on is None


class Passage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    culture_id = db.Column(db.Integer, db.ForeignKey("culture.id"), nullable=False)
    passage_number = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    media = db.Column(db.Text, nullable=True)
    cell_concentration = db.Column(db.Float, nullable=True)
    doubling_time_hours = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    vessel_id = db.Column(db.Integer, db.ForeignKey("vessel.id"), nullable=True)
    vessels_used = db.Column(db.Integer, nullable=True)
    seeded_cells = db.Column(db.Float, nullable=True)

    culture = db.relationship("Culture", back_populates="passages")
    vessel = db.relationship("Vessel")


class Vessel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    area_cm2 = db.Column(db.Float, nullable=False)
    cells_at_100_confluency = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)


def load_json_data(filename: str) -> list[dict]:
    data_path = Path(__file__).parent / "data" / filename
    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def bootstrap_cell_lines() -> None:
    records = load_json_data("cell_lines.json")
    existing_names = {name for (name,) in db.session.query(CellLine.name).all()}
    for record in records:
        if record["name"] in existing_names:
            continue
        cell_line = CellLine(
            name=record["name"],
            doubling_time_min_hours=record.get("doubling_time_min_hours"),
            doubling_time_max_hours=record.get("doubling_time_max_hours"),
            reference_url=record.get("reference_url"),
            notes=record.get("notes"),
        )
        db.session.add(cell_line)
    db.session.commit()


def bootstrap_vessels() -> None:
    records = load_json_data("vessels.json")
    existing_names = {name for (name,) in db.session.query(Vessel.name).all()}
    for record in records:
        if record["name"] in existing_names:
            continue
        vessel = Vessel(
            name=record["name"],
            area_cm2=record["area_cm2"],
            cells_at_100_confluency=record["cells_at_100_confluency"],
            notes=record.get("notes"),
        )
        db.session.add(vessel)
    db.session.commit()


def setup_database() -> None:
    db.create_all()
    bootstrap_cell_lines()
    bootstrap_vessels()
    ensure_columns()


def ensure_columns() -> None:
    inspector = inspect(db.engine)

    def has_column(table: str, column: str) -> bool:
        return column in {col["name"] for col in inspector.get_columns(table)}

    with db.engine.begin() as connection:
        if not has_column("culture", "ended_on"):
            connection.execute(text("ALTER TABLE culture ADD COLUMN ended_on DATE"))
        if not has_column("passage", "vessel_id"):
            connection.execute(text("ALTER TABLE passage ADD COLUMN vessel_id INTEGER"))
        if not has_column("passage", "vessels_used"):
            connection.execute(text("ALTER TABLE passage ADD COLUMN vessels_used INTEGER"))
        if not has_column("passage", "seeded_cells"):
            connection.execute(text("ALTER TABLE passage ADD COLUMN seeded_cells FLOAT"))


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def parse_numeric(value: str | None) -> Optional[float]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = cleaned.upper()
    try:
        if cleaned.endswith("K"):
            return float(cleaned[:-1]) * 1_000
        if cleaned.endswith("M"):
            return float(cleaned[:-1]) * 1_000_000
        if cleaned.endswith("B"):
            return float(cleaned[:-1]) * 1_000_000_000
        return float(cleaned)
    except ValueError:
        # allow forms like 300E3
        try:
            return float(cleaned.replace("E", "e"))
        except ValueError:
            return None


def format_cells(value: Optional[float]) -> str:
    if value is None:
        return "—"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f} M"
    if absolute >= 1_000:
        return f"{value / 1_000:.2f} K"
    return f"{value:.0f}"


def format_hours(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:g} h"


app.jinja_env.filters["format_cells"] = format_cells
app.jinja_env.filters["format_hours"] = format_hours


@app.route("/")
def index():
    active_cultures = (
        Culture.query.filter(Culture.ended_on.is_(None))
        .order_by(Culture.name.asc())
        .all()
    )
    ended_cultures = (
        Culture.query.filter(Culture.ended_on.isnot(None))
        .order_by(Culture.name.asc())
        .all()
    )
    cell_lines = CellLine.query.order_by(CellLine.name.asc()).all()
    return render_template(
        "index.html",
        active_cultures=active_cultures,
        ended_cultures=ended_cultures,
        cell_lines=cell_lines,
        today=date.today(),
    )


@app.route("/culture", methods=["POST"])
def create_culture():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Culture name is required.", "error")
        return redirect(url_for("index"))

    cell_line_id_raw = request.form.get("cell_line_id")
    if not cell_line_id_raw:
        flash("Please choose a cell line for the culture.", "error")
        return redirect(url_for("index"))

    try:
        cell_line_id = int(cell_line_id_raw)
    except (TypeError, ValueError):
        flash("Invalid cell line selection.", "error")
        return redirect(url_for("index"))

    cell_line = CellLine.query.get(cell_line_id)
    if cell_line is None:
        flash("Selected cell line could not be found.", "error")
        return redirect(url_for("index"))

    start_date = parse_date(request.form.get("start_date"))
    culture_notes = request.form.get("culture_notes")

    culture = Culture(
        name=name,
        cell_line=cell_line,
        start_date=start_date,
        notes=culture_notes,
    )
    db.session.add(culture)
    db.session.flush()

    initial_media = request.form.get("initial_media")
    initial_cell_concentration = parse_numeric(request.form.get("initial_cell_concentration"))
    initial_doubling_time = parse_numeric(request.form.get("initial_doubling_time"))
    initial_notes = request.form.get("initial_notes")

    passage = Passage(
        culture=culture,
        passage_number=1,
        date=start_date,
        media=initial_media,
        cell_concentration=initial_cell_concentration,
        doubling_time_hours=initial_doubling_time,
        notes=initial_notes,
    )
    db.session.add(passage)
    db.session.commit()

    flash(f"Culture '{culture.name}' created with initial passage P1.", "success")
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>")
def view_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    vessels = Vessel.query.order_by(Vessel.area_cm2.asc()).all()
    last_passage = culture.latest_passage
    return render_template(
        "culture_detail.html",
        culture=culture,
        vessels=vessels,
        last_passage=last_passage,
        today=date.today(),
    )


@app.route("/culture/<int:culture_id>/add_passage", methods=["POST"])
def add_passage(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)

    if culture.ended_on is not None:
        flash(
            "This culture has been ended. Reactivate it before logging new passages.",
            "error",
        )
        return redirect(url_for("view_culture", culture_id=culture.id))

    passage_date = parse_date(request.form.get("date"))
    media = request.form.get("media")
    cell_concentration = parse_numeric(request.form.get("cell_concentration"))
    doubling_time = parse_numeric(request.form.get("doubling_time_hours"))
    notes = request.form.get("notes")
    last_passage = culture.latest_passage

    if request.form.get("use_previous_media") and last_passage:
        media = last_passage.media

    vessel_id = None
    vessel = None
    vessel_id_raw = request.form.get("vessel_id")
    if vessel_id_raw:
        try:
            vessel_id = int(vessel_id_raw)
        except (TypeError, ValueError):
            vessel_id = None
    if vessel_id:
        vessel = Vessel.query.get(vessel_id)

    vessels_used_raw = request.form.get("vessels_used")
    vessels_used = None
    if vessels_used_raw:
        try:
            vessels_used_candidate = int(vessels_used_raw)
        except (TypeError, ValueError):
            vessels_used_candidate = None
        if vessels_used_candidate and vessels_used_candidate > 0:
            vessels_used = vessels_used_candidate

    seeded_cells = parse_numeric(request.form.get("seeded_cells"))

    passage = Passage(
        culture=culture,
        passage_number=culture.next_passage_number,
        date=passage_date,
        media=media,
        cell_concentration=cell_concentration,
        doubling_time_hours=doubling_time,
        notes=notes,
        vessel=vessel,
        vessels_used=vessels_used,
        seeded_cells=seeded_cells,
    )
    db.session.add(passage)
    db.session.commit()

    flash(
        f"Recorded passage P{passage.passage_number} for culture '{culture.name}'.",
        "success",
    )
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/cell_line", methods=["POST"])
def create_cell_line():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Cell line name is required.", "error")
        return redirect(url_for("index"))

    existing = CellLine.query.filter_by(name=name).first()
    if existing:
        flash("A cell line with that name already exists.", "error")
        return redirect(url_for("index"))

    doubling_time_min = parse_numeric(request.form.get("doubling_time_min_hours"))
    doubling_time_max = parse_numeric(request.form.get("doubling_time_max_hours"))
    reference_url = request.form.get("reference_url")
    notes = request.form.get("notes")

    cell_line = CellLine(
        name=name,
        doubling_time_min_hours=doubling_time_min,
        doubling_time_max_hours=doubling_time_max,
        reference_url=reference_url,
        notes=notes,
    )
    db.session.add(cell_line)
    db.session.commit()

    flash(f"Added cell line '{cell_line.name}'.", "success")
    return redirect(url_for("index"))


@app.route("/api/doubling-times")
def doubling_times():
    cell_lines = CellLine.query.order_by(CellLine.name.asc()).all()
    payload = [
        {
            "id": cell_line.id,
            "name": cell_line.name,
            "doubling_time_min_hours": cell_line.doubling_time_min_hours,
            "doubling_time_max_hours": cell_line.doubling_time_max_hours,
            "reference_url": cell_line.reference_url,
            "notes": cell_line.notes,
        }
        for cell_line in cell_lines
    ]
    return jsonify(payload)


@app.route("/api/calc-seeding", methods=["POST"])
def calculate_seeding():
    payload = request.get_json(force=True)

    vessel_id_raw = payload.get("vessel_id")
    target_confluency = payload.get("target_confluency", 0)
    target_hours = payload.get("target_hours", 0)
    cell_concentration_raw = payload.get("cell_concentration")
    doubling_time_override = parse_numeric(payload.get("doubling_time_override"))
    culture_id = payload.get("culture_id")
    vessel_count_raw = payload.get("vessels_used", 1)

    try:
        vessel_id = int(vessel_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid vessel selection."}), 400

    vessel = Vessel.query.get(vessel_id)
    if vessel is None:
        return jsonify({"error": "Vessel not found."}), 404

    try:
        confluency_fraction = max(0.0, min(float(target_confluency), 100.0)) / 100.0
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid confluency percentage."}), 400

    if confluency_fraction <= 0:
        return jsonify({"error": "Target confluency must be greater than zero."}), 400

    try:
        hours = float(target_hours)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid time horizon."}), 400

    if hours <= 0:
        return jsonify({"error": "Time horizon must be greater than zero."}), 400

    try:
        vessel_count = int(vessel_count_raw)
    except (TypeError, ValueError):
        vessel_count = 1
    if vessel_count <= 0:
        vessel_count = 1

    cell_concentration = parse_numeric(cell_concentration_raw)

    cell_line = None
    if culture_id:
        try:
            culture_lookup_id = int(culture_id)
        except (TypeError, ValueError):
            culture_lookup_id = None
        if culture_lookup_id:
            culture = Culture.query.get(culture_lookup_id)
            if culture:
                cell_line = culture.cell_line

    doubling_time = doubling_time_override
    if doubling_time is None and cell_line is not None:
        doubling_time = cell_line.average_doubling_time

    if doubling_time is None or doubling_time <= 0:
        return jsonify({"error": "A valid doubling time is required."}), 400

    final_cells_per_vessel = vessel.cells_at_100_confluency * confluency_fraction
    final_cells_total = final_cells_per_vessel * vessel_count
    growth_cycles = hours / doubling_time
    growth_factor = math.pow(2, growth_cycles)
    if growth_factor <= 0:
        return jsonify({"error": "Could not compute growth factor."}), 400

    required_cells_per_vessel = final_cells_per_vessel / growth_factor
    required_cells_total = required_cells_per_vessel * vessel_count
    volume_needed_per_vessel_ml = (
        required_cells_per_vessel / cell_concentration if cell_concentration else None
    )
    volume_needed_total_ml = (
        volume_needed_per_vessel_ml * vessel_count if volume_needed_per_vessel_ml else None
    )

    note_suggestion = (
        "Seeding planner: Seed "
        f"{format_cells(required_cells_per_vessel)} cells per {vessel.name} "
        f"({vessel.area_cm2:g} cm²) × {vessel_count} vessel(s) to reach "
        f"{confluency_fraction * 100:.1f}% confluency in {hours:.1f} hours."
    )

    response = {
        "vessel": vessel.name,
        "vessel_id": vessel.id,
        "vessel_area_cm2": vessel.area_cm2,
        "target_confluency": confluency_fraction * 100,
        "hours": hours,
        "doubling_time_used": doubling_time,
        "growth_cycles": growth_cycles,
        "final_cells": final_cells_per_vessel,
        "final_cells_formatted": format_cells(final_cells_per_vessel),
        "final_cells_total": final_cells_total,
        "final_cells_total_formatted": format_cells(final_cells_total),
        "required_cells": required_cells_per_vessel,
        "required_cells_formatted": format_cells(required_cells_per_vessel),
        "required_cells_total": required_cells_total,
        "required_cells_total_formatted": format_cells(required_cells_total),
        "volume_needed_ml": volume_needed_per_vessel_ml,
        "volume_needed_formatted": f"{volume_needed_per_vessel_ml:.2f} mL"
        if volume_needed_per_vessel_ml
        else None,
        "volume_needed_total_ml": volume_needed_total_ml,
        "volume_needed_total_formatted": f"{volume_needed_total_ml:.2f} mL"
        if volume_needed_total_ml
        else None,
        "cell_concentration": cell_concentration,
        "vessels_used": vessel_count,
        "note_suggestion": note_suggestion,
    }
    return jsonify(response)


@app.route("/culture/<int:culture_id>/end", methods=["POST"])
def end_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    if culture.ended_on is not None:
        flash("Culture is already marked as ended.", "info")
        return redirect(url_for("view_culture", culture_id=culture.id))

    ended_on = parse_date(request.form.get("ended_on"))
    culture.ended_on = ended_on
    db.session.commit()

    flash(f"Culture '{culture.name}' marked as ended.", "success")
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>/reactivate", methods=["POST"])
def reactivate_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    if culture.ended_on is None:
        flash("Culture is already active.", "info")
        return redirect(url_for("view_culture", culture_id=culture.id))

    culture.ended_on = None
    db.session.commit()

    flash(f"Culture '{culture.name}' reactivated.", "success")
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.context_processor
def inject_helpers():
    return {"format_cells": format_cells, "format_hours": format_hours}


with app.app_context():
    setup_database()


if __name__ == "__main__":
    app.run(debug=True)
