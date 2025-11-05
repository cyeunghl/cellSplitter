from __future__ import annotations

import csv
import io
import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import bcrypt

# Use absolute paths for static and template folders to work in Vercel serverless
_app_root = Path(__file__).parent
app = Flask(
    __name__,
    static_folder=str(_app_root / 'static'),
    static_url_path='/static',
    template_folder=str(_app_root / 'templates')
)

# Database configuration: Support Turso (libSQL) or local SQLite
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Turso/libSQL connection string (libsql:// or turso://)
    # For Turso, use the connection string directly
    if database_url.startswith('libsql://') or database_url.startswith('turso://'):
        # Convert Turso URL to SQLAlchemy format if needed
        # Turso uses libSQL which is SQLite-compatible
        # For now, we'll use the URL as-is (may need libsql-client for actual connection)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url.replace('libsql://', 'sqlite:///').replace('turso://', 'sqlite:///')
    else:
        # Standard SQLite URL format
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
elif os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    # Vercel serverless environment: use /tmp
    db_path = '/tmp/cellsplitter.db'
    os.makedirs('/tmp', exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_path}'
else:
    # Local development: use instance directory
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cellsplitter.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cellsplitter-secret-key")

db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


HARVEST_VOLUME_HINTS: list[tuple[str, float]] = [
    ("t225", 15.0),
    ("t175", 10.0),
    ("t150", 12.0),
    ("t125", 9.0),
    ("t75", 7.0),
    ("t25", 3.0),
    ("t12", 2.0),
    ("225", 15.0),
    ("175", 10.0),
    ("150", 10.0),
    ("125", 9.0),
    ("75", 7.0),
    ("25", 3.0),
    ("12.5", 2.0),
    ("100 mm", 7.0),
    ("150 mm", 10.0),
    ("60 mm", 5.0),
    ("35 mm", 2.0),
    ("6-well", 1.5),
    ("12-well", 1.0),
    ("24-well", 0.5),
    ("48-well", 0.25),
    ("96-well", 0.1),
    ("384-well", 0.02),
    ("1536", 0.01),
]

PASSAGE_WARNING_SETTING = "passage_warning_threshold"
DEFAULT_PASSAGE_WARNING = 20

STALE_WARNING_SETTING = "stale_cutoff_days"
DEFAULT_STALE_CUTOFF_DAYS = 4

LABEL_LIBRARY_SETTING = "label_library"
DEFAULT_LABEL_LIBRARY = [
    "+10% FBS + anti-/anti",
    "FBS",
    "0.05% trypsin-EDTA",
    "CTG reagent",
]

MYCO_STATUS_UNTESTED = "myco_untested"
MYCO_STATUS_TESTED = "myco_tested"
MYCO_STATUS_FREE = "myco_free"
MYCO_STATUS_CONTAMINATED = "myco_contaminated"

MYCO_STATUS_CHOICES: list[tuple[str, str]] = [
    (MYCO_STATUS_UNTESTED, "Myco-untested"),
    (MYCO_STATUS_FREE, "Myco-free"),
    (MYCO_STATUS_CONTAMINATED, "Myco-contaminated"),
]

MYCO_STATUS_DISPLAY_FALLBACK = {
    MYCO_STATUS_TESTED: "Myco-free",
}


def normalize_myco_status(value: Optional[str]) -> str:
    if not value:
        return MYCO_STATUS_UNTESTED
    if value == MYCO_STATUS_TESTED:
        return MYCO_STATUS_FREE
    if value in {MYCO_STATUS_UNTESTED, MYCO_STATUS_FREE, MYCO_STATUS_CONTAMINATED}:
        return value
    return MYCO_STATUS_UNTESTED


def suggest_slurry_volume(vessel_name: Optional[str]) -> Optional[float]:
    if not vessel_name:
        return None
    normalized = vessel_name.lower()
    for keyword, volume in HARVEST_VOLUME_HINTS:
        if keyword in normalized:
            return volume
    return None


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
    last_handled_on = db.Column(db.Date, nullable=True)
    measured_cell_concentration = db.Column(db.Float, nullable=True)
    measured_slurry_volume_ml = db.Column(db.Float, nullable=True)
    pre_split_confluence_percent = db.Column(db.Integer, nullable=True)
    measured_viability_percent = db.Column(db.Integer, nullable=True)
    end_reason = db.Column(db.Text, nullable=True)

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

    @property
    def measured_cells_total(self) -> Optional[float]:
        if (
            self.measured_cell_concentration
            and self.measured_slurry_volume_ml
            and self.measured_slurry_volume_ml > 0
        ):
            return self.measured_cell_concentration * self.measured_slurry_volume_ml
        return None

    @property
    def current_myco_status(self) -> str:
        latest = self.latest_passage
        if latest and latest.myco_status:
            return normalize_myco_status(latest.myco_status)
        return MYCO_STATUS_UNTESTED


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
    measured_yield_cells = db.Column(db.Float, nullable=True)
    pre_split_confluence_percent = db.Column(db.Integer, nullable=True)
    measured_viability_percent = db.Column(db.Integer, nullable=True)
    myco_status = db.Column(db.String(32), nullable=True)
    myco_status_locked = db.Column(db.Boolean, nullable=False, default=False)

    culture = db.relationship("Culture", back_populates="passages")
    vessel = db.relationship("Vessel")


class Vessel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    area_cm2 = db.Column(db.Float, nullable=False)
    cells_at_100_confluency = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Setting(db.Model):
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), nullable=True)

    @staticmethod
    def get_value(key: str, default: Optional[str] = None) -> Optional[str]:
        record = Setting.query.get(key)
        if record is None:
            return default
        return record.value

    @staticmethod
    def set_value(key: str, value: Optional[str]) -> None:
        record = Setting.query.get(key)
        if record is None:
            record = Setting(key=key, value=value)
            db.session.add(record)
        else:
            record.value = value
        db.session.commit()


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
    if Setting.get_value(PASSAGE_WARNING_SETTING) is None:
        Setting.set_value(PASSAGE_WARNING_SETTING, str(DEFAULT_PASSAGE_WARNING))
    if Setting.get_value(STALE_WARNING_SETTING) is None:
        Setting.set_value(STALE_WARNING_SETTING, str(DEFAULT_STALE_CUTOFF_DAYS))
    if Setting.get_value(LABEL_LIBRARY_SETTING) is None:
        Setting.set_value(LABEL_LIBRARY_SETTING, json.dumps(DEFAULT_LABEL_LIBRARY))


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
        if not has_column("passage", "measured_yield_cells"):
            connection.execute(
                text("ALTER TABLE passage ADD COLUMN measured_yield_cells FLOAT")
            )
        if not has_column("culture", "measured_cell_concentration"):
            connection.execute(
                text("ALTER TABLE culture ADD COLUMN measured_cell_concentration FLOAT")
            )
        if not has_column("culture", "measured_slurry_volume_ml"):
            connection.execute(
                text("ALTER TABLE culture ADD COLUMN measured_slurry_volume_ml FLOAT")
            )
        if not has_column("culture", "last_handled_on"):
            connection.execute(text("ALTER TABLE culture ADD COLUMN last_handled_on DATE"))
        if not has_column("culture", "pre_split_confluence_percent"):
            connection.execute(
                text("ALTER TABLE culture ADD COLUMN pre_split_confluence_percent INTEGER")
            )
        if not has_column("passage", "pre_split_confluence_percent"):
            connection.execute(
                text("ALTER TABLE passage ADD COLUMN pre_split_confluence_percent INTEGER")
            )
        if not has_column("culture", "measured_viability_percent"):
            connection.execute(
                text("ALTER TABLE culture ADD COLUMN measured_viability_percent INTEGER")
            )
        if not has_column("passage", "measured_viability_percent"):
            connection.execute(
                text("ALTER TABLE passage ADD COLUMN measured_viability_percent INTEGER")
            )
        if not has_column("culture", "end_reason"):
            connection.execute(text("ALTER TABLE culture ADD COLUMN end_reason TEXT"))
        if not has_column("passage", "myco_status"):
            connection.execute(text("ALTER TABLE passage ADD COLUMN myco_status TEXT"))
        if not has_column("passage", "myco_status_locked"):
            connection.execute(
                text("ALTER TABLE passage ADD COLUMN myco_status_locked BOOLEAN DEFAULT 0")
            )
        connection.execute(
            text(
                "UPDATE passage SET myco_status = :free WHERE myco_status = :tested"
            ),
            {"free": MYCO_STATUS_FREE, "tested": MYCO_STATUS_TESTED},
        )
        connection.execute(
            text(
                "UPDATE culture SET last_handled_on = start_date "
                "WHERE last_handled_on IS NULL"
            )
        )


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def parse_numeric(value: str | float | int | None) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        # Prevent booleans (which are ints) from being treated as numeric input.
        return None
    if isinstance(value, (int, float)):
        numeric_value = float(value)
        if math.isnan(numeric_value):
            return None
        return numeric_value
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


