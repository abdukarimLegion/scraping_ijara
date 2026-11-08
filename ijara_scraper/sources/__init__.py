from __future__ import annotations

from typing import Any

from .base import PollingSource, PushSource
from .generic import HtmlListSource, JsonApiSource
from .olx import OlxSource
from .telegram_live import TelegramLiveSource
from .telegram_web import TelegramWebSource

REGISTRY: dict[str, type] = {
    "olx": OlxSource,
    "telegram_web": TelegramWebSource,
    "telegram_live": TelegramLiveSource,
    "html": HtmlListSource,
    "json_api": JsonApiSource,
}


def build_source(name: str, cfg: dict[str, Any]) -> PollingSource | PushSource:
    kind = cfg.get("type")
    if kind not in REGISTRY:
        raise ValueError(f"'{name}': noma'lum type={kind!r}. Mavjud: {', '.join(REGISTRY)}")
    return REGISTRY[kind](name, cfg)
