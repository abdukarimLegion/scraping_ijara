"""OLX.uz — ommaviy JSON API (`/api/v1/offers/`) orqali.

DIQQAT: bu modul yozilgan paytda OLX (CloudFront) ishlab chiqish muhitidagi IP'ga 403 qaytargan,
shuning uchun maydon nomlari jonli javobda tekshirilmagan. `tests/fixtures/olx_offers.json`
taxminiy javob; birinchi ishga tushirishda haqiqiy javobga qarab moslang.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..http import fetch
from ..models import Listing
from ..utils import extract_phone
from .base import PollingSource

API = "https://www.olx.uz/api/v1/offers/"


def _param(params: list[dict], key: str) -> dict | None:
    for p in params or []:
        if p.get("key") == key:
            return p.get("value")
    return None


def parse_offers(payload: dict, source: str) -> list[Listing]:
    out: list[Listing] = []
    for o in payload.get("data", []):
        price = _param(o.get("params", []), "price") or {}
        loc = o.get("location") or {}
        loc_s = ", ".join(
            x for x in (
                (loc.get("region") or {}).get("name"),
                (loc.get("city") or {}).get("name"),
                (loc.get("district") or {}).get("name"),
            ) if x
        ) or None
        posted = o.get("created_time") or o.get("last_refresh_time")
        desc = o.get("description") or ""
        out.append(
            Listing(
                source=source,
                external_id=str(o["id"]),
                url=o.get("url", ""),
                title=o.get("title", ""),
                description=desc,
                price=price.get("value"),
                currency=price.get("currency"),
                location=loc_s,
                phone=extract_phone(desc),
                images=[
                    p["link"].replace("{width}", "800").replace("{height}", "600")
                    for p in o.get("photos", []) if p.get("link")
                ],
                posted_at=datetime.fromisoformat(posted) if posted else None,
                extra={"user_id": (o.get("user") or {}).get("id")},
            )
        )
    return out


class OlxSource(PollingSource):
    """config: category_id, region_id?, city_id?, query?, limit (default 40)."""

    async def fetch(self, client: httpx.AsyncClient) -> list[Listing]:
        params: dict[str, Any] = {
            "offset": 0,
            "limit": self.cfg.get("limit", 40),
            "sort_by": "created_at:desc",
        }
        for k in ("category_id", "region_id", "city_id", "district_id", "query"):
            if self.cfg.get(k) is not None:
                params[k] = self.cfg[k]
        r = await fetch(client, API, params=params, headers={"Accept": "application/json"})
        return parse_offers(r.json(), self.name)
