import logging
import time

import discord
from discord.ext import commands

from config import COOLDOWN_SECONDS
from store import find_binding

logger = logging.getLogger("thcbot")

_SENT_CACHE: dict[tuple[int, int], float] = {}


class ReactionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            if payload.user_id == self.bot.user.id:
                return

            binding = find_binding(payload.message_id)
            if not binding:
                return

            if binding.get("guild_id") and str(payload.guild_id) != str(binding.get("guild_id")):
                return
            if binding.get("channel_id") and str(payload.channel_id) != str(
                binding.get("channel_id")
            ):
                return

            target_emoji = binding.get("emoji", "ANY")
            if target_emoji != "ANY":
                if (
                    str(payload.emoji) != target_emoji
                    and getattr(payload.emoji, "name", None) != target_emoji
                ):
                    return
            else:
                if str(payload.emoji) != "✅" and getattr(payload.emoji, "name", None) != "✅":
                    return

            key = (payload.message_id, payload.user_id)
            now = time.time()
            if now - _SENT_CACHE.get(key, 0) < COOLDOWN_SECONDS:
                return

            role_id_raw = binding.get("role_id")
            if role_id_raw:
                try:
                    role_id = int(role_id_raw)
                    guild = self.bot.get_guild(payload.guild_id) or await self.bot.fetch_guild(
                        payload.guild_id
                    )
                    member = guild.get_member(payload.user_id) or await guild.fetch_member(
                        payload.user_id
                    )
                    role = guild.get_role(role_id)
                    if role:
                        await member.add_roles(
                            role,
                            reason=f"Reaction role for {binding.get('brand', 'deal')}",
                        )
                except Exception:
                    logger.exception(
                        "Reaction role assign error for message %d", payload.message_id
                    )

            form = (binding.get("form") or "").strip()
            if form:
                user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(
                    payload.user_id
                )
                try:
                    await user.send(
                        f"Here is your **{binding.get('brand', '')}** onboarding form:\n{form}"
                    )
                except Exception:
                    try:
                        channel = self.bot.get_channel(
                            payload.channel_id
                        ) or await self.bot.fetch_channel(payload.channel_id)
                        await channel.send(
                            f"<@{payload.user_id}>, I could not DM you. "
                            f"Please enable **Allow DMs from server members** "
                            f"or contact an admin for the **{binding.get('brand', '')}** form."
                        )
                    except Exception:
                        logger.exception(
                            "Failed to notify channel after failed DM for user %d",
                            payload.user_id,
                        )

            _SENT_CACHE[key] = now

        except Exception:
            logger.exception("Reaction handler error for message %d", payload.message_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionsCog(bot))
