from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx

from ..models import Listing

OnListing = Callable[[Listing], Awaitable[None]]


class PollingSource(ABC):
    """Davriy so'raladigan manba: runner har `interval` soniyada `fetch()` ni chaqiradi."""

    def __init__(self, name: str, cfg: dict[str, Any]) -> None:
        self.name = name
        self.cfg = cfg
        self.interval: float = float(cfg.get("interval", 60))

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        """Eng so'nggi e'lonlarni qaytaradi (yangi-dan eskiga yoki aksincha — farqi yo'q)."""


class PushSource(ABC):
    """Real-time manba (Telegram Telethon): yangi xabar kelishi bilan `emit` chaqiriladi."""

    def __init__(self, name: str, cfg: dict[str, Any]) -> None:
        self.name = name
        self.cfg = cfg

    @abstractmethod
    async def run(self, emit: OnListing) -> None:
        """Doimiy ishlaydi; har bir yangi e'lon uchun `await emit(listing)`."""
