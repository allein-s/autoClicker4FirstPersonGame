"""Small always-on-top indicator shown at the bottom-right of the work area
(above the Windows taskbar) while a feature is running. It lists every active
feature (auto-click / key-hold) with its hotkey so the state is unambiguous."""

from __future__ import annotations

import tkinter as tk

from ..platforms import work_area


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
        _, _, right, bottom = work_area()
        width = self._win.winfo_width()
        height = self._win.winfo_height()
        x = right - width - self.MARGIN
        y = bottom - height - self.MARGIN
        self._win.geometry(f"+{x}+{y}")

    def set_items(self, items: list[tuple[str, str]]) -> None:
        """Show one line per active feature, or hide when nothing is active.

        Each item is a ``(name, hotkey_label)`` pair.
        """
        if not items:
            self.hide()
            return
        self._build()
        assert self._win is not None
        assert self._label is not None
        text = "\n".join(f"\u25cf {name}  ({hotkey})" for name, hotkey in items)
        self._label.config(text=text)
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
