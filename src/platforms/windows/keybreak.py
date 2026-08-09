"""Detect physical presses of held keys via a low-level keyboard hook.

When the user physically presses a key that the tool is currently holding,
games typically cancel that key's held state. This monitor reports those
presses so the app can release the matching logical token and stay in sync.

Injected events (SendInput from this process, including hold-repeat re-sends)
are ignored via ``LLKHF_INJECTED``.

The hook thread uses a timed ``MsgWaitForMultipleObjects`` pump instead of a
blocking ``GetMessage`` + ``WM_QUIT`` wake-up, so ``stop()`` does not race on
thread-id publication when called immediately after ``start()``.
"""

from __future__ import annotations

import ctypes
import queue
import threading
from ctypes import wintypes
from typing import Callable, Iterable

from .inputs import _HOLD_KEY_CODES

user32 = ctypes.windll.user32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0
LLKHF_INJECTED = 0x10
PM_REMOVE = 0x0001
QS_ALLINPUT = 0x04FF
# How often the pump notices ``_stop`` without needing PostThreadMessage.
_POLL_MS = 50

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

# Also treat right-side modifiers as breaking left-side holds.
_EXTRA_VK_TO_TOKEN: dict[int, str] = {
    0xA3: "ctrl",  # VK_RCONTROL
    0xA5: "alt",  # VK_RMENU
}


def _build_vk_to_token() -> dict[int, str]:
    mapping = {vk: token for token, (vk, _ext) in _HOLD_KEY_CODES.items()}
    mapping.update(_EXTRA_VK_TO_TOKEN)
    return mapping


_VK_TO_TOKEN = _build_vk_to_token()


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelKeyboardProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = ctypes.c_long
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.MsgWaitForMultipleObjects.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.BOOL,
    wintypes.DWORD,
    wintypes.DWORD,
]
user32.MsgWaitForMultipleObjects.restype = wintypes.DWORD
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL


class KeyBreakMonitor:
    """Watch physical key-downs for a set of logical hold tokens."""

    def __init__(self, on_key: Callable[[str], None]) -> None:
        self._on_key = on_key
        self._tokens: set[str] = set()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._pending: queue.Queue[str] = queue.Queue()
        self._hook: int | None = None
        # Keep a strong reference so ctypes does not GC the callback.
        self._proc = LowLevelKeyboardProc(self._low_level_proc)

    def ignore_injected(self, token: str) -> None:
        """No-op on Windows: injected events are filtered by LLKHF_INJECTED."""
        del token

    def set_tokens(self, tokens: Iterable[str]) -> None:
        with self._lock:
            self._tokens = set(tokens)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._tokens.clear()
        thread = self._thread
        if thread is not None:
            # Pump wakes at least every _POLL_MS; allow a little headroom.
            thread.join(timeout=(_POLL_MS / 1000.0) + 1.0)
        self._thread = None
        while True:
            try:
                self._pending.get_nowait()
            except queue.Empty:
                break

    def _low_level_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
            kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if not (kb.flags & LLKHF_INJECTED):
                token = _VK_TO_TOKEN.get(int(kb.vkCode))
                if token is not None:
                    with self._lock:
                        watching = token in self._tokens
                    if watching:
                        # Defer work out of the hook to avoid re-entrancy with SendInput.
                        self._pending.put(token)
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    def _drain_pending(self) -> None:
        seen: set[str] = set()
        while True:
            try:
                token = self._pending.get_nowait()
            except queue.Empty:
                break
            if token in seen:
                continue
            seen.add(token)
            self._on_key(token)

    def _message_loop(self) -> None:
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            return
        try:
            msg = wintypes.MSG()
            while not self._stop.is_set():
                # Timed wait so stop() never depends on posting WM_QUIT to a
                # thread id that may not be published yet.
                user32.MsgWaitForMultipleObjects(0, None, False, _POLL_MS, QS_ALLINPUT)
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                # LL hook callbacks run during PeekMessage; drain afterward.
                self._drain_pending()
        finally:
            if self._hook:
                user32.UnhookWindowsHookEx(self._hook)
                self._hook = None
