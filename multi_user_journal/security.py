"""Minimal session-based auth helpers that mimic Flask-Login's API surface."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

try:
    from flask_login import (  # type: ignore
        LoginManager as FlaskLoginManager,
        UserMixin as FlaskUserMixin,
        login_user as flask_login_user,
        logout_user as flask_logout_user,
        login_required as flask_login_required,
        current_user as flask_current_user,
    )
    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    FLASK_LOGIN_AVAILABLE = False

from flask import abort, g, session
from werkzeug.local import LocalProxy


class UserMixin:
    """
    User mixin compatible with Flask-Login.
    
    If Flask-Login is available, use FlaskUserMixin instead.
    This provides a fallback implementation for environments without Flask-Login.
    """
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - simple property
        return True

    @property
    def is_active(self) -> bool:  # pragma: no cover
        return True

    @property
    def is_anonymous(self) -> bool:  # pragma: no cover
        return False

    def get_id(self) -> str:
        return str(self.id)


class AnonymousUser(UserMixin):
    """Anonymous user for unauthenticated requests."""
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover
        return False

    def get_id(self) -> Optional[str]:  # pragma: no cover
        return None


class LoginManager:
    """
    Login manager compatible with Flask-Login.
    
    If Flask-Login is available, use FlaskLoginManager instead.
    This provides a fallback implementation for environments without Flask-Login.
    """
    def __init__(self) -> None:
        self._user_callback: Optional[Callable[[str], Any]] = None
        self.login_view: str | None = None

    def init_app(self, app) -> None:
        """Initialize the login manager with the Flask app."""
        if FLASK_LOGIN_AVAILABLE:
            # Use Flask-Login if available
            flask_login_manager = FlaskLoginManager()
            flask_login_manager.init_app(app)
            flask_login_manager.login_view = self.login_view
            if self._user_callback:
                flask_login_manager.user_loader(self._user_callback)
            app.login_manager = flask_login_manager
            return

        # Fallback to custom session-based implementation
        app.login_manager = self

        @app.before_request
        def load_user() -> None:
            user_id = session.get("_user_id")
            if user_id and self._user_callback:
                g._current_user = self._user_callback(user_id)
            else:
                g._current_user = AnonymousUser()

    def user_loader(self, callback: Callable[[str], Any]) -> Callable[[str], Any]:
        """Register the user loader callback."""
        self._user_callback = callback
        return callback


def _get_user() -> UserMixin:
    """Get the current user from Flask-Login or session."""
    if FLASK_LOGIN_AVAILABLE:
        return flask_current_user
    
    # Fallback to custom session-based implementation
    user = getattr(g, "_current_user", None)
    if user is None:
        user = AnonymousUser()
        g._current_user = user
    return user


# Export current_user - uses Flask-Login if available, otherwise custom implementation
current_user: UserMixin = LocalProxy(_get_user)


def login_user(user: UserMixin) -> None:
    """Log in a user."""
    if FLASK_LOGIN_AVAILABLE:
        flask_login_user(user)
        return
    
    # Fallback to custom session-based implementation
    session["_user_id"] = user.get_id()
    g._current_user = user


def logout_user() -> None:
    """Log out the current user."""
    if FLASK_LOGIN_AVAILABLE:
        flask_logout_user()
        return
    
    # Fallback to custom session-based implementation
    session.pop("_user_id", None)
    g._current_user = AnonymousUser()


def login_required(func: Callable) -> Callable:
    """Decorator to require authentication."""
    if FLASK_LOGIN_AVAILABLE:
        return flask_login_required(func)
    
    # Fallback to custom implementation
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return func(*args, **kwargs)

    return wrapper





