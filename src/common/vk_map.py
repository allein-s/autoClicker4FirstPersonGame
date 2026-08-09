"""Tkinter keysym <-> Windows virtual-key code mapping for hotkey capture/display."""

from __future__ import annotations

VK_F1 = 0x70
DEFAULT_HOTKEY_VK = VK_F1 + 7  # F8
DEFAULT_HOLD_HOTKEY_VK = VK_F1 + 8  # F9

_NAMED_VK: dict[str, int] = {
    "Escape": 0x1B,
    "Tab": 0x09,
    "space": 0x20,
    "Return": 0x0D,
    "KP_Enter": 0x0D,
    "BackSpace": 0x08,
    "Delete": 0x2E,
    "Insert": 0x2D,
    "Home": 0x24,
    "End": 0x23,
    "Prior": 0x21,  # Page Up
    "Next": 0x22,  # Page Down
    "Up": 0x26,
    "Down": 0x28,
    "Left": 0x25,
    "Right": 0x27,
    "Pause": 0x13,
    "Caps_Lock": 0x14,
    "Num_Lock": 0x90,
    "Scroll_Lock": 0x91,
    "Print": 0x2C,
}

_NAMED_LABEL: dict[int, str] = {
    0x1B: "Esc",
    0x09: "Tab",
    0x20: "Space",
    0x0D: "Enter",
    0x08: "BackSpace",
    0x2E: "Delete",
    0x2D: "Insert",
    0x24: "Home",
    0x23: "End",
    0x21: "PageUp",
    0x22: "PageDown",
    0x26: "Up",
    0x28: "Down",
    0x25: "Left",
    0x27: "Right",
    0x13: "Pause",
    0x14: "CapsLock",
    0x90: "NumLock",
    0x91: "ScrollLock",
    0x2C: "PrintScreen",
}

MODIFIER_KEYSYMS = {
    "Control_L",
    "Control_R",
    "Shift_L",
    "Shift_R",
    "Alt_L",
    "Alt_R",
    "Win_L",
    "Win_R",
    "Super_L",
    "Super_R",
}

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008


def vk_from_keysym(keysym: str) -> int | None:
    if keysym in _NAMED_VK:
        return _NAMED_VK[keysym]
    if len(keysym) == 1:
        ch = keysym.upper()
        if "0" <= ch <= "9" or "A" <= ch <= "Z":
            return ord(ch)
        return None
    if len(keysym) >= 2 and keysym[0] in ("F", "f") and keysym[1:].isdigit():
        n = int(keysym[1:])
        if 1 <= n <= 24:
            return VK_F1 + (n - 1)
    return None


def vk_label(vk: int) -> str:
    if vk in _NAMED_LABEL:
        return _NAMED_LABEL[vk]
    if VK_F1 <= vk <= VK_F1 + 23:
        return f"F{vk - VK_F1 + 1}"
    if ord("0") <= vk <= ord("9") or ord("A") <= vk <= ord("Z"):
        return chr(vk)
    return f"VK_{vk:02X}"


def hotkey_label(vk: int, mods: int) -> str:
    parts = []
    if mods & MOD_CONTROL:
        parts.append("Ctrl")
    if mods & MOD_ALT:
        parts.append("Alt")
    if mods & MOD_SHIFT:
        parts.append("Shift")
    if mods & MOD_WIN:
        parts.append("Win")
    parts.append(vk_label(vk))
    return "+".join(parts)
