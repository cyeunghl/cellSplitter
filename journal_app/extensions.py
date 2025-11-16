"""Shared extensions."""
from __future__ import annotations

try:  # pragma: no cover - import preference
    from flask_mail import Mail, Message  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from .stubs.mail import Mail  # type: ignore

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


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
migrate = Migrate()

login_manager.login_view = "auth.login"
