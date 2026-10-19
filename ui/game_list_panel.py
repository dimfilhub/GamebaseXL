import tkinter as tk
from tkinter import ttk

from ui.filter_box import FilterBox


class GameListPanel(ttk.Frame):
    """Search box, dropdown filters and the game tree (one column per filter)."""

    def __init__(self, parent, games, on_select, on_activate):
        super().__init__(parent, padding=6)
        self.games = games
        self._by_id = {g.id: g for g in games}
        self._on_select = on_select
        self._on_activate = on_activate
        self._build()
        self._fill_filters()
        self.refresh()

    def _build(self):
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.refresh())
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Search:").pack(side="left")
        ttk.Entry(row, textvariable=self.search).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ttk.Button(row, text="Clear", width=6,
                   command=self.clear_filters).pack(side="left", padx=(4, 0))

        # Two rows of dropdown filters; the second column lines up in both rows.
        filt = ttk.Frame(self)
        filt.pack(fill="x", pady=4)
        filt.columnconfigure((0, 1), weight=1, uniform="filters")
        self.filters = [
            FilterBox(filt, "Genre:", "genre_text", self.refresh, column_width=110),
            FilterBox(filt, "Year:", "year_text", self.refresh, width=8,
                      column_width=50, anchor="center"),
            FilterBox(filt, "Publisher:", "publisher_text", self.refresh, column_width=130),
            FilterBox(filt, "Developer:", "developer_text", self.refresh, column_width=130),
        ]
        for i, box in enumerate(self.filters):
            box.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 8) if i % 2 == 0 else 0,
                     pady=(0, 3))

        # The count label is packed before the tree so it stays visible at the bottom.
        self.count = ttk.Label(self, anchor="w")
        self.count.pack(side="bottom", fill="x")

        # One list column per filter, so the filtered values are visible in the list.
        self.tree = ttk.Treeview(self, columns=[f.attribute for f in self.filters],
                                 selectmode="browse")
        self.tree.heading("#0", text="Name")
        self.tree.column("#0", width=260)
        for f in self.filters:
            self.tree.heading(f.attribute, text=f.title)
            self.tree.column(f.attribute, width=f.column_width, anchor=f.column_anchor)
        sb = ttk.Scrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.notify_selection())
        self.tree.bind("<Double-1>", self._double_click)

    def clear_filters(self):
        """Empty the search box and set every dropdown back to (all)."""
        for box in self.filters:
            box.reset()
        self.search.set("")  # triggers the refresh when the text changed
        self.refresh()

    def _fill_filters(self):
        for box in self.filters:
            box.fill(self.games)

    def reload(self, games):
        """Replace the game data, keeping the filters and the selected game."""
        keep = self.selected()
        self.games = games
        self._by_id = {g.id: g for g in games}
        self._fill_filters()
        self.refresh()
        if keep and str(keep.id) in self.tree.get_children():
            self.tree.selection_set(str(keep.id))
            self.notify_selection()  # re-read the files of the selected game

    def refresh(self):
        q = self.search.get().strip().casefold()
        had_selection = self.selected() is not None
        self.tree.delete(*self.tree.get_children())
        n = 0
        for g in self.games:
            if q and q not in g.name.casefold():
                continue
            if not all(box.matches(g) for box in self.filters):
                continue
            self.tree.insert("", "end", iid=str(g.id), text=g.name,
                             values=[f.value(g) for f in self.filters])
            n += 1
        self.count.configure(text=f"{n} of {len(self.games)} games")
        if had_selection and self.selected() is None:
            self._on_select(None)  # the selected game was filtered out

    def selected(self):
        sel = self.tree.selection()
        return self._by_id[int(sel[0])] if sel else None

    def notify_selection(self):
        self._on_select(self.selected())  # None when nothing is selected

    def _double_click(self, event):
        # Only react to double-clicks on a game row, not on headings or empty space.
        row = self.tree.identify_row(event.y)
        if row and self.tree.identify_region(event.x, event.y) != "heading":
            self.tree.selection_set(row)
            self.notify_selection()  # make sure the clicked row is the current game
            self._on_activate(self._by_id[int(row)])
