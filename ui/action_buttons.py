from tkinter import ttk


BUTTON_WIDTH = 24  # in characters; sets the width of the whole column


class ActionButtons(ttk.Frame):
    """Column of buttons next to the preview. `commands` maps button key -> callable."""

    def __init__(self, parent, commands):
        super().__init__(parent)
        specs = [("shot", "Screenshot"), ("cover", "Cover"), ("game", "Reveal game file"),
                 ("launch", "Launch in Atari800")]
        self.buttons = {}
        for key, text in specs:
            b = ttk.Button(self, text=text, width=BUTTON_WIDTH, command=commands[key])
            b.pack(fill="x", pady=(0, 4))
            self.buttons[key] = b
        ttk.Button(self, text="Quit", style="quit.TButton", width=BUTTON_WIDTH,
                   command=commands["quit"]).pack(side="bottom", fill="x")
        ttk.Button(self, text="Settings…", width=BUTTON_WIDTH,
                   command=commands["settings"]).pack(side="bottom", fill="x", pady=(0, 4))
        ttk.Button(self, text="Populate folders…", width=BUTTON_WIDTH,
                   command=commands["populate"]).pack(side="bottom", fill="x", pady=(0, 4))

    def set_enabled(self, **states):
        for key, enabled in states.items():
            self.buttons[key].state(["!disabled" if enabled else "disabled"])
