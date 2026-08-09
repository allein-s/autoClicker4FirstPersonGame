"""macOS mouse/keyboard injection via pynput.

Key identifiers are the app's logical tokens (see
``src.keyhold.controller.HOLDABLE_KEYS``); this module maps them to pynput keys.
"""

from __future__ import annotations

import time

from pynput.keyboard import Controller as _KeyController
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button
from pynput.mouse import Controller as _MouseController

# Logical token -> pynput key. Letters use KeyCode.from_char; specials use Key.
_HOLD_KEYS: dict[str, object] = {
    "w": KeyCode.from_char("w"),
    "a": KeyCode.from_char("a"),
    "s": KeyCode.from_char("s"),
    "d": KeyCode.from_char("d"),
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "space": Key.space,
    "tab": Key.tab,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
}

_keyboard = _KeyController()
_mouse = _MouseController()


def game_left_click(hold_ms: float = 0.012) -> None:
    """Left click at the current cursor position."""
    _mouse.press(Button.left)
    if hold_ms > 0:
        time.sleep(hold_ms)
    _mouse.release(Button.left)


def key_down(token: str) -> None:
    """Press a logical key down (and keep it down)."""
    key = _HOLD_KEYS.get(token)
    if key is not None:
        _keyboard.press(key)


def key_up(token: str) -> None:
    """Release a previously pressed logical key."""
    key = _HOLD_KEYS.get(token)
    if key is not None:
        _keyboard.release(key)
