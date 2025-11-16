"""Minimal Flask-Mail compatible shim used when Flask-Mail is unavailable."""
from __future__ import annotations


class Message:
    def __init__(self, subject: str = "", recipients: list[str] | None = None, body: str = "") -> None:
        self.subject = subject
        self.recipients = recipients or []
        self.body = body


class Mail:
    def __init__(self, app=None) -> None:
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        self.app = app

    def send(self, message: Message) -> None:  # pragma: no cover - replaced in tests
        # Production deployments should install Flask-Mail; this shim only prevents import
        # errors inside the exercise environment.
        if self.app and self.app.config.get("MAIL_SUPPRESS_SEND"):
            return
        raise RuntimeError("Mail backend not configured. Install Flask-Mail in production.")
