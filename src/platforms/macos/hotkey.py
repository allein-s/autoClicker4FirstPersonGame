"""macOS global hotkey via pynput's GlobalHotKeys listener.

The app stores hotkeys as Windows virtual-key codes + a modifier bitmask (see
``src.common.vk_map``). Here we translate that into a pynput hotkey spec string
(e.g. ``"<ctrl>+<alt>+<f8>"``) and register a global listener.

Requires macOS Accessibility / Input Monitoring permission to receive events.
"""

from __future__ import annotations

from typing import Callable

from pynput import keyboard

from ...common.vk_map import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, VK_F1

# Windows virtual-key code -> pynput hotkey token (for non-alphanumeric keys).
_SPECIAL_SPEC: dict[int, str] = {
    0x1B: "<esc>",
    0x20: "<space>",
    0x09: "<tab>",
    0x0D: "<enter>",
    0x08: "<backspace>",
    0x2E: "<delete>",
    0x2D: "<insert>",
    0x24: "<home>",
    0x23: "<end>",
    0x21: "<page_up>",
    0x22: "<page_down>",
    0x25: "<left>",
    0x26: "<up>",
    0x27: "<right>",
    0x28: "<down>",
}


def _key_spec(vk: int) -> str | None:
    if VK_F1 <= vk <= VK_F1 + 19:  # pynput supports <f1>..<f20>
        return f"<f{vk - VK_F1 + 1}>"
    if ord("A") <= vk <= ord("Z"):
        return chr(vk).lower()
    if ord("0") <= vk <= ord("9"):
        return chr(vk)
    return _SPECIAL_SPEC.get(vk)


def hotkey_spec(vk: int, mods: int) -> str | None:
    """Build a pynput GlobalHotKeys spec string from (vk, mods), or None."""
    key = _key_spec(vk)
    if key is None:
        return None
    parts: list[str] = []
    if mods & MOD_CONTROL:
        parts.append("<ctrl>")
    if mods & MOD_ALT:
        parts.append("<alt>")
    if mods & MOD_SHIFT:
        parts.append("<shift>")
    if mods & MOD_WIN:
        parts.append("<cmd>")
    parts.append(key)
    return "+".join(parts)


class HotkeyService:
    """Same interface as the Windows HotkeyService (see platforms/base.py)."""

    def __init__(self, vk: int, mods: int, on_trigger: Callable[[], None]) -> None:
        self._vk = vk
        self._mods = mods
        self._on_trigger = on_trigger
        self._listener: keyboard.GlobalHotKeys | None = None
        self._registered = False

    def start(self) -> None:
        self._register()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._registered = False

    def set_hotkey(self, vk: int, mods: int) -> None:
        self._vk = vk
        self._mods = mods
        self.stop()
        self._register()

    @property
    def registered(self) -> bool:
        return self._registered

    @property
    def current(self) -> tuple[int, int]:
        return self._vk, self._mods

    def _register(self) -> None:
        spec = hotkey_spec(self._vk, self._mods)
        if spec is None:
            self._registered = False
            return
        try:
            self._listener = keyboard.GlobalHotKeys({spec: self._on_trigger})
            self._listener.start()
            self._registered = True
        except Exception:
            self._listener = None
            self._registered = False
