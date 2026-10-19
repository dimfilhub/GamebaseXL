"""Display-text helpers."""


PLACEHOLDERS = ("(Unknown)", "(No Publisher)", "(None)", "[uncategorized]")


def clean(v):
    """Hide NULLs and the database's placeholder values."""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in PLACEHOLDERS else s


def year_text(y):
    return str(y) if isinstance(y, int) and 1970 <= y <= 2100 else ""
