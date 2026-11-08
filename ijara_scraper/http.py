from __future__ import annotations

import asyncio
import logging
import random

import httpx

log = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "uz,ru;q=0.9,en;q=0.8",
}


class BlockedError(RuntimeError):
    """Sayt so'rovni bloklagan (403/429/Cloudflare challenge)."""


def make_client(timeout: float = 25.0, proxy: str | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True, proxy=proxy
    )


async def fetch(
    client: httpx.AsyncClient, url: str, *, params: dict | None = None,
    headers: dict | None = None, retries: int = 3,
) -> httpx.Response:
    """GET + qayta urinish. 403/429 uchun BlockedError ko'taradi (aylanib o'tishga urinmaydi)."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = await client.get(url, params=params, headers=headers)
            if r.status_code in (403, 429):
                raise BlockedError(f"{url} -> HTTP {r.status_code}")
            if "Just a moment" in r.text[:2000] and "challenges.cloudflare.com" in r.text[:6000]:
                raise BlockedError(f"{url} -> Cloudflare challenge")
            r.raise_for_status()
            return r
        except BlockedError:
            raise
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            last = e
            await asyncio.sleep((2 ** attempt) + random.random())
    raise RuntimeError(f"{url}: {last}")
