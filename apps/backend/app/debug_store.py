"""In-memory ring buffer for API debug logs (per X-Debug-Session header)."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Deque

_MAX_PER_SESSION = 20
_buffers: dict[str, Deque[dict]] = {}
_lock = Lock()


def append_log(session_id: str, entry: dict, *, max_entries: int = _MAX_PER_SESSION) -> None:
    with _lock:
        if session_id not in _buffers:
            _buffers[session_id] = deque(maxlen=max_entries)
        _buffers[session_id].appendleft(entry)


def get_logs(session_id: str) -> list[dict]:
    with _lock:
        q = _buffers.get(session_id)
        if not q:
            return []
        return list(q)


def clear_logs(session_id: str) -> None:
    with _lock:
        _buffers.pop(session_id, None)
