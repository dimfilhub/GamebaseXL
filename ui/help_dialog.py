import re
import tkinter as tk
import webbrowser
from tkinter import ttk

from data_layout import RESOURCE_ROOT
from ui.style import BACKGROUND_COLOR, LINK_COLOR, TEXT_COLOR

# README sections shown in the help window, in order.
SECTIONS = ("1. Get the source zips", "What the app does", "Using the app", "Settings")
TITLES = {"1. Get the source zips": "Where to get the game files"}
FALLBACK = "The README.md file could not be found."


def readme_sections(text, titles):
    """Return [(title, body)] for the `## title` sections of the README that are in `titles`."""
    parts = re.split(r"^#{2,3} (.+)$", text, flags=re.M)
    found = {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    return [(t, found[t]) for t in titles if t in found]


class HelpDialog(tk.Toplevel):
    def __init__(self, parent, name):
        super().__init__(parent)
        self.title(f"{name} Help")
        self.configure(background=BACKGROUND_COLOR)
        self.transient(parent)
        self.geometry("720x560")

        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        self.text = tk.Text(frame, wrap="word", padx=10, pady=8, yscrollcommand=scroll.set,
                            borderwidth=0, highlightthickness=0, background=BACKGROUND_COLOR,
                            foreground=TEXT_COLOR)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.text.yview)
        self.text.tag_configure("h", font=("Helvetica", 14, "bold"), spacing1=10, spacing3=4)
        self.text.tag_configure("b", font=("Helvetica", 12, "bold"))
        self.text.tag_configure("code", font=("Courier", 11))
        self._fill()
        self.text.config(state="disabled")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _fill(self):
        try:
            readme = (RESOURCE_ROOT / "README.md").read_text(encoding="utf-8")
        except OSError:
            self.text.insert("end", FALLBACK)
            return
        sections = readme_sections(readme, SECTIONS)
        if not sections:
            self.text.insert("end", FALLBACK)
        for title, body in sections:
            self.text.insert("end", TITLES.get(title, title) + "\n", "h")
            for line in body.splitlines():
                self._line(line)
            self.text.insert("end", "\n")

    def _plain(self, chunk):
        """Insert text, turning bare URLs into clickable links."""
        for part in re.split(r"(https?://[^\s)]+)", chunk):
            if part.startswith("http"):
                tag = f"link{part}"
                self.text.tag_configure(tag, foreground=LINK_COLOR, underline=True)
                self.text.tag_bind(tag, "<Button-1>", lambda _e, u=part: webbrowser.open(u))
                self.text.tag_bind(tag, "<Enter>", lambda _e: self.text.config(cursor="hand2"))
                self.text.tag_bind(tag, "<Leave>", lambda _e: self.text.config(cursor=""))
                self.text.insert("end", part, tag)
            else:
                self.text.insert("end", part)

    def _line(self, line):
        if line.startswith("|") and set(line) <= set("|- "):
            return  # table separator
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            line = "- " + ": ".join(cells)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"<(https?://[^>]+)>", r"\1", line)
        if line.startswith("- "):
            line = "  • " + line[2:]
        # **bold** and `code` spans
        for chunk in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", line):
            if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
                self.text.insert("end", chunk[2:-2], "b")
            elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
                self.text.insert("end", chunk[1:-1], "code")
            else:
                self._plain(chunk.replace("*", ""))
        self.text.insert("end", "\n")
