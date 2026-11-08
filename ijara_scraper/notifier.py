from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .models import Listing

log = logging.getLogger(__name__)


def format_listing(l: Listing) -> str:
    price = f"{l.price:,.0f} {l.currency or ''}".strip() if l.price else "narx ko'rsatilmagan"
    lines = [f"🆕 [{l.source}] {l.title or '(sarlavhasiz)'}", f"💰 {price}"]
    if l.location:
        lines.append(f"📍 {l.location}")
    if l.phone:
        lines.append(f"📞 {l.phone}")
    lines.append(l.url)
    return "\n".join(lines)


class Notifier:
    """Yangi e'lon topilganda xabar yuboradi: konsol, Telegram bot, webhook."""

    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        cfg = cfg or {}
        self.console = cfg.get("console", True)
        self.bot_token = os.environ.get("BOT_TOKEN") or (cfg.get("telegram") or {}).get("bot_token")
        self.chat_id = os.environ.get("BOT_CHAT_ID") or (cfg.get("telegram") or {}).get("chat_id")
        self.webhook = os.environ.get("WEBHOOK_URL") or cfg.get("webhook")
        self._client = httpx.AsyncClient(timeout=15)

    async def notify(self, l: Listing) -> None:
        text = format_listing(l)
        if self.console:
            print(text, "\n", flush=True)
        if self.bot_token and self.chat_id:
            await self._safe(
                self._client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": text[:4000]},
                )
            )
        if self.webhook:
            await self._safe(self._client.post(self.webhook, json=l.to_dict()))

    async def _safe(self, coro) -> None:
        try:
            r = await coro
            r.raise_for_status()
        except Exception as e:  # bildirishnoma xatosi scraping'ni to'xtatmasligi kerak
            log.warning("notify xatosi: %s", e)

    async def aclose(self) -> None:
        await self._client.aclose()
