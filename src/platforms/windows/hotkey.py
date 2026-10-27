"""Global configurable hotkey via RegisterHotKey (works while games capture keyboard)."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

from ...common.vk_map import hotkey_modifier_variants

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostThreadMessageW.restype = wintypes.BOOL

WM_QUIT = 0x0012
WM_HOTKEY = 0x0312
WM_APP = 0x8000
WM_SET_HOTKEY = WM_APP + 1
WM_SET_EXTRA_MODS = WM_APP + 2
PM_NOREMOVE = 0x0000

MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0xAC01
# IDs for the modifier variants registered while keys are held down.
VARIANT_ID_BASE = HOTKEY_ID + 1


class HotkeyService:
    def __init__(self, vk: int, mods: int, on_trigger: Callable[[], None]) -> None:
        self._vk = vk
        self._mods = mods
        self._on_trigger = on_trigger
        self._thread: threading.Thread | None = None
        self._win_thread_id: int | None = None
        self._stop = threading.Event()
        self._registered = False
        self._extra_mods = 0
        self._variant_count = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        tid = self._win_thread_id
        if tid:
            user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)

    def set_hotkey(self, vk: int, mods: int) -> None:
        """Request the hotkey thread to re-register with a new key/modifiers."""
        tid = self._win_thread_id
        if tid:
            user32.PostThreadMessageW(tid, WM_SET_HOTKEY, vk, mods)
        else:
            self._vk = vk
            self._mods = mods

    def set_extra_modifiers(self, mods: int) -> None:
        """Also fire while these modifiers are held down (e.g. Ctrl held by key-hold)."""
        self._extra_mods = mods
        tid = self._win_thread_id
        if tid:
            user32.PostThreadMessageW(tid, WM_SET_EXTRA_MODS, 0, 0)

    @property
    def registered(self) -> bool:
        return self._registered

    @property
    def current(self) -> tuple[int, int]:
        return self._vk, self._mods

    def _register(self, vk: int, mods: int) -> bool:
        ok = bool(user32.RegisterHotKey(None, HOTKEY_ID, mods | MOD_NOREPEAT, vk))
        if ok:
            self._vk = vk
            self._mods = mods
        return ok

    def _unregister_variants(self) -> None:
        for i in range(self._variant_count):
            user32.UnregisterHotKey(None, VARIANT_ID_BASE + i)
        self._variant_count = 0

    def _register_variants(self) -> None:
        self._unregister_variants()
        variants = hotkey_modifier_variants(self._mods, self._extra_mods)
        for i, mods in enumerate(variants):
            # Best effort: a variant taken by another app must not affect the base hotkey.
            user32.RegisterHotKey(None, VARIANT_ID_BASE + i, mods | MOD_NOREPEAT, self._vk)
        self._variant_count = len(variants)

    def _message_loop(self) -> None:
        msg = wintypes.MSG()
        # Create this thread's message queue before publishing its id, so posts
        # made right after start() are not dropped.
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)
        self._win_thread_id = kernel32.GetCurrentThreadId()
        self._registered = self._register(self._vk, self._mods)
        self._register_variants()
        try:
            while not self._stop.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break
                if msg.message == WM_HOTKEY and (
                    HOTKEY_ID <= msg.wParam < VARIANT_ID_BASE + self._variant_count
                ):
                    self._on_trigger()
                elif msg.message == WM_SET_HOTKEY:
                    new_vk = int(msg.wParam)
                    new_mods = int(msg.lParam)
                    user32.UnregisterHotKey(None, HOTKEY_ID)
                    self._registered = self._register(new_vk, new_mods)
                    self._register_variants()
                elif msg.message == WM_SET_EXTRA_MODS:
                    self._register_variants()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self._unregister_variants()
            self._registered = False
