"""Configuration helpers with Turso and Vercel support."""
from __future__ import annotations

import os


def get_database_uri() -> str:
    """
    Get database URI with support for Turso, Vercel, and local development.
    
    Priority:
    1. DATABASE_URL environment variable (Turso or standard SQLite)
    2. Vercel environment: use /tmp for SQLite
    3. Local development: use instance directory
    
    Turso URLs (libsql:// or turso://) are detected and handled appropriately.
    For production Turso connections, ensure libsql-client is installed.
    """
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # Turso/libSQL connection string (libsql:// or turso://)
        # Turso uses libSQL which is SQLite-compatible
        # Note: For actual Turso remote connections, you may need libsql-client
        # For now, we handle the URL format - production deployments should
        # configure proper Turso connection handling
        if database_url.startswith("libsql://") or database_url.startswith("turso://"):
            # Convert to SQLite-compatible format for SQLAlchemy
            # In production with Turso, you may need a custom engine
            return database_url.replace("libsql://", "sqlite:///").replace("turso://", "sqlite:///")
        else:
            # Standard SQLite URL format or other database URLs
            return database_url
    
    # Vercel serverless environment: use /tmp (ephemeral storage)
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        db_path = "/tmp/journal.db"
        os.makedirs("/tmp", exist_ok=True)
        return f"sqlite:///{db_path}"
    
    # Local development: use instance directory
    return "sqlite:///journal.db"


class BaseConfig:
    """Default configuration that can be overridden per environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security: separate salt for password reset tokens (different from SECRET_KEY)
    # In production, use a strong random value stored in environment variables
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", "change-this-salt-in-production"
    )

    # Mail setup: configure for SMTP provider or Mailtrap for testing.
    # 
    # For Mailtrap (testing):
    #   MAIL_SERVER=sandbox.smtp.mailtrap.io
    #   MAIL_PORT=2525
    #   MAIL_USERNAME=<your-mailtrap-username>
    #   MAIL_PASSWORD=<your-mailtrap-password>
    #
    # For production SMTP (e.g., SendGrid, AWS SES, Gmail):
    #   MAIL_SERVER=smtp.sendgrid.net  # or your SMTP server
    #   MAIL_PORT=587
    #   MAIL_USE_TLS=True
    #   MAIL_USERNAME=<your-smtp-username>
    #   MAIL_PASSWORD=<your-smtp-password>
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 2525))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "mailtrap-user")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "mailtrap-pass")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "journal@example.com"
    )

    # CSRF + WTF config.
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_ENABLED = True

    # Password reset token expiration (seconds).
    # Default: 1 hour (3600 seconds)
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.environ.get("RESET_TOKEN_AGE", 3600))


class TestingConfig(BaseConfig):
    """Configuration for testing environment."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    # Short token expiration for testing
    PASSWORD_RESET_TOKEN_MAX_AGE = 60


class ProductionConfig(BaseConfig):
    """
    Configuration for production environment.
    
    Note: In production, ensure these environment variables are set:
    - SECRET_KEY: Strong random secret key
    - SECURITY_PASSWORD_SALT: Strong random salt
    - MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD: SMTP configuration
    
    Validation happens at runtime when the config is used, not at import time.
    """
    # Production should use secure values from environment
    # These will be None if not set, which should be caught at runtime
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")
    
    # Production should use real SMTP
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    
    @classmethod
    def validate(cls):
        """
        Validate that required production settings are present.
        Call this method when using ProductionConfig to ensure all required
        values are set.
        """
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in production")
        if not cls.SECURITY_PASSWORD_SALT:
            raise ValueError("SECURITY_PASSWORD_SALT must be set in production")
        if not all([cls.MAIL_SERVER, cls.MAIL_USERNAME, cls.MAIL_PASSWORD]):
            raise ValueError("Mail configuration must be set in production")

