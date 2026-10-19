"""All SQL access to atarixl.sqlite3."""
import sqlite3

from models import Extra, Game, GameDetails

LIST_SQL = """
SELECT g.GA_Id, g.Name, y.Year, p.Publisher, ge.Genre, pg.ParentGenre,
       g.Filename, g.ScrnshotFilename, g.SidFilename, dv.Developer
FROM Games g
LEFT JOIN Years y      ON y.YE_Id = g.YE_Id
LEFT JOIN Publishers p ON p.PU_Id = g.PU_Id
LEFT JOIN Developers dv ON dv.DE_Id = g.DE_Id
LEFT JOIN Genres ge    ON ge.GE_Id = g.GE_Id
LEFT JOIN PGenres pg   ON pg.PG_Id = ge.PG_Id
ORDER BY g.Name COLLATE NOCASE
"""

DETAIL_SQL = """
SELECT g.Name, y.Year, p.Publisher, dv.Developer, pr.Programmer, ar.Artist,
       mu.Musician, ge.Genre, la.Language, li.License, cr.Cracker,
       g.PlayersFrom, g.PlayersTo, g.Rating, g.Control, g.Version,
       g.Comment, g.MemoText, g.WebLink_Name, g.WebLink_URL
FROM Games g
LEFT JOIN Years y       ON y.YE_Id = g.YE_Id
LEFT JOIN Publishers p  ON p.PU_Id = g.PU_Id
LEFT JOIN Developers dv ON dv.DE_Id = g.DE_Id
LEFT JOIN Programmers pr ON pr.PR_Id = g.PR_Id
LEFT JOIN Artists ar    ON ar.AR_Id = g.AR_Id
LEFT JOIN Musicians mu  ON mu.MU_Id = g.MU_Id
LEFT JOIN Genres ge     ON ge.GE_Id = g.GE_Id
LEFT JOIN Languages la  ON la.LA_Id = g.LA_Id
LEFT JOIN Licenses li   ON li.LI_Id = g.LI_Id
LEFT JOIN Crackers cr   ON cr.CR_Id = g.CR_Id
WHERE g.GA_Id = ?
"""


class GameRepository:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def close(self):
        self.conn.close()

    def list_games(self):
        return [Game(*row) for row in self.conn.execute(LIST_SQL)]

    def details(self, ga_id):
        row = self.conn.execute(DETAIL_SQL, (ga_id,)).fetchone()
        return GameDetails(*row) if row else None

    def extras(self, ga_id):
        rows = self.conn.execute(
            "SELECT EX_Id, Name, Path, Type, Data, FileToRun FROM Extras "
            "WHERE GA_Id=? ORDER BY DisplayOrder", (ga_id,))
        return [Extra(*r) for r in rows]

    def cover_paths(self, ga_id):
        """Raw DB paths of the game's cover scans ('Cover', 'Cover (Disk)', ...), best first."""
        rows = self.conn.execute(
            "SELECT Path FROM Extras WHERE GA_Id=? AND Type=0 AND Name LIKE 'Cover%' "
            "ORDER BY (Name <> 'Cover'), DisplayOrder", (ga_id,))
        return [r[0] for r in rows]

    def launch_options(self, ga_id):
        """(FileToRun, Gemus emulator options) of a game; (None, None) if unknown."""
        row = self.conn.execute(
            "SELECT FileToRun, Gemus FROM Games WHERE GA_Id=?", (ga_id,)).fetchone()
        return row if row else (None, None)

    def referenced_paths(self):
        """Yield (GA_Id, kind, raw_db_path) for every file the DB references."""
        for ga_id, fn, sc, snd in self.conn.execute(
                "SELECT GA_Id, Filename, ScrnshotFilename, SidFilename FROM Games"):
            yield ga_id, "game", fn
            yield ga_id, "screenshot", sc
            yield ga_id, "music", snd
        for ga_id, path in self.conn.execute("SELECT GA_Id, Path FROM Extras"):
            yield ga_id, "extra", path
