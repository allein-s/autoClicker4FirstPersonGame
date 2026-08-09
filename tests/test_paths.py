"""Tests for portable (exe-relative) path handling."""

from __future__ import annotations

from pathlib import Path

from src.common import paths


def test_resolve_relative_against_base_dir():
    resolved = paths.resolve_path("schedule")
    assert resolved == paths.base_dir() / "schedule"


def test_resolve_absolute_is_unchanged():
    absolute = Path(paths.base_dir()) / "somewhere" / "file.json"
    assert paths.resolve_path(str(absolute)) == absolute


def test_to_portable_string_is_relative_inside_base_dir():
    target = paths.base_dir() / "schedule" / "loop.json"
    portable = paths.to_portable_string(target)
    assert not Path(portable).is_absolute()
    assert paths.resolve_path(portable) == target


def test_portable_roundtrip_for_nested_path():
    target = paths.base_dir() / "a" / "b" / "c.json"
    assert paths.resolve_path(paths.to_portable_string(target)) == target
