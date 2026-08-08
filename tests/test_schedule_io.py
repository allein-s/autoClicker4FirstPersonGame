"""Tests for schedule save/load and validation."""

from __future__ import annotations

import pytest

from autoclicker.scheduling import ScheduleTask, load_tasks, save_tasks
from autoclicker.scheduling.io import tasks_from_dict, tasks_to_dict


def _sample_tasks() -> list[ScheduleTask]:
    return [
        ScheduleTask(kind="click"),
        ScheduleTask(kind="interval", ms=200),
        ScheduleTask(kind="click"),
        ScheduleTask(kind="interval", ms=3000),
    ]


def test_roundtrip(tmp_path):
    tasks = _sample_tasks()
    path = tmp_path / "schedule.json"
    save_tasks(path, tasks)
    loaded = load_tasks(path)
    assert [(t.kind, t.ms) for t in loaded] == [(t.kind, t.ms) for t in tasks]


def test_to_dict_omits_ms_for_click():
    data = tasks_to_dict([ScheduleTask(kind="click")])
    assert data["tasks"] == [{"kind": "click"}]


def test_float_ms_is_coerced_to_int():
    tasks = tasks_from_dict({"tasks": [{"kind": "interval", "ms": 200.0}]})
    assert tasks[0].ms == 200
    assert isinstance(tasks[0].ms, int)


@pytest.mark.parametrize(
    "payload",
    [
        {"tasks": "not-a-list"},
        {"tasks": [{"kind": "bogus"}]},
        {"tasks": [{"kind": "interval", "ms": -5}]},
        {"tasks": [{"kind": "interval"}]},
        {"tasks": [123]},
    ],
)
def test_invalid_payloads_raise(payload):
    with pytest.raises(ValueError):
        tasks_from_dict(payload)


def test_load_rejects_non_object(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_tasks(path)
