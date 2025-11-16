"""Simple in-memory tracker used in tests to simulate rate limiting."""
from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict


class FailedLoginTracker:
    """Track login failures per-identifier (email/IP)."""

    def __init__(self) -> None:
        self._data: DefaultDict[str, int] = defaultdict(int)

    def increment(self, key: str) -> int:
        self._data[key] += 1
        return self._data[key]

    def get_attempts(self, key: str) -> int:
        return self._data[key]

    def reset(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
