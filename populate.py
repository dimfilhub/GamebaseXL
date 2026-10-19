"""Extract the zips in sources/ into the data/ tree.

Usage: python3 populate.py [--dry-run]
"""
import sys
import zipfile
from pathlib import Path

from data_layout import DataLayout

SOURCES_URL = "https://forums.atariage.com/topic/326710-atari-800-gamebases-gamepacks-%E2%80%93-links-working-2021/"
PROGRESS_EVERY = 2000  # files


class Populator:
    """Existing files with the same size are skipped, so it can be re-run safely."""

    def __init__(self, layout: DataLayout, log=print):
        self.layout = layout
        self.log = log  # callable(str) receiving progress lines

    @property
    def plan(self):
        """zip name -> [(zip-internal prefix to strip, destination folder, only these
        extensions or None)]. Entries outside a prefix are ignored."""
        l = self.layout
        return {
            "Atari-XL GB.zip": [
                ("Atari-XL/Games/",       l.games,       None),
                ("Atari-XL/screenshots/", l.screenshots, None),
                ("Atari-XL/Music/",       l.music_dir,   None),
                ("Atari-XL/Altirra/",     l.emulator_dir, {".rom"}),  # OS and BASIC ROMs only
            ],
            "Extras.zip":                [("Extras/", l.extras_dir, None)],
            "EXTRAS-Manuals_(0-E).zip":  [("", l.extras_dir / "manuals", None)],
            "EXTRAS-Manuals_(F-O).zip":  [("", l.extras_dir / "manuals", None)],
            "EXTRAS-Manuals_(P-Z).zip":  [("", l.extras_dir / "manuals", None)],
        }

    def check_sources(self, folder=None):
        """Compare `folder` (default: the sources folder) with the zips the plan expects.
        Returns (found, missing, broken, extra) lists of zip names."""
        folder = Path(folder or self.layout.sources)
        present = {p.name for p in folder.iterdir() if p.is_file()} if folder.is_dir() else set()
        expected = list(self.plan)
        found = [n for n in expected if n in present]
        broken = [n for n in found if not zipfile.is_zipfile(folder / n)]
        found = [n for n in found if n not in broken]
        missing = [n for n in expected if n not in present]
        extra = sorted(n for n in present - set(expected) if n.lower().endswith(".zip"))
        return found, missing, broken, extra

    def extract(self, zip_path, rules, dry=False):
        n = skipped = 0
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                name = info.filename
                if info.is_dir() or name.startswith("__MACOSX") or name.endswith(".DS_Store"):
                    continue
                rule = next((r for r in rules if name.startswith(r[0])
                             and (r[2] is None or Path(name).suffix.lower() in r[2])), None)
                if rule is None:
                    continue
                prefix, dest, _exts = rule
                target = (dest / Path(name[len(prefix):])).resolve()
                if dest.resolve() not in target.parents:  # zip-slip guard
                    self.log(f"  skip unsafe path: {name}")
                    continue
                if target.exists() and target.stat().st_size == info.file_size:
                    skipped += 1
                    continue
                n += 1
                if not dry:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src, open(target, "wb") as out:
                        while chunk := src.read(1 << 20):
                            out.write(chunk)
                    if n % PROGRESS_EVERY == 0:
                        self.log(f"  ...{n} files")
        return n, skipped

    def run(self, dry=False):
        for zname, rules in self.plan.items():
            zp = self.layout.sources / zname
            if not zp.exists():
                self.log(f"missing: {zname}")
                continue
            n, s = self.extract(zp, rules, dry)
            self.log(f"{zname}: {'would extract' if dry else 'extracted'} {n}, skipped {s}")


if __name__ == "__main__":
    Populator(DataLayout()).run(dry="--dry-run" in sys.argv)
