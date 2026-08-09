"""Tests for settings defaults and JSON persistence."""

from __future__ import annotations

from src.common import paths, settings
from src.common.settings import AppSettings, load_settings, save_settings
from src.common.vk_map import DEFAULT_HOTKEY_VK


def test_defaults_use_relative_schedule_dir():
    s = AppSettings()
    assert s.schedule_dir == "schedule"
    assert s.hotkey_vk == DEFAULT_HOTKEY_VK
    assert s.language == "ja"


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(paths, "settings_path", lambda: settings_file)
    monkeypatch.setattr(settings.paths, "settings_path", lambda: settings_file)

    original = AppSettings(hotkey_vk=0x41, language="en", click_hold_ms=25)
    save_settings(original)
    assert settings_file.exists()

    loaded = load_settings()
    assert loaded.hotkey_vk == 0x41
    assert loaded.language == "en"
    assert loaded.click_hold_ms == 25


def test_missing_file_creates_defaults(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(paths, "settings_path", lambda: settings_file)
    monkeypatch.setattr(settings.paths, "settings_path", lambda: settings_file)

    loaded = load_settings()
    assert loaded.schedule_dir == "schedule"
    assert settings_file.exists()


def test_corrupt_file_falls_back_to_defaults(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{ this is not valid json", encoding="utf-8")
    monkeypatch.setattr(paths, "settings_path", lambda: settings_file)
    monkeypatch.setattr(settings.paths, "settings_path", lambda: settings_file)

    loaded = load_settings()
    assert loaded.language == "ja"


def test_unknown_keys_are_ignored(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"language": "en", "totally_unknown": 123}', encoding="utf-8")
    monkeypatch.setattr(paths, "settings_path", lambda: settings_file)
    monkeypatch.setattr(settings.paths, "settings_path", lambda: settings_file)

    loaded = load_settings()
    assert loaded.language == "en"
    assert not hasattr(loaded, "totally_unknown")
