"""Hold selected keys down for games (concurrent with the auto-clicker).

A separate global hotkey toggles this feature. While active, the chosen keys
are pressed down (via SendInput scan codes) and kept down until stopped. An
optional repeat mode re-sends the key-down at a fixed interval for games that
react to WM_KEYDOWN auto-repeat rather than raw key state.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .. import platforms


@dataclass(frozen=True)
class KeyDef:
    token: str  # stable identifier stored in settings + sent to the platform
    label: str  # short label shown in the UI (language-neutral)


# Order defines the layout in the key-hold tab. Each token's native key code is
# resolved by the active platform backend (see src/platforms/base.py), so this
# list stays OS-agnostic.
HOLDABLE_KEYS: list[KeyDef] = [
    KeyDef("w", "W"),
    KeyDef("a", "A"),
    KeyDef("s", "S"),
    KeyDef("d", "D"),
    KeyDef("up", "\u2191"),
    KeyDef("left", "\u2190"),
    KeyDef("down", "\u2193"),
    KeyDef("right", "\u2192"),
    KeyDef("space", "Space"),
    KeyDef("tab", "Tab"),
    KeyDef("ctrl", "Ctrl"),
    KeyDef("alt", "Alt"),
]

KEY_BY_TOKEN: dict[str, KeyDef] = {k.token: k for k in HOLDABLE_KEYS}


def resolve_tokens(tokens: list[str]) -> list[KeyDef]:
    """Map stored tokens to KeyDefs, preserving the canonical layout order."""
    selected = set(tokens)
    return [k for k in HOLDABLE_KEYS if k.token in selected]


class KeyHoldController:
    """Presses a set of keys and keeps them down until stopped."""

    def __init__(self) -> None:
        self._active = False
        self._held: list[KeyDef] = []
        self._repeat_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def held_labels(self) -> list[str]:
        return [k.label for k in self._held]

    def start(self, keys: list[KeyDef], repeat: bool, interval_ms: int) -> bool:
        with self._lock:
            if self._active or not keys:
                return False
            self._held = list(keys)
            for key in self._held:
                platforms.key_down(key.token)
            self._active = True
            if repeat and interval_ms > 0:
                self._stop.clear()
                self._repeat_thread = threading.Thread(
                    target=self._repeat_loop,
                    args=(interval_ms / 1000.0,),
                    daemon=True,
                )
                self._repeat_thread.start()
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._stop.set()
            thread = self._repeat_thread
            self._repeat_thread = None
            held = self._held
            self._held = []
            self._active = False
        if thread is not None:
            thread.join(timeout=1.0)
        for key in held:
            platforms.key_up(key.token)

    def _repeat_loop(self, interval: float) -> None:
        while not self._stop.wait(interval):
            for key in list(self._held):
                platforms.key_down(key.token)
