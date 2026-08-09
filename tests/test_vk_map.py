"""Tests for keysym <-> virtual-key mapping and hotkey labels."""

from __future__ import annotations

from src.common import vk_map


def test_function_key_roundtrip():
    vk = vk_map.vk_from_keysym("F8")
    assert vk == vk_map.DEFAULT_HOTKEY_VK
    assert vk_map.vk_label(vk) == "F8"


def test_letter_and_digit_mapping():
    assert vk_map.vk_from_keysym("a") == ord("A")
    assert vk_map.vk_from_keysym("5") == ord("5")


def test_named_key_mapping():
    assert vk_map.vk_from_keysym("Escape") == 0x1B
    assert vk_map.vk_label(0x1B) == "Esc"


def test_unsupported_keysym_returns_none():
    assert vk_map.vk_from_keysym("comma") is None


def test_hotkey_label_with_modifiers():
    label = vk_map.hotkey_label(vk_map.DEFAULT_HOTKEY_VK, vk_map.MOD_CONTROL | vk_map.MOD_SHIFT)
    assert label == "Ctrl+Shift+F8"
