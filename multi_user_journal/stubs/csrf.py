"""Basic CSRF shim for testing when Flask-WTF is not installed."""
from __future__ import annotations


class CSRFProtect:
    """Stub CSRFProtect class compatible with Flask-WTF."""
    def __init__(self, app=None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        """
        Initialize CSRF protection.
        
        In production, use Flask-WTF's CSRFProtect for full protection.
        This stub provides a no-op implementation for testing.
        """
        app.csrf_protect = self





