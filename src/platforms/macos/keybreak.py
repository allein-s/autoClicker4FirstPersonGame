"""Detect physical presses of held keys via pynput's keyboard Listener.

Injected presses from ``pynput.keyboard.Controller`` also reach the listener,
so callers must call :meth:`ignore_injected` once per synthetic key-down
(including hold-repeat re-sends) before the event arrives.
"""

from __future__ import annotations

import threading
from typing import Callable, Iterable

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


def _token_for_key(key: object) -> str | None:
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        return "ctrl"
    if key in (Key.alt, Key.alt_l, Key.alt_r):
        return "alt"
    if key == Key.space:
        return "space"
    if key == Key.tab:
        return "tab"
    if key == Key.up:
        return "up"
    if key == Key.down:
        return "down"
    if key == Key.left:
        return "left"
    if key == Key.right:
        return "right"
    if isinstance(key, KeyCode) and key.char:
        char = key.char.lower()
        if char in ("w", "a", "s", "d"):
            return char
    return None


class KeyBreakMonitor:
    """Watch physical key-downs for a set of logical hold tokens."""

    def __init__(self, on_key: Callable[[str], None]) -> None:
        self._on_key = on_key
        self._tokens: set[str] = set()
        self._suppress: dict[str, int] = {}
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None

    def ignore_injected(self, token: str) -> None:
        """Ignore the next listener event for ``token`` (synthetic press)."""
        with self._lock:
            self._suppress[token] = self._suppress.get(token, 0) + 1

    def set_tokens(self, tokens: Iterable[str]) -> None:
        with self._lock:
            self._tokens = set(tokens)

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass
        with self._lock:
            self._tokens.clear()
            self._suppress.clear()

    def _on_press(self, key: object) -> None:
        token = _token_for_key(key)
        if token is None:
            return
        with self._lock:
            pending = self._suppress.get(token, 0)
            if pending > 0:
                self._suppress[token] = pending - 1
                return
            if token not in self._tokens:
                return
        self._on_key(token)
