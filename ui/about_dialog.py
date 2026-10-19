import tkinter as tk
import webbrowser
from tkinter import ttk

from ui.populate_dialog import SOURCES_URL
from ui.style import BACKGROUND_COLOR, LINK_COLOR

ABOUT_TEXT = ("GamebaseXL Browser and Player: a browser and launcher for the GameBase Atari XL "
              "collection (Atari 8-bit: 800XL / 130XE).\n\n"
              "@Dimfil 2026\n\n"
              "Game data and files come from the GameBase Atari XL project (based on Atarimania "
              "by Sparky, updated by .mad.). All credit goes to that project and its contributors.\n\n"
              "Tested with the Atari-XL GameBase 2021 (by .mad.) database from:")


class AboutDialog(tk.Toplevel):
    def __init__(self, parent, name, version):
        super().__init__(parent)
        self.title(f"About {name}")
        self.configure(background=BACKGROUND_COLOR)
        self.transient(parent)
        self.resizable(False, False)

        body = ttk.Frame(self, padding=20)
        body.pack()
        ttk.Label(body, text=name, font=("Helvetica", 16, "bold")).pack()
        ttk.Label(body, text=f"Version {version}").pack(pady=(0, 10))
        ttk.Label(body, text=ABOUT_TEXT, wraplength=380, justify="center").pack()
        link = ttk.Label(body, text=SOURCES_URL, foreground=LINK_COLOR, cursor="hand2")
        link.pack(pady=(4, 12))
        link.bind("<Button-1>", lambda _e: webbrowser.open(SOURCES_URL))
        ttk.Button(body, text="Close", command=self.destroy).pack()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.destroy())
        self.grab_set()
