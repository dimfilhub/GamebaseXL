"""The update check as the user sees it: the startup check, Help > Check for Updates… and the answer dialogs.

`get(key, default)` and `put(key, value)` read and write the app's saved settings; `background` is an optional
colour for the dialog."""
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import updates

SETTING_ENABLED = "check_updates"
SETTING_LAST = "last_update_check"
SETTING_SKIPPED = "skipped_version"


class UpdateChecker:
    def __init__(self, root, name, version, get, put, background=None):
        self.root, self.name, self.version = root, name, version
        self._get, self._put_raw, self.background = get, put, background
        self.enabled = tk.BooleanVar(root, value=self._get(SETTING_ENABLED, True) is not False)
        self.enabled.trace_add("write", lambda *_: self._put(SETTING_ENABLED, bool(self.enabled.get())))

    def _put(self, key, value):
        try:
            self._put_raw(key, value)
        except OSError:
            pass     # settings that cannot be saved are not worth stopping for

    def add_menu_items(self, menu):
        menu.add_separator()
        menu.add_command(label="Check for Updates…", command=lambda: self.check(manual=True))
        menu.add_checkbutton(label="Check for updates at startup", variable=self.enabled)

    def check_at_startup(self):
        """Once a day, a few seconds after the window is up (unless switched off)."""
        last = self._get(SETTING_LAST, 0.0)
        last = float(last) if isinstance(last, (int, float)) and not isinstance(last, bool) else 0.0
        if self.enabled.get() and updates.due(last):
            self.root.after(2000, lambda: self.check(manual=False))

    def check(self, manual):
        """Ask GitHub on a background thread; the answer is shown from the Tk thread."""
        if not manual:
            self._put(SETTING_LAST, time.time())

        def done(release, error):
            try:
                self.root.after(0, lambda: self.report(release, error, manual))
            except (RuntimeError, tk.TclError):
                pass     # the window was closed meanwhile
        updates.check_in_background(done)

    def report(self, release, error, manual):
        """An automatic check says something only when a newer release exists that the user has not skipped;
        a manual one always answers."""
        if error:
            if manual:
                messagebox.showinfo("Check for updates", f"Could not check for updates:\n{error}\n\nCheck your internet "
                                    f"connection and try again, or look at {updates.RELEASES_URL}", parent=self.root)
            return
        if not updates.is_newer(release.version, self.version):
            if manual:
                messagebox.showinfo("Check for updates", f"You have the newest version ({self.version}).", parent=self.root)
            return
        if not manual and release.version == self._get(SETTING_SKIPPED, ""):
            return
        answer = self._ask(release)
        if answer == "open":
            webbrowser.open(release.url)
        elif answer == "skip":
            self._put(SETTING_SKIPPED, release.version)

    def _ask(self, release):
        """'Update available' window with Open download page / Skip this version / Later; returns open, skip or later."""
        notes = release.notes[:600] + ("…" if len(release.notes) > 600 else "")
        window = tk.Toplevel(self.root)
        window.title("Update available")
        window.transient(self.root)
        window.resizable(False, False)
        if self.background:
            window.configure(background=self.background)
        result = ["later"]

        def pick(value):
            result[0] = value
            window.destroy()
        body = ttk.Frame(window, padding=20)
        body.pack()
        ttk.Label(body, text=f"{self.name} {release.version} is available. You have {self.version}.",
                  wraplength=420, justify="center").pack()
        if notes:
            ttk.Label(body, text=notes, wraplength=420, justify="left").pack(pady=(10, 0))
        buttons = ttk.Frame(body)
        buttons.pack(pady=(14, 0))
        first = ttk.Button(buttons, text="Open download page", command=lambda: pick("open"))
        first.pack(side="left", padx=3)
        ttk.Button(buttons, text="Skip this version", command=lambda: pick("skip")).pack(side="left", padx=3)
        ttk.Button(buttons, text="Later", command=lambda: pick("later")).pack(side="left", padx=3)
        window.bind("<Escape>", lambda _e: pick("later"))
        window.bind("<Return>", lambda _e: pick("open"))
        window.protocol("WM_DELETE_WINDOW", lambda: pick("later"))
        first.focus_set()
        window.grab_set()
        self.root.wait_window(window)
        return result[0]
