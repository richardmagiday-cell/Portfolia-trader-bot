"""
Broker abstraction: dry-run mode (default) + Alpaca paper/live trading.

Usage:
    broker = Broker()
    await broker.execute(signal)
"""

import logging
from typing import Optional

import config
from trade_parser import TradeSignal

log = logging.getLogger(__name__)


class Broker:
    def __init__(self) -> None:
        self.dry_run = config.DRY_RUN
        self._alpaca: Optional[object] = None

        if not self.dry_run:
            self._alpaca = self._build_alpaca_client()

    # ── Public ────────────────────────────────────────────────────────────────

    async def execute(self, signal: TradeSignal) -> None:
        qty = self._resolve_qty(signal)
        if qty is None or qty <= 0:
            log.warning("Cannot determine quantity for %s — skipping.", signal.ticker)
            return

        if self.dry_run:
            self._log_dry_run(signal, qty)
        else:
            await self._place_order(signal, qty)

    # ── Private ───────────────────────────────────────────────────────────────

    def _resolve_qty(self, signal: TradeSignal) -> Optional[float]:
        """Return explicit qty, or compute from MAX_TRADE_USD if price is known."""
        if signal.qty:
            return signal.qty
        if signal.price and signal.price > 0:
            return int(config.MAX_TRADE_USD / signal.price)
        # Market order with no qty — use a single share as safe default
        return 1

    def _log_dry_run(self, signal: TradeSignal, qty: float) -> None:
        order_type = "MARKET" if signal.is_market_order() else f"LIMIT @ {signal.price}"
        log.info(
            "[DRY RUN] %s %s x%.0f %s%s%s",
            signal.action,
            signal.ticker,
            qty,
            order_type,
            f" SL={signal.stop_loss}" if signal.stop_loss else "",
            f" TP={signal.take_profit}" if signal.take_profit else "",
        )

    async def _place_order(self, signal: TradeSignal, qty: float) -> None:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client: TradingClient = self._alpaca  # type: ignore[assignment]
        side = OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL

        try:
            if signal.is_market_order():
                req = MarketOrderRequest(
                    symbol=signal.ticker,
                    qty=qty,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                )
            else:
                req = LimitOrderRequest(
                    symbol=signal.ticker,
                    qty=qty,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=signal.price,
                )

            order = client.submit_order(req)
            log.info("Order placed: %s %s x%.0f — id=%s", signal.action, signal.ticker, qty, order.id)
        except Exception as exc:
            log.error("Order failed for %s: %s", signal.ticker, exc)

    @staticmethod
    def _build_alpaca_client():
        from alpaca.trading.client import TradingClient

        paper = config.ALPACA_MODE != "live"
        return TradingClient(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            paper=paper,
        )
