"""Minimal stub for Flask-Migrate."""
from __future__ import annotations


class Migrate:
    def __init__(self, app=None, db=None) -> None:
        if app is not None:
            self.init_app(app, db)

    def init_app(self, app, db=None) -> None:
        app.migrate = self
