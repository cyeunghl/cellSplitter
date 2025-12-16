"""Simple in-memory tracker used in tests to simulate rate limiting."""
from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict


class FailedLoginTracker:
    """
    Track login failures per-identifier (email/IP).
    
    This is a simple in-memory implementation for development and testing.
    
    For production deployments, replace this with:
    - Flask-Limiter (https://flask-limiter.readthedocs.io/)
    - Redis-backed rate limiting
    - Distributed rate limiting service
    
    Example Flask-Limiter integration:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )
        
        @auth_bp.route("/login", methods=["POST"])
        @limiter.limit("5 per minute")
        def login():
            # ... login logic
    """

    def __init__(self) -> None:
        self._data: DefaultDict[str, int] = defaultdict(int)

    def increment(self, key: str) -> int:
        """Increment failed login attempts for the given key (email/IP)."""
        self._data[key] += 1
        return self._data[key]

    def get_attempts(self, key: str) -> int:
        """Get the number of failed attempts for the given key."""
        return self._data[key]

    def reset(self, key: str) -> None:
        """Reset failed login attempts for the given key."""
        if key in self._data:
            del self._data[key]





