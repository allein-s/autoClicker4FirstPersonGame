"""Small always-on-top indicator shown at the bottom-right of the work area
(above the Windows taskbar) while the schedule is running."""

from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes

from .i18n import t

user32 = ctypes.windll.user32

SPI_GETWORKAREA = 0x0030


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def _work_area() -> tuple[int, int, int, int]:
    rect = _RECT()
    if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, 800, 600


class RunningOverlay:
    MARGIN = 12

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._win: tk.Toplevel | None = None
        self._label: tk.Label | None = None

    def _build(self) -> None:
        if self._win is not None:
            return
        win = tk.Toplevel(self._root)
        self._win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.88)
        except tk.TclError:
            pass
        win.configure(bg="#1e8e3e")

        self._label = tk.Label(
            win,
            bg="#1e8e3e",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
        )
        self._label.pack()
        win.withdraw()

    def _position(self) -> None:
        if self._win is None:
            return
        self._win.update_idletasks()
        _, _, right, bottom = _work_area()
        width = self._win.winfo_width()
        height = self._win.winfo_height()
        x = right - width - self.MARGIN
        y = bottom - height - self.MARGIN
        self._win.geometry(f"+{x}+{y}")

    def show(self, hotkey_label: str) -> None:
        self._build()
        assert self._win is not None
        assert self._label is not None
        self._label.config(text=t("overlay.running_text", hotkey=hotkey_label))
        self._win.deiconify()
        self._position()
        self._win.lift()

    def hide(self) -> None:
        if self._win is not None:
            self._win.withdraw()

    def destroy(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None
