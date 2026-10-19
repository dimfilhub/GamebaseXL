import re
import tkinter as tk
from tkinter import font as tkfont, ttk

from text import clean, year_text


class TextTab(ttk.Frame):
    # Break points: after a path separator or whitespace.
    _TOKEN = re.compile(r"[^/\\\s]*[/\\\s]+|[^/\\\s]+")

    def __init__(self, parent, hang_chars=None):
        """With hang_chars set, long lines are wrapped at path separators and the
        continuation lines are indented by that many characters (under a label column)."""
        super().__init__(parent)
        self.text = tk.Text(self, wrap="word", height=10, state="disabled", padx=6, pady=6)
        self.font = tkfont.Font(font=self.text.cget("font"))
        self.hang_chars = hang_chars
        self.content = ""
        self._rendered_width = None
        sb = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        if hang_chars is not None:
            indent = self.font.measure("0" * hang_chars)
            self.text.tag_configure("cont", lmargin1=indent, lmargin2=indent)
            self.text.bind("<Configure>", lambda _e: self._render())

    def set(self, content):
        self.content = content
        self._rendered_width = None
        self._render()

    def _render(self):
        width = self.text.winfo_width()
        if self.hang_chars is not None and width == self._rendered_width:
            return
        self._rendered_width = width
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if self.hang_chars is None or width < 100:  # not laid out yet: plain text
            self.text.insert("1.0", self.content)
        else:
            self._insert_wrapped(width)
        self.text.configure(state="disabled")

    def _insert_wrapped(self, width):
        avail = width - 2 * (int(self.text.cget("padx")) + int(self.text.cget("borderwidth"))
                             + int(self.text.cget("highlightthickness"))) - 2
        indent = self.font.measure("0" * self.hang_chars)
        for n, line in enumerate(self.content.split("\n")):
            pieces, cur = [], ""
            for tok in self._TOKEN.findall(line):
                limit = avail if not pieces else avail - indent
                if cur and self.font.measure((cur + tok).rstrip()) > limit:
                    pieces.append(cur.rstrip())
                    cur = tok
                else:
                    cur += tok
            pieces.append(cur.rstrip())
            for i, piece in enumerate(pieces):
                last = n == self.content.count("\n") and i == len(pieces) - 1
                self.text.insert("end", piece + ("" if last else "\n"), "cont" if i else "")


class ExtrasTab(ttk.Frame):
    def __init__(self, parent, on_select, on_open):
        super().__init__(parent)
        self.files = {}  # tree item id -> ExtraFile (only those present on disk)
        self.tree = ttk.Treeview(self, columns=("file",), selectmode="browse")
        self.tree.heading("#0", text="Name")
        self.tree.heading("file", text="File")
        self.tree.column("#0", width=200)
        self.tree.pack(fill="both", expand=True)
        self._on_select = on_select
        self._on_open = on_open
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._fire(self._on_select))
        self.tree.bind("<Double-1>", lambda _e: self._fire(self._on_open))

    def _fire(self, callback):
        sel = self.tree.selection()
        extra_file = self.files.get(sel[0]) if sel else None
        if extra_file:
            callback(extra_file)

    def set(self, extra_files):
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        for ef in extra_files:
            label = ef.extra.name + ("" if ef.exists else "  (missing)")
            if ef.runnable:
                label += "  ▶"
            iid = self.tree.insert("", "end", text=label,
                                   values=(ef.path.name if ef.path else "",))
            if ef.exists:
                self.files[iid] = ef


class InfoTabs(ttk.Notebook):
    """Info, Notes and Extras tabs."""
    LABEL_WIDTH = 12  # width of the "Label:" column in the Info text

    def __init__(self, parent, on_extra_select, on_extra_open):
        super().__init__(parent)
        self.info = TextTab(self, hang_chars=self.LABEL_WIDTH)
        self.notes = TextTab(self)
        self.extras = ExtrasTab(self, on_extra_select, on_extra_open)
        self.add(self.info, text="Info")
        self.add(self.notes, text="Notes")
        self.add(self.extras, text="Extras")

    def clear(self):
        self.info.set("")
        self.notes.set("")
        self.extras.set([])

    def show_game(self, game, details, assets):
        d = details
        fields = [
            ("Name", d.name), ("Year", year_text(d.year)),
            ("Publisher", d.publisher), ("Developer", d.developer),
            ("Programmer", d.programmer), ("Artist", d.artist),
            ("Musician", d.musician), ("Genre", d.genre), ("Language", d.language),
            ("License", d.license), ("Cracker", d.cracker), ("Players", d.players),
            ("Link", f"{clean(d.weblink_name)} {clean(d.weblink_url)}"),
            ("Game file", assets.game_file(game)),
            ("Screenshot", assets.screenshot(game)),
            ("Music", assets.music(game)),
        ]
        lines = [f"{k + ':':<{self.LABEL_WIDTH}}{clean(v)}" for k, v in fields if clean(v)]
        self.info.set("\n".join(lines))
        self.notes.set(d.notes or "(no notes)")
        self.extras.set(assets.extras(game))

