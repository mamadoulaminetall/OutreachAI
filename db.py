import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "outreach.db")


@contextmanager
def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS prospects (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                email            TEXT NOT NULL,
                company          TEXT,
                role             TEXT,
                context          TEXT,
                product          TEXT,
                generated_email  TEXT,
                status           TEXT DEFAULT 'draft',
                notes            TEXT,
                date_added       TEXT DEFAULT (datetime('now')),
                date_sent        TEXT,
                date_replied     TEXT,
                revenue_attributed REAL DEFAULT 0
            )
        """)


def add_prospect(name, email, company, role, context, product, generated_email=""):
    with _conn() as con:
        con.execute(
            """INSERT OR IGNORE INTO prospects
               (name, email, company, role, context, product, generated_email)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, email, company, role, context, product, generated_email),
        )


def get_all_prospects():
    with _conn() as con:
        rows = con.execute("SELECT * FROM prospects ORDER BY date_added DESC").fetchall()
        return [dict(r) for r in rows]


def update_prospect(pid, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [pid]
    with _conn() as con:
        con.execute(f"UPDATE prospects SET {sets} WHERE id = ?", vals)


def delete_prospect(pid):
    with _conn() as con:
        con.execute("DELETE FROM prospects WHERE id = ?", (pid,))


def get_stats():
    with _conn() as con:
        total     = con.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        sent      = con.execute("SELECT COUNT(*) FROM prospects WHERE status='sent'").fetchone()[0]
        replied   = con.execute("SELECT COUNT(*) FROM prospects WHERE status='replied'").fetchone()[0]
        converted = con.execute("SELECT COUNT(*) FROM prospects WHERE status='converted'").fetchone()[0]
        revenue   = con.execute(
            "SELECT COALESCE(SUM(revenue_attributed),0) FROM prospects WHERE status='converted'"
        ).fetchone()[0]
    return {
        "total": total, "sent": sent,
        "replied": replied, "converted": converted, "revenue": revenue,
    }
