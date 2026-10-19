import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from data_layout import DataLayout
from emulator import (CONSOLE_ACTIONS, CONTROLLERS, DEFAULT_CONSOLE_KEYS, DEFAULT_JOYSTICK_KEYS,
                      JOYSTICK_ACTIONS, load_console_keys, load_controller_settings, sdl_keycode)
from ui.style import BACKGROUND_COLOR

# Tk keysym (lowercase) -> key name used in config.json (see emulator.SDL_KEYS)
KEY_NAMES = {
    "space": "Space", "control_l": "Left Ctrl", "control_r": "Right Ctrl",
    "shift_l": "Left Shift", "shift_r": "Right Shift", "alt_l": "Left Alt", "alt_r": "Right Alt",
    "return": "Return", "tab": "Tab", "backspace": "Backspace", "up": "Up", "down": "Down",
    "left": "Left", "right": "Right", "insert": "Insert", "delete": "Delete", "home": "Home",
    "end": "End", "prior": "PageUp", "next": "PageDown",
}


def key_name(event, allow_function=False):
    """Translate a Tk key event to a key name atari800 can use, or None if unsupported.
    Function keys belong to the emulator's own menus, so only the console keys accept them."""
    keysym = event.keysym
    name = KEY_NAMES.get(keysym.casefold())
    if allow_function and keysym[0] == "F" and keysym[1:].isdigit():
        name = keysym
    if keysym.startswith("KP_") and keysym[3:].isdigit():
        name = f"Keypad {keysym[3:]}"
    elif len(keysym) == 1 and keysym.isalnum():
        name = keysym.upper()
    return name if name and sdl_keycode(name) else None


