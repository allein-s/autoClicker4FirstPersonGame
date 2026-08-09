"""Platform abstraction layer.

All OS-specific logic (input injection, global hotkeys, autostart registration,
work-area query) lives under ``src/platforms/<os>/``. The rest of the app only
imports the neutral API re-exported here, so adding a new OS means creating a
sibling package that implements the same names described in ``base.py`` and
wiring it into the dispatch below -- no changes to shared code.

Windows and macOS are implemented. Linux is not yet provided.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .windows.hotkey import HotkeyService
    from .windows.inputs import game_left_click, key_down, key_up
    from .windows.startup import is_registered, set_registered
    from .windows.window import work_area
elif sys.platform == "darwin":
    from .macos.hotkey import HotkeyService
    from .macos.inputs import game_left_click, key_down, key_up
    from .macos.startup import is_registered, set_registered
    from .macos.window import work_area
else:  # pragma: no cover - implemented on a dedicated per-OS branch
    raise NotImplementedError(
        f"No platform backend for sys.platform={sys.platform!r}. "
        "Implement src/platforms/<os>/ following src/platforms/base.py and "
        "wire it into src/platforms/__init__.py."
    )

__all__ = [
    "HotkeyService",
    "game_left_click",
    "key_down",
    "key_up",
    "is_registered",
    "set_registered",
    "work_area",
]
