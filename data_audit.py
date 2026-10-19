"""Create the data/ folder tree and report files the DB references but are missing."""
from data_layout import DataLayout
from populate import SOURCES_URL
from repository import GameRepository


class DataAudit:
    def __init__(self, layout: DataLayout, repo: GameRepository):
        self.layout = layout
        self.repo = repo

    def make_folders(self):
        """Create data/ tree: fixed folders plus the sub-folders the DB references."""
        layout = self.layout
        for d in layout.all_dirs:
            d.mkdir(parents=True, exist_ok=True)
        for _ga_id, kind, value in self.repo.referenced_paths():
            p = layout.resolver_for(kind)(value)
            # Skip deep HardDisk trees; they are created on demand.
            if p and len(p.relative_to(layout.data).parts) <= 4:
                p.parent.mkdir(parents=True, exist_ok=True)

    def startup_problem(self):
        """Create the folder tree; return a message if the data still needs populating, else None."""
        layout = self.layout
        try:
            self.make_folders()
        except OSError as e:
            return f"Cannot create the data folders under:\n{layout.data}\n\n{e}"
        if any(p.is_file() for p in layout.games.rglob("*")):
            return None
        zips = sorted(layout.sources.glob("*.zip")) if layout.sources.is_dir() else []
        if zips:
            return (f"No game files found in:\n{layout.games}\n\n"
                    f"{len(zips)} zip(s) are waiting in sources/. Run:\n    python3 populate.py")
        return (f"No game files found in:\n{layout.games}\n\n"
                "Put the source zips in sources/ and run:\n    python3 populate.py\n\n"
                f"The sources are available from the GameBase Atari XL project on the AtariAge forum:\n{SOURCES_URL}\n"
                "All credit goes to the GameBase project and its contributors.")

    def missing(self, limit=None):
        """Yield (GA_Id, kind, path) for referenced files not present on disk."""
        n = 0
        for ga_id, kind, value in self.repo.referenced_paths():
            p = self.layout.resolver_for(kind)(value)
            if p and not p.exists():
                yield ga_id, kind, p
                n += 1
                if limit and n >= limit:
                    return


if __name__ == "__main__":
    _layout = DataLayout()
    _repo = GameRepository(_layout.db_path)
    try:
        DataAudit(_layout, _repo).make_folders()
    finally:
        _repo.close()
    print(f"Folders created under {_layout.data}")
