"""Top-level app: hosts the two feature tabs (auto-click / key-hold), owns the
window, the running overlay, the status/hint bar and the two global hotkeys."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import i18n, platforms
from .autoclick.tab import AutoClickTab
from .common.overlay import RunningOverlay
from .common.settings import AppSettings, load_settings, save_settings
from .common.settings_window import SettingsWindow
from .common.vk_map import hotkey_label
from .i18n import t
from .keyhold.tab import KeyHoldTab
from .platforms import HotkeyService


class AutoClickerApp:
    def __init__(self) -> None:
        self._settings: AppSettings = load_settings()
        i18n.set_language(self._settings.language)

        self._hotkey: HotkeyService | None = None
        self._hold_hotkey: HotkeyService | None = None

        self.root = tk.Tk()
        self.root.title(t("app.title"))
        self.root.minsize(620, 420)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if self._settings.main_window_topmost:
            self.root.attributes("-topmost", True)

        self._overlay = RunningOverlay(self.root)

        self._build_ui()
        self._start_hotkey_listener()
        self.autoclick.maybe_auto_load()
        self._refresh_status()
        self.root.after(500, self._check_hotkey)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        topbar = ttk.Frame(self.root, padding=(12, 8, 12, 0))
        topbar.pack(fill=tk.X)
        ttk.Button(
            topbar, text=t("button.settings"), command=self._open_settings
        ).pack(side=tk.RIGHT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        autoclick_frame = ttk.Frame(notebook)
        notebook.add(autoclick_frame, text=t("tab.autoclick"))
        self.autoclick = AutoClickTab(
            self.root, autoclick_frame, self._settings, self._on_state_changed
        )

        keyhold_frame = ttk.Frame(notebook)
        notebook.add(keyhold_frame, text=t("tab.keyhold"))
        self.keyhold = KeyHoldTab(
            self.root, keyhold_frame, self._settings, self._on_state_changed
        )

        self.status_var = tk.StringVar()
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            padding=(12, 0, 12, 10),
            anchor=tk.W,
        ).pack(fill=tk.X)

        self.hint_var = tk.StringVar()
        ttk.Label(
            self.root,
            textvariable=self.hint_var,
            padding=(12, 0, 12, 8),
            foreground="#555",
        ).pack(fill=tk.X)
        self._refresh_hint()

    # ------------------------------------------------------------------
    # Shared status / overlay
    # ------------------------------------------------------------------
    def _click_hotkey_label(self) -> str:
        return hotkey_label(self._settings.hotkey_vk, self._settings.hotkey_mods)

    def _hold_hotkey_label(self) -> str:
        return hotkey_label(self._settings.hold_hotkey_vk, self._settings.hold_hotkey_mods)

    def _refresh_hint(self) -> None:
        self.hint_var.set(
            t(
                "hint.format",
                click_hotkey=self._click_hotkey_label(),
                hold_hotkey=self._hold_hotkey_label(),
            )
        )

    def _refresh_status(self) -> None:
        click = t("status.running") if self.autoclick.running else t("status.stopped")
        hold = t("status.running") if self.keyhold.active else t("status.stopped")
        self.status_var.set(
            t("status.format", click=click, hold=hold, count=self.autoclick.task_count)
        )

    def _on_state_changed(self) -> None:
        self._refresh_status()
        self._update_overlay()

    def _update_overlay(self) -> None:
        if not self._settings.show_overlay:
            self._overlay.hide()
            return
        items: list[tuple[str, str]] = []
        if self.autoclick.running:
            items.append((t("overlay.autoclick"), self._click_hotkey_label()))
        if self.keyhold.active:
            items.append((t("overlay.keyhold"), self._hold_hotkey_label()))
        self._overlay.set_items(items)

    # ------------------------------------------------------------------
    # Hotkeys
    # ------------------------------------------------------------------
    def _on_click_hotkey(self) -> None:
        self.root.after(0, self._toggle_click)

    def _on_hold_hotkey(self) -> None:
        self.root.after(0, self._toggle_hold)

    def _toggle_click(self) -> None:
        if self.autoclick.running:
            self.autoclick.stop()
            self._restore_window()
        elif self.autoclick.start() and self._settings.minimize_on_run:
            self.root.iconify()

    def _toggle_hold(self) -> None:
        if self.keyhold.active:
            self.keyhold.stop()
            self._restore_window()
        else:
            self.keyhold.start()
            if self.keyhold.active and self._settings.minimize_on_hold_run:
                self.root.iconify()

    def _restore_window(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            if not self._settings.main_window_topmost:
                self.root.after(100, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            pass

    def _check_hotkey(self) -> None:
        failed = (self._hotkey is not None and not self._hotkey.registered) or (
            self._hold_hotkey is not None and not self._hold_hotkey.registered
        )
        if failed:
            messagebox.showwarning(
                t("dialog.hotkey.title"), t("dialog.hotkey.register_failed")
            )

    def _start_hotkey_listener(self) -> None:
        self._hotkey = HotkeyService(
            self._settings.hotkey_vk, self._settings.hotkey_mods, self._on_click_hotkey
        )
        self._hotkey.start()
        self._hold_hotkey = HotkeyService(
            self._settings.hold_hotkey_vk,
            self._settings.hold_hotkey_mods,
            self._on_hold_hotkey,
        )
        self._hold_hotkey.start()

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        SettingsWindow(self.root, self._settings, self._apply_settings)

    def _apply_settings(self, new_settings: AppSettings) -> None:
        old = self._settings
        new_settings.last_schedule_path = old.last_schedule_path
        new_settings.hold_keys = old.hold_keys  # owned by the key-hold tab

        hotkey_changed = (
            new_settings.hotkey_vk != old.hotkey_vk
            or new_settings.hotkey_mods != old.hotkey_mods
        )
        hold_hotkey_changed = (
            new_settings.hold_hotkey_vk != old.hold_hotkey_vk
            or new_settings.hold_hotkey_mods != old.hold_hotkey_mods
        )
        repeat_changed = (
            new_settings.hold_repeat != old.hold_repeat
            or new_settings.hold_repeat_interval_ms != old.hold_repeat_interval_ms
        )
        dir_changed = new_settings.schedule_dir != old.schedule_dir
        startup_changed = new_settings.start_with_windows != old.start_with_windows
        topmost_changed = new_settings.main_window_topmost != old.main_window_topmost

        self._settings = new_settings
        save_settings(self._settings)
        self.autoclick.set_settings(new_settings)
        self.keyhold.set_settings(new_settings)
        self._refresh_hint()
        self.keyhold.refresh_hotkey_hint()

        if hotkey_changed and self._hotkey is not None:
            self._hotkey.set_hotkey(new_settings.hotkey_vk, new_settings.hotkey_mods)
            self.root.after(300, self._check_hotkey)

        if hold_hotkey_changed and self._hold_hotkey is not None:
            self._hold_hotkey.set_hotkey(
                new_settings.hold_hotkey_vk, new_settings.hold_hotkey_mods
            )
            self.root.after(300, self._check_hotkey)

        if repeat_changed:
            self.keyhold.restart_if_active()

        if dir_changed:
            self.autoclick.reload_schedule_dir()

        if topmost_changed:
            try:
                self.root.attributes("-topmost", new_settings.main_window_topmost)
            except tk.TclError:
                pass

        if startup_changed:
            try:
                platforms.set_registered(new_settings.start_with_windows)
            except OSError as exc:
                messagebox.showerror(
                    t("settings.error.startup_title"),
                    t("settings.error.startup", error=exc),
                )

        self._update_overlay()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _on_close(self) -> None:
        self.autoclick.shutdown()
        self.keyhold.shutdown()  # release any held keys
        if self._hotkey is not None:
            self._hotkey.stop()
        if self._hold_hotkey is not None:
            self._hold_hotkey.stop()
        self._overlay.destroy()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    AutoClickerApp().run()
