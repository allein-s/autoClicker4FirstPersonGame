"""Application settings persisted as JSON next to the exe.

Paths (schedule_dir, last_schedule_path) are stored as strings relative to
the executable's directory whenever possible -- see `src.common.paths` --
so settings.json stays portable across machines and folder locations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths
from ..i18n import DEFAULT_LANGUAGE
from .vk_map import DEFAULT_HOLD_HOTKEY_VK, DEFAULT_HOTKEY_VK

SETTINGS_VERSION = 1


@dataclass
class AppSettings:
    hotkey_vk: int = DEFAULT_HOTKEY_VK
    hotkey_mods: int = 0
    schedule_dir: str = paths.DEFAULT_SCHEDULE_DIRNAME
    show_overlay: bool = True
    click_hold_ms: int = 12
    minimize_on_run: bool = True
    auto_load_last_schedule: bool = False
    last_schedule_path: str | None = None
    main_window_topmost: bool = False
    start_with_windows: bool = False
    language: str = DEFAULT_LANGUAGE
    # --- Key-hold feature ---
    hold_hotkey_vk: int = DEFAULT_HOLD_HOTKEY_VK
    hold_hotkey_mods: int = 0
    hold_keys: list[str] = field(default_factory=lambda: ["w"])
    hold_repeat: bool = False
    hold_repeat_interval_ms: int = 30
    minimize_on_hold_run: bool = False

    def schedule_dir_path(self) -> Path:
        return paths.resolve_path(self.schedule_dir)

    def last_schedule_file(self) -> Path | None:
        if not self.last_schedule_path:
            return None
        return paths.resolve_path(self.last_schedule_path)


def load_settings() -> AppSettings:
    path = paths.settings_path()
    if not path.exists():
        settings = AppSettings()
        save_settings(settings)
        return settings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid settings file")
        defaults = AppSettings()
        kwargs = {key: data[key] for key in asdict(defaults) if key in data}
        return AppSettings(**kwargs)
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        settings = AppSettings()
        save_settings(settings)
        return settings


def save_settings(settings: AppSettings) -> None:
    data = asdict(settings)
    data["version"] = SETTINGS_VERSION
    path = paths.settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
