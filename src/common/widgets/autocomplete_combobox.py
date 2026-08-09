"""ttk.Combobox with typeable text + prefix-match autocomplete suggestions."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

_IGNORED_KEYSYMS = {
    "Up",
    "Down",
    "Left",
    "Right",
    "Return",
    "KP_Enter",
    "Escape",
    "Tab",
    "Shift_L",
    "Shift_R",
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
}


class AutocompleteCombobox(ttk.Combobox):
    """Combobox that filters its dropdown values by prefix as the user types."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._all_values: list[str] = []
        self.bind("<KeyRelease>", self._on_keyrelease)

    def set_completion_list(self, values: list[str]) -> None:
        self._all_values = list(values)
        self["values"] = self._all_values

    def _on_keyrelease(self, event: tk.Event) -> None:
        if event.keysym in _IGNORED_KEYSYMS:
            return
        typed = self.get()
        if not typed:
            matches = self._all_values
        else:
            needle = typed.lower()
            matches = [v for v in self._all_values if v.lower().startswith(needle)]
        self["values"] = matches if matches else self._all_values
        if matches and typed:
            try:
                self.tk.call("ttk::combobox::Post", self)
                self.focus_set()
            except tk.TclError:
                pass
            self.icursor(tk.END)
