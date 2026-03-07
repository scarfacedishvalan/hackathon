import sqlite3
import json
import pathlib

DB_PATH = pathlib.Path(__file__).resolve().parents[3] / "data" / "portfolios.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id       TEXT PRIMARY KEY,
                name     TEXT NOT NULL,
                holdings TEXT NOT NULL
            )
        """)
        conn.commit()


def seed_portfolios(portfolios: list) -> None:
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM portfolios").fetchone()[0]
        if count == 0:
            for p in portfolios:
                conn.execute(
                    "INSERT OR IGNORE INTO portfolios (id, name, holdings) VALUES (?,?,?)",
                    (p["id"], p["name"], json.dumps(p["holdings"]))
                )
            conn.commit()
