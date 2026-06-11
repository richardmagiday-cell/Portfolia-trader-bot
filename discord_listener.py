"""
Discord bot that monitors configured channels for trade signals.

Setup:
  1. Create a bot at https://discord.com/developers/applications
  2. Enable "Message Content Intent" under Bot → Privileged Gateway Intents
  3. Invite the bot with scopes: bot, with permission: Read Messages/View Channels
  4. Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_IDS in .env
"""

import logging

import discord

import config
import trade_parser
from broker import Broker

log = logging.getLogger(__name__)


class TradeBot(discord.Client):
    def __init__(self, broker: Broker) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.broker = broker
        self.watched_channels: set[int] = set(config.DISCORD_CHANNEL_IDS)

    async def on_ready(self) -> None:
        log.info("Discord bot logged in as %s (id=%s)", self.user, self.user.id)
        if self.watched_channels:
            log.info("Watching channel IDs: %s", self.watched_channels)
        else:
            log.warning("No DISCORD_CHANNEL_IDS set — watching ALL channels.")

    async def on_message(self, message: discord.Message) -> None:
        # Ignore the bot's own messages
        if message.author == self.user:
            return

        # Filter by channel if configured
        if self.watched_channels and message.channel.id not in self.watched_channels:
            return

        signal = trade_parser.parse(message.content)
        if signal is None:
            return

        log.info(
            "Signal detected in #%s from %s: %s",
            message.channel,
            message.author,
            signal,
        )
        await self.broker.execute(signal)


def create_client(broker: Broker) -> TradeBot:
    return TradeBot(broker)
