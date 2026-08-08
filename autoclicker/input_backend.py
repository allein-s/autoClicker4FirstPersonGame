"""Low-level mouse input for games (SendInput + thread attach)."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

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


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


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
