"""Application factory for the multi-user journal app."""
from __future__ import annotations

from flask import Flask

from .config import BaseConfig
from .extensions import csrf, db, login_manager, mail, migrate
from .auth import auth_bp
from .journals import journal_bp
from .failed_login import FailedLoginTracker


def create_app(config_object: type[BaseConfig] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or BaseConfig)

    # Initialize extensions.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Simple in-memory tracker to hint at rate-limiting. In production, replace
    # with Redis-backed Flask-Limiter or similar service.
    app.failed_login_tracker = FailedLoginTracker()

    # Register blueprints.
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(journal_bp, url_prefix="/journals")

    # Provide CLI helper for local dev.
    @app.cli.command("create-db")
    def create_db_command() -> None:
        """Create tables using SQLAlchemy metadata for quick testing."""
        with app.app_context():
            db.create_all()
            print("Database tables created.")

    return app
