"""Low-level mouse/keyboard input for games (SendInput + thread attach)."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUTUNION),
    ]


def _mouse_event_legacy(down: bool) -> None:
    flag = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    user32.mouse_event(flag, 0, 0, 0, 0)


def _send_input_flag(flag: int) -> bool:
    inp = INPUT(
        type=INPUT_MOUSE,
        union=_INPUTUNION(mi=MOUSEINPUT(dwFlags=flag)),
    )
    sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return sent == 1


def _with_foreground_input(callback) -> None:
    """Attach to foreground window thread so games receive injected input."""
    foreground = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None)
    cur_thread = kernel32.GetCurrentThreadId()
    attached = False
    if fg_thread and fg_thread != cur_thread:
        attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
    try:
        callback()
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)


def game_left_click(hold_ms: float = 0.012) -> None:
    """Left click at current cursor position (Minecraft / fullscreen friendly)."""

    def do_click() -> None:
        if not _send_input_flag(MOUSEEVENTF_LEFTDOWN):
            _mouse_event_legacy(True)
        if hold_ms > 0:
            time.sleep(hold_ms)
        if not _send_input_flag(MOUSEEVENTF_LEFTUP):
            _mouse_event_legacy(False)

    _with_foreground_input(do_click)


# ----------------------------------------------------------------------
# Keyboard (hold keys down for games)
# ----------------------------------------------------------------------
# Map the app's logical key tokens (see src.keyhold.controller.HOLDABLE_KEYS)
# to Windows virtual-key codes + the extended-key flag. This table is the only
# Windows-specific part of the key-hold feature; other platforms provide their
# own token -> native code mapping.
_HOLD_KEY_CODES: dict[str, tuple[int, bool]] = {
    "w": (0x57, False),
    "a": (0x41, False),
    "s": (0x53, False),
    "d": (0x44, False),
    "up": (0x26, True),
    "down": (0x28, True),
    "left": (0x25, True),
    "right": (0x27, True),
    "space": (0x20, False),
    "tab": (0x09, False),
    "ctrl": (0xA2, False),  # left Ctrl
    "alt": (0xA4, False),  # left Alt
}


def _send_key(vk: int, down: bool, extended: bool) -> bool:
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    if scan:
        flags = KEYEVENTF_SCANCODE
        w_vk = 0
        w_scan = scan
    else:  # fall back to virtual-key injection when no scan code exists
        flags = 0
        w_vk = vk
        w_scan = 0
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not down:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(
        type=INPUT_KEYBOARD,
        union=_INPUTUNION(ki=KEYBDINPUT(wVk=w_vk, wScan=w_scan, dwFlags=flags)),
    )
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1


def key_down(token: str) -> None:
    """Press a logical key down (and keep it down) at the foreground window."""
    code = _HOLD_KEY_CODES.get(token)
    if code is None:
        return
    vk, extended = code
    _with_foreground_input(lambda: _send_key(vk, True, extended))


def key_up(token: str) -> None:
    """Release a previously pressed logical key at the foreground window."""
    code = _HOLD_KEY_CODES.get(token)
    if code is None:
        return
    vk, extended = code
    _with_foreground_input(lambda: _send_key(vk, False, extended))
