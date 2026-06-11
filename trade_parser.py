"""
Parse trade signals from free-form text (Discord messages, forum posts).

Supported formats (case-insensitive):
  BUY AAPL 10
  SELL TSLA 5 @ 200
  BUY $NVDA 3 shares at market
  Long MSFT entry 380 SL 370 TP 400
  Short AMZN 2 @ 185.50
  $AAPL buy 100
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# Common action synonyms
_BUY_WORDS = {"buy", "long", "bought", "buying", "entry", "enter"}
_SELL_WORDS = {"sell", "short", "sold", "selling", "exit", "close"}

# Matches a stock ticker: 1-5 uppercase letters, optionally prefixed with $
_TICKER_RE = re.compile(r"\$?([A-Z]{1,5})")

# Matches a positive number (integer or decimal)
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")

# Words that signal an optional field follows
_ENTRY_WORDS = {"entry", "at", "@", "price", "limit"}
_SL_WORDS = {"sl", "stop", "stoploss", "stop-loss"}
_TP_WORDS = {"tp", "target", "takeprofit", "take-profit", "pt"}


@dataclass
class TradeSignal:
    action: str          # "BUY" or "SELL"
    ticker: str          # e.g. "AAPL"
    qty: Optional[float] = None
    price: Optional[float] = None   # None = market order
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    raw: str = field(default="", repr=False)

    def is_market_order(self) -> bool:
        return self.price is None

    def __str__(self) -> str:
        order_type = "MARKET" if self.is_market_order() else f"LIMIT@{self.price}"
        parts = [f"{self.action} {self.ticker} qty={self.qty} {order_type}"]
        if self.stop_loss:
            parts.append(f"SL={self.stop_loss}")
        if self.take_profit:
            parts.append(f"TP={self.take_profit}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(text: str) -> Optional[TradeSignal]:
    """Return a TradeSignal if the text looks like a trade, else None."""
    tokens = _tokenize(text)
    if not tokens:
        return None

    action = _find_action(tokens)
    if action is None:
        return None

    ticker = _find_ticker(tokens)
    if ticker is None:
        return None

    qty, price, sl, tp = _find_numerics(tokens)

    return TradeSignal(
        action=action,
        ticker=ticker,
        qty=qty,
        price=price,
        stop_loss=sl,
        take_profit=tp,
        raw=text,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lower-case words + preserve $ prefix; strip punctuation except $ . @."""
    cleaned = re.sub(r"[^\w\s$@.]", " ", text)
    return cleaned.lower().split()


def _find_action(tokens: list[str]) -> Optional[str]:
    for t in tokens:
        if t in _BUY_WORDS:
            return "BUY"
        if t in _SELL_WORDS:
            return "SELL"
    return None


def _find_ticker(tokens: list[str]) -> Optional[str]:
    for t in tokens:
        # $AAPL or plain AAPL (upper in original, but we lowercased)
        # Re-check against original-case in raw text via regex on token
        raw_upper = t.upper()
        if t.startswith("$"):
            candidate = raw_upper[1:]
        else:
            candidate = raw_upper

        if re.fullmatch(r"[A-Z]{1,5}", candidate) and candidate not in _ALL_KEYWORDS:
            return candidate
    return None


def _find_numerics(
    tokens: list[str],
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Extract qty, price, stop_loss, take_profit from the token stream."""
    qty = price = sl = tp = None
    numbers: list[float] = []

    context: Optional[str] = None  # tracks what the next number means

    for t in tokens:
        if t in _ENTRY_WORDS:
            context = "price"
        elif t in _SL_WORDS:
            context = "sl"
        elif t in _TP_WORDS:
            context = "tp"
        elif _NUM_RE.fullmatch(t):
            val = float(t)
            if context == "price":
                price = val
                context = None
            elif context == "sl":
                sl = val
                context = None
            elif context == "tp":
                tp = val
                context = None
            else:
                numbers.append(val)

    # Heuristic: first bare number is qty, second is price
    if numbers:
        qty = numbers[0]
    if len(numbers) >= 2:
        price = numbers[1]

    return qty, price, sl, tp


_ALL_KEYWORDS = (
    _BUY_WORDS | _SELL_WORDS | _ENTRY_WORDS | _SL_WORDS | _TP_WORDS
    | {"shares", "share", "market", "limit", "order"}
)
