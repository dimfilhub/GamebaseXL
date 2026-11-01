import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from assets import GameAssets, exists
from config import Config
from data_audit import DataAudit
from data_layout import RESOURCE_ROOT, DataLayout
from emulator import Atari800Launcher, Atari800Locator, LaunchError, MediaPreparer
from repository import GameRepository
from system import OperatingSystem
from text import clean
from ui.about_dialog import AboutDialog
from ui.action_buttons import ActionButtons
from ui.game_list_panel import GameListPanel
from ui.help_dialog import HelpDialog
from ui.image_preview import PLACEHOLDER_CREDIT, ImagePreview
from ui.info_tabs import InfoTabs
from ui.populate_dialog import PopulateDialog
from ui.settings_dialog import SettingsDialog
from ui.style import AppStyle

APP_NAME = "GamebaseXL Browser and Player"
APP_VERSION = "1.0.1"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


class App(tk.Tk):
    """Main window: wires the panels to the services."""

    def __init__(self, layout=None):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION} © DimFil 2026")
        self._set_window_icon()
        self._maximize()

        self.layout = layout or DataLayout()
        self.repo = GameRepository(self.layout.db_path)
        self.assets = GameAssets(self.layout, self.repo)
        self.os = OperatingSystem()
        self.locator = Atari800Locator(self.layout, Config(self.layout.config_file))
        self.settings = Config(self.layout.config_file)
        self.launcher = Atari800Launcher(self.layout, MediaPreparer(self.layout), self.settings)
        self.current = None  # currently selected Game

        AppStyle(self).apply()
        self._build_ui()
        self._build_menu()
        self.after(200, self._check_data)

    def _set_window_icon(self):
        try:
            from PIL import Image, ImageTk
            with Image.open(RESOURCE_ROOT / "images" / "icon.png") as im:
                self._icon = ImageTk.PhotoImage(im.resize((256, 256), Image.LANCZOS))
            self.iconphoto(True, self._icon)
        except (OSError, tk.TclError, ImportError):
            pass  # a missing icon is not worth stopping for

    def _check_data(self):
        problem = DataAudit(self.layout, self.repo).startup_problem()
        if problem:
            messagebox.showwarning("Data folder", problem, parent=self)

    def _maximize(self):
        """Fill the available screen area (menu bar / taskbar excluded), not true fullscreen."""
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        for apply in (lambda: self.state("zoomed"),
                      lambda: self.attributes("-zoomed", True)):
            try:
                apply()
                return
            except tk.TclError:
                continue

    def _build_menu(self):
        menubar = tk.Menu(self)
        data = tk.Menu(menubar, tearoff=False)
        data.add_command(label="Populate folders…", command=self.open_populate)
        menubar.add_cascade(label="Gamebase", menu=data)
        options = tk.Menu(menubar, tearoff=False)
        options.add_command(label="Settings…", command=self.open_settings)
        menubar.add_cascade(label="Options", menu=options)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=f"{APP_NAME} Help", command=self.open_help)
        help_menu.add_command(label=f"About {APP_NAME}…", command=self.open_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)
        # macOS: the app-menu "About" item calls this command instead of the bare system panel
        self.createcommand("tkAboutDialog", self.open_about)

    def open_help(self):
        HelpDialog(self, APP_NAME)

    def open_about(self):
        AboutDialog(self, APP_NAME, APP_VERSION)

    def open_settings(self):
        SettingsDialog(self, self.layout, self.settings, on_data_changed=self.refresh_games,
                       on_populate=self.open_populate, locator=self.locator)

    def open_populate(self):
        PopulateDialog(self, self.layout, self.repo, on_populated=self.refresh_games)

    def refresh_games(self):
        self.game_list.reload(self.repo.list_games())

    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient="vertical")
        paned.pack(fill="both", expand=True)

        self.game_list = GameListPanel(paned, self.repo.list_games(),
                                       on_select=self.on_select, on_activate=self.launch)
        paned.add(self.game_list, weight=1)

        # Below the list: preview + buttons on the left, game info tabs on the right.
        bottom = ttk.Frame(paned, padding=6)
        paned.add(bottom, weight=0)
        self.preview = ImagePreview(bottom)
        self.preview.pack(side="left", anchor="n")
        self.buttons = ActionButtons(bottom, {
            "shot": self.show_screenshot, "cover": self.show_cover,
            "game": self.reveal_game,
            "launch": self.launch, "populate": self.open_populate, "settings": self.open_settings,
            "quit": self.destroy,
        })
        self.buttons.pack(side="left", fill="y", padx=8)

        self.tabs = InfoTabs(bottom, on_extra_select=self.on_extra_select,
                             on_extra_open=self.open_extra)
        self.tabs.pack(side="left", fill="both", expand=True)

        self._show_nothing()
        self._paned, self._bottom = paned, bottom
        self.bind("<Configure>", lambda e: e.widget is self and self._fit_preview())
        self.after(150, self._fit_preview)  # the first Configure only reports a 1x1 window

    def _fit_preview(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w > 100 and h > 100 and self.preview.fit_to_window(w, h):
            # Bottom section keeps the height it needs; the list takes the rest.
            self.after_idle(self._place_sash)

    def _place_sash(self):
        self._paned.sashpos(0, max(200, self._paned.winfo_height() - self._bottom.winfo_reqheight()))

    # ---------- selection ----------
    def on_select(self, game):
        self.current = game
        if game is None:
            self._show_nothing()
            return
        details = self.repo.details(game.id)
        self.tabs.show_game(game, details, self.assets)
        has_zip = exists(self.assets.game_file(game))
        has_shot = exists(self.assets.screenshot(game))
        cover = self.assets.cover(game)
        self.buttons.set_enabled(game=has_zip, launch=has_zip, shot=has_shot,
                                 cover=bool(cover))
        # Screenshot is the default; fall back to the cover when there is none.
        if has_shot or not cover:
            self.show_screenshot()
        else:
            self.show_cover()

    def _show_nothing(self):
        """No game selected: empty the panels and show the Atari logo with a hint."""
        self.current = None
        self.tabs.clear()
        self.tabs.info.set(PLACEHOLDER_CREDIT)
        self.buttons.set_enabled(**{k: False for k in self.buttons.buttons})
        self.preview.show_placeholder()

    # ---------- images ----------
    def show_cover(self):
        self.preview.show(self.assets.cover(self.current) if self.current else None)

    def show_screenshot(self):
        self.preview.show(self.assets.screenshot(self.current) if self.current else None)

    def on_extra_select(self, extra_file):
        if extra_file.path.suffix.lower() in IMAGE_EXTS:
            self.preview.show(extra_file.path)

    def open_extra(self, extra_file):
        """Double-click on an extra: run it in the emulator, or open it with the OS."""
        if extra_file.runnable:
            self.run_in_emulator(f"x{extra_file.extra.id}", self.current.name if self.current else
                                 extra_file.extra.name, extra_file.path,
                                 clean(extra_file.extra.file_to_run), extra_file.extra.options)
        else:
            self.os.open(extra_file.path)

    # ---------- actions ----------
    def reveal_game(self):
        p = self.assets.game_file(self.current) if self.current else None
        if exists(p):
            self.os.reveal(p)

    def choose_emulator(self):
        p = filedialog.askopenfilename(title="Select the atari800 executable")
        exe = self.locator.remember(p) if p else None
        if p and not exe:
            messagebox.showerror("Atari800", f"Not an executable file:\n{p}")
        return exe

    def launch(self, game=None):
        game = game or self.current
        path = self.assets.game_file(game) if game else None
        if not exists(path):
            return
        file_to_run, gemus = self.repo.launch_options(game.id)
        self.run_in_emulator(game.id, game.name, path, clean(file_to_run), gemus)

    def run_in_emulator(self, key, name, path, file_to_run, gemus):
        exe = self.locator.find() or self.choose_emulator()
        if not exe:
            return
        try:
            self.launcher.launch(exe, key, name, path, file_to_run, gemus)
        except LaunchError as e:
            messagebox.showerror("Cannot launch", str(e))

    def destroy(self):
        self.repo.close()
        super().destroy()
