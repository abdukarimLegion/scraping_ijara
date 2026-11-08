"""Telegram kanal VA guruhlarni real-time kuzatish (Telethon, foydalanuvchi akkaunti orqali).

Xabar kelishi bilan darhol ishlaydi (polling yo'q). Yopiq guruh/kanallar ham ishlaydi —
akkaunt ularning a'zosi bo'lishi kerak.

Kerak: https://my.telegram.org -> API development tools -> api_id va api_hash.
Muhit o'zgaruvchilari: TG_API_ID, TG_API_HASH. Birinchi ishga tushishda telefon/kod so'raladi:
    python -m ijara_scraper tg-login
"""
from __future__ import annotations

import os
from typing import Any

from ..models import Listing
from ..utils import extract_phone, extract_price
from .base import OnListing, PushSource


def message_to_listing(source: str, chat_username: str | None, chat_id: int, msg_id: int,
                       text: str, date, has_photo: bool) -> Listing | None:
    if not text and not has_photo:
        return None
    if chat_username:
        url = f"https://t.me/{chat_username}/{msg_id}"
    else:
        cid = str(abs(chat_id))
        cid = cid[3:] if cid.startswith("100") else cid
        url = f"https://t.me/c/{cid}/{msg_id}"
    price, cur = extract_price(text)
    return Listing(
        source=source, external_id=f"{chat_id}/{msg_id}", url=url,
        title=text.split("\n", 1)[0][:120], description=text, price=price, currency=cur,
        phone=extract_phone(text), posted_at=date,
        extra={"chat": chat_username or chat_id, "has_photo": has_photo},
    )


def make_client(session: str):
    try:
        from telethon import TelegramClient
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("`pip install telethon` kerak") from e
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise RuntimeError("TG_API_ID va TG_API_HASH muhit o'zgaruvchilarini o'rnating")
    return TelegramClient(session, int(api_id), api_hash)


class TelegramLiveSource(PushSource):
    """config: session (default 'tg'), chats: [username | invite | id] (bo'sh = barcha chatlar)."""

    async def run(self, emit: OnListing) -> None:
        from telethon import events

        client = make_client(self.cfg.get("session", "tg"))
        await client.start()  # sessiya fayli bo'lmasa interaktiv login so'raydi
        chats: list[Any] | None = self.cfg.get("chats") or None

        @client.on(events.NewMessage(chats=chats))
        async def handler(event):  # noqa: ANN001
            chat = await event.get_chat()
            listing = message_to_listing(
                self.name, getattr(chat, "username", None), event.chat_id, event.id,
                event.raw_text or "", event.date, bool(event.photo),
            )
            if listing:
                await emit(listing)

        await client.run_until_disconnected()
