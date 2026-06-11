"""
Entry point for the trade copy bot.

Runs Discord listener and/or forum scraper concurrently.
At least one source must be configured via .env.
"""

import asyncio
import logging
import sys

import config
from broker import Broker
from discord_listener import create_client
from forum_scraper import ForumScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def main() -> None:
    has_discord = bool(config.DISCORD_BOT_TOKEN)
    has_forum = bool(config.FORUM_URLS)

    if not has_discord and not has_forum:
        log.error(
            "No sources configured. Set DISCORD_BOT_TOKEN or FORUM_URLS in .env and try again."
        )
        sys.exit(1)

    broker = Broker()
    mode = "DRY RUN" if broker.dry_run else f"LIVE ({config.ALPACA_MODE.upper()})"
    log.info("Trade bot starting — mode: %s", mode)

    tasks: list[asyncio.Task] = []

    if has_forum:
        scraper = ForumScraper(callback=broker.execute)
        tasks.append(asyncio.create_task(scraper.run(), name="forum-scraper"))

    if has_discord:
        client = create_client(broker)
        tasks.append(asyncio.create_task(client.start(config.DISCORD_BOT_TOKEN), name="discord-bot"))

    if not tasks:
        log.error("Nothing to run.")
        sys.exit(1)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        log.info("Shutting down…")
    finally:
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())
