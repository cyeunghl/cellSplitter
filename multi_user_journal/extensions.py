"""Shared extensions with graceful fallbacks for optional dependencies."""
from __future__ import annotations

try:  # pragma: no cover - import preference
    from flask_mail import Mail, Message  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from .stubs.mail import Mail, Message  # type: ignore

try:  # pragma: no cover
    from flask_wtf import CSRFProtect  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from .stubs.csrf import CSRFProtect  # type: ignore

try:  # pragma: no cover
    from flask_migrate import Migrate  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from .stubs.migrate import Migrate  # type: ignore

from flask_sqlalchemy import SQLAlchemy

from .security import LoginManager


# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
migrate = Migrate()

# Configure login manager
login_manager.login_view = "auth.login"





