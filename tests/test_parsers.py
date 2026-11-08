import json
from pathlib import Path

from ijara_scraper.sources.generic import parse_html_items, parse_json_items
from ijara_scraper.sources.olx import parse_offers
from ijara_scraper.sources.telegram_live import message_to_listing
from ijara_scraper.sources.telegram_web import parse_channel_html
from ijara_scraper.utils import extract_phone, extract_price, matches_filters

FIX = Path(__file__).parent / "fixtures"


def test_telegram_web_real_html():
    ls = parse_channel_html((FIX / "telegram_channel.html").read_text(), "tg:durov")
    assert ls, "kamida bitta post parse bo'lishi kerak"
    for l in ls:
        assert l.external_id.startswith("durov/")
        assert l.url == f"https://t.me/{l.external_id}"
        assert l.posted_at is not None
        assert l.title


def test_olx_parse():
    (l,) = parse_offers(json.loads((FIX / "olx_offers.json").read_text()), "olx")
    assert l.external_id == "123456"
    assert (l.price, l.currency) == (300, "USD")
    assert l.location == "Toshkent, Toshkent, Chilonzor"
    assert l.phone == "+998901234567"
    assert l.images == ["https://apollo.olxcdn.com/v1/files/x/image;s=800x600"]
    assert l.posted_at.year == 2026


def test_generic_json():
    cfg = {"items_path": "data", "url_template": "https://x/{id}", "currency": "UZS",
           "fields": {"id": "id", "title": "name", "price": "cost"}}
    (l,) = parse_json_items({"data": [{"id": 5, "name": "Uy", "cost": "1000"}]}, "j", cfg)
    assert (l.external_id, l.url, l.price, l.currency) == ("5", "https://x/5", 1000.0, "UZS")


def test_generic_html():
    html = '<div class="c"><a href="/ad/12345"><span class="t">Kvartira</span></a><b class="p">250 $</b></div>'
    cfg = {"selectors": {"item": ".c", "title": ".t", "price": ".p"}}
    (l,) = parse_html_items(html, "h", cfg, "https://site.uz/")
    assert l.url == "https://site.uz/ad/12345" and l.external_id == "12345"
    assert (l.title, l.price, l.currency) == ("Kvartira", 250, "USD")


def test_live_message_url():
    l = message_to_listing("s", None, -1001234567890, 7, "ijara 200$", None, False)
    assert l.url == "https://t.me/c/1234567890/7" and l.price == 200
    l = message_to_listing("s", "kanal", -100123, 7, "x", None, False)
    assert l.url == "https://t.me/kanal/7"
    assert message_to_listing("s", "k", 1, 1, "", None, False) is None


def test_utils():
    assert extract_phone("tel 90 123-45-67") == "+998901234567"
    assert extract_phone("+998 (93) 111 22 33") == "+998931112233"
    assert extract_phone("narx 1234") is None
    assert extract_price("Narxi 300$ oyiga") == (300.0, "USD")
    assert extract_price("2 500 000 so'm") == (2500000.0, "UZS")
    assert extract_price("hech narsa") == (None, None)
    assert matches_filters("Kvartira IJARA", ["ijara"], ["sotiladi"])
    assert not matches_filters("kvartira sotiladi ijara", ["ijara"], ["sotiladi"])
    assert not matches_filters("boshqa", ["ijara"], [])