class SettingsDialog(tk.Toplevel):
    """Controller (keyboard / joystick), joystick keys, fullscreen, atari800 and the data folder."""

    def __init__(self, parent, layout, config, on_data_changed=None, on_populate=None, locator=None):
        super().__init__(parent)
        self.title("Settings")
        self.configure(background=BACKGROUND_COLOR)
        self.transient(parent)
        self.resizable(False, False)
        self.layout, self.config, self.on_data_changed = layout, config, on_data_changed
        self.locator = locator
        self.on_populate = on_populate  # opens the Populate folders window

        controller, keys = load_controller_settings(config)
        console = load_console_keys(config)

        box = ttk.LabelFrame(self, text="Controller", padding=10)
        box.pack(fill="x", padx=10, pady=10)
        self.controller = tk.StringVar(self, value=controller)
        for label, value in zip(("Keyboard", "Joystick"), CONTROLLERS):
            ttk.Radiobutton(box, text=label, variable=self.controller,
                            value=value).pack(side="left", padx=(0, 15))
        ttk.Label(box, text="Keyboard takes the keys below, so they cannot be typed in games "
                            "that need them (choose Joystick for those, or for a real gamepad).",
                  wraplength=420).pack(side="bottom", anchor="w", pady=(6, 0))

        self.key_vars, self._capturing = {}, {}
        kf = ttk.LabelFrame(self, text="Keyboard joystick keys (atari800)", padding=10)
        kf.pack(fill="x", padx=10, pady=(0, 10))
        for row, (action, label) in enumerate(JOYSTICK_ACTIONS):
            self.key_vars[action] = tk.StringVar(self, value=keys[action])
            ttk.Label(kf, text=label + ":").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(kf, textvariable=self.key_vars[action], width=14,
                      state="readonly").grid(row=row, column=1, padx=5, pady=2)
            b = ttk.Button(kf, text="Set...")
            b.configure(command=lambda a=action, btn=b: self._capture(a, btn))
            b.grid(row=row, column=2, pady=2)
        ttk.Button(kf, text="Defaults", command=self._default_keys).grid(
            row=len(JOYSTICK_ACTIONS), column=0, columnspan=3, sticky="e", pady=(5, 0))

        cf = ttk.LabelFrame(self, text="Console keys (atari800)", padding=10)
        cf.pack(fill="x", padx=10, pady=(0, 10))
        for row, (action, label) in enumerate(CONSOLE_ACTIONS):
            self.key_vars[action] = tk.StringVar(self, value=console[action])
            ttk.Label(cf, text=label + ":").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(cf, textvariable=self.key_vars[action], width=14,
                      state="readonly").grid(row=row, column=1, padx=5, pady=2)
            b = ttk.Button(cf, text="Set...")
            b.configure(command=lambda a=action, btn=b: self._capture(a, btn))
            b.grid(row=row, column=2, pady=2)
        ttk.Label(cf, text="Atari OPTION / SELECT / START. F2-F4 need the fn key on a Mac "
                           "keyboard, so pick other keys if they do nothing.",
                  wraplength=420).grid(row=len(CONSOLE_ACTIONS), column=0, columnspan=3,
                                       sticky="w", pady=(5, 0))

        df0 = ttk.LabelFrame(self, text="Display", padding=10)
        df0.pack(fill="x", padx=10, pady=(0, 10))
        self.fullscreen = tk.BooleanVar(self, value=bool(config.get("fullscreen", False)))
        ttk.Checkbutton(df0, text="Start games in fullscreen", variable=self.fullscreen).pack(anchor="w")

        ef = ttk.LabelFrame(self, text="atari800 executable", padding=10)
        ef.pack(fill="x", padx=10, pady=(0, 10))
        found = locator.find() if locator else None
        self.emulator_var = tk.StringVar(self, value=str(found) if found else "")
        ttk.Entry(ef, textvariable=self.emulator_var, width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(ef, text="Browse...", command=self._browse_emulator).grid(row=0, column=1, padx=(5, 0))
        ef.columnconfigure(0, weight=1)

        df = ttk.LabelFrame(self, text="Data folder (already populated)", padding=10)
        df.pack(fill="x", padx=10, pady=(0, 10))
        self.data_var = tk.StringVar(self, value=str(layout.data))
        ttk.Entry(df, textvariable=self.data_var, width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(df, text="Browse...", command=self._browse_data).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(df, text="Default", command=lambda: self.data_var.set(
            str(layout.root / "data"))).grid(row=0, column=2, padx=(5, 0))
        df.columnconfigure(0, weight=1)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Save", command=self._save).pack(side="right", padx=(0, 5))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()

    def _default_keys(self):
        self._stop_capture()
        defaults = {**DEFAULT_JOYSTICK_KEYS, **DEFAULT_CONSOLE_KEYS}
        for action, var in self.key_vars.items():
            var.set(defaults[action])

    def _stop_capture(self):
        if self._capturing:
            self.unbind("<KeyPress>", self._capturing.pop("binding"))
            self._capturing.pop("button").configure(text="Set...")

    def _capture(self, action, button):
        """Wait for the next key press and assign it to the joystick `action`."""
        self._stop_capture()
        button.configure(text="Press a key")
        self.focus_set()

        def on_key(event):
            name = key_name(event, allow_function=action in DEFAULT_CONSOLE_KEYS)
            if name:
                self.key_vars[action].set(name)
            self._stop_capture()
            return "break"

        self._capturing["button"] = button
        self._capturing["binding"] = self.bind("<KeyPress>", on_key)

    def _browse_data(self):
        d = filedialog.askdirectory(parent=self, title="Select the populated data folder",
                                    initialdir=self.data_var.get(), mustexist=True)
        if d:
            self.data_var.set(d)

    def _browse_emulator(self):
        p = filedialog.askopenfilename(parent=self, title="Select the atari800 executable")
        if p:
            self.emulator_var.set(p)

    @staticmethod
    def _folder_problem(data):
        """Describe what is wrong with a data folder, or None if it is complete and populated."""
        probe = DataLayout(data=data)
        if not all(d.is_dir() for d in probe.all_dirs):
            return "does not have the correct folder structure"
        if not any(p.is_file() for p in probe.games.rglob("*")):
            return "has no game files (it is not populated)"
        return None

    def _save(self):
        data = Path(self.data_var.get().strip() or self.layout.root / "data").expanduser()
        changed = data != self.layout.data
        populate = False
        problem = self._folder_problem(data) if changed else None
        if problem:
            answer = messagebox.askyesnocancel(
                "Data folder needs setting up",
                f"The selected data folder {problem}:\n{data}\n\n"
                "Yes: use it and open the Populate folders window to create/populate it\n"
                "No: use it as it is\nCancel: go back",
                parent=self)
            if answer is None:
                return
            populate = answer
        emulator = self.emulator_var.get().strip()
        if emulator and self.locator and not self.locator.remember(emulator):
            messagebox.showerror("atari800", f"Not an executable file:\n{emulator}", parent=self)
            return
        try:
            self.config.set("fullscreen", self.fullscreen.get())
            self.config.set("controller", self.controller.get())
            self.config.set("joystick_keys", {a: self.key_vars[a].get() for a, _ in JOYSTICK_ACTIONS})
            self.config.set("console_keys", {a: self.key_vars[a].get() for a, _ in CONSOLE_ACTIONS})
            if changed:
                self.layout.set_data(data)
        except OSError as e:
            messagebox.showerror("Could not save settings", str(e), parent=self)
            return
        self.destroy()
        if changed and self.on_data_changed:
            self.on_data_changed()
        if populate and self.on_populate:
            self.on_populate()
