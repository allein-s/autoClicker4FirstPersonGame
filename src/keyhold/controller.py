"""Hold selected keys down for games (concurrent with the auto-clicker).

A separate global hotkey toggles this feature. While active, the chosen keys
are pressed down (via SendInput scan codes) and kept down until stopped. An
optional repeat mode re-sends the key-down at a fixed interval for games that
react to WM_KEYDOWN auto-repeat rather than raw key state.

If the user physically presses a held key, games usually cancel that hold; the
controller mirrors that by releasing only the matching key (and deactivates
when none remain).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

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

    def __init__(self, on_changed: Callable[[], None] | None = None) -> None:
        self._active = False
        self._held: list[KeyDef] = []
        self._repeat_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._on_changed = on_changed
        self._monitor = platforms.KeyBreakMonitor(self._on_physical_key)

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
                # Ignore before inject so macOS does not treat our own press as a break.
                self._monitor.ignore_injected(key.token)
                platforms.key_down(key.token)
            self._active = True
            self._monitor.set_tokens(k.token for k in self._held)
            self._monitor.start()
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
            self._stop.set()
            thread = self._repeat_thread
            self._repeat_thread = None
            held = self._held
            self._held = []
            was_active = self._active
            self._active = False
        # Always tear down the monitor, even if a physical break already cleared hold.
        self._monitor.set_tokens([])
        self._monitor.stop()
        if not was_active:
            return
        if thread is not None:
            thread.join(timeout=1.0)
        for key in held:
            platforms.key_up(key.token)

    def release_key(self, token: str) -> bool:
        """Release one held key. Returns True if a key was released."""
        with self._lock:
            if not self._active:
                return False
            if not any(k.token == token for k in self._held):
                return False
            remaining = [k for k in self._held if k.token != token]
            became_idle = not remaining
            thread = None
            if became_idle:
                self._stop.set()
                thread = self._repeat_thread
                self._repeat_thread = None
                self._held = []
                self._active = False
            else:
                self._held = remaining
        # Do not stop the monitor here: this may run on the monitor's own thread.
        self._monitor.set_tokens(k.token for k in remaining)
        if thread is not None:
            thread.join(timeout=1.0)
        platforms.key_up(token)
        return True

    def _on_physical_key(self, token: str) -> None:
        if not self.release_key(token):
            return
        if self._on_changed is not None:
            self._on_changed()

    def _repeat_loop(self, interval: float) -> None:
        while not self._stop.wait(interval):
            with self._lock:
                held = list(self._held)
            for key in held:
                self._monitor.ignore_injected(key.token)
                platforms.key_down(key.token)
