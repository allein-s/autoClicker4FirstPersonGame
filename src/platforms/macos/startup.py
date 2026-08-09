"""Launch-at-login on macOS via a per-user LaunchAgent plist."""

from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

from ...common.paths import executable_path

LABEL = "com.autoclicker.launch"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def is_registered() -> bool:
    return _plist_path().exists()


def set_registered(enabled: bool) -> None:
    path = _plist_path()
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "Label": LABEL,
            "ProgramArguments": [str(executable_path())],
            "RunAtLoad": True,
        }
        with open(path, "wb") as fh:
            plistlib.dump(data, fh)
        subprocess.run(["launchctl", "load", str(path)], check=False)
    else:
        if path.exists():
            subprocess.run(["launchctl", "unload", str(path)], check=False)
            path.unlink(missing_ok=True)
