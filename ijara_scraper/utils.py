from __future__ import annotations

import re

_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?998[\s\-]?)?\(?(\d{2})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})(?!\d)"
)
_PRICE_RE = re.compile(
    r"(?P<num>\d[\d\s.,]*\d|\d)\s*(?P<cur>\$|usd|y\.?e\.?|у\.?е\.?|сум|so['’`]?m|sum|сўм|млн|mln)?",
    re.IGNORECASE,
)
_USD = {"$", "usd", "y.e", "ye", "y.e.", "у.е", "уе", "у.е."}


def extract_phone(text: str) -> str | None:
    """Matndan birinchi O'zbekiston telefon raqamini +998XXXXXXXXX ko'rinishida qaytaradi."""
    m = _PHONE_RE.search(text or "")
    if not m:
        return None
    return "+998" + "".join(m.groups())


def extract_price(text: str) -> tuple[float | None, str | None]:
    """Matndan narx va valyutani taxminan ajratadi ("300$", "2 500 000 so'm")."""
    best: tuple[float, str] | None = None
    for m in _PRICE_RE.finditer(text or ""):
        cur = (m.group("cur") or "").lower()
        if not cur:
            continue
        digits = re.sub(r"[\s.,]", "", m.group("num"))
        if not digits:
            continue
        value = float(digits)
        if cur in ("млн", "mln"):
            value *= 1_000_000
            currency = "UZS"
        elif cur in _USD:
            currency = "USD"
        else:
            currency = "UZS"
        best = (value, currency)
        break
    return best if best else (None, None)


def matches_filters(text: str, include: list[str], exclude: list[str]) -> bool:
    t = (text or "").lower()
    if include and not any(k.lower() in t for k in include):
        return False
    if exclude and any(k.lower() in t for k in exclude):
        return False
    return True
