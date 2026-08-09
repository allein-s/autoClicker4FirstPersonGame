"""Unit tests for KeyHoldController physical-break behaviour."""

from __future__ import annotations

from typing import Callable, Iterable

import pytest

from src.keyhold.controller import KEY_BY_TOKEN, KeyHoldController


class FakeMonitor:
    def __init__(self, on_key: Callable[[str], None]) -> None:
        self.on_key = on_key
        self.tokens: set[str] = set()
        self.started = False
        self.stopped = False
        self.ignored: list[str] = []

    def ignore_injected(self, token: str) -> None:
        self.ignored.append(token)

    def set_tokens(self, tokens: Iterable[str]) -> None:
        self.tokens = set(tokens)

    def start(self) -> None:
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True
        self.tokens.clear()


@pytest.fixture
def controller(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[KeyHoldController, FakeMonitor, list[str], list[str], list[str]]:
    downs: list[str] = []
    ups: list[str] = []
    monitor_box: dict[str, FakeMonitor] = {}

    def fake_key_down(token: str) -> None:
        downs.append(token)

    def fake_key_up(token: str) -> None:
        ups.append(token)

    def fake_monitor(on_key: Callable[[str], None]) -> FakeMonitor:
        monitor_box["m"] = FakeMonitor(on_key)
        return monitor_box["m"]

    monkeypatch.setattr("src.keyhold.controller.platforms.key_down", fake_key_down)
    monkeypatch.setattr("src.keyhold.controller.platforms.key_up", fake_key_up)
    monkeypatch.setattr("src.keyhold.controller.platforms.KeyBreakMonitor", fake_monitor)

    changes: list[str] = []
    ctrl = KeyHoldController(on_changed=lambda: changes.append("changed"))
    return ctrl, monitor_box["m"], changes, downs, ups


def test_physical_break_releases_only_that_key(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    keys = [KEY_BY_TOKEN["w"], KEY_BY_TOKEN["a"], KEY_BY_TOKEN["d"]]
    assert ctrl.start(keys, repeat=False, interval_ms=0)
    assert ctrl.active
    assert monitor.tokens == {"w", "a", "d"}
    assert downs == ["w", "a", "d"]

    monitor.on_key("a")

    assert ctrl.active
    assert ctrl.held_labels == ["W", "D"]
    assert ups == ["a"]
    assert monitor.tokens == {"w", "d"}
    assert changes == ["changed"]


def test_physical_break_last_key_deactivates(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    assert ctrl.start([KEY_BY_TOKEN["w"]], repeat=False, interval_ms=0)

    monitor.on_key("w")

    assert not ctrl.active
    assert ctrl.held_labels == []
    assert ups == ["w"]
    assert monitor.tokens == set()
    assert changes == ["changed"]
    # Avoid self-join deadlock: monitor is not stopped from its own callback.
    assert not monitor.stopped


def test_physical_break_unknown_key_is_ignored(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    assert ctrl.start([KEY_BY_TOKEN["w"]], repeat=False, interval_ms=0)

    monitor.on_key("s")

    assert ctrl.active
    assert ups == []
    assert changes == []


def test_stop_after_physical_idle_still_stops_monitor(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    assert ctrl.start([KEY_BY_TOKEN["w"]], repeat=False, interval_ms=0)
    monitor.on_key("w")
    assert not ctrl.active
    assert not monitor.stopped

    ctrl.stop()

    assert monitor.stopped
    # Already released by the physical break; do not key_up again.
    assert ups == ["w"]


def test_stop_releases_remaining_and_stops_monitor(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    assert ctrl.start([KEY_BY_TOKEN["w"], KEY_BY_TOKEN["a"]], repeat=False, interval_ms=0)
    monitor.on_key("w")
    ctrl.stop()

    assert not ctrl.active
    assert ups == ["w", "a"]
    assert monitor.stopped


def test_start_ignores_injected_before_key_down(controller) -> None:
    ctrl, monitor, changes, downs, ups = controller
    assert ctrl.start([KEY_BY_TOKEN["w"], KEY_BY_TOKEN["a"]], repeat=False, interval_ms=0)
    # ignore_injected must be recorded before each synthetic key_down.
    assert monitor.ignored == ["w", "a"]
    assert downs == ["w", "a"]
