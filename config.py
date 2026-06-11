import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


def _csv(key: str) -> list[str]:
    raw = os.getenv(key, "")
    return [v.strip() for v in raw.split(",") if v.strip()]


DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_IDS: list[int] = [int(c) for c in _csv("DISCORD_CHANNEL_IDS")]

ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_MODE: str = os.getenv("ALPACA_MODE", "paper").lower()  # "paper" or "live"

DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
MAX_TRADE_USD: float = float(os.getenv("MAX_TRADE_USD", "500"))

FORUM_URLS: list[str] = _csv("FORUM_URLS")
FORUM_POLL_INTERVAL: int = int(os.getenv("FORUM_POLL_INTERVAL", "60"))
