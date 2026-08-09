"""Tests for the i18n string catalogs and lookup helper."""

from __future__ import annotations

from src import i18n
from src.i18n import en, ja


def test_all_languages_share_the_same_keys():
    ja_keys = set(ja.STRINGS)
    for lang in i18n.available_languages():
        strings = i18n._STRINGS[lang]  # noqa: SLF001 - intentional in tests
        assert set(strings) == ja_keys, f"key mismatch in language '{lang}'"


def test_default_language_is_japanese():
    assert i18n.DEFAULT_LANGUAGE == "ja"


def test_every_language_has_a_display_name():
    for lang in i18n.available_languages():
        assert lang in i18n.LANGUAGE_NAMES


def test_translation_lookup_and_formatting():
    i18n.set_language("en")
    assert i18n.t("task.wait_ms", ms=200) == "Wait 200 ms"
    i18n.set_language("ja")
    assert i18n.t("task.wait_ms", ms=200) == "待機 200 ms"


def test_unknown_key_returns_key_itself():
    assert i18n.t("this.key.does.not.exist") == "this.key.does.not.exist"


def test_unknown_language_falls_back_to_default():
    i18n.set_language("zz")
    assert i18n.get_language() == i18n.DEFAULT_LANGUAGE
    i18n.set_language("ja")
