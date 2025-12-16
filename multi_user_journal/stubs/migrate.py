"""Minimal stub for Flask-Migrate."""
from __future__ import annotations


class Migrate:
    """Stub Migrate class compatible with Flask-Migrate."""
    def __init__(self, app=None, db=None) -> None:
        if app is not None:
            self.init_app(app, db)

    def init_app(self, app, db=None) -> None:
        """
        Initialize database migrations.
        
        In production, use Flask-Migrate for proper database migrations.
        This stub provides a no-op implementation for testing.
        """
        app.migrate = self





