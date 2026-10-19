"""Convert a GameBase .mdb (MS Access) file to a SQLite database using mdb-tools.

The schema comes from `mdb-schema sqlite` (tables, primary keys, indexes) and every
table's rows are loaded with `mdb-export -I sqlite`.

Usage: python3 mdb2sqlite.py [source.mdb] [target.sqlite3]
Requires mdb-tools (brew install mdb-tools).
"""
import sqlite3
import subprocess
import sys
from pathlib import Path


def mdb(*args):
    return subprocess.run(["mdb-" + args[0], *args[1:]], check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


def convert(mdb_path, sqlite_path):
    sqlite_path = Path(sqlite_path)
    sqlite_path.unlink(missing_ok=True)
    conn = sqlite3.connect(sqlite_path)
    conn.executescript(mdb("schema", mdb_path, "sqlite"))
    for table in mdb("tables", "-1", mdb_path).splitlines():
        if not table.strip():
            continue
        # Single quotes for strings, doubled to escape: valid SQL for SQLite.
        sql = mdb("export", "-I", "sqlite", "-q", "'", "-X", "'", "-D", "%Y-%m-%d %H:%M:%S", mdb_path, table)
        conn.executescript(sql)
        print(f"{table}: {conn.execute(f'select count(*) from `{table}`').fetchone()[0]} rows")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "Atari-XL.mdb"
    dst = sys.argv[2] if len(sys.argv) > 2 else "atarixl.sqlite3"
    convert(src, dst)
