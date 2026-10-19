"""Build a standalone executable for the current OS with PyInstaller (run: python build.py).

Needs: pip install pyinstaller pillow
The database and the data/emulator folder are copied next to the app; the (large) game data
folder is chosen by the user in Settings, or placed next to the app as data/.
"""
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

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
if sys.platform != "darwin":  # Windows/Linux: single executable in dist/, next to the database
    args.append("--onefile")
PyInstaller.__main__.run(args)

# Ship the database and (if populated) the emulator ROMs next to the app, where DataLayout looks for them.
dist = Path("dist")
shutil.copy("atarixl.sqlite3", dist / "atarixl.sqlite3")
if Path("data/emulator").is_dir():
    shutil.copytree("data/emulator", dist / "data" / "emulator", dirs_exist_ok=True)
