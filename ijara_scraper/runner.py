from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from .http import BlockedError, make_client
from .models import Listing
from .notifier import Notifier
from .sources import build_source
from .sources.base import PollingSource, PushSource
from .storage import Storage
from .utils import matches_filters

log = logging.getLogger(__name__)


class Runner:
    def __init__(self, config: dict[str, Any], storage: Storage, notifier: Notifier) -> None:
        self.config = config
        self.storage = storage
        self.notifier = notifier
        self.filters = config.get("filters") or {}
        self.sources = [
            build_source(name, cfg)
            for name, cfg in (config.get("sources") or {}).items()
            if cfg.get("enabled", True)
        ]

    async def handle(self, l: Listing, *, notify: bool = True) -> bool:
        """Saqlaydi; yangi bo'lsa (va filtrdan o'tsa) xabar beradi. Yangi bo'lsa True."""
        f = {**self.filters, **(self._cfg_of(l.source).get("filters") or {})}
        if not matches_filters(l.text, f.get("include", []), f.get("exclude", [])):
            return False
        is_new = self.storage.add(l)
        if is_new and notify:
            await self.notifier.notify(l)
        return is_new

    def _cfg_of(self, source_key: str) -> dict:
        base = source_key.split(":", 1)[0]
        return (self.config.get("sources") or {}).get(base, {})

    async def poll_once(self, src: PollingSource, client: httpx.AsyncClient) -> int:
        listings = await src.fetch(client)
        # Birinchi yurishda (yangi manba/kanal) eski e'lonlar bilan spam qilmaslik: jim saqlaymiz.
        fresh = set()
        if not self.config.get("notify_on_first_run", False):
            fresh = {s for s in {l.source for l in listings} if self.storage.count(s) == 0}
        new = 0
        silent = bool(fresh)
        # eskidan yangiga qarab xabar berish
        for l in sorted(listings, key=lambda x: x.posted_at.timestamp() if x.posted_at else 0):
            if await self.handle(l, notify=l.source not in fresh):
                new += 1
        log.info("%s: %d ta e'lon, %d ta yangi%s", src.name, len(listings), new,
                 " (yangi manba — birinchi yurish jim)" if silent else "")
        return new

    async def _poll_loop(self, src: PollingSource, client: httpx.AsyncClient) -> None:
        backoff = 0.0
        while True:
            try:
                await self.poll_once(src, client)
                backoff = 0.0
            except BlockedError as e:
                backoff = min(max(backoff * 2, 300), 3600)
                log.error("%s bloklandi: %s — %ds kutamiz", src.name, e, backoff)
            except Exception as e:
                backoff = min(max(backoff * 2, 30), 900)
                log.exception("%s xato: %s — %ds kutamiz", src.name, e, backoff)
            await asyncio.sleep(src.interval + backoff + random.uniform(0, src.interval * 0.1))

    async def _push_loop(self, src: PushSource) -> None:
        async def emit(l: Listing) -> None:
            await self.handle(l)

        while True:
            try:
                await src.run(emit)
            except Exception as e:
                log.exception("%s uzildi: %s — 30s dan keyin qayta ulanamiz", src.name, e)
            await asyncio.sleep(30)

    async def run_forever(self) -> None:
        async with make_client(proxy=self.config.get("proxy")) as client:
            tasks = []
            for s in self.sources:
                if isinstance(s, PollingSource):
                    tasks.append(asyncio.create_task(self._poll_loop(s, client)))
                else:
                    tasks.append(asyncio.create_task(self._push_loop(s)))
            if not tasks:
                raise SystemExit("config.yaml'da yoqilgan manba yo'q")
            await asyncio.gather(*tasks)

    async def run_once(self) -> int:
        total = 0
        async with make_client(proxy=self.config.get("proxy")) as client:
            for s in self.sources:
                if isinstance(s, PollingSource):
                    try:
                        total += await self.poll_once(s, client)
                    except Exception as e:
                        log.error("%s: %s", s.name, e)
        return total
