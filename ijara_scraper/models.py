from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class Listing:
    """Bitta e'lon (OLX e'loni, Telegram post va h.k.)."""

    source: str                 # config'dagi manba nomi, masalan "olx_toshkent"
    external_id: str            # manba ichida unikal ID
    url: str
    title: str = ""
    description: str = ""
    price: float | None = None
    currency: str | None = None
    location: str | None = None
    phone: str | None = None
    images: list[str] = field(default_factory=list)
    posted_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.source, self.external_id)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}".strip()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["posted_at"] = self.posted_at.isoformat() if self.posted_at else None
        return d
