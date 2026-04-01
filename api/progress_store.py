"""
Thread-safe in-memory store for pipeline progress events.
Background threads (LangGraph pipeline) write to it.
Async SSE endpoints read from it.
"""
import threading
from collections import defaultdict
from typing import Any

_lock = threading.Lock()

_store: dict[str, dict] = {}  # doc_id -> {events: list, result: dict|None, done: bool}


def _init(doc_id: str):
    with _lock:
        if doc_id not in _store:
            _store[doc_id] = {"events": [], "result": None, "done": False}


def publish_event(doc_id: str, event: dict[str, Any]):
    _init(doc_id)
    with _lock:
        _store[doc_id]["events"].append(event)


def publish_result(doc_id: str, result: dict[str, Any]):
    _init(doc_id)
    with _lock:
        _store[doc_id]["result"] = result
        _store[doc_id]["done"] = True


def get_events(doc_id: str, after_idx: int = 0) -> list[dict]:
    with _lock:
        events = _store.get(doc_id, {}).get("events", [])
        return events[after_idx:]


def get_result(doc_id: str) -> dict | None:
    with _lock:
        return _store.get(doc_id, {}).get("result")


def is_done(doc_id: str) -> bool:
    with _lock:
        return _store.get(doc_id, {}).get("done", False)


def clear(doc_id: str):
    with _lock:
        _store.pop(doc_id, None)
