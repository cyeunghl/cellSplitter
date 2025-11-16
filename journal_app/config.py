"""Configuration helpers."""
from __future__ import annotations

import os


class BaseConfig:
    """Default configuration that can be overridden per environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///journal.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", "change-this-salt"
    )

    # Mail setup: configure for SMTP provider or Mailtrap for testing.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 2525))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "mailtrap-user")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "mailtrap-pass")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "journal@example.com"
    )

    # CSRF + WTF config.
    WTF_CSRF_TIME_LIMIT = None

    # Password reset token expiration (seconds).
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.environ.get("RESET_TOKEN_AGE", 3600))


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
