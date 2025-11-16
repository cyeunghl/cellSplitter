"""Minimal session-based auth helpers that mimic Flask-Login's API surface."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from flask import abort, g, session
from werkzeug.local import LocalProxy


class UserMixin:
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
    @property
    def is_authenticated(self) -> bool:  # pragma: no cover
        return False

    def get_id(self) -> Optional[str]:  # pragma: no cover
        return None


class LoginManager:
    def __init__(self) -> None:
        self._user_callback: Optional[Callable[[str], Any]] = None
        self.login_view: str | None = None

    def init_app(self, app) -> None:
        app.login_manager = self

        @app.before_request
        def load_user() -> None:
            user_id = session.get("_user_id")
            if user_id and self._user_callback:
                g._current_user = self._user_callback(user_id)
            else:
                g._current_user = AnonymousUser()

    def user_loader(self, callback: Callable[[str], Any]) -> Callable[[str], Any]:
        self._user_callback = callback
        return callback


def _get_user() -> UserMixin:
    user = getattr(g, "_current_user", None)
    if user is None:
        user = AnonymousUser()
        g._current_user = user
    return user


current_user: UserMixin = LocalProxy(_get_user)


def login_user(user: UserMixin) -> None:
    session["_user_id"] = user.get_id()
    g._current_user = user


def logout_user() -> None:
    session.pop("_user_id", None)
    g._current_user = AnonymousUser()


def login_required(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return func(*args, **kwargs)

    return wrapper
