from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Iterator

from .models import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    source       TEXT NOT NULL,
    external_id  TEXT NOT NULL,
    url          TEXT,
    title        TEXT,
    description  TEXT,
    price        REAL,
    currency     TEXT,
    location     TEXT,
    phone        TEXT,
    images       TEXT,
    posted_at    TEXT,
    extra        TEXT,
    first_seen   TEXT NOT NULL,
    PRIMARY KEY (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_listings_first_seen ON listings(first_seen);
"""


class Storage:
    """SQLite ombor. `add()` e'lon yangi bo'lsagina True qaytaradi (dublikatlardan himoya)."""

    def __init__(self, path: str = "listings.db") -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    def add(self, l: Listing) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._db:
            cur = self._db.execute(
                """INSERT OR IGNORE INTO listings
                   (source, external_id, url, title, description, price, currency,
                    location, phone, images, posted_at, extra, first_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    l.source, l.external_id, l.url, l.title, l.description, l.price,
                    l.currency, l.location, l.phone,
                    json.dumps(l.images, ensure_ascii=False),
                    l.posted_at.isoformat() if l.posted_at else None,
                    json.dumps(l.extra, ensure_ascii=False, default=str),
                    now,
                ),
            )
            return cur.rowcount == 1

    def count(self, source: str | None = None) -> int:
        with self._lock:
            if source:
                r = self._db.execute("SELECT COUNT(*) FROM listings WHERE source=?", (source,))
            else:
                r = self._db.execute("SELECT COUNT(*) FROM listings")
            return r.fetchone()[0]

    def stats(self) -> dict[str, int]:
        with self._lock:
            rows = self._db.execute(
                "SELECT source, COUNT(*) c FROM listings GROUP BY source ORDER BY c DESC"
            ).fetchall()
        return {r["source"]: r["c"] for r in rows}

    def iter_all(self, source: str | None = None) -> Iterator[dict]:
        q = "SELECT * FROM listings"
        args: tuple = ()
        if source:
            q += " WHERE source=?"
            args = (source,)
        q += " ORDER BY first_seen DESC"
        with self._lock:
            rows = self._db.execute(q, args).fetchall()
        for r in rows:
            d = dict(r)
            d["images"] = json.loads(d["images"] or "[]")
            d["extra"] = json.loads(d["extra"] or "{}")
            yield d

    def close(self) -> None:
        self._db.close()
