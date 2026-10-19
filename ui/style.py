from tkinter import ttk

# The Atari XL BASIC screen: deep blue background (COLOR2 = $94), light blue text.
BACKGROUND_COLOR = "#3a3f9e"
TEXT_COLOR = "#b9c0ff"
LINK_COLOR = "#ffe27a"  # readable on the blue; a classic blue link would vanish


class AppStyle:
    """clam has fixed light colours; the native macOS theme follows system dark mode."""

    def __init__(self, root):
        self.root = root

    def apply(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        bg = BACKGROUND_COLOR
        self.root.configure(background=bg)
        for name in ("TFrame", "TLabel", "TPanedwindow", "TNotebook", "TLabelframe",
                     "TLabelframe.Label", "TRadiobutton", "TCheckbutton"):
            style.configure(name, background=bg, foreground=TEXT_COLOR)
        style.map("TRadiobutton", background=[("active", bg)])
        style.map("TCheckbutton", background=[("active", bg)])
        style.configure("TNotebook.Tab", background="#e0e0e0", foreground="black")
        style.map("TNotebook.Tab", background=[("selected", "white")])
        style.configure("TButton", background="#e0e0e0", foreground="black")
        style.configure("TEntry", fieldbackground="white", foreground="blue")
        style.configure("TCombobox", fieldbackground="white", foreground="black")
        style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
        style.map("Treeview", background=[("selected", "#0078d7")],
                  foreground=[("selected", "white")])
        style.configure("Treeview.Heading", foreground="blue")
        style.configure("quit.TButton", foreground="red")
