import asyncio
import logging

import discord
from discord.ext import commands

from config import (
    FORM_DELAY_SECONDS,
    FORM_DM_TEMPLATE,
    FORM_LINK,
    HELPER_USER_ID,
    WELCOME_CHANNEL_ID,
    WELCOME_MESSAGE,
)

logger = logging.getLogger("thcbot")


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._send_welcome(member)
        asyncio.create_task(self._send_delayed_form(member))

    async def _send_welcome(self, member: discord.Member):
        if member.bot:
            return

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID) or await self.bot.fetch_channel(WELCOME_CHANNEL_ID)

        live_text = WELCOME_MESSAGE.format(
            mention=member.mention,
            name=member.display_name,
            id=member.id,
            guild=member.guild.name,
        )
        msg = await channel.send(
            live_text,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

        await asyncio.sleep(2)
        safe_mention = f"`@{member.display_name}`"
        safe_text = WELCOME_MESSAGE.format(
            mention=safe_mention,
            name=member.display_name,
            id=member.id,
            guild=member.guild.name,
        )
        await msg.edit(content=safe_text, allowed_mentions=discord.AllowedMentions.none())

    async def _send_delayed_form(self, member: discord.Member):
        await asyncio.sleep(FORM_DELAY_SECONDS)

        if member.guild.get_member(member.id) is None:
            return

        helper_mention = f"<@{HELPER_USER_ID}>"
        try:
            await member.send(
                FORM_DM_TEMPLATE.format(
                    name=member.display_name,
                    form_link=FORM_LINK,
                    helper_mention=helper_mention,
                )
            )
        except discord.Forbidden:
            logger.debug(
                "Could not DM form to %s (%d) — DMs closed", member.display_name, member.id
            )
        except Exception:
            logger.exception(
                "Unexpected error sending form DM to %s (%d)", member.display_name, member.id
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
