import tkinter as tk
from tkinter import ttk

ALL = "(all)"
LABEL_WIDTH = 10  # characters; same for every filter so the dropdowns line up


class FilterBox(ttk.Frame):
    """Label + read-only dropdown that filters games on one text attribute."""

    def __init__(self, parent, label, attribute, on_change, width=18, column_width=130, anchor="w"):
        super().__init__(parent)
        self.title = label.rstrip(":")      # heading of the matching list column
        self.column_width = column_width
        self.column_anchor = anchor
        self.attribute = attribute  # name of a Game property returning display text
        self.var = tk.StringVar(value=ALL)
        ttk.Label(self, text=label, width=LABEL_WIDTH, anchor="w").pack(side="left")
        self.combo = ttk.Combobox(self, textvariable=self.var, state="readonly", width=width)
        self.combo.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.combo.bind("<<ComboboxSelected>>", lambda _e: on_change())

    def value(self, game):
        return getattr(game, self.attribute)

    def fill(self, games):
        values = sorted({self.value(g) for g in games} - {""}, key=str.casefold)
        self.combo["values"] = [ALL] + values

    def reset(self):
        self.var.set(ALL)

    def matches(self, game):
        selected = self.var.get()
        return selected == ALL or self.value(game) == selected
