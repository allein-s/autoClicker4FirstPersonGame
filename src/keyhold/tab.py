"""Key-hold tab: pick keys to hold down and toggle them.

Window minimize/restore, the running overlay and the global hotkey are owned
by the top-level app; this tab only reports state changes via a callback.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..common.settings import AppSettings, save_settings
from ..common.vk_map import hotkey_label
from ..i18n import t
from .controller import HOLDABLE_KEYS, KeyHoldController, resolve_tokens


class KeyHoldTab:
    def __init__(
        self,
        root: tk.Tk,
        parent: ttk.Frame,
        settings: AppSettings,
        on_state_changed: Callable[[], None],
    ) -> None:
        self._root = root
        self._settings = settings
        self._on_state_changed = on_state_changed
        self._controller = KeyHoldController(on_changed=self._on_hold_changed)
        self._key_vars: dict[str, tk.BooleanVar] = {}
        self._build(parent)

    # ------------------------------------------------------------------
    # Public API used by the app
    # ------------------------------------------------------------------
    @property
    def active(self) -> bool:
        return self._controller.active

    @property
    def held_labels(self) -> list[str]:
        return self._controller.held_labels

    def set_settings(self, settings: AppSettings) -> None:
        self._settings = settings
        self.hold_repeat_var.set(settings.hold_repeat)
        self.hold_interval_var.set(str(settings.hold_repeat_interval_ms))

    def start(self, notify_empty: bool = True) -> None:
        keys = resolve_tokens(self._selected_tokens())
        if not keys:
            if notify_empty:
                messagebox.showinfo(t("keyhold.no_keys_title"), t("keyhold.no_keys"))
            return
        self._controller.start(
            keys, self._settings.hold_repeat, self._settings.hold_repeat_interval_ms
        )
        self._refresh_status()
        self._on_state_changed()

    def stop(self) -> None:
        self._controller.stop()
        self._refresh_status()
        self._on_state_changed()

    def toggle(self) -> None:
        if self._controller.active:
            self.stop()
        else:
            self.start()

    def restart_if_active(self) -> None:
        if self._controller.active:
            self._controller.stop()
            self.start(notify_empty=False)

    def refresh_hotkey_hint(self) -> None:
        self.hint_var.set(t("keyhold.hint", hotkey=self._hold_hotkey_label()))

    def shutdown(self) -> None:
        self._controller.stop()

    def _on_hold_changed(self) -> None:
        # KeyBreakMonitor callbacks may arrive off the Tk thread.
        self._root.after(0, self._apply_hold_changed)

    def _apply_hold_changed(self) -> None:
        self._refresh_status()
        self._on_state_changed()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build(self, parent: ttk.Frame) -> None:
        outer = ttk.Frame(parent, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        self.hint_var = tk.StringVar()
        ttk.Label(outer, textvariable=self.hint_var, foreground="#555").pack(
            anchor=tk.W, pady=(0, 8)
        )

        keys_frame = ttk.LabelFrame(outer, text=t("keyhold.keys_frame"), padding=10)
        keys_frame.pack(fill=tk.X)

        enabled = set(self._settings.hold_keys)
        columns = 4
        for index, key in enumerate(HOLDABLE_KEYS):
            var = tk.BooleanVar(value=key.token in enabled)
            self._key_vars[key.token] = var
            ttk.Checkbutton(
                keys_frame,
                text=key.label,
                variable=var,
                command=self._on_keys_changed,
            ).grid(
                row=index // columns,
                column=index % columns,
                sticky=tk.W,
                padx=6,
                pady=4,
            )

        self.hold_repeat_var = tk.BooleanVar(value=self._settings.hold_repeat)
        ttk.Checkbutton(
            outer,
            text=t("keyhold.repeat"),
            variable=self.hold_repeat_var,
            command=self._on_repeat_toggled,
        ).pack(anchor=tk.W, pady=(12, 0))

        repeat_row = ttk.Frame(outer)
        repeat_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(repeat_row, text=t("keyhold.repeat_interval")).pack(side=tk.LEFT)
        self.hold_interval_var = tk.StringVar(value=str(self._settings.hold_repeat_interval_ms))
        interval_spin = ttk.Spinbox(
            repeat_row,
            from_=1,
            to=1000,
            textvariable=self.hold_interval_var,
            width=6,
        )
        interval_spin.pack(side=tk.LEFT, padx=(8, 0))
        interval_spin.bind("<FocusOut>", self._on_interval_commit)
        interval_spin.bind("<Return>", self._on_interval_commit)

        ttk.Label(
            outer,
            text=t("keyhold.note"),
            foreground="#666",
            wraplength=440,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 8))

        self.status_var = tk.StringVar()
        ttk.Label(outer, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W
        )

        ttk.Button(outer, text=t("keyhold.toggle"), command=self.toggle).pack(
            anchor=tk.W, pady=(10, 0)
        )

        self.refresh_hotkey_hint()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _hold_hotkey_label(self) -> str:
        return hotkey_label(self._settings.hold_hotkey_vk, self._settings.hold_hotkey_mods)

    def _selected_tokens(self) -> list[str]:
        return [token for token, var in self._key_vars.items() if var.get()]

    def _on_keys_changed(self) -> None:
        self._settings.hold_keys = self._selected_tokens()
        save_settings(self._settings)
        # Re-apply immediately if currently holding so changes take effect.
        self.restart_if_active()
        self._refresh_status()

    def _on_repeat_toggled(self) -> None:
        self._settings.hold_repeat = self.hold_repeat_var.get()
        save_settings(self._settings)
        self.restart_if_active()

    def _on_interval_commit(self, _event: object | None = None) -> None:
        try:
            interval = int(self.hold_interval_var.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                t("keyhold.repeat_error_title"), t("keyhold.repeat_interval_error")
            )
            self.hold_interval_var.set(str(self._settings.hold_repeat_interval_ms))
            return
        if interval == self._settings.hold_repeat_interval_ms:
            return
        self._settings.hold_repeat_interval_ms = interval
        save_settings(self._settings)
        self.restart_if_active()

    def _refresh_status(self) -> None:
        if self._controller.active:
            keys = ", ".join(self._controller.held_labels)
            self.status_var.set(t("keyhold.status_active", keys=keys))
        else:
            self.status_var.set(t("keyhold.status_idle"))
