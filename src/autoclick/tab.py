"""Auto-click tab: build the schedule UI and run the clicking loop.

Window minimize/restore, the running overlay and the global hotkey are owned
by the top-level app; this tab only reports state changes via a callback.
"""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from ..common import paths
from ..common.settings import AppSettings, save_settings
from ..platforms import game_left_click
from ..common.widgets.autocomplete_combobox import AutocompleteCombobox
from ..i18n import t
from .scheduling import DEFAULT_SUFFIX, ScheduleTask, load_tasks, save_tasks


class AutoClickTab:
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

        self._tasks: list[ScheduleTask] = []
        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._schedule_menu: tk.Menu | None = None

        self._ensure_schedule_dir()
        self._build(parent)
        self._refresh_schedule_files()

    # ------------------------------------------------------------------
    # Public API used by the app
    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._running

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def set_settings(self, settings: AppSettings) -> None:
        self._settings = settings

    def reload_schedule_dir(self) -> None:
        self._ensure_schedule_dir()
        self._refresh_schedule_files()

    def start(self) -> bool:
        if not self._tasks:
            messagebox.showinfo(t("dialog.schedule.title"), t("dialog.schedule.empty"))
            return False
        if self._running:
            return False
        self._running = True
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()
        self._on_state_changed()
        return True

    def stop(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        self._on_state_changed()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._running = False

    def maybe_auto_load(self) -> None:
        if not self._settings.auto_load_last_schedule:
            return
        path = self._settings.last_schedule_file()
        if path is None or not path.exists():
            return
        try:
            self._tasks = load_tasks(path)
            self._refresh_schedule_list()
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build(self, parent: ttk.Frame) -> None:
        main = ttk.Frame(parent, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(main, text=t("panel.operations"), padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        click_btn = ttk.Button(left, text=t("button.click"), width=18, command=self._add_click)
        click_btn.pack(pady=(0, 8))
        click_btn.bind("<Button-3>", lambda e: self._add_click())

        interval_row = ttk.Frame(left)
        interval_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(interval_row, text=t("label.interval_ms")).pack(anchor=tk.W)
        self.interval_var = tk.StringVar(value="200")
        ttk.Entry(interval_row, textvariable=self.interval_var, width=20).pack(
            fill=tk.X, pady=(4, 0)
        )
        interval_btn = ttk.Button(
            left, text=t("button.interval"), width=18, command=self._add_interval
        )
        interval_btn.pack(pady=(0, 8))
        interval_btn.bind("<Button-3>", lambda e: self._add_interval())

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Button(
            left, text=t("button.remove_selected"), width=18, command=self._remove_selected
        ).pack(pady=(0, 4))
        ttk.Button(
            left, text=t("button.clear_schedule"), width=18, command=self._clear_schedule
        ).pack(pady=(0, 8))

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Button(left, text=t("button.save"), width=18, command=self._save_schedule).pack(
            pady=(0, 8)
        )

        load_box_frame = ttk.Frame(left)
        load_box_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(load_box_frame, text=t("label.saved_schedules")).pack(anchor=tk.W)
        self.schedule_pick_var = tk.StringVar()
        self.schedule_combo = AutocompleteCombobox(
            load_box_frame, textvariable=self.schedule_pick_var, width=18
        )
        self.schedule_combo.pack(fill=tk.X, pady=(4, 4))
        ttk.Button(
            left, text=t("button.load_selected"), width=18, command=self._load_from_combo
        ).pack(pady=(0, 8))

        right = ttk.LabelFrame(main, text=t("panel.schedule"), padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(
            right,
            text=t("label.schedule_hint"),
            foreground="#555",
        ).pack(anchor=tk.W, pady=(0, 6))

        list_frame = ttk.Frame(right)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.schedule_list = tk.Listbox(
            list_frame,
            yscrollcommand=scroll.set,
            font=("Segoe UI", 10),
            activestyle="dotbox",
        )
        self.schedule_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.schedule_list.yview)

        self._schedule_menu = tk.Menu(self._root, tearoff=0)
        self._schedule_menu.add_command(label=t("menu.add_click"), command=self._add_click)
        self._schedule_menu.add_command(label=t("menu.add_interval"), command=self._add_interval)
        self._schedule_menu.add_separator()
        self._schedule_menu.add_command(
            label=t("menu.remove_selected"), command=self._remove_selected
        )

        self.schedule_list.bind("<Button-3>", self._on_schedule_right_click)

    # ------------------------------------------------------------------
    # Paths / schedule helpers
    # ------------------------------------------------------------------
    def _ensure_schedule_dir(self) -> None:
        try:
            self._settings.schedule_dir_path().mkdir(parents=True, exist_ok=True)
        except OSError:
            self._settings.schedule_dir = paths.DEFAULT_SCHEDULE_DIRNAME
            self._settings.schedule_dir_path().mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Schedule list editing
    # ------------------------------------------------------------------
    def _insert_index(self) -> int:
        sel = self.schedule_list.curselection()
        if sel:
            return sel[0] + 1
        return len(self._tasks)

    def _insert_task(self, task: ScheduleTask) -> None:
        index = self._insert_index()
        self._tasks.insert(index, task)
        self._refresh_schedule_list(select_index=index)

    def _on_schedule_right_click(self, event: tk.Event) -> None:
        if self._schedule_menu is None:
            return
        index = self.schedule_list.nearest(event.y)
        if 0 <= index < self.schedule_list.size():
            self.schedule_list.selection_clear(0, tk.END)
            self.schedule_list.selection_set(index)
            self.schedule_list.activate(index)
        try:
            self._schedule_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._schedule_menu.grab_release()

    def _parse_interval_ms(self) -> int | None:
        raw = self.interval_var.get().strip()
        if not raw:
            messagebox.showwarning(
                t("dialog.input_error.title"), t("dialog.input_error.interval_required")
            )
            return None
        try:
            ms = int(raw)
        except ValueError:
            messagebox.showwarning(
                t("dialog.input_error.title"), t("dialog.input_error.interval_integer")
            )
            return None
        if ms < 0:
            messagebox.showwarning(
                t("dialog.input_error.title"), t("dialog.input_error.interval_nonnegative")
            )
            return None
        return ms

    def _add_click(self) -> None:
        self._insert_task(ScheduleTask(kind="click"))

    def _add_interval(self) -> None:
        ms = self._parse_interval_ms()
        if ms is None:
            return
        self._insert_task(ScheduleTask(kind="interval", ms=ms))

    def _remove_selected(self) -> None:
        sel = self.schedule_list.curselection()
        if not sel:
            return
        index = sel[0]
        if 0 <= index < len(self._tasks):
            del self._tasks[index]
            self._refresh_schedule_list()

    def _clear_schedule(self) -> None:
        if not self._tasks:
            return
        if messagebox.askyesno(t("dialog.confirm.title"), t("dialog.confirm.clear_schedule")):
            self._tasks.clear()
            self._refresh_schedule_list()

    def _ensure_not_running(self) -> bool:
        if self._running:
            messagebox.showwarning(t("dialog.running.title"), t("dialog.running.cannot_edit"))
            return False
        return True

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------
    def _refresh_schedule_files(self) -> None:
        directory = self._settings.schedule_dir_path()
        names: list[str] = []
        if directory.is_dir():
            names = sorted(p.stem for p in directory.glob(f"*{DEFAULT_SUFFIX}"))
        self.schedule_combo.set_completion_list(names)

    def _save_schedule(self) -> None:
        if not self._ensure_not_running():
            return
        directory = self._settings.schedule_dir_path()
        path = filedialog.asksaveasfilename(
            title=t("dialog.save.title"),
            defaultextension=DEFAULT_SUFFIX,
            initialdir=str(directory),
            filetypes=[
                (t("dialog.save.filetype"), f"*{DEFAULT_SUFFIX}"),
                (t("dialog.save.filetype_all"), "*.*"),
            ],
        )
        if not path:
            return
        try:
            save_tasks(Path(path), self._tasks)
            self._remember_last_schedule(Path(path))
            self._refresh_schedule_files()
            messagebox.showinfo(t("dialog.save.success_title"), t("dialog.save.success"))
        except OSError as exc:
            messagebox.showerror(t("dialog.save.error_title"), t("dialog.save.error", error=exc))

    def _load_from_combo(self) -> None:
        if not self._ensure_not_running():
            return
        name = self.schedule_pick_var.get().strip()
        if not name:
            messagebox.showinfo(t("dialog.load.title"), t("dialog.load.select_name"))
            return
        path = self._settings.schedule_dir_path() / f"{name}{DEFAULT_SUFFIX}"
        if not path.exists():
            messagebox.showerror(
                t("dialog.load.error_title"), t("dialog.load.not_found", name=name)
            )
            return
        self._load_schedule_from_path(path)

    def _load_schedule_from_path(self, path: Path) -> None:
        try:
            self._tasks = load_tasks(path)
            self._refresh_schedule_list()
            self._remember_last_schedule(path)
            messagebox.showinfo(t("dialog.load.title"), t("dialog.load.success"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror(t("dialog.load.error_title"), t("dialog.load.error", error=exc))

    def _remember_last_schedule(self, path: Path) -> None:
        self._settings.last_schedule_path = paths.to_portable_string(path)
        save_settings(self._settings)

    def _refresh_schedule_list(self, select_index: int | None = None) -> None:
        self.schedule_list.delete(0, tk.END)
        for i, task in enumerate(self._tasks, start=1):
            self.schedule_list.insert(tk.END, f"{i}. {task.label()}")
        if select_index is not None and 0 <= select_index < len(self._tasks):
            self.schedule_list.selection_set(select_index)
            self.schedule_list.see(select_index)
        self._on_state_changed()

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------
    def _perform_click(self) -> None:
        game_left_click(hold_ms=self._settings.click_hold_ms / 1000.0)

    def _run_loop(self) -> None:
        tasks_snapshot = list(self._tasks)
        while not self._stop_event.is_set():
            for task in tasks_snapshot:
                if self._stop_event.is_set():
                    break
                if task.kind == "click":
                    self._perform_click()
                else:
                    deadline = time.perf_counter() + task.ms / 1000.0
                    while time.perf_counter() < deadline:
                        if self._stop_event.is_set():
                            break
                        time.sleep(min(0.05, deadline - time.perf_counter()))
        self._root.after(0, self._set_running_false)

    def _set_running_false(self) -> None:
        self._running = False
        self._on_state_changed()
