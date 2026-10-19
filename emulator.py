"""Finding atari800, preparing game media and launching games.

GameBase stores per-game emulator options ("Gemus" text such as `model=130xe`,
`basic=yes`, `artifact=ntsc`) written for Altirra. GemusOptions parses them and
Atari800Launcher translates the ones atari800 understands into command-line flags.
"""
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from config import Config
from data_layout import DataLayout


# Keyboard-emulated joystick: atari800 config key suffix -> label shown in Settings.
JOYSTICK_ACTIONS = (("UP", "Up"), ("DOWN", "Down"), ("LEFT", "Left"),
                    ("RIGHT", "Right"), ("TRIGGER", "Fire"))
DEFAULT_JOYSTICK_KEYS = {"UP": "Up", "DOWN": "Down", "LEFT": "Left",
                         "RIGHT": "Right", "TRIGGER": "Space"}
CONTROLLERS = ("keyboard", "joystick")

# Console keys (the Atari's OPTION / SELECT / START buttons). atari800 uses F2-F4, which macOS
# grabs for brightness / Mission Control unless fn is held, so they can be reassigned.
CONSOLE_ACTIONS = (("OPTION", "Option"), ("SELECT", "Select"), ("START", "Start"))
DEFAULT_CONSOLE_KEYS = {"OPTION": "F2", "SELECT": "F3", "START": "F4"}

_SDL_SCANCODE = 1 << 30  # SDL2 keycode of a non-printable key = scancode | this bit
# Key name (as stored in config.json and shown in Settings) -> SDL2 keycode.
SDL_KEYS = {
    "Space": 32, "Return": 13, "Tab": 9, "Backspace": 8, "Delete": 127,
    "Right": _SDL_SCANCODE | 0x4F, "Left": _SDL_SCANCODE | 0x50,
    "Down": _SDL_SCANCODE | 0x51, "Up": _SDL_SCANCODE | 0x52,
    "Insert": _SDL_SCANCODE | 0x49, "Home": _SDL_SCANCODE | 0x4A,
    "PageUp": _SDL_SCANCODE | 0x4B, "End": _SDL_SCANCODE | 0x4D,
    "PageDown": _SDL_SCANCODE | 0x4E,
    "Left Ctrl": _SDL_SCANCODE | 0xE0, "Left Shift": _SDL_SCANCODE | 0xE1,
    "Left Alt": _SDL_SCANCODE | 0xE2, "Right Ctrl": _SDL_SCANCODE | 0xE4,
    "Right Shift": _SDL_SCANCODE | 0xE5, "Right Alt": _SDL_SCANCODE | 0xE6,
}
SDL_KEYS.update({f"Keypad {n}": _SDL_SCANCODE | (0x58 + n if n else 0x62) for n in range(10)})
SDL_KEYS.update({f"F{n}": _SDL_SCANCODE | (0x39 + n) for n in range(1, 13)})


def sdl_keycode(name):
    """SDL2 keycode for a key name such as "Up", "Keypad 4" or "A"; None if unsupported."""
    if name in SDL_KEYS:
        return SDL_KEYS[name]
    if len(name) == 1 and name.isalnum():
        return ord(name.lower())
    return None


def load_controller_settings(config: Config):
    """(controller, joystick_keys) from config.json, with defaults filled in."""
    controller = config.get("controller", "keyboard")
    if controller not in CONTROLLERS:
        controller = "keyboard"
    saved = config.get("joystick_keys", {}) or {}
    keys = {a: saved.get(a) if sdl_keycode(saved.get(a) or "") else d
            for a, d in DEFAULT_JOYSTICK_KEYS.items()}
    return controller, keys


def load_console_keys(config: Config):
    """Console key names from config.json, with defaults filled in."""
    saved = config.get("console_keys", {}) or {}
    return {a: saved.get(a) if sdl_keycode(saved.get(a) or "") else d
            for a, d in DEFAULT_CONSOLE_KEYS.items()}


def config_text(joystick_keys, console_keys):
    """Contents of the private atari800 config. The first line is a header that atari800
    skips, so it must not be a setting."""
    lines = ["Atari 800 Emulator, Version 7.2.1"]
    lines += [f"SDL2_JOY_0_{action}={sdl_keycode(name)}" for action, name in joystick_keys.items()]
    lines += [f"SDL2_{action}_KEY={sdl_keycode(name)}" for action, name in console_keys.items()]
    return "\n".join(lines) + "\n"


