"""Sozlanadigan umumiy manbalar — birbir.uz, joyme.uz va boshqa saytlar uchun.

Selektorlar/yo'llar config.yaml'da beriladi, shuning uchun sayt o'zgarsa kodni emas, configni
tuzatasiz.

`render: true` bo'lsa sahifa Playwright (oddiy brauzer) orqali yuklanadi — JS bilan chizilgan
saytlar uchun. Cloudflare "Just a moment" challenge'ini aylanib o'tishga URINILMAYDI: bunday
holatda BlockedError ko'tariladi.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..http import BlockedError, fetch
from ..models import Listing
from ..utils import extract_phone, extract_price
from .base import PollingSource


def _dig(obj: Any, path: str | None) -> Any:
    """'a.b.0.c' ko'rinishidagi yo'l bo'yicha ichma-ich qiymat olish."""
    if not path:
        return None
    for part in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def parse_json_items(payload: Any, source: str, cfg: dict[str, Any]) -> list[Listing]:
    f = cfg["fields"]
    items = _dig(payload, cfg.get("items_path")) if cfg.get("items_path") else payload
    out: list[Listing] = []
    for it in items or []:
        ext = _dig(it, f["id"])
        if ext is None:
            continue
        url = _dig(it, f.get("url")) or ""
        if "url_template" in cfg:
            url = cfg["url_template"].format(id=ext)
        title = str(_dig(it, f.get("title")) or "")
        desc = str(_dig(it, f.get("description")) or "")
        price = _dig(it, f.get("price"))
        try:
            price = float(price) if price is not None else None
        except (TypeError, ValueError):
            price = None
        images = _dig(it, f.get("image"))
        out.append(
            Listing(
                source=source, external_id=str(ext), url=url, title=title, description=desc,
                price=price, currency=cfg.get("currency"),
                location=_dig(it, f.get("location")),
                phone=extract_phone(desc) or _dig(it, f.get("phone")),
                images=[images] if isinstance(images, str) else list(images or []),
                extra={"raw": it},
            )
        )
    return out


def parse_html_items(html: str, source: str, cfg: dict[str, Any], base_url: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    sel = cfg["selectors"]
    out: list[Listing] = []
    for card in soup.select(sel["item"]):
        a = card if card.name == "a" else card.select_one(sel.get("link", "a"))
        if not a or not a.get("href"):
            continue
        url = urljoin(base_url, a["href"])
        m = re.search(cfg.get("id_regex", r"(\d{5,})"), url)
        ext = m.group(1) if m else hashlib.sha1(url.encode()).hexdigest()[:16]

        def txt(key: str) -> str:
            el = card.select_one(sel[key]) if sel.get(key) else None
            return el.get_text(" ", strip=True) if el else ""

        title = txt("title") or a.get_text(" ", strip=True)
        price_text = txt("price")
        price, cur = extract_price(price_text)
        img = card.select_one(sel["image"]) if sel.get("image") else None
        out.append(
            Listing(
                source=source, external_id=ext, url=url, title=title,
                description=txt("description"), price=price,
                currency=cur or cfg.get("currency"), location=txt("location") or None,
                phone=extract_phone(card.get_text(" ")),
                images=[urljoin(base_url, img["src"])] if img is not None and img.get("src") else [],
            )
        )
    return out


class _FetchMixin:
    cfg: dict[str, Any]

    async def _get(self, client: httpx.AsyncClient, url: str, params: dict | None = None):
        if self.cfg.get("render"):
            return await _render(url), None
        r = await fetch(client, url, params=params, headers=self.cfg.get("headers"))
        return None, r


async def _render(url: str) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("render: true uchun `pip install playwright && playwright install chromium`") from e
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        html = await page.content()
        await browser.close()
    if "challenges.cloudflare.com" in html and "Just a moment" in html:
        raise BlockedError(f"{url} -> Cloudflare challenge")
    return html


class JsonApiSource(_FetchMixin, PollingSource):
    """config: url, params?, items_path, fields: {id,title,description,price,url,image,location}."""

    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        _, r = await self._get(client, self.cfg["url"], self.cfg.get("params"))
        return parse_json_items(r.json(), self.name, self.cfg)


class HtmlListSource(_FetchMixin, PollingSource):
    """config: url (yoki urls: [...]), selectors: {item, link?, title?, price?, ...}."""

    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        urls = self.cfg.get("urls") or [self.cfg["url"]]
        out: list[Listing] = []
        for u in urls:
            html, r = await self._get(client, u)
            out.extend(parse_html_items(html or r.text, self.name, self.cfg, u))
        return out
