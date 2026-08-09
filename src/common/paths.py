"""Filesystem path helpers.

All paths persisted to settings are kept relative to the executable's own
directory whenever possible, so the app stays portable when the folder is
moved, copied, or run on a different machine/user account.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_SCHEDULE_DIRNAME = "schedule"
SETTINGS_FILENAME = "settings.json"


def base_dir() -> Path:
    """Directory containing the running exe (or the project root when run from source).

    Set the ``AUTOCLICKER_HOME`` environment variable to redirect where
    ``settings.json`` / the schedule directory are read and written. This keeps
    tests and dev runs from scattering runtime files into the repository root.
    """
    override = os.environ.get("AUTOCLICKER_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # .../src/common/paths.py -> project root is three levels up.
    return Path(__file__).resolve().parent.parent.parent


def executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return base_dir() / "main.py"


def settings_path() -> Path:
    return base_dir() / SETTINGS_FILENAME


def resolve_path(value: str) -> Path:
    """Resolve a possibly-relative stored path against the app's base directory."""
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return base_dir() / candidate


def to_portable_string(target: Path) -> str:
    """Convert `target` to a string relative to the base directory when
    possible, avoiding machine-specific absolute paths in saved settings."""
    base = base_dir()
    try:
        resolved = target.resolve()
    except OSError:
        resolved = target
    try:
        return os.path.relpath(resolved, base)
    except ValueError:
        # Different drive on Windows: a relative path cannot express this.
        return str(resolved)
