"""Save / load a schedule (list of ScheduleTask) as JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...i18n import t
from .model import ScheduleTask

FILE_VERSION = 1
DEFAULT_SUFFIX = ".json"


def tasks_to_dict(tasks: list[ScheduleTask]) -> dict[str, Any]:
    return {
        "version": FILE_VERSION,
        "tasks": [
            {"kind": task.kind, **({"ms": task.ms} if task.kind == "interval" else {})}
            for task in tasks
        ],
    }


def tasks_from_dict(data: dict[str, Any]) -> list[ScheduleTask]:
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError(t("schedule.error.invalid_tasks"))

    tasks: list[ScheduleTask] = []
    for i, item in enumerate(raw_tasks, start=1):
        if not isinstance(item, dict):
            raise ValueError(t("schedule.error.invalid_task_format", index=i))
        kind = item.get("kind")
        if kind == "click":
            tasks.append(ScheduleTask(kind="click"))
        elif kind == "interval":
            ms = item.get("ms")
            if isinstance(ms, float) and ms.is_integer():
                ms = int(ms)
            if not isinstance(ms, int) or ms < 0:
                raise ValueError(t("schedule.error.invalid_ms", index=i))
            tasks.append(ScheduleTask(kind="interval", ms=ms))
        else:
            raise ValueError(t("schedule.error.invalid_kind", index=i))
    return tasks


def save_tasks(path: Path, tasks: list[ScheduleTask]) -> None:
    path.write_text(
        json.dumps(tasks_to_dict(tasks), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_tasks(path: Path) -> list[ScheduleTask]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(t("schedule.error.invalid_file"))
    return tasks_from_dict(data)
