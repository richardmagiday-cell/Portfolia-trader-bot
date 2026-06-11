"""
Forum / web-page scraper that polls URLs for new trade signals.

Works on any page with visible text — not limited to a specific forum engine.
Tracks already-seen text so it only processes new content between polls.
"""

import asyncio
import hashlib
import logging
from typing import Callable, Coroutine, Any

import aiohttp
from bs4 import BeautifulSoup

import config
import trade_parser
from trade_parser import TradeSignal

log = logging.getLogger(__name__)

# Callback type: async fn that receives a TradeSignal
SignalCallback = Callable[[TradeSignal], Coroutine[Any, Any, None]]


class ForumScraper:
    def __init__(self, callback: SignalCallback) -> None:
        self.callback = callback
        self._seen: dict[str, set[str]] = {}   # url → set of content hashes

    async def run(self) -> None:
        if not config.FORUM_URLS:
            log.info("No FORUM_URLS configured — forum scraper idle.")
            return

        log.info(
            "Forum scraper polling %d URL(s) every %ds",
            len(config.FORUM_URLS),
            config.FORUM_POLL_INTERVAL,
        )

        async with aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 TradeBot/1.0"}
        ) as session:
            while True:
                await asyncio.gather(
                    *[self._poll(session, url) for url in config.FORUM_URLS]
                )
                await asyncio.sleep(config.FORUM_POLL_INTERVAL)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _poll(self, session: aiohttp.ClientSession, url: str) -> None:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                html = await resp.text()
        except Exception as exc:
            log.warning("Failed to fetch %s: %s", url, exc)
            return

        paragraphs = self._extract_paragraphs(html)
        seen = self._seen.setdefault(url, set())

        for para in paragraphs:
            key = hashlib.md5(para.encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            signal = trade_parser.parse(para)
            if signal:
                log.info("Forum signal from %s: %s", url, signal)
                await self.callback(signal)

    @staticmethod
    def _extract_paragraphs(html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        # Remove nav/script/style noise
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        texts = []
        for element in soup.find_all(["p", "div", "li", "td", "span"]):
            text = element.get_text(" ", strip=True)
            if len(text) > 10:   # skip tiny fragments
                texts.append(text)
        return texts