class LaunchError(Exception):
    """Raised when a game cannot be launched; the message is user-facing."""


class GemusOptions:
    """Parsed Gemus text: `key=value` lines (keys lowercase); `;` lines are comments."""

    def __init__(self, text=None):
        self.values = {}
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.startswith((";", ":")):
                continue
            key, _, value = line.partition("=")
            self.values[key.strip().lower()] = value.strip().lower()

    def get(self, key, default=""):
        return self.values.get(key, default)

    def is_yes(self, key):
        return self.get(key) in ("yes", "on", "true", "1")


class Atari800Locator:
    def __init__(self, layout: DataLayout, config: Config):
        self.layout = layout
        self.config = config

    @staticmethod
    def normalize(p):
        """Accept an .app bundle and return the real executable inside it."""
        p = Path(p)
        if p.suffix == ".app":
            p = p / "Contents" / "MacOS" / "atari800"
        return p

    def find(self):
        """Locate the atari800 executable: env var, saved config, data/emulator, PATH, usual places."""
        candidates = [os.environ.get("ATARI800_PATH"), self.config.get("emulator"),
                      self.layout.emulator_dir / "atari800.exe",
                      self.layout.emulator_dir / "atari800",
                      shutil.which("atari800"),
                      "/opt/homebrew/bin/atari800",
                      "/usr/local/bin/atari800",
                      "/usr/bin/atari800",
                      r"C:\Program Files\Atari800\atari800.exe",
                      r"C:\Program Files (x86)\Atari800\atari800.exe"]
        for c in candidates:
            if c and self.normalize(c).is_file():
                return self.normalize(c)
        return None

    def remember(self, path):
        """Validate and persist a user-chosen executable; returns it or None."""
        exe = self.normalize(path)
        if not exe.is_file():
            return None
        self.config.set("emulator", str(exe))
        return exe


DISK_EXTS = {".atr", ".atx", ".xfd", ".dcm", ".pro"}
PROGRAM_EXTS = {".xex", ".com", ".exe", ".bas", ".lst"}
CART_EXTS = {".car", ".rom", ".bin"}   # .rom/.bin are raw dumps; .car has a header
TAPE_EXTS = {".cas"}
MEDIA_EXTS = DISK_EXTS | PROGRAM_EXTS | CART_EXTS | TAPE_EXTS

# atari800 -cart-type values for raw cartridge dumps, by file size, when the extra gives no mapper.
RAW_CART_TYPES = {8192: 1, 16384: 2}


class MediaPreparer:
    """Copies a game's media into data/cache/run/<key>, so writes never touch the library."""

    def __init__(self, layout: DataLayout):
        self.layout = layout

    def prepare(self, key, source, file_to_run):
        """Return the list of runnable files: for a zip the member named `file_to_run`
        (or its disk images, or its first program/cartridge/tape); else the file itself.
        Extracting by basename only avoids any path-traversal from zip entries."""
        run_dir = self.layout.cache / "run" / str(key)
        shutil.rmtree(run_dir, ignore_errors=True)
        run_dir.mkdir(parents=True)
        source = Path(source)
        if source.suffix.lower() != ".zip":
            if source.suffix.lower() not in MEDIA_EXTS:
                raise ValueError(f"Unsupported file type: {source.name}")
            target = run_dir / source.name
            shutil.copyfile(source, target)
            return [target]
        with zipfile.ZipFile(source) as z:
            members = [i for i in z.infolist()
                       if not i.is_dir() and Path(i.filename).suffix.lower() in MEDIA_EXTS]
            by_name = sorted(members, key=lambda i: i.filename.lower())
            wanted = None
            if file_to_run:
                wanted = next((i for i in by_name
                               if Path(i.filename).name.lower() == Path(file_to_run).name.lower()), None)
            disks = [i for i in by_name if Path(i.filename).suffix.lower() in DISK_EXTS]
            chosen = [wanted] if wanted else (disks[:2] or by_name[:1])
            if not chosen:
                raise ValueError("No disk image, program, cartridge or tape found in the zip.")
            out = []
            for info in chosen:
                target = run_dir / Path(info.filename).name
                with z.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                out.append(target)
        return out


