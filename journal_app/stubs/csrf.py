"""Basic CSRF shim for testing when Flask-WTF is not installed."""
from __future__ import annotations


class CSRFProtect:
    def __init__(self, app=None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        # In production, use Flask-WTF's CSRFProtect for full protection.
        app.csrf_protect = self
