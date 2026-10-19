from tkinter import ttk

from PIL import Image, ImageOps, ImageTk

from data_layout import RESOURCE_ROOT
from ui.atari_logo import AtariLogo

PLACEHOLDER_PHOTO = RESOURCE_ROOT / "images" / "atari_800xl.jpg"
PLACEHOLDER_CREDIT = ('Select a game to see its screenshot, details and extras.\n\n'
                      'Photo: "Atari-800XL" by Evan-Amos, CC BY-SA 3.0 (commons.wikimedia.org)')

# Preview area as a fraction of the window, so it follows the window size.
WIDTH_FRACTION = 0.35
HEIGHT_FRACTION = 0.46        # upper limit on the height
ASPECT = 336 / 240             # GameBase Atari XL screenshots


class ImagePreview(ttk.Frame):
    """Fixed-size image area so the layout doesn't jump."""

    def __init__(self, parent):
        self.size = (560, 380)  # replaced by fit_to_window() once the window size is known
        super().__init__(parent, width=self.size[0], height=self.size[1])
        self.pack_propagate(False)
        self.label = ttk.Label(self, anchor="n", borderwidth=0)
        self.label.pack(fill="both", expand=True)
        self._photo = None  # keep reference to avoid GC
        self._path = None
        self._logo = False  # showing the Atari logo (nothing selected)

    def fit_to_window(self, window_width, window_height):
        """Resize the preview area relative to the window; returns True if it changed."""
        width = int(window_width * WIDTH_FRACTION)
        height = min(int(width / ASPECT), int(window_height * HEIGHT_FRACTION))
        size = (int(height * ASPECT), height)  # shrink the width too if the height was capped
        if size == self.size:
            return False
        self.size = size
        self.configure(width=size[0], height=size[1])
        self.show_placeholder() if self._logo else self.show(self._path)
        return True

    def show_placeholder(self):
        """Shown when no game is selected: an Atari 800XL photo (drawn logo if it is missing)."""
        self._logo, self._path = True, None
        try:
            with Image.open(PLACEHOLDER_PHOTO) as im:
                # pad() fits the photo and fills the rest with its white background
                image = ImageOps.pad(im.convert("RGB"), self.size, Image.LANCZOS,
                                     color=(255, 255, 255))
        except OSError:
            image = AtariLogo.render(self.size)
        self._photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self._photo, text="")

    def show(self, path):
        self._logo, self._path = False, path
        if not (path and path.is_file()):
            self._photo = None
            self.label.configure(image="", text="(no image)")
            return
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                # contain() scales up as well as down, keeping the aspect ratio
                im = ImageOps.contain(im, self.size, Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(im)
        except Exception as e:  # corrupt/unsupported file
            self._photo = None
            self.label.configure(image="", text=f"Cannot load {path.name}: {e}")
            return
        self.label.configure(image=self._photo, text="")
