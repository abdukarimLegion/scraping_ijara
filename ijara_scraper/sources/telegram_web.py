"""Ochiq Telegram kanallar uchun: https://t.me/s/<kanal> veb-preview sahifasini o'qiydi.

Login/API kalit kerak emas, lekin faqat OMMAVIY kanallar (va ommaviy guruhlar emas) ishlaydi.
Yopiq kanal/guruhlar uchun `telegram_live` (Telethon) dan foydalaning.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..http import fetch
from ..models import Listing
from ..utils import extract_phone, extract_price
from .base import PollingSource

_BG_URL = re.compile(r"url\(['\"]?([^'\")]+)['\"]?\)")


def parse_channel_html(html: str, source: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Listing] = []
    for msg in soup.select(".tgme_widget_message[data-post]"):
        post = msg["data-post"]  # "kanal/123"
        text_el = msg.select_one(".tgme_widget_message_text")
        text = ""
        if text_el:
            for br in text_el.find_all("br"):
                br.replace_with("\n")
            text = text_el.get_text().strip()

        images = []
        for el in msg.select(".tgme_widget_message_photo_wrap"):
            m = _BG_URL.search(el.get("style", ""))
            if m:
                images.append(m.group(1))

        posted_at = None
        t = msg.select_one(".tgme_widget_message_date time")
        if t and t.get("datetime"):
            posted_at = datetime.fromisoformat(t["datetime"])

        if not text and not images:
            continue  # servis xabarlari

        price, currency = extract_price(text)
        first_line = text.split("\n", 1)[0][:120]
        out.append(
            Listing(
                source=source,
                external_id=post,
                url=f"https://t.me/{post}",
                title=first_line,
                description=text,
                price=price,
                currency=currency,
                phone=extract_phone(text),
                images=images,
                posted_at=posted_at,
                extra={"channel": post.split("/")[0]},
            )
        )
    return out


class TelegramWebSource(PollingSource):
    """config: channels: [kanal1, kanal2]  (@ belgisiz yoki bilan)."""

    def __init__(self, name: str, cfg: dict[str, Any]) -> None:
        super().__init__(name, cfg)
        self.channels = [c.lstrip("@").strip() for c in cfg.get("channels", [])]
        self.interval = float(cfg.get("interval", 30))

    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        result: list[Listing] = []
        for ch in self.channels:
            r = await fetch(client, f"https://t.me/s/{ch}")
            result.extend(parse_channel_html(r.text, f"{self.name}:{ch}"))
        return result