def parse_millions(value: str | float | int | None) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_value = parse_numeric(value)
        if numeric_value is None:
            return None
        if numeric_value >= 1_000_000:
            return numeric_value
        return numeric_value * 1_000_000

    cleaned = value.strip()
    if not cleaned:
        return None

    lower_cleaned = cleaned.lower()
    if lower_cleaned.endswith("cells"):
        cleaned = cleaned[: -5].strip()
    elif lower_cleaned.endswith("cell"):
        cleaned = cleaned[: -4].strip()

    numeric = parse_numeric(cleaned)
    if numeric is None:
        return None

    cleaned_upper = cleaned.upper()
    if cleaned_upper.endswith("M"):
        return numeric
    if "E" in cleaned_upper or cleaned_upper.endswith("CELLS"):
        return numeric
    if numeric >= 1_000_000:
        return numeric
    return numeric * 1_000_000


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


def format_volume(volume_ml: Optional[float]) -> Optional[str]:
    if volume_ml is None:
        return None
    if volume_ml < 0:
        return f"-{format_volume(abs(volume_ml))}"
    if volume_ml == 0:
        return "0.00 mL"
    if volume_ml < 0.01:
        return f"{volume_ml * 1000:.2f} uL"
    return f"{volume_ml:.2f} mL"


def format_significant(value: Optional[float], digits: int = 2) -> Optional[str]:
    if value is None:
        return None
    if value == 0:
        return "0"
    absolute = abs(value)
    if absolute == 0:
        return "0"
    order = math.floor(math.log10(absolute))
    scale = digits - 1 - order
    rounded = round(value, scale)
    if scale < 0:
        return f"{rounded:.0f}"
    return f"{rounded:.{scale}f}"


def display_myco_status(value: Optional[str]) -> str:
    lookup = {key: label for key, label in MYCO_STATUS_CHOICES}
    normalized = normalize_myco_status(value)
    if normalized in lookup:
        return lookup[normalized]
    fallback = MYCO_STATUS_DISPLAY_FALLBACK.get(normalized)
    if fallback:
        return fallback
    return lookup[MYCO_STATUS_UNTESTED]


app.jinja_env.filters["format_cells"] = format_cells
app.jinja_env.filters["format_hours"] = format_hours
app.jinja_env.filters["format_volume"] = format_volume
app.jinja_env.filters["display_myco_status"] = display_myco_status


def get_passage_warning_threshold() -> int:
    raw = Setting.get_value(PASSAGE_WARNING_SETTING)
    if raw is None:
        return DEFAULT_PASSAGE_WARNING
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PASSAGE_WARNING
    return max(1, value)


def get_stale_cutoff_days() -> int:
    raw = Setting.get_value(STALE_WARNING_SETTING)
    if raw is None:
        return DEFAULT_STALE_CUTOFF_DAYS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_STALE_CUTOFF_DAYS
    return max(0, value)


def get_label_library() -> list[str]:
    raw = Setting.get_value(LABEL_LIBRARY_SETTING)
    if not raw:
        return DEFAULT_LABEL_LIBRARY.copy()
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return DEFAULT_LABEL_LIBRARY.copy()
    if not isinstance(data, list):
        return DEFAULT_LABEL_LIBRARY.copy()
    labels: list[str] = []
    for entry in data:
        if isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                labels.append(cleaned)
    return labels


def save_label_library(labels: list[str]) -> None:
    Setting.set_value(LABEL_LIBRARY_SETTING, json.dumps(labels))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login route"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Please provide both email and password.", "error")
            return render_template("login.html")
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Signup route"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not email or not password:
            flash("Please provide both email and password.", "error")
            return render_template("signup.html")
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
        
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html")
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "error")
            return render_template("signup.html")
        
        # Create new user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template("signup.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Logout route"""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    """API endpoint for user registration"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "An account with this email already exists"}), 400
    
    # Create new user
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully", "user_id": user.id}), 201


