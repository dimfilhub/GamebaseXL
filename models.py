"""Plain data objects returned by the repository."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from text import clean, year_text


@dataclass(frozen=True)
class Game:
    """One row of the game list."""
    id: int
    name: str
    year: Optional[int]
    publisher: Optional[str]
    genre: Optional[str]
    parent_genre: Optional[str]
    filename: Optional[str]
    screenshot_filename: Optional[str]
    sid_filename: Optional[str]
    developer: Optional[str]

    @property
    def year_text(self):
        return year_text(self.year)

    @property
    def publisher_text(self):
        return clean(self.publisher)

    @property
    def genre_text(self):
        return clean(self.genre)

    @property
    def developer_text(self):
        return clean(self.developer)


@dataclass(frozen=True)
class GameDetails:
    """Full record shown in the Info / Notes tabs."""
    name: str
    year: Optional[int]
    publisher: Optional[str]
    developer: Optional[str]
    programmer: Optional[str]
    artist: Optional[str]
    musician: Optional[str]
    genre: Optional[str]
    language: Optional[str]
    license: Optional[str]
    cracker: Optional[str]
    players_from: Optional[int]
    players_to: Optional[int]
    rating: Optional[int]
    control: Optional[str]
    version: Optional[str]
    comment: Optional[str]
    memo: Optional[str]
    weblink_name: Optional[str]
    weblink_url: Optional[str]

    @property
    def players(self):
        if not self.players_from:
            return ""
        if self.players_from == self.players_to or not self.players_to:
            return str(self.players_from)
        return f"{self.players_from}-{self.players_to}"

    @property
    def notes(self):
        return "\n\n".join(x for x in (clean(self.comment), clean(self.memo)) if x)


@dataclass(frozen=True)
class Extra:
    id: int
    name: str
    path: Optional[str]
    type: int = 0                    # 0 = document / image / video, 1 = runnable in the emulator
    data: Optional[str] = None       # "|~|"-separated record; field 7 holds emulator options
    file_to_run: Optional[str] = None

    @property
    def runnable(self):
        return self.type == 1

    @property
    def options(self):
        """Emulator options (Gemus text) of a runnable extra, or ''."""
        parts = (self.data or "").split("|~|")
        return parts[7] if len(parts) > 7 else ""


@dataclass(frozen=True)
class ExtraFile:
    """An Extra resolved against the data folder."""
    extra: Extra
    path: Optional[Path]

    @property
    def exists(self):
        return bool(self.path) and self.path.is_file()

    @property
    def runnable(self):
        return self.exists and self.extra.runnable
