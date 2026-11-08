from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import sys

import yaml

from .notifier import Notifier
from .runner import Runner
from .storage import Storage


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="ijara_scraper")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="doimiy kuzatish (yangi e'lon -> darhol xabar)")
    sub.add_parser("once", help="bir marta yurib chiqish")
    sub.add_parser("stats", help="manbalar bo'yicha e'lonlar soni")
    ex = sub.add_parser("export", help="bazani CSV/JSON'ga chiqarish")
    ex.add_argument("--format", choices=["csv", "json"], default="csv")
    ex.add_argument("--source")
    sub.add_parser("tg-login", help="Telegram akkauntga bir martalik kirish (Telethon)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    cfg = load_config(args.config)
    storage = Storage(cfg.get("database", "listings.db"))

    if args.cmd == "stats":
        for s, c in storage.stats().items():
            print(f"{s:40} {c}")
        print(f"{'JAMI':40} {storage.count()}")
    elif args.cmd == "export":
        rows = list(storage.iter_all(args.source))
        if args.format == "json":
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        else:
            w = csv.writer(sys.stdout)
            cols = ["source", "external_id", "url", "title", "price", "currency",
                    "location", "phone", "posted_at", "first_seen"]
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] for c in cols])
    elif args.cmd == "tg-login":
        from .sources.telegram_live import make_client

        async def login():
            c = make_client(cfg.get("sources", {}).get("telegram_live", {}).get("session", "tg"))
            await c.start()
            me = await c.get_me()
            print("Kirildi:", me.first_name, me.username)
            await c.disconnect()

        asyncio.run(login())
    else:
        runner = Runner(cfg, storage, Notifier(cfg.get("notify")))
        try:
            asyncio.run(runner.run_forever() if args.cmd == "run" else runner.run_once())
        except KeyboardInterrupt:
            pass
