"""Map relative paths stored in atarixl.sqlite3 to files under data/.

The database uses Windows-style backslash paths. DataLayout converts them
to a real path inside the matching data/ sub-folder.
"""
import os
import sys
import unicodedata
from pathlib import Path

from config import Config

# Bundled read-only resources (images/...) live next to the code, or in PyInstaller's bundle.
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _app_root():
    """Folder holding the writable files (database, config.json, data/)."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent
    exe = Path(sys.executable).resolve()
    # macOS: <folder>/GamebaseXL.app/Contents/MacOS/GamebaseXL -> <folder>
    return exe.parents[3] if sys.platform == "darwin" and exe.parents[2].suffix == ".app" else exe.parent


PROJECT_ROOT = _app_root()


def _nfc(s):
    """macOS may store names decomposed (NFD), Windows composed (NFC)."""
    return unicodedata.normalize("NFC", s)


class DataLayout:
    def __init__(self, root=PROJECT_ROOT, data=None):
        self.root = Path(root)
        self.db_path = self.root / "atarixl.sqlite3"
        self.config_file = self.root / "config.json"
        # Data location: argument > GAMEBASE_DATA=/path/to/data > folder chosen in the app > ./data
        saved = Config(self.config_file)
        self._set_data(data or os.environ.get("GAMEBASE_DATA") or saved.get("data_dir")
                       or self.root / "data")
        self.sources = Path(saved.get("sources_dir") or self.root / "sources").expanduser()

    def _set_data(self, data):
        self.data = Path(data).expanduser()
        self.games = self.data / "games"
        self.screenshots = self.data / "screenshots"
        self.music_dir = self.data / "music"
        self.extras_dir = self.data / "extras"
        self.cache = self.data / "cache"
        self.emulator_dir = self.data / "emulator"   # OS and BASIC ROMs (+ atari800.exe on Windows)

    def set_data(self, data):
        """Use another data folder from now on and remember it in config.json."""
        self._set_data(data)
        Config(self.config_file).set("data_dir", str(self.data))

    def set_sources(self, sources):
        """Look for the zips in another folder and remember it in config.json."""
        self.sources = Path(sources).expanduser()
        Config(self.config_file).set("sources_dir", str(self.sources))

    @property
    def all_dirs(self):
        return [self.emulator_dir, self.games, self.screenshots, self.music_dir,
                self.extras_dir, self.cache]

    @staticmethod
    def _rel(db_path):
        """'xex\\G\\Game.xex' -> Path('xex/G/Game.xex'); None for empty values."""
        if not db_path:
            return None
        return Path(*[_nfc(p) for p in db_path.replace("\\", "/").split("/") if p])

    def resolve(self, path):
        """Return the real on-disk path for `path`, matching each component
        case-insensitively and NFC/NFD-insensitively. If nothing matches,
        return `path` unchanged (so callers can still create it)."""
        if path is None or path.exists():
            return path
        try:
            rel = path.relative_to(self.data)
        except ValueError:
            return path
        cur = self.data
        for part in rel.parts:
            nxt = cur / part
            if not nxt.exists():
                try:
                    want = _nfc(part).casefold()
                    nxt = next((c for c in cur.iterdir()
                                if _nfc(c.name).casefold() == want), None)
                except OSError:
                    nxt = None
                if nxt is None:
                    return path
            cur = nxt
        return cur

    def _under(self, base, db_path):
        rel = self._rel(db_path)
        return self.resolve(base / rel) if rel else None

    def game_file(self, filename):
        """Games.Filename -> data/games/..."""
        return self._under(self.games, filename)

    def screenshot(self, filename):
        """Games.ScrnshotFilename -> data/screenshots/..."""
        return self._under(self.screenshots, filename)

    def music(self, filename):
        """Games.SidFilename -> data/music/..."""
        return self._under(self.music_dir, filename)

    def extra(self, path):
        """Extras.Path -> data/extras/... (documents, covers, carts, original disks/tapes,
        manuals/...) or, for the few extras that sit beside the games, data/games/..."""
        rel = self._rel(path)
        if rel is None:
            return None
        first = self.resolve(self.extras_dir / rel)
        if first.exists():
            return first
        second = self.resolve(self.games / rel)
        return second if second.exists() else first

    def rom(self, name):
        """An emulator ROM (800XL.ROM, BASIC-B.ROM, ...) in data/emulator."""
        return self.resolve(self.emulator_dir / name)

    def resolver_for(self, kind):
        return {"game": self.game_file, "screenshot": self.screenshot,
                "music": self.music, "extra": self.extra}[kind]
