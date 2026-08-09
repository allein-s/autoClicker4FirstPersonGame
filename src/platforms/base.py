"""Contract every platform backend must provide.

This module is documentation-only: it defines the API surface that
``src/platforms/__init__.py`` re-exports and that the rest of the app depends
on. A new backend (e.g. ``src/platforms/macos/``) should expose callables and a
``HotkeyService`` class matching these signatures.

Notes for non-Windows implementers:
- Key identifiers are the *logical tokens* used by the key-hold feature
  (see ``src.keyhold.controller.HOLDABLE_KEYS``): "w", "a", "s", "d",
  "up", "down", "left", "right", "space", "tab", "ctrl", "alt".
  Each backend maps these tokens to its own native key codes internally.
- ``HotkeyService`` currently takes a numeric key id + modifier bitmask. On
  Windows these are virtual-key codes / RegisterHotKey modifier flags. Other
  platforms may reinterpret them as needed.
- ``KeyBreakMonitor`` reports physical presses of watched hold tokens so the
  app can release those keys when the user overrides them. Synthetic presses
  from ``key_down`` must not be reported (filter injected events, or use
  ``ignore_injected``).
"""

from __future__ import annotations

from typing import Callable, Iterable, Protocol


class HotkeyServiceProtocol(Protocol):
    def __init__(self, vk: int, mods: int, on_trigger: Callable[[], None]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def set_hotkey(self, vk: int, mods: int) -> None: ...

    @property
    def registered(self) -> bool: ...


class KeyBreakMonitorProtocol(Protocol):
    def __init__(self, on_key: Callable[[str], None]) -> None: ...

    def ignore_injected(self, token: str) -> None: ...

    def set_tokens(self, tokens: Iterable[str]) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class PlatformBackend(Protocol):
    """The set of module-level callables a backend must expose."""

    def game_left_click(self, hold_ms: float = ...) -> None: ...

    def key_down(self, token: str) -> None: ...

    def key_up(self, token: str) -> None: ...

    def is_registered(self) -> bool: ...

    def set_registered(self, enabled: bool) -> None: ...

    def work_area(self) -> tuple[int, int, int, int]: ...
