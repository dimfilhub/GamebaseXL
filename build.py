"""Build a standalone executable for the current OS with PyInstaller (run: python build.py).

Needs: pip install pyinstaller pillow
The database and the data/emulator folder are copied next to the app; the (large) game data
folder is chosen by the user in Settings, or placed next to the app as data/.
"""
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import PyInstaller.__main__


def make_icon(image, stem):
    """An .icns (macOS) or .ico (Windows) made from `image`; None elsewhere or on failure."""
    if sys.platform not in ("darwin", "win32"):
        return None  # Linux binaries cannot embed an icon
    try:
        from PIL import Image, ImageOps
        with Image.open(image) as im:
            fitted = ImageOps.contain(im.convert("RGBA"), (1024, 1024))
        square = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
        square.paste(fitted, ((1024 - fitted.width) // 2, (1024 - fitted.height) // 2))
        if sys.platform == "win32":
            out = stem.with_suffix(".ico")
            square.save(out, sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
            return out
        out = stem.with_suffix(".icns")
        with tempfile.TemporaryDirectory() as tmp:
            iconset = Path(tmp) / "app.iconset"
            iconset.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale, suffix in ((1, ""), (2, "@2x")):
                    px = size * scale
                    square.resize((px, px), Image.LANCZOS).save(iconset / f"icon_{size}x{size}{suffix}.png")
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
        return out
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


NAME = "GamebaseXL"
separator = ";" if sys.platform == "win32" else ":"
args = [
    "gamebaseXL.py",
    "--name", NAME,
    "--windowed",
    "--noconfirm",
    "--add-data", f"images{separator}images",
    "--add-data", f"README.md{separator}.",
]
# App icon: .ico on Windows, .icns on macOS (Linux binaries cannot embed one).
Path("build").mkdir(exist_ok=True)
icon = make_icon(Path("images/icon.png"), Path("build/app_icon"))
if icon:
    args += ["--icon", str(icon)]
if sys.platform != "darwin":  # Windows/Linux: single executable in dist/, next to the database
    args.append("--onefile")
PyInstaller.__main__.run(args)

if sys.platform == "darwin":
    # PyInstaller writes version 0.0.0 into Info.plist; use the app's own version instead.
    version = re.search(r'^APP_VERSION = "(.+)"', Path("ui/app.py").read_text(), re.M).group(1)
    app = Path("dist") / f"{NAME}.app"
    plist_path = app / "Contents" / "Info.plist"
    plist = plistlib.loads(plist_path.read_bytes())
    plist["CFBundleShortVersionString"] = plist["CFBundleVersion"] = version
    plist_path.write_bytes(plistlib.dumps(plist))
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)

# Ship the database and (if populated) the emulator ROMs next to the app, where DataLayout looks for them.
dist = Path("dist")
shutil.copy("atarixl.sqlite3", dist / "atarixl.sqlite3")
if Path("data/emulator").is_dir():
    shutil.copytree("data/emulator", dist / "data" / "emulator", dirs_exist_ok=True)
