import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from config import (
    BADGE_ROLE_IDS,
    MAIN_CHAT_ID,
    TIER_ROLE_IDS,
    WELCOME_CHANNEL_ID,
    WINS_CHANNEL_ID,
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

logger = logging.getLogger("thcbot")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_reactions = True
intents.dm_messages = True
intents.members = True
intents.message_content = True

_EXTENSIONS = [
    "cogs.admin",
    "cogs.welcome",
    "cogs.tickets",
    "cogs.payments",
    "cogs.badges",
    "cogs.reactions",
    "cogs.help_menu",
    "cogs.growi_stats",
]


class SonOfAndOn(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for ext in _EXTENSIONS:
            await self.load_extension(ext)

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %d commands to guild %s", len(synced), GUILD_ID)
        else:
            synced = await self.tree.sync()
            logger.info(
                "Synced %d global commands (can take ~1h to appear)", len(synced)
            )

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %d)", self.user, self.user.id)
        await self._validate_config()

    async def _validate_config(self):
        guilds_to_check = (
            [g for g in self.guilds if str(g.id) == GUILD_ID]
            if GUILD_ID
            else self.guilds
        )
        for guild in guilds_to_check:
            for name, cid in [
                ("WELCOME_CHANNEL_ID", WELCOME_CHANNEL_ID),
                ("MAIN_CHAT_ID", MAIN_CHAT_ID),
                ("WINS_CHANNEL_ID", WINS_CHANNEL_ID),
            ]:
                if cid and guild.get_channel(cid) is None:
                    logger.error(
                        "Config check: %s=%d not found in guild '%s'", name, cid, guild.name
                    )

            for tier, rid in TIER_ROLE_IDS.items():
                if guild.get_role(rid) is None:
                    logger.error(
                        "Config check: TIER_ROLE_IDS[%s]=%d not found in guild '%s'",
                        tier, rid, guild.name,
                    )

            for badge, rid in BADGE_ROLE_IDS.items():
                if guild.get_role(rid) is None:
                    logger.error(
                        "Config check: BADGE_ROLE_IDS[%s]=%d not found in guild '%s'",
                        badge, rid, guild.name,
                    )


bot = SonOfAndOn()


def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing in .env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("thcbot.log", encoding="utf-8"),
        ],
    )

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
