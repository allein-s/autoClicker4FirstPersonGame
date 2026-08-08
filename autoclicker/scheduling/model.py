from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..i18n import t

TaskType = Literal["click", "interval"]


@dataclass
class ScheduleTask:
    kind: TaskType
    ms: int = 0

    def label(self) -> str:
        if self.kind == "click":
            return t("task.click")
        return t("task.wait_ms", ms=self.ms)
