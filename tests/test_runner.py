from datetime import datetime, timezone

import pytest

from ijara_scraper.models import Listing
from ijara_scraper.runner import Runner
from ijara_scraper.sources.base import PollingSource
from ijara_scraper.storage import Storage


class FakeNotifier:
    def __init__(self):
        self.sent = []

    async def notify(self, l):
        self.sent.append(l.external_id)


class FakeSource(PollingSource):
    batches: list = []

    async def fetch(self, client):
        return self.batches.pop(0)


def L(i, text="ijara"):
    return Listing("fake", str(i), f"http://x/{i}", text, posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


@pytest.mark.asyncio
async def test_first_run_silent_then_only_new_notified():
    st, n = Storage(":memory:"), FakeNotifier()
    r = Runner({"sources": {}, "filters": {"include": ["ijara"]}}, st, n)
    src = FakeSource("fake", {})
    src.batches = [[L(1), L(2)], [L(1), L(2), L(3), L(4, "sotiladi")], [L(3)]]
    await r.poll_once(src, None)
    assert n.sent == [] and st.count("fake") == 2        # birinchi yurish — jim
    await r.poll_once(src, None)
    assert n.sent == ["3"]                                 # faqat yangi va filtrdan o'tgani
    await r.poll_once(src, None)
    assert n.sent == ["3"]                                 # takror xabar yo'q
    assert st.count() == 3


@pytest.mark.asyncio
async def test_notify_on_first_run():
    st, n = Storage(":memory:"), FakeNotifier()
    r = Runner({"sources": {}, "notify_on_first_run": True}, st, n)
    src = FakeSource("fake", {})
    src.batches = [[L(1)]]
    await r.poll_once(src, None)
    assert n.sent == ["1"]
