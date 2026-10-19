import queue
import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from data_audit import DataAudit
from ui.style import BACKGROUND_COLOR, LINK_COLOR
from populate import SOURCES_URL, Populator


SOURCES_CREDIT = ("The source zips needed here come from the GameBase Atari XL project (based on "
                  "Atarimania by Sparky, updated by .mad.), shared on the AtariAge forum. All "
                  "credit for the GameBase Atari XL data and files goes to that project and its "
                  "contributors.")


class PopulateDialog(tk.Toplevel):
    """Create the data/ folder tree and extract sources/*.zip into it."""

    def __init__(self, parent, layout, repo, on_populated=None):
        super().__init__(parent)
        self.title("Populate folders")
        self.configure(background=BACKGROUND_COLOR)
        self.geometry("700x480")
        self.transient(parent)
        self.layout, self.repo = layout, repo
        self.lines = queue.Queue()
        self.busy = False
        self.on_populated = on_populated
        self._populating = False

        bar = ttk.Frame(self, padding=8)
        bar.pack(side="bottom", fill="x")  # packed first so it stays visible at the bottom
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")

        paths = ttk.Frame(self, padding=(8, 0))
        paths.pack(fill="x")
        paths.columnconfigure(1, weight=1)
        self.data_var = tk.StringVar(value=str(layout.data))
        self.sources_var = tk.StringVar(value=str(layout.sources))
        for row, (label, var, pick) in enumerate([
                ("Data folder:", self.data_var, self.choose_data),
                ("Sources folder:", self.sources_var, self.choose_sources)]):
            ttk.Label(paths, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(paths, textvariable=var, state="readonly").grid(
                row=row, column=1, sticky="ew", padx=6)
            ttk.Button(paths, text="Browse…", command=pick).grid(row=row, column=2)
        self.create_btn = ttk.Button(paths, text="Create Folder Structure",
                                     command=self.create_folders)
        self.create_btn.grid(row=0, column=3, sticky="ew", padx=(6, 0))
        self.populate_btn = ttk.Button(paths, text="Populate folders", command=self.populate)
        self.populate_btn.grid(row=1, column=3, sticky="ew", padx=(6, 0))
        credit = ttk.Frame(self, padding=(8, 6, 8, 0))
        credit.pack(fill="x")
        ttk.Label(credit, text=SOURCES_CREDIT, wraplength=660, justify="left").pack(anchor="w")
        link = ttk.Label(credit, text=SOURCES_URL, foreground=LINK_COLOR, cursor="hand2")
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda _e: webbrowser.open(SOURCES_URL))
        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)
        self.log = tk.Text(frame, state="disabled", wrap="word")
        sb = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.after(100, self._drain)
        self.report_sources()

    def choose_data(self):
        d = filedialog.askdirectory(parent=self, title="Where should the data folder be?",
                                    initialdir=self.layout.data.parent, mustexist=False)
        if d:
            self.layout.set_data(d)
            self.data_var.set(str(self.layout.data))
            self._write(f"Data folder set to {self.layout.data}")
            if self.on_populated:
                self.on_populated()  # the files the app shows come from the new folder

    def choose_sources(self):
        d = filedialog.askdirectory(parent=self, title="Folder containing the source zips",
                                    initialdir=self.layout.sources, mustexist=True)
        if d:
            self.layout.set_sources(d)
            self.sources_var.set(str(self.layout.sources))
            self._write(f"Sources folder set to {self.layout.sources}")
            self.report_sources()

    def report_sources(self):
        found, missing, broken, extra = Populator(self.layout).check_sources()
        self._write(f"Sources check: {len(found)} found, {len(missing)} missing"
                    + (f", {len(broken)} unreadable" if broken else ""))
        for label, names in (("  found:     ", found), ("  MISSING:   ", missing),
                             ("  UNREADABLE:", broken), ("  not needed:", extra)):
            for n in names:
                self._write(f"{label} {n}")

    def _write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain(self):
        try:
            while True:
                item = self.lines.get_nowait()
                if item is None:
                    self._set_busy(False)
                    if self._populating and self.on_populated:
                        self.on_populated()
                    self._populating = False
                else:
                    self._write(item)
        except queue.Empty:
            pass
        self.after(100, self._drain)

    def _set_busy(self, busy):
        self.busy = busy
        state = ["disabled"] if busy else ["!disabled"]
        self.create_btn.state(state)
        self.populate_btn.state(state)

    def _run(self, work):
        self._set_busy(True)

        def target():
            try:
                work()
            except Exception as e:  # report in the log instead of dying silently
                self.lines.put(f"Error: {e}")
            self.lines.put(None)
        threading.Thread(target=target, daemon=True).start()

    def create_folders(self):
        def work():
            DataAudit(self.layout, self.repo).make_folders()
            self.lines.put(f"Folder structure created under {self.layout.data}")
        self._write("Creating folder structure…")
        self._run(work)

    def populate(self):
        def work():
            Populator(self.layout, log=self.lines.put).run()
            self.lines.put("Done.")
        self._write("Populating from sources/…")
        self._populating = True
        self._run(work)
