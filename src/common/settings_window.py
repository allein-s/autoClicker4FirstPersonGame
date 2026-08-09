"""Settings dialog: hotkey capture, schedule folder, overlay, language and misc options."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .. import i18n
from . import paths
from ..i18n import t
from .settings import AppSettings
from .vk_map import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, hotkey_label, vk_from_keysym

_MOD_KEYSYM_MAP = {
    "Control_L": MOD_CONTROL,
    "Control_R": MOD_CONTROL,
    "Shift_L": MOD_SHIFT,
    "Shift_R": MOD_SHIFT,
    "Alt_L": MOD_ALT,
    "Alt_R": MOD_ALT,
    "Win_L": MOD_WIN,
    "Win_R": MOD_WIN,
    "Super_L": MOD_WIN,
    "Super_R": MOD_WIN,
}


class SettingsWindow:
    def __init__(
        self,
        parent: tk.Tk,
        settings: AppSettings,
        on_save: Callable[[AppSettings], None],
    ) -> None:
        self._parent = parent
        self._on_save = on_save
        self._settings = settings
        self._pending_vk = settings.hotkey_vk
        self._pending_mods = settings.hotkey_mods
        self._pending_hold_vk = settings.hold_hotkey_vk
        self._pending_hold_mods = settings.hold_hotkey_mods
        self._mod_flags = 0
        self._capture_target: str | None = None  # "click" | "hold" | None

        self.win = tk.Toplevel(parent)
        self.win.title(t("settings.title"))
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)

        pad = {"padx": 12, "pady": 6}

        # --- Hotkey ---
        hk_frame = ttk.LabelFrame(self.win, text=t("settings.hotkey.frame"), padding=10)
        hk_frame.pack(fill=tk.X, **pad)

        row = ttk.Frame(hk_frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text=t("settings.hotkey.current")).pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar(value=hotkey_label(self._pending_vk, self._pending_mods))
        self.hotkey_display = ttk.Label(
            row, textvariable=self.hotkey_var, font=("Segoe UI", 10, "bold")
        )
        self.hotkey_display.pack(side=tk.LEFT, padx=(6, 12))
        self._change_label = t("settings.hotkey.change")
        self.capture_btn = ttk.Button(
            row, text=self._change_label, command=lambda: self._start_capture("click")
        )
        self.capture_btn.pack(side=tk.LEFT)

        ttk.Label(
            hk_frame,
            text=t("settings.hotkey.hint"),
            foreground="#666",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(6, 0))

        # --- Key-hold ---
        hold_frame = ttk.LabelFrame(self.win, text=t("settings.hold.frame"), padding=10)
        hold_frame.pack(fill=tk.X, **pad)

        hold_hk_row = ttk.Frame(hold_frame)
        hold_hk_row.pack(fill=tk.X)
        ttk.Label(hold_hk_row, text=t("settings.hold.hotkey_label")).pack(side=tk.LEFT)
        self.hold_hotkey_var = tk.StringVar(
            value=hotkey_label(self._pending_hold_vk, self._pending_hold_mods)
        )
        ttk.Label(
            hold_hk_row, textvariable=self.hold_hotkey_var, font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(6, 12))
        self.hold_capture_btn = ttk.Button(
            hold_hk_row, text=self._change_label, command=lambda: self._start_capture("hold")
        )
        self.hold_capture_btn.pack(side=tk.LEFT)

        self.hold_minimize_var = tk.BooleanVar(value=settings.minimize_on_hold_run)
        ttk.Checkbutton(
            hold_frame,
            text=t("settings.hold.minimize_on_run"),
            variable=self.hold_minimize_var,
        ).pack(anchor=tk.W, pady=(8, 0))

        self.hold_repeat_var = tk.BooleanVar(value=settings.hold_repeat)
        ttk.Checkbutton(
            hold_frame,
            text=t("settings.hold.repeat"),
            variable=self.hold_repeat_var,
        ).pack(anchor=tk.W, pady=(8, 0))

        repeat_row = ttk.Frame(hold_frame)
        repeat_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(repeat_row, text=t("settings.hold.repeat_interval")).pack(side=tk.LEFT)
        self.hold_interval_var = tk.StringVar(value=str(settings.hold_repeat_interval_ms))
        ttk.Spinbox(
            repeat_row, from_=1, to=1000, textvariable=self.hold_interval_var, width=6
        ).pack(side=tk.LEFT, padx=(8, 0))

        # --- Schedule folder ---
        dir_frame = ttk.LabelFrame(self.win, text=t("settings.folder.frame"), padding=10)
        dir_frame.pack(fill=tk.X, **pad)

        dir_row = ttk.Frame(dir_frame)
        dir_row.pack(fill=tk.X)
        self.schedule_dir_var = tk.StringVar(value=settings.schedule_dir)
        ttk.Entry(dir_row, textvariable=self.schedule_dir_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(dir_row, text=t("settings.folder.browse"), command=self._browse_dir).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # --- Overlay ---
        overlay_frame = ttk.LabelFrame(self.win, text=t("settings.overlay.frame"), padding=10)
        overlay_frame.pack(fill=tk.X, **pad)
        self.show_overlay_var = tk.BooleanVar(value=settings.show_overlay)
        ttk.Checkbutton(
            overlay_frame,
            text=t("settings.overlay.checkbox"),
            variable=self.show_overlay_var,
        ).pack(anchor=tk.W)

        # --- Behavior ---
        behavior_frame = ttk.LabelFrame(self.win, text=t("settings.behavior.frame"), padding=10)
        behavior_frame.pack(fill=tk.X, **pad)

        self.minimize_var = tk.BooleanVar(value=settings.minimize_on_run)
        ttk.Checkbutton(
            behavior_frame,
            text=t("settings.behavior.minimize_on_run"),
            variable=self.minimize_var,
        ).pack(anchor=tk.W)

        self.topmost_var = tk.BooleanVar(value=settings.main_window_topmost)
        ttk.Checkbutton(
            behavior_frame,
            text=t("settings.behavior.topmost"),
            variable=self.topmost_var,
        ).pack(anchor=tk.W)

        self.auto_load_var = tk.BooleanVar(value=settings.auto_load_last_schedule)
        ttk.Checkbutton(
            behavior_frame,
            text=t("settings.behavior.auto_load"),
            variable=self.auto_load_var,
        ).pack(anchor=tk.W)

        self.startup_var = tk.BooleanVar(value=settings.start_with_windows)
        ttk.Checkbutton(
            behavior_frame,
            text=t("settings.behavior.start_with_windows"),
            variable=self.startup_var,
        ).pack(anchor=tk.W)

        hold_row = ttk.Frame(behavior_frame)
        hold_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(hold_row, text=t("settings.behavior.click_hold_ms")).pack(side=tk.LEFT)
        self.hold_ms_var = tk.StringVar(value=str(settings.click_hold_ms))
        ttk.Spinbox(hold_row, from_=1, to=200, textvariable=self.hold_ms_var, width=6).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # --- Language ---
        lang_frame = ttk.LabelFrame(self.win, text=t("settings.language.frame"), padding=10)
        lang_frame.pack(fill=tk.X, **pad)
        lang_row = ttk.Frame(lang_frame)
        lang_row.pack(fill=tk.X)
        ttk.Label(lang_row, text=t("settings.language.label")).pack(side=tk.LEFT)
        self._lang_codes = i18n.available_languages()
        self._lang_names = [i18n.LANGUAGE_NAMES.get(code, code) for code in self._lang_codes]
        current_name = i18n.LANGUAGE_NAMES.get(settings.language, settings.language)
        self.language_var = tk.StringVar(value=current_name)
        ttk.Combobox(
            lang_row,
            textvariable=self.language_var,
            values=self._lang_names,
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(
            lang_frame,
            text=t("settings.language.restart_note"),
            foreground="#666",
        ).pack(anchor=tk.W, pady=(6, 0))

        # --- Buttons ---
        btn_row = ttk.Frame(self.win, padding=(12, 6, 12, 12))
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text=t("settings.buttons.save"), command=self._save).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text=t("settings.buttons.cancel"), command=self._cancel).pack(
            side=tk.RIGHT, padx=(0, 8)
        )

        self.win.bind("<KeyPress>", self._on_capture_keypress)
        self.win.bind("<KeyRelease>", self._on_capture_keyrelease)
        self.win.focus_set()

    # --- Hotkey capture ---
    def _capture_button(self, target: str) -> ttk.Button:
        return self.hold_capture_btn if target == "hold" else self.capture_btn

    def _start_capture(self, target: str) -> None:
        # Reset any button that might have been left in the "capturing" state.
        self.capture_btn.config(text=self._change_label)
        self.hold_capture_btn.config(text=self._change_label)
        self._capture_target = target
        self._mod_flags = 0
        self._capture_button(target).config(text=t("settings.hotkey.capture_prompt"))
        self.win.focus_set()

    def _on_capture_keyrelease(self, event: tk.Event) -> None:
        if self._capture_target is None:
            return
        if event.keysym in _MOD_KEYSYM_MAP:
            self._mod_flags &= ~_MOD_KEYSYM_MAP[event.keysym]

    def _on_capture_keypress(self, event: tk.Event) -> None:
        target = self._capture_target
        if target is None:
            return
        keysym = event.keysym
        if keysym in _MOD_KEYSYM_MAP:
            self._mod_flags |= _MOD_KEYSYM_MAP[keysym]
            return
        if keysym == "Escape":
            self._capture_target = None
            self._capture_button(target).config(text=self._change_label)
            return
        vk = vk_from_keysym(keysym)
        if vk is None:
            messagebox.showwarning(
                t("dialog.hotkey.title"), t("dialog.hotkey.unsupported_key", key=keysym)
            )
            return
        if target == "hold":
            self._pending_hold_vk = vk
            self._pending_hold_mods = self._mod_flags
            self.hold_hotkey_var.set(hotkey_label(vk, self._mod_flags))
        else:
            self._pending_vk = vk
            self._pending_mods = self._mod_flags
            self.hotkey_var.set(hotkey_label(vk, self._mod_flags))
        self._capture_target = None
        self._capture_button(target).config(text=self._change_label)

    # --- Folder ---
    def _browse_dir(self) -> None:
        current = self.schedule_dir_var.get()
        initial = str(paths.resolve_path(current)) if current else str(paths.base_dir())
        selected = filedialog.askdirectory(
            title=t("settings.folder.select_title"), initialdir=initial
        )
        if selected:
            portable = paths.to_portable_string(Path(selected))
            self.schedule_dir_var.set(portable)

    # --- Save / cancel ---
    def _save(self) -> None:
        try:
            hold_ms = int(self.hold_ms_var.get())
            if hold_ms < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(t("settings.error.input_title"), t("settings.error.hold_ms"))
            return

        try:
            repeat_interval = int(self.hold_interval_var.get())
            if repeat_interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                t("settings.error.input_title"), t("settings.error.repeat_interval")
            )
            return

        schedule_dir = self.schedule_dir_var.get().strip()
        if not schedule_dir:
            messagebox.showwarning(
                t("settings.error.input_title"), t("settings.error.folder_required")
            )
            return
        try:
            paths.resolve_path(schedule_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                t("settings.error.folder_create_title"),
                t("settings.error.folder_create", error=exc),
            )
            return

        selected_name = self.language_var.get()
        language = next(
            (
                code
                for code, name in zip(self._lang_codes, self._lang_names)
                if name == selected_name
            ),
            i18n.DEFAULT_LANGUAGE,
        )

        new_settings = AppSettings(
            hotkey_vk=self._pending_vk,
            hotkey_mods=self._pending_mods,
            schedule_dir=schedule_dir,
            show_overlay=self.show_overlay_var.get(),
            click_hold_ms=hold_ms,
            minimize_on_run=self.minimize_var.get(),
            auto_load_last_schedule=self.auto_load_var.get(),
            last_schedule_path=None,  # preserved by caller from previous settings
            main_window_topmost=self.topmost_var.get(),
            start_with_windows=self.startup_var.get(),
            language=language,
            hold_hotkey_vk=self._pending_hold_vk,
            hold_hotkey_mods=self._pending_hold_mods,
            hold_keys=list(self._settings.hold_keys),  # managed in the key-hold tab
            hold_repeat=self.hold_repeat_var.get(),
            hold_repeat_interval_ms=repeat_interval,
            minimize_on_hold_run=self.hold_minimize_var.get(),
        )
        self._on_save(new_settings)
        self.win.destroy()

    def _cancel(self) -> None:
        self.win.destroy()