class Atari800Launcher:
    def __init__(self, layout: DataLayout, preparer: MediaPreparer, config: Config):
        self.layout = layout
        self.preparer = preparer
        self.config = config  # fullscreen and controller settings are read on every launch

    def _rom(self, name):
        rom = self.layout.rom(name)
        if not rom.is_file():
            raise LaunchError(f"ROM not found:\n{rom}\n\nUse Populate folders… to extract the "
                              "Atari-XL zip, or put the ROM there.")
        return str(rom)

    def build_command(self, exe, media, options: GemusOptions, mapper=None):
        """The atari800 command line for `media` (list of prepared files) and Gemus `options`."""
        first = media[0]
        ext = first.suffix.lower()
        model = options.get("model")
        cmd = [str(exe)]

        # Machine and operating system. Default: 800XL with 64 KB.
        if model == "osb":
            cmd += ["-atari", "-osb_rom", self._rom("OSBNTSC.ROM")]
        elif model == "osa":
            cmd += ["-atari", "-osa_rom", self._rom("OSAPAL.ROM")]
        elif model == "130xe":
            cmd += ["-xe", "-xlxe_rom", self._rom("800XE.ROM")]
        elif model == "rambo":
            cmd += ["-rambo", "-xlxe_rom", self._rom("800XE.ROM")]
        else:
            cmd += ["-xl", "-xlxe_rom", self._rom("800XL.ROM")]

        # BASIC: off unless the game asks for it (basic=yes, a BASIC cartridge, or a .bas file).
        cart_basic = options.get("cart")
        rev = options.get("basicrom") or (cart_basic[-1] if cart_basic.startswith("basic") else "")
        if options.is_yes("basic") or cart_basic.startswith("basic") or ext == ".bas":
            rev = rev if rev in ("a", "b", "c") else "b"
            cmd += ["-basic", "-basic_rom", self._rom(f"BASIC-{rev.upper()}.ROM")]
        else:
            cmd += ["-nobasic"]

        # Video and speed.
        cmd += ["-ntsc", "-artif", "1"] if options.get("artifact") == "ntsc" else ["-pal"]
        if options.is_yes("stereo"):
            cmd += ["-stereo"]
        if options.get("turbo") == "on":
            cmd += ["-turbo"]
        if options.get("siopatch") == "off":
            cmd += ["-nopatch"]
        if self.config.get("fullscreen", False):
            cmd += ["-fullscreen"]

        # Controller: the keyboard as joystick 1 (keys are in the private config), or a real
        # gamepad. The keyboard stays off port 2 so its letter keys remain free for typing.
        controller, _keys = load_controller_settings(self.config)
        cmd += ["-kbdjoy0" if controller == "keyboard" else "-no-kbdjoy0", "-no-kbdjoy1"]

        # The media itself.
        if ext in DISK_EXTS:
            cmd += [str(p) for p in media]           # mounted in order: D1:, D2:
        elif ext in PROGRAM_EXTS:
            cmd += ["-run", str(first)]
        elif ext in CART_EXTS:
            cmd += ["-cart", str(first)]
            ctype = int(mapper) if str(mapper or "").isdigit() else None
            if ext != ".car":
                ctype = ctype or RAW_CART_TYPES.get(first.stat().st_size)
                if ctype:
                    cmd += ["-cart-type", str(ctype)]
        elif ext in TAPE_EXTS:
            cmd += ["-tape" if options.get("tape") == "manual" else "-boottape", str(first)]
        return cmd

    def launch(self, exe, key, name, source, file_to_run, gemus=None):
        """Prepare the media of `source` and start atari800 on it."""
        try:
            media = self.preparer.prepare(key, source, file_to_run)
        except (zipfile.BadZipFile, ValueError, OSError) as e:
            raise LaunchError(f"{name}\n\n{e}") from e
        options = GemusOptions(gemus)
        cmd = self.build_command(exe, media, options, options.get("mapper"))
        # A private config keeps atari800 away from the user's ~/.atari800.cfg. It only holds the
        # joystick and console keys; the file must exist or atari800 falls back to ~/.atari800.cfg.
        cfg = self.layout.cache / "atari800.cfg"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        _controller, keys = load_controller_settings(self.config)
        cfg.write_text(config_text(keys, load_console_keys(self.config)))
        cmd[1:1] = ["-config", str(cfg)]
        try:
            subprocess.Popen(cmd, cwd=media[0].parent)
        except OSError as e:
            raise LaunchError(str(e)) from e
