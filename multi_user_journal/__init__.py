"""Application factory for the multi-user journal app with Turso support."""
from __future__ import annotations

from flask import Flask, jsonify

from .config import BaseConfig
from .extensions import csrf, db, login_manager, mail, migrate
from .auth import auth_bp
from .journals import journal_bp
from .rate_limit import FailedLoginTracker


def create_app(config_object: type[BaseConfig] | None = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Supports Turso database connections via DATABASE_URL environment variable.
    Falls back to SQLite for local development or when DATABASE_URL is not set.
    """
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

    # Root route - API information
    @app.route("/")
    def index():
        """Root endpoint with API information."""
        return jsonify({
            "message": "Multi-User Journal API",
            "version": "1.0.0",
            "endpoints": {
                "authentication": {
                    "signup": "POST /auth/signup",
                    "login": "POST /auth/login",
                    "logout": "POST /auth/logout",
                    "request_password_reset": "POST /auth/request-reset",
                    "reset_password": "POST /auth/reset/<token>",
                    "get_security_question": "POST /auth/security-question",
                    "reset_with_security": "POST /auth/reset-with-security",
                },
                "journals": {
                    "list": "GET /journals",
                    "create": "POST /journals",
                    "get": "GET /journals/<id>",
                    "update": "PUT /journals/<id>",
                    "delete": "DELETE /journals/<id>",
                }
            },
            "documentation": "See README.md for API documentation"
        })

    # Provide CLI helper for local dev.
    @app.cli.command("create-db")
    def create_db_command() -> None:
        """Create tables using SQLAlchemy metadata for quick testing."""
        with app.app_context():
            db.create_all()
            print("Database tables created.")

    return app

