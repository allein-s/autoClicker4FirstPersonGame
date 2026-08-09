"""Minimal i18n: string lookup by key with .format() style substitution.

Usage:
    from src.i18n import t, set_language

    set_language("en")
    label = t("button.click")
"""

from __future__ import annotations

from typing import Any

from . import en, ja

DEFAULT_LANGUAGE = "ja"

_STRINGS: dict[str, dict[str, str]] = {
    "ja": ja.STRINGS,
    "en": en.STRINGS,
}

LANGUAGE_NAMES: dict[str, str] = {
    "ja": "日本語",
    "en": "English",
}

_current_language = DEFAULT_LANGUAGE


def available_languages() -> list[str]:
    return list(_STRINGS.keys())


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in _STRINGS else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language


def t(key: str, **kwargs: Any) -> str:
    strings = _STRINGS.get(_current_language, _STRINGS[DEFAULT_LANGUAGE])
    template = strings.get(key)
    if template is None:
        template = _STRINGS[DEFAULT_LANGUAGE].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