@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard route - protected, requires login"""
    return redirect(url_for('index'))


@app.route("/")
@login_required
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
    vessels = Vessel.query.order_by(Vessel.area_cm2.asc()).all()

    today_value = date.today()
    passage_warning_threshold = get_passage_warning_threshold()
    stale_cutoff_days = get_stale_cutoff_days()
    label_library = get_label_library()

    t75_vessel_id = None
    for vessel in vessels:
        if vessel.name.lower().startswith("t75"):
            t75_vessel_id = vessel.id
            break

    bulk_culture_payload: list[dict] = []
    prefill_active: list[dict] = []
    prefill_ended: list[dict] = []

    def build_prefill_entry(culture: Culture) -> dict:
        latest = culture.latest_passage
        default_cell_concentration = culture.measured_cell_concentration
        if default_cell_concentration is None and latest and latest.cell_concentration:
            default_cell_concentration = latest.cell_concentration
        measured_viability = culture.measured_viability_percent
        if (
            measured_viability is None
            and latest
            and latest.measured_viability_percent is not None
        ):
            measured_viability = latest.measured_viability_percent
        default_vessel_id = None
        if latest and latest.vessel_id:
            default_vessel_id = latest.vessel_id
        latest_seeded_value = None
        latest_seeded_display = None
        if latest and latest.seeded_cells is not None:
            latest_seeded_value = latest.seeded_cells
            latest_seeded_display = format_cells(latest.seeded_cells)
        return {
            "id": culture.id,
            "name": culture.name,
            "cell_line": culture.cell_line.name,
            "status": "active" if culture.ended_on is None else "ended",
            "latest_passage_number": latest.passage_number if latest else None,
            "default_cell_concentration": default_cell_concentration,
            "measured_viability_percent": measured_viability,
            "latest_seeded_cells": latest_seeded_value,
            "latest_seeded_display": latest_seeded_display,
            "default_vessel_id": default_vessel_id,
        }

    for culture in active_cultures:
        latest = culture.latest_passage
        last_activity_date = culture.start_date
        if latest is not None and latest.date > last_activity_date:
            last_activity_date = latest.date
        if culture.last_handled_on and culture.last_handled_on > last_activity_date:
            last_activity_date = culture.last_handled_on
        days_since_last_activity = (today_value - last_activity_date).days

        culture.days_since_last_passage = days_since_last_activity
        culture.is_stale = days_since_last_activity is not None and days_since_last_activity > stale_cutoff_days
        culture.passage_warning_threshold = passage_warning_threshold
        culture.current_myco_status_value = culture.current_myco_status
        culture.current_myco_status_label = display_myco_status(culture.current_myco_status_value)
        culture.myco_status_locked = bool(latest and latest.myco_status_locked)
        default_cell_concentration = culture.measured_cell_concentration
        if default_cell_concentration is None and latest and latest.cell_concentration:
            default_cell_concentration = latest.cell_concentration
        if default_cell_concentration is None:
            default_cell_concentration = 1_000_000

        default_vessel_id = None
        latest_vessel_name = None
        if latest and latest.vessel_id:
            default_vessel_id = latest.vessel_id
            latest_vessel_name = latest.vessel.name if latest.vessel else None
        elif t75_vessel_id is not None:
            default_vessel_id = t75_vessel_id

        latest_seeded_display = None
        latest_seeded_value = None
        if latest and latest.seeded_cells is not None:
            latest_seeded_value = latest.seeded_cells
            latest_seeded_display = format_cells(latest.seeded_cells)

        measured_yield_millions = None
        if latest and latest.measured_yield_cells:
            measured_yield_millions = latest.measured_yield_cells / 1_000_000

        measured_cells_total = None
        if (
            culture.measured_cell_concentration is not None
            and culture.measured_slurry_volume_ml is not None
        ):
            measured_cells_total = (
                culture.measured_cell_concentration * culture.measured_slurry_volume_ml
            )

        default_slurry_volume_ml = culture.measured_slurry_volume_ml
        if default_slurry_volume_ml is None:
            default_slurry_volume_ml = suggest_slurry_volume(latest_vessel_name)

        last_total_area = None
        if latest and latest.vessel and latest.vessel.area_cm2:
            vessels_used = latest.vessels_used or 1
            last_total_area = latest.vessel.area_cm2 * vessels_used

        culture_payload = {
            "id": culture.id,
            "name": culture.name,
            "cell_line": culture.cell_line.name,
            "latest_passage_number": latest.passage_number if latest else None,
            "latest_passage_date": latest.date.isoformat() if latest else None,
            "latest_media": latest.media if latest else "",
            "latest_seeded_cells": latest_seeded_value,
            "latest_seeded_display": latest_seeded_display,
            "latest_vessels_used": latest.vessels_used if latest else None,
            "next_passage_number": culture.next_passage_number,
            "default_cell_concentration": default_cell_concentration,
            "default_vessel_id": default_vessel_id,
            "default_doubling_time": (
                latest.doubling_time_hours
                if latest and latest.doubling_time_hours
                else culture.cell_line.average_doubling_time
            ),
            "measured_cell_concentration": culture.measured_cell_concentration,
            "measured_slurry_volume_ml": culture.measured_slurry_volume_ml,
            "measured_viability_percent": culture.measured_viability_percent,
            "measured_yield_millions": measured_yield_millions,
            "measured_cells_total": measured_cells_total,
            "latest_vessel_name": latest_vessel_name,
            "default_slurry_volume_ml": default_slurry_volume_ml,
            "pre_split_confluence_percent": culture.pre_split_confluence_percent,
            "days_since_last_passage": days_since_last_activity,
            "myco_status": culture.current_myco_status_value,
            "myco_status_locked": culture.myco_status_locked,
            "last_total_area_cm2": last_total_area,
        }
        bulk_culture_payload.append(culture_payload)
        prefill_active.append(build_prefill_entry(culture))

    bulk_culture_map = {entry["id"]: entry for entry in bulk_culture_payload}

    vessel_payload = [
        {
            "id": vessel.id,
            "name": vessel.name,
            "area_cm2": vessel.area_cm2,
            "cells_at_100_confluency": vessel.cells_at_100_confluency,
        }
        for vessel in vessels
    ]

    for culture in ended_cultures:
        culture.current_myco_status_value = culture.current_myco_status
        culture.current_myco_status_label = display_myco_status(culture.current_myco_status_value)
        prefill_ended.append(build_prefill_entry(culture))

    prefill_groups: list[dict] = []
    if prefill_active:
        prefill_groups.append({"label": "Active cultures", "entries": prefill_active})
    if prefill_ended:
        prefill_groups.append({"label": "Ended cultures", "entries": prefill_ended})

    prefill_payload = prefill_active + prefill_ended

    return render_template(
        "index.html",
        active_cultures=active_cultures,
        ended_cultures=ended_cultures,
        cell_lines=cell_lines,
        vessels=vessels,
        bulk_cultures=bulk_culture_map,
        bulk_cultures_json=json.dumps(bulk_culture_payload),
        vessel_payload_json=json.dumps(vessel_payload),
        default_vessel_id=t75_vessel_id,
        today=today_value,
        passage_warning_threshold=passage_warning_threshold,
        stale_cutoff_days=stale_cutoff_days,
        label_library=label_library,
        myco_status_choices=MYCO_STATUS_CHOICES,
        culture_prefill_groups=prefill_groups,
        culture_prefill_json=json.dumps(prefill_payload),
    )


@app.route("/settings/passage-threshold", methods=["POST"])
def update_passage_threshold():
    raw_value = request.form.get("passage_warning_threshold")
    if raw_value in (None, ""):
        flash("Enter a passage number for the reminder threshold.", "error")
        return redirect(url_for("index"))
    try:
        numeric = int(raw_value)
    except (TypeError, ValueError):
        flash("Enter a whole-number passage threshold (e.g. 20).", "error")
        return redirect(url_for("index"))
    if numeric < 1:
        flash("Threshold must be at least 1.", "error")
        return redirect(url_for("index"))
    Setting.set_value(PASSAGE_WARNING_SETTING, str(numeric))
    flash(f"Passage reminder threshold updated to P{numeric}.", "success")
    return redirect(url_for("index"))


@app.route("/settings/stale-cutoff", methods=["POST"])
def update_stale_cutoff():
    raw_value = request.form.get("stale_cutoff_days")
    if raw_value in (None, ""):
        flash("Enter the number of days before a culture is considered stale.", "error")
        return redirect(url_for("index"))
    try:
        numeric = int(raw_value)
    except (TypeError, ValueError):
        flash("Enter a whole number of days (e.g. 4).", "error")
        return redirect(url_for("index"))
    if numeric < 0:
        flash("Days cannot be negative.", "error")
        return redirect(url_for("index"))
    Setting.set_value(STALE_WARNING_SETTING, str(numeric))
    if numeric == 1:
        message = "Stale reminder updates after 1 day of inactivity."
    else:
        message = f"Stale reminder updates after {numeric} days of inactivity."
    flash(message, "success")
    return redirect(url_for("index"))


@app.route("/labels", methods=["POST"])
def add_label():
    label_text = (request.form.get("label_text") or "").strip()
    if not label_text:
        flash("Enter label text before saving.", "error")
        return redirect(url_for("index"))
    if not label_text.isascii():
        flash("Use ASCII characters for label text.", "error")
        return redirect(url_for("index"))
    labels = get_label_library()
    labels.append(label_text)
    save_label_library(labels)
    flash("Label added to the library.", "success")
    return redirect(url_for("index"))


@app.route("/labels/<int:label_index>/delete", methods=["POST"])
def delete_label(label_index: int):
    labels = get_label_library()
    if label_index < 0 or label_index >= len(labels):
        flash("Selected label could not be found.", "error")
        return redirect(url_for("index"))
    removed = labels.pop(label_index)
    save_label_library(labels)
    if removed:
        flash(f"Removed label '{removed}'.", "info")
    else:
        flash("Label removed.", "info")
    return redirect(url_for("index"))


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

    initial_vessel_id_raw = request.form.get("initial_vessel_id")
    initial_vessel: Optional[Vessel] = None
    if initial_vessel_id_raw not in (None, ""):
        try:
            initial_vessel_id = int(initial_vessel_id_raw)
        except (TypeError, ValueError):
            flash("Select a valid vessel for the initial passage.", "error")
            return redirect(url_for("index"))
        initial_vessel = Vessel.query.get(initial_vessel_id)
        if initial_vessel is None:
            flash("Selected vessel could not be found.", "error")
            return redirect(url_for("index"))

    passage_number_raw = request.form.get("initial_passage_number")
    initial_passage_number = 1
    if passage_number_raw is not None and passage_number_raw != "":
        try:
            candidate = int(passage_number_raw)
        except (TypeError, ValueError):
            candidate = None
        if candidate is not None and candidate >= 1:
            initial_passage_number = candidate

    culture = Culture(
        name=name,
        cell_line=cell_line,
        start_date=start_date,
        last_handled_on=start_date,
        notes=culture_notes,
    )
    db.session.add(culture)
    db.session.flush()

    initial_media = request.form.get("initial_media")
    initial_cell_concentration = parse_numeric(request.form.get("initial_cell_concentration"))
    initial_seeded_cells = parse_numeric(request.form.get("initial_seeded_cells"))
    initial_doubling_time = parse_numeric(request.form.get("initial_doubling_time"))
    initial_notes = request.form.get("initial_notes")

    initial_viability_raw = request.form.get("initial_viability_percent")
    initial_viability: Optional[int] = None
    if initial_viability_raw not in (None, ""):
        viability_clean = initial_viability_raw.strip()
        if viability_clean:
            viability_numeric = parse_numeric(viability_clean)
            if viability_numeric is None:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("index"))
            viability_int = int(round(viability_numeric))
            if viability_int < 0 or viability_int > 100:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("index"))
            initial_viability = viability_int

    passage = Passage(
        culture=culture,
        passage_number=initial_passage_number,
        date=start_date,
        media=initial_media,
        cell_concentration=initial_cell_concentration,
        doubling_time_hours=initial_doubling_time,
        notes=initial_notes,
        seeded_cells=initial_seeded_cells,
        vessel=initial_vessel,
        measured_viability_percent=initial_viability,
        myco_status=MYCO_STATUS_UNTESTED,
        myco_status_locked=False,
    )
    db.session.add(passage)

    if initial_cell_concentration is not None:
        culture.measured_cell_concentration = initial_cell_concentration
    if initial_viability is not None:
        culture.measured_viability_percent = initial_viability

    db.session.commit()

    flash(
        f"Culture '{culture.name}' created with initial passage P{initial_passage_number}.",
        "success",
    )
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>/clone", methods=["POST"])
def clone_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    latest = culture.latest_passage

    if latest is None:
        return jsonify({"error": "Clone requires at least one recorded passage."}), 400

    payload = request.get_json(silent=True)
    if not payload:
        payload = request.form.to_dict(flat=True)

    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Provide a name for the cloned culture."}), 400

    vessel_id_raw = payload.get("vessel_id")
    if vessel_id_raw in (None, ""):
        return jsonify({"error": "Select a vessel for the cloned culture."}), 400
    try:
        vessel_id = int(vessel_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Select a valid vessel for the cloned culture."}), 400

    vessel = Vessel.query.get(vessel_id)
    if vessel is None:
        return jsonify({"error": "The selected vessel could not be found."}), 400

    seeded_raw = payload.get("seeded_cells")
    seeded_cells = parse_numeric(seeded_raw)
    if seeded_cells is None or seeded_cells <= 0:
        return jsonify({"error": "Enter the total cells seeded for the cloned culture."}), 400

    today_value = date.today()

    new_culture = Culture(
        name=name,
        cell_line=culture.cell_line,
        start_date=today_value,
        last_handled_on=today_value,
        notes=culture.notes,
    )
    db.session.add(new_culture)
    db.session.flush()

    new_passage = Passage(
        culture=new_culture,
        passage_number=latest.passage_number,
        date=today_value,
        media=latest.media,
        cell_concentration=latest.cell_concentration,
        doubling_time_hours=latest.doubling_time_hours,
        notes=latest.notes,
        vessel=vessel,
        vessels_used=1,
        seeded_cells=seeded_cells,
        myco_status=MYCO_STATUS_UNTESTED,
        myco_status_locked=False,
    )
    db.session.add(new_passage)
    db.session.commit()

    flash(
        f"Cloned culture '{culture.name}' as '{new_culture.name}'.",
        "success",
    )

    return jsonify(
        {
            "success": True,
            "culture_id": new_culture.id,
            "redirect_url": url_for("view_culture", culture_id=new_culture.id),
        }
    )


@app.route("/culture/<int:culture_id>")
def view_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    vessels = Vessel.query.order_by(Vessel.area_cm2.asc()).all()
    last_passage = culture.latest_passage
    default_cell_concentration = (
        culture.measured_cell_concentration
        or (last_passage.cell_concentration if last_passage and last_passage.cell_concentration else 1e6)
    )
    default_vessel_id = None
    for vessel in vessels:
        if vessel.name.lower().startswith("t75"):
            default_vessel_id = vessel.id
            break

    default_measured_yield_millions = None
    if culture.measured_cells_total:
        default_measured_yield_millions = culture.measured_cells_total / 1_000_000
    elif last_passage and last_passage.measured_yield_cells:
        default_measured_yield_millions = last_passage.measured_yield_cells / 1_000_000

    default_measured_yield_display = None
    if default_measured_yield_millions is not None:
        formatted = format_significant(default_measured_yield_millions, 3)
        if formatted is not None:
            default_measured_yield_display = formatted

    default_viability = culture.measured_viability_percent
    if default_viability is None and last_passage and last_passage.measured_viability_percent is not None:
        default_viability = last_passage.measured_viability_percent

    clone_default_vessel_id = default_vessel_id
    if last_passage and last_passage.vessel_id:
        clone_default_vessel_id = last_passage.vessel_id
    clone_default_seeded = (
        last_passage.seeded_cells
        if last_passage and last_passage.seeded_cells is not None
        else None
    )
    last_total_area = None
    if last_passage and last_passage.vessel and last_passage.vessel.area_cm2:
        vessels_used = last_passage.vessels_used or 1
        last_total_area = last_passage.vessel.area_cm2 * vessels_used
    clone_vessel_payload = [
        {"id": vessel.id, "name": vessel.name, "area_cm2": vessel.area_cm2}
        for vessel in vessels
    ]

    culture.current_myco_status_value = culture.current_myco_status
    culture.current_myco_status_label = display_myco_status(culture.current_myco_status_value)
    culture.myco_status_locked = bool(last_passage and last_passage.myco_status_locked)

    return render_template(
        "culture_detail.html",
        culture=culture,
        vessels=vessels,
        last_passage=last_passage,
        default_cell_concentration=default_cell_concentration,
        default_vessel_id=default_vessel_id,
        default_measured_yield_display=default_measured_yield_display,
        default_measured_yield_millions=default_measured_yield_millions,
        default_pre_split_confluence=culture.pre_split_confluence_percent,
        default_viability_percent=default_viability,
        today=date.today(),
        myco_status_choices=MYCO_STATUS_CHOICES,
        clone_vessel_payload=clone_vessel_payload,
        clone_default_vessel_id=clone_default_vessel_id,
        clone_default_seeded=clone_default_seeded,
        last_total_area=last_total_area,
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
    measured_yield_cells = parse_millions(request.form.get("measured_yield_millions"))
    viability_raw = request.form.get("measured_viability_percent")
    measured_viability: Optional[int] = None
    if viability_raw not in (None, ""):
        viability_clean = viability_raw.strip()
        if viability_clean:
            viability_numeric = parse_numeric(viability_clean)
            if viability_numeric is None:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            viability_int = int(round(viability_numeric))
            if viability_int < 0 or viability_int > 100:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            measured_viability = viability_int
    pre_split_confluence = request.form.get("pre_split_confluence_percent")
    pre_split_value: Optional[int] = None
    if pre_split_confluence not in (None, ""):
        cleaned = pre_split_confluence.strip()
        if cleaned:
            numeric = parse_numeric(cleaned)
            if numeric is None:
                flash("Enter a valid pre-split confluency between 0 and 100%.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            rounded = int(round(numeric))
            if rounded < 0 or rounded > 100:
                flash("Confluency should be between 0 and 100%.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            pre_split_value = rounded

    pre_split_for_new = None
    measured_yield_for_new = None
    viability_for_new = None
    if pre_split_value is not None:
        if last_passage is not None:
            last_passage.pre_split_confluence_percent = pre_split_value
        else:
            pre_split_for_new = pre_split_value
    if measured_yield_cells is not None:
        if last_passage is not None:
            last_passage.measured_yield_cells = measured_yield_cells
        else:
            measured_yield_for_new = measured_yield_cells
    if measured_viability is not None:
        culture.measured_viability_percent = measured_viability
        if last_passage is not None:
            last_passage.measured_viability_percent = measured_viability
        else:
            viability_for_new = measured_viability

    myco_status = request.form.get("myco_status")
    valid_statuses = {choice[0] for choice in MYCO_STATUS_CHOICES}
    if not myco_status or myco_status not in valid_statuses:
        myco_status = MYCO_STATUS_UNTESTED
    else:
        myco_status = normalize_myco_status(myco_status)

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
        measured_yield_cells=measured_yield_for_new,
        pre_split_confluence_percent=pre_split_for_new,
        measured_viability_percent=viability_for_new,
        myco_status=myco_status,
        myco_status_locked=False,
    )
    db.session.add(passage)

    culture.pre_split_confluence_percent = None
    culture.last_handled_on = passage_date
    db.session.commit()

    flash(
        f"Recorded passage P{passage.passage_number} for culture '{culture.name}'.",
        "success",
    )
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>/measurement", methods=["POST"])
def record_measurement(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)

    if request.form.get("clear"):
        culture.measured_cell_concentration = None
        culture.measured_slurry_volume_ml = None
        culture.measured_viability_percent = None
        latest = culture.latest_passage
        if latest is not None:
            latest.measured_yield_cells = None
            latest.measured_viability_percent = None
        db.session.commit()
        flash(f"Cleared measured yield details for '{culture.name}'.", "info")
        return redirect(url_for("view_culture", culture_id=culture.id))

    concentration = parse_numeric(request.form.get("measured_cell_concentration"))
    volume_ml = parse_numeric(request.form.get("measured_slurry_volume_ml"))
    viability_raw = request.form.get("measured_viability_percent")
    viability_value: Optional[int] = None
    if viability_raw not in (None, ""):
        viability_clean = viability_raw.strip()
        if viability_clean:
            viability_numeric = parse_numeric(viability_clean)
            if viability_numeric is None:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            viability_int = int(round(viability_numeric))
            if viability_int < 0 or viability_int > 100:
                flash("Enter viability as a percentage between 0 and 100.", "error")
                return redirect(url_for("view_culture", culture_id=culture.id))
            viability_value = viability_int

    culture.measured_cell_concentration = concentration
    culture.measured_slurry_volume_ml = volume_ml
    culture.measured_viability_percent = viability_value

    latest_passage = culture.latest_passage
    total_cells: Optional[float] = None
    if concentration and volume_ml:
        total_cells = concentration * volume_ml
        if latest_passage is not None:
            latest_passage.measured_yield_cells = total_cells
    if viability_value is not None and latest_passage is not None:
        latest_passage.measured_viability_percent = viability_value

    db.session.commit()

    if total_cells is not None:
        flash(
            f"Saved measured yield for '{culture.name}': "
            f"{format_cells(total_cells)} cells in {format_volume(volume_ml)}.",
            "success",
        )
        if viability_value is not None:
            flash(
                f"Viability recorded at {viability_value}% for '{culture.name}'.",
                "info",
            )
    elif concentration or volume_ml:
        flash(
            f"Saved measured yield details for '{culture.name}'. Add both values to compute total cells.",
            "info",
        )
        if viability_value is not None:
            flash(
                f"Viability recorded at {viability_value}% for '{culture.name}'.",
                "info",
            )
    elif viability_value is not None:
        flash(
            f"Saved viability of {viability_value}% for '{culture.name}'.",
            "info",
        )
    else:
        flash(f"No measurement values provided for '{culture.name}'.", "info")

    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>/confluence", methods=["POST"])
def record_confluence(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    latest_passage = culture.latest_passage

    if request.form.get("clear"):
        culture.pre_split_confluence_percent = None
        if latest_passage is not None:
            latest_passage.pre_split_confluence_percent = None
        db.session.commit()
        flash(f"Cleared confluence entry for '{culture.name}'.", "info")
        return redirect(url_for("view_culture", culture_id=culture.id))

    raw_value = request.form.get("pre_split_confluence_percent")
    if raw_value in (None, ""):
        flash("Enter a confluency percentage before saving.", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    cleaned = raw_value.strip()
    if not cleaned:
        flash("Enter a confluency percentage before saving.", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    numeric = parse_numeric(cleaned)
    if numeric is None:
        flash("Enter a valid confluency percentage (0–100).", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    rounded = int(round(numeric))
    if rounded < 0 or rounded > 100:
        flash("Confluency should be between 0 and 100%.", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    culture.pre_split_confluence_percent = rounded
    if latest_passage is not None:
        latest_passage.pre_split_confluence_percent = rounded
    db.session.commit()

    flash(
        f"Recorded pre-split confluency of {rounded}% for '{culture.name}'.",
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

    mode = payload.get("mode", "confluency")
    cell_concentration_raw = payload.get("cell_concentration")
    culture_id = payload.get("culture_id")
    cell_concentration = parse_numeric(cell_concentration_raw)

    if cell_concentration is None or cell_concentration <= 0:
        return jsonify(
            {"error": "Provide a valid starting cell concentration (e.g. 1e6 cells/mL)."}
        ), 400

    if mode == "dilution":
        input_mode = (payload.get("dilution_input_mode") or "concentration").strip().lower()

        total_volume_ml = parse_numeric(payload.get("total_volume_ml"))
        if total_volume_ml is None or total_volume_ml <= 0:
            return jsonify({"error": "Total volume must be greater than zero."}), 400

        final_concentration = None
        cells_to_seed = None
        volume_per_seed_ml = None

        if input_mode == "cells":
            cells_to_seed = parse_numeric(payload.get("cells_to_seed"))
            volume_per_seed_ml = parse_numeric(payload.get("volume_per_seed_ml"))

            if cells_to_seed is None or cells_to_seed <= 0:
                return jsonify({"error": "Number of cells to seed must be greater than zero."}), 400
            if volume_per_seed_ml is None or volume_per_seed_ml <= 0:
                return jsonify({"error": "Volume for seeding must be greater than zero."}), 400

            final_concentration = cells_to_seed / volume_per_seed_ml
        else:
            final_concentration = parse_numeric(payload.get("final_concentration"))
            if final_concentration is None or final_concentration <= 0:
                return jsonify({"error": "Final concentration must be greater than zero."}), 400
            input_mode = "concentration"

        cells_needed = final_concentration * total_volume_ml
        slurry_volume_ml = cells_needed / cell_concentration

        if slurry_volume_ml > total_volume_ml:
            return (
                jsonify(
                    {
                        "error": "Target concentration is higher than the starting suspension. "
                        "Use a more concentrated source or reduce the final volume.",
                    }
                ),
                400,
            )

        media_volume_ml = total_volume_ml - slurry_volume_ml

        total_volume_formatted = format_volume(total_volume_ml)
        note_suggestion = (
            "Dilution planner: Combine "
            f"{format_volume(slurry_volume_ml)} of culture at {format_cells(cell_concentration)} cells/mL "
            f"with {format_volume(media_volume_ml)} of media to yield {total_volume_formatted} "
            f"at {format_cells(final_concentration)} cells/mL."
        )

        if cells_to_seed is not None and volume_per_seed_ml is not None:
            note_suggestion += (
                " This delivers "
                f"{format_cells(cells_to_seed)} cells in {format_volume(volume_per_seed_ml)} "
                "per portion."
            )

        portions_prepared = None
        if volume_per_seed_ml and volume_per_seed_ml > 0:
            portions_prepared = total_volume_ml / volume_per_seed_ml

        response = {
            "mode": "dilution",
            "dilution_input_mode": input_mode,
            "final_concentration": final_concentration,
            "final_concentration_formatted": format_cells(final_concentration),
            "total_volume_ml": total_volume_ml,
            "total_volume_formatted": total_volume_formatted,
            "cells_needed": cells_needed,
            "cells_needed_formatted": format_cells(cells_needed),
            "slurry_volume_ml": slurry_volume_ml,
            "slurry_volume_formatted": format_volume(slurry_volume_ml),
            "media_volume_ml": media_volume_ml,
            "media_volume_formatted": format_volume(media_volume_ml),
            "cell_concentration": cell_concentration,
            "note_suggestion": note_suggestion,
        }

        if cells_to_seed is not None:
            response["cells_to_seed"] = cells_to_seed
            response["cells_to_seed_formatted"] = format_cells(cells_to_seed)
        if volume_per_seed_ml is not None:
            response["volume_per_seed_ml"] = volume_per_seed_ml
            response["volume_per_seed_formatted"] = format_volume(volume_per_seed_ml)
        if portions_prepared is not None:
            response["portions_prepared"] = portions_prepared

        return jsonify(response)

    vessel_id_raw = payload.get("vessel_id")
    target_confluency = payload.get("target_confluency", 0)
    target_hours = payload.get("target_hours", 0)
    doubling_time_override = parse_numeric(payload.get("doubling_time_override"))
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
    volume_needed_per_vessel_ml = required_cells_per_vessel / cell_concentration
    volume_needed_total_ml = volume_needed_per_vessel_ml * vessel_count

    note_suggestion = (
        "Seeding planner: Seed "
        f"{format_cells(required_cells_per_vessel)} cells per {vessel.name} "
        f"({vessel.area_cm2:g} cm²) × {vessel_count} vessel(s) to reach "
        f"{confluency_fraction * 100:.1f}% confluency in {hours:.1f} hours."
    )

    response = {
        "mode": "confluency",
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
        "volume_needed_formatted": format_volume(volume_needed_per_vessel_ml),
        "volume_needed_total_ml": volume_needed_total_ml,
        "volume_needed_total_formatted": format_volume(volume_needed_total_ml),
        "cell_concentration": cell_concentration,
        "vessels_used": vessel_count,
        "note_suggestion": note_suggestion,
    }
    return jsonify(response)


@app.route("/api/bulk-harvest", methods=["POST"])
def record_bulk_harvest():
    payload = request.get_json(silent=True) or {}
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return jsonify({"error": "Select at least one culture to record."}), 400

    results: list[dict] = []

    for entry in entries:
        culture_id_raw = entry.get("culture_id")
        try:
            culture_id = int(culture_id_raw)
        except (TypeError, ValueError):
            db.session.rollback()
            return jsonify({"error": "Invalid culture identifier supplied."}), 400

        culture = Culture.query.get(culture_id)
        if culture is None:
            db.session.rollback()
            return jsonify({"error": f"Culture {culture_id} could not be found."}), 404
        if not culture.is_active:
            db.session.rollback()
            return jsonify(
                {"error": f"Culture '{culture.name}' has been ended and cannot be updated."}
            ), 400

        measured_concentration = parse_numeric(entry.get("measured_cell_concentration"))
        measured_volume = parse_numeric(entry.get("measured_slurry_volume_ml"))
        viability_raw = entry.get("measured_viability_percent")
        viability_value: Optional[int] = None
        if viability_raw not in (None, ""):
            if isinstance(viability_raw, str):
                viability_candidate = viability_raw.strip()
            else:
                viability_candidate = viability_raw
            if viability_candidate not in (None, ""):
                viability_numeric = parse_numeric(viability_candidate)
                if viability_numeric is None:
                    db.session.rollback()
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Enter viability between 0 and 100% for culture '{culture.name}'."
                                )
                            }
                        ),
                        400,
                    )
                viability_int = int(round(viability_numeric))
                if viability_int < 0 or viability_int > 100:
                    db.session.rollback()
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Enter viability between 0 and 100% for culture '{culture.name}'."
                                )
                            }
                        ),
                        400,
                    )
                viability_value = viability_int
        pre_split_value: Optional[int] = None

        pre_split_raw = entry.get("pre_split_confluence_percent")
        if isinstance(pre_split_raw, str):
            pre_split_candidate = pre_split_raw.strip()
        else:
            pre_split_candidate = pre_split_raw
        if pre_split_candidate not in (None, ""):
            numeric = parse_numeric(pre_split_candidate)
            if numeric is None:
                db.session.rollback()
                return (
                    jsonify(
                        {
                            "error": (
                                f"Enter a valid pre-split confluency for culture '{culture.name}'."
                            )
                        }
                    ),
                    400,
                )
            rounded = int(round(numeric))
            if rounded < 0 or rounded > 100:
                db.session.rollback()
                return (
                    jsonify(
                        {
                            "error": (
                                "Confluency should be between 0 and 100% for "
                                f"culture '{culture.name}'."
                            )
                        }
                    ),
                    400,
                )
            pre_split_value = rounded

        if measured_concentration is None or measured_concentration <= 0:
            db.session.rollback()
            return jsonify(
                {
                    "error": (
                        f"Enter the measured concentration for culture '{culture.name}' "
                        "before continuing."
                    )
                }
            ), 400

        if measured_volume is None or measured_volume <= 0:
            db.session.rollback()
            return jsonify(
                {
                    "error": (
                        f"Enter the slurry volume for culture '{culture.name}' before continuing."
                    )
                }
            ), 400

        culture.measured_cell_concentration = measured_concentration
        culture.measured_slurry_volume_ml = measured_volume
        culture.measured_viability_percent = viability_value
        if pre_split_value is not None:
            culture.pre_split_confluence_percent = pre_split_value
            latest_passage = culture.latest_passage
            if latest_passage is not None:
                latest_passage.pre_split_confluence_percent = pre_split_value
        else:
            latest_passage = culture.latest_passage

        measured_yield_cells = measured_concentration * measured_volume
        if latest_passage is not None:
            latest_passage.measured_yield_cells = measured_yield_cells
            if viability_value is not None:
                latest_passage.measured_viability_percent = viability_value

        results.append(
            {
                "culture_id": culture.id,
                "measured_cell_concentration": measured_concentration,
                "measured_slurry_volume_ml": measured_volume,
                "measured_yield_cells": measured_yield_cells,
                "measured_yield_millions": measured_yield_cells / 1_000_000,
                "measured_yield_display": format_cells(measured_yield_cells),
                "pre_split_confluence_percent": pre_split_value,
                "measured_viability_percent": viability_value,
            }
        )

    db.session.commit()
    return jsonify({"success": True, "records": results})


@app.route("/api/bulk-passages", methods=["POST"])
def create_bulk_passages():
    payload = request.get_json(silent=True) or {}
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return jsonify({"error": "Select at least one culture to process."}), 400

    created_passages: list[dict] = []
    passage_counters: dict[int, int] = {}

    for entry in entries:
        culture_id = entry.get("culture_id")
        try:
            culture_id_int = int(culture_id)
        except (TypeError, ValueError):
            db.session.rollback()
            return jsonify({"error": "Invalid culture identifier supplied."}), 400

        culture = Culture.query.get(culture_id_int)
        if culture is None:
            db.session.rollback()
            return jsonify({"error": f"Culture {culture_id_int} could not be found."}), 404
        if not culture.is_active:
            db.session.rollback()
            return jsonify(
                {"error": f"Culture '{culture.name}' has been ended and cannot be updated."}
            ), 400

        last_passage = culture.latest_passage
        passage_number = passage_counters.get(culture.id)
        if passage_number is None:
            passage_number = culture.next_passage_number
        passage_counters[culture.id] = passage_number + 1

        passage_date = parse_date(entry.get("date"))
        media = entry.get("media") or None
        notes = entry.get("notes") or None
        cell_concentration = parse_numeric(entry.get("cell_concentration"))
        doubling_time = parse_numeric(entry.get("doubling_time_hours"))
        seeded_cells = parse_numeric(entry.get("seeded_cells"))
        measured_yield_cells = parse_millions(entry.get("measured_yield_millions"))
        viability_raw = entry.get("measured_viability_percent")
        measured_viability: Optional[int] = None
        if viability_raw not in (None, ""):
            if isinstance(viability_raw, str):
                viability_raw = viability_raw.strip()
            if viability_raw not in (None, ""):
                viability_numeric = parse_numeric(viability_raw)
                if viability_numeric is None:
                    db.session.rollback()
                    return jsonify({"error": "Enter viability as a percentage between 0 and 100."}), 400
                viability_int = int(round(viability_numeric))
                if viability_int < 0 or viability_int > 100:
                    db.session.rollback()
                    return jsonify({"error": "Enter viability as a percentage between 0 and 100."}), 400
                measured_viability = viability_int
        pre_split_confluence_value = None
        pre_split_raw = entry.get("pre_split_confluence_percent")
        if isinstance(pre_split_raw, str):
            pre_split_raw = pre_split_raw.strip()
        if pre_split_raw not in (None, ""):
            numeric = parse_numeric(pre_split_raw)
            if numeric is None:
                db.session.rollback()
                return jsonify({"error": "Enter a valid confluency percentage."}), 400
            rounded = int(round(numeric))
            if rounded < 0 or rounded > 100:
                db.session.rollback()
                return jsonify({"error": "Confluency should be between 0 and 100%."}), 400
            pre_split_confluence_value = rounded
        elif culture.pre_split_confluence_percent is not None:
            pre_split_confluence_value = culture.pre_split_confluence_percent

        if entry.get("use_previous_media") and last_passage:
            media = last_passage.media

        vessel = None
        vessel_id_raw = entry.get("vessel_id")
        if vessel_id_raw not in (None, ""):
            try:
                vessel_id = int(vessel_id_raw)
            except (TypeError, ValueError):
                db.session.rollback()
                return jsonify({"error": "Invalid vessel selection."}), 400
            vessel = Vessel.query.get(vessel_id)
            if vessel is None:
                db.session.rollback()
                return jsonify({"error": "Selected vessel could not be found."}), 404

        vessels_used = None
        vessels_used_raw = entry.get("vessels_used")
        if vessels_used_raw not in (None, ""):
            try:
                vessels_candidate = int(vessels_used_raw)
            except (TypeError, ValueError):
                db.session.rollback()
                return jsonify({"error": "Number of vessels must be a whole number."}), 400
            if vessels_candidate > 0:
                vessels_used = vessels_candidate

        measured_cell_concentration = parse_numeric(
            entry.get("measured_cell_concentration")
        )
        measured_slurry_volume = parse_numeric(entry.get("measured_slurry_volume_ml"))

        if measured_cell_concentration is not None:
            culture.measured_cell_concentration = measured_cell_concentration
        if measured_slurry_volume is not None:
            culture.measured_slurry_volume_ml = measured_slurry_volume
        if measured_viability is not None:
            culture.measured_viability_percent = measured_viability

        if measured_yield_cells is None:
            if (
                measured_cell_concentration is not None
                and measured_slurry_volume is not None
            ):
                measured_yield_cells = measured_cell_concentration * measured_slurry_volume
            elif (
                culture.measured_cell_concentration is not None
                and culture.measured_slurry_volume_ml is not None
            ):
                measured_yield_cells = (
                    culture.measured_cell_concentration
                    * culture.measured_slurry_volume_ml
                )

        pre_split_for_new = None
        measured_yield_for_new = None
        viability_for_new = None
        if pre_split_confluence_value is not None:
            if last_passage is not None:
                last_passage.pre_split_confluence_percent = pre_split_confluence_value
            else:
                pre_split_for_new = pre_split_confluence_value
        if measured_yield_cells is not None:
            if last_passage is not None:
                last_passage.measured_yield_cells = measured_yield_cells
            else:
                measured_yield_for_new = measured_yield_cells
        if measured_viability is not None:
            if last_passage is not None:
                last_passage.measured_viability_percent = measured_viability
            else:
                viability_for_new = measured_viability

        myco_status_value = entry.get("myco_status")
        valid_statuses = {choice[0] for choice in MYCO_STATUS_CHOICES}
        if myco_status_value not in valid_statuses:
            myco_status_value = MYCO_STATUS_UNTESTED
        else:
            myco_status_value = normalize_myco_status(myco_status_value)

        passage = Passage(
            culture=culture,
            passage_number=passage_number,
            date=passage_date,
            media=media,
            cell_concentration=cell_concentration,
            doubling_time_hours=doubling_time,
            notes=notes,
            vessel=vessel,
            vessels_used=vessels_used,
            seeded_cells=seeded_cells,
            measured_yield_cells=measured_yield_for_new,
            pre_split_confluence_percent=pre_split_for_new,
            measured_viability_percent=viability_for_new,
            myco_status=myco_status_value,
            myco_status_locked=False,
        )
        db.session.add(passage)

        culture.pre_split_confluence_percent = None
        culture.last_handled_on = passage_date

        created_passages.append(
            {
                "culture_id": culture.id,
                "culture_name": culture.name,
                "passage_number": passage_number,
                "date": passage_date.strftime("%Y-%m-%d"),
                "media": media or "",
                "seeded_cells": seeded_cells,
                "seeded_cells_formatted": format_cells(seeded_cells)
                if seeded_cells is not None
                else None,
                "measured_cell_concentration": culture.measured_cell_concentration,
                "measured_slurry_volume_ml": culture.measured_slurry_volume_ml,
                "measured_yield_cells": measured_yield_cells,
                "measured_yield_display": format_cells(measured_yield_cells)
                if measured_yield_cells is not None
                else None,
                "measured_viability_percent": measured_viability,
                "pre_split_confluence_percent": pre_split_confluence_value,
                "myco_status": myco_status_value,
            }
        )

    if not created_passages:
        db.session.rollback()
        return jsonify({"error": "No passages were created."}), 400

    db.session.commit()
    return jsonify({"success": True, "created": len(created_passages), "passages": created_passages})


@app.route("/export/cultures.csv")
def export_cultures():
    status = (request.args.get("status") or "active").strip().lower()
    if status not in {"active", "ended", "both", "all"}:
        return jsonify({"error": "Invalid export status."}), 400

    query = Culture.query
    if status == "active":
        query = query.filter(Culture.ended_on.is_(None))
    elif status == "ended":
        query = query.filter(Culture.ended_on.isnot(None))

    cultures = query.order_by(Culture.name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Culture name",
            "Cell line",
            "Status",
            "Start date",
            "Ended on",
            "Current passage",
            "Current passage date",
            "Media",
            "Cell concentration (cells/mL)",
            "Doubling time (hours)",
            "Vessel usage",
            "Pre-split confluence (%)",
            "Seeded cells",
            "Measured yield (cells)",
            "Measured viability (%)",
            "Myco status",
            "End reason",
        ]
    )
    for culture in cultures:
        latest = culture.latest_passage
        vessel_info = ""
        if latest and latest.vessel:
            count = latest.vessels_used or 1
            vessel_info = f"{count} x {latest.vessel.name}"
            if latest.vessel.area_cm2:
                vessel_info += f" ({latest.vessel.area_cm2:g} cm^2)"

        seeded_cells_value = ""
        if latest and latest.seeded_cells is not None:
            formatted_seeded = format_significant(latest.seeded_cells, 2)
            if formatted_seeded is not None:
                seeded_cells_value = formatted_seeded

        confluence_display = ""
        if latest and latest.pre_split_confluence_percent is not None:
            confluence_display = f"{latest.pre_split_confluence_percent}"

        measured_yield_display = ""
        if latest and latest.measured_yield_cells is not None:
            formatted_yield = format_significant(latest.measured_yield_cells, 2)
            if formatted_yield is not None:
                measured_yield_display = formatted_yield

        viability_display = ""
        if latest and latest.measured_viability_percent is not None:
            viability_display = f"{latest.measured_viability_percent}"

        myco_display = display_myco_status(latest.myco_status) if latest else display_myco_status(None)

        writer.writerow(
            [
                culture.name,
                culture.cell_line.name,
                "Active" if culture.ended_on is None else "Ended",
                culture.start_date.strftime("%Y-%m-%d"),
                culture.ended_on.strftime("%Y-%m-%d") if culture.ended_on else "",
                f"P{latest.passage_number}" if latest else "—",
                latest.date.strftime("%Y-%m-%d") if latest else "—",
                latest.media if latest and latest.media else "",
                f"{latest.cell_concentration:g}" if latest and latest.cell_concentration else "",
                f"{latest.doubling_time_hours:g}" if latest and latest.doubling_time_hours else "",
                vessel_info,
                confluence_display,
                seeded_cells_value,
                measured_yield_display,
                viability_display,
                myco_display,
                culture.end_reason or "",
            ]
        )

    output.seek(0)
    if status in {"both", "all"}:
        status_slug = "all"
    else:
        status_slug = status
    filename = f"{status_slug}_cultures_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/export/active-cultures.csv")
def export_active_cultures_legacy():
    return export_cultures()


@app.route("/culture/<int:culture_id>/end", methods=["POST"])
def end_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    if culture.ended_on is not None:
        flash("Culture is already marked as ended.", "info")
        return redirect(url_for("view_culture", culture_id=culture.id))

    ended_on = parse_date(request.form.get("ended_on"))
    reason_raw = request.form.get("end_reason") or ""
    culture.ended_on = ended_on
    culture.end_reason = reason_raw.strip() or None
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
    culture.end_reason = None
    db.session.commit()

    flash(f"Culture '{culture.name}' reactivated.", "success")
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.route("/culture/<int:culture_id>/refresh_media", methods=["POST"])
def refresh_media(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    if not culture.is_active:
        flash("Reactivate the culture before recording a media refresh.", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    latest = culture.latest_passage
    today_stamp = date.today().strftime("%Y-%m-%d")
    entry = f"media refreshed on {today_stamp}"

    if latest is not None:
        existing_notes = latest.notes.strip() if latest.notes else ""
        if existing_notes:
            latest.notes = f"{existing_notes}\n{entry}"
        else:
            latest.notes = entry
    else:
        existing_notes = culture.notes.strip() if culture.notes else ""
        if existing_notes:
            culture.notes = f"{existing_notes}\n{entry}"
        else:
            culture.notes = entry

    culture.last_handled_on = date.today()
    db.session.commit()
    flash("Media refreshed.", "success")
    return redirect(url_for("index"))


@app.route("/culture/<int:culture_id>/myco", methods=["POST"])
def update_myco_status(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)
    status = request.form.get("myco_status") or ""
    valid_statuses = {choice[0] for choice in MYCO_STATUS_CHOICES}

    if status not in valid_statuses:
        db.session.rollback()
        flash("Select a valid Myco status before saving.", "error")
    else:
        latest = culture.latest_passage
        if latest is None:
            db.session.rollback()
            flash("Create at least one passage before setting Myco status.", "error")
        elif latest.myco_status_locked:
            db.session.rollback()
            flash("Myco status is locked until the next passage is logged.", "error")
        else:
            latest.myco_status = status
            latest.myco_status_locked = True
            db.session.commit()
            flash(
                f"Updated Myco status for '{culture.name}' to {display_myco_status(status)}.",
                "success",
            )

    redirect_target = request.form.get("redirect")
    if redirect_target:
        return redirect(redirect_target)
    return redirect(url_for("index"))


@app.route("/culture/<int:culture_id>/delete", methods=["POST"])
def delete_culture(culture_id: int):
    culture = Culture.query.get_or_404(culture_id)

    if culture.ended_on is None:
        flash("End the culture before deleting it permanently.", "error")
        return redirect(url_for("view_culture", culture_id=culture.id))

    name = culture.name
    db.session.delete(culture)
    db.session.commit()

    flash(f"Culture '{name}' permanently deleted.", "success")
    return redirect(url_for("index"))


@app.route("/passage/<int:passage_id>/edit", methods=["GET", "POST"])
def edit_passage(passage_id: int):
    passage = Passage.query.get_or_404(passage_id)
    culture = passage.culture
    if request.method == "POST":
        passage.date = parse_date(request.form.get("date"))
        passage.media = request.form.get("media")
        passage.cell_concentration = parse_numeric(
            request.form.get("cell_concentration")
        )
        passage.doubling_time_hours = parse_numeric(
            request.form.get("doubling_time_hours")
        )
        passage.notes = request.form.get("notes")

        vessel_id = None
        vessel_id_raw = request.form.get("vessel_id")
        if vessel_id_raw:
            try:
                vessel_id = int(vessel_id_raw)
            except (TypeError, ValueError):
                vessel_id = None
        passage.vessel = Vessel.query.get(vessel_id) if vessel_id else None

        vessels_used_raw = request.form.get("vessels_used")
        vessels_used = None
        if vessels_used_raw:
            try:
                candidate = int(vessels_used_raw)
            except (TypeError, ValueError):
                candidate = None
            if candidate and candidate > 0:
                vessels_used = candidate
        passage.vessels_used = vessels_used

        passage.seeded_cells = parse_numeric(request.form.get("seeded_cells"))
        passage.measured_yield_cells = parse_millions(
            request.form.get("measured_yield_millions")
        )
        pre_split_raw = request.form.get("pre_split_confluence_percent")
        if pre_split_raw in (None, ""):
            passage.pre_split_confluence_percent = None
        else:
            cleaned = pre_split_raw.strip()
            if not cleaned:
                passage.pre_split_confluence_percent = None
            else:
                numeric = parse_numeric(cleaned)
                if numeric is not None:
                    rounded = int(round(numeric))
                    if 0 <= rounded <= 100:
                        passage.pre_split_confluence_percent = rounded
                    else:
                        flash("Confluency should be between 0 and 100%.", "error")
                        return redirect(url_for("edit_passage", passage_id=passage.id))
                else:
                    flash("Enter a valid confluency percentage (0–100).", "error")
                    return redirect(url_for("edit_passage", passage_id=passage.id))

        myco_status = request.form.get("myco_status") or ""
        valid_statuses = {choice[0] for choice in MYCO_STATUS_CHOICES}
        if myco_status in valid_statuses:
            passage.myco_status = myco_status

        db.session.commit()
        flash(
            f"Updated passage P{passage.passage_number} for culture '{culture.name}'.",
            "success",
        )
        return redirect(url_for("view_culture", culture_id=culture.id))

    vessels = Vessel.query.order_by(Vessel.area_cm2.asc()).all()
    return render_template(
        "edit_passage.html",
        passage=passage,
        culture=culture,
        vessels=vessels,
        today=date.today(),
        myco_status_choices=MYCO_STATUS_CHOICES,
    )


@app.route("/passage/<int:passage_id>/delete", methods=["POST"])
def delete_passage(passage_id: int):
    passage = Passage.query.get_or_404(passage_id)
    culture = passage.culture
    db.session.delete(passage)
    db.session.commit()
    flash(
        f"Deleted passage P{passage.passage_number} from culture '{culture.name}'.",
        "success",
    )
    return redirect(url_for("view_culture", culture_id=culture.id))


@app.context_processor
def inject_helpers():
    return {"format_cells": format_cells, "format_hours": format_hours}


with app.app_context():
    setup_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
