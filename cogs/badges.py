import atexit
import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands

from activity_store import load_activity, save_activity
from util import is_staff
from config import (
    BADGE_ROLE_IDS,
    DIAMOND_CHAT_MIN,
    DIAMOND_GMV_MIN,
    DIAMOND_WINS_MIN,
    GOLD_CHAT_MIN,
    GOLD_WINS_MIN,
    MAIN_CHAT_ID,
    PLATINUM_CHAT_MIN,
    PLATINUM_GMV_MIN,
    PLATINUM_WINS_MIN,
    SAVE_ACTIVITY_INTERVAL,
    TIER_ROLE_IDS,
    WINS_CHANNEL_ID,
)

logger = logging.getLogger("thcbot")

ACTIVITY: dict = load_activity()
_last_activity_save = time.time()

_DM_REPLY = (
    "# 🎉 Welcome to the THC Server 🎉\n"
    "Here at THC, we:\n"
    "- Work with TikTok Shop creators.\n"
    "- Provide opportunities and retainers.\n"
    "- Support your growth as a creator.\n"
    "💬 If you have any questions, please reach out to <@563044854792323082>.\n"
)

BADGE_DISPLAY = {
    "bronze": "🥉 Bronze",
    "silver": "🥈 Silver",
    "gold": "🥇 Gold",
    "diamond": "💎 Diamond",
    "platinum": "🏆 Platinum",
}


@atexit.register
def _flush_activity_on_exit():
    try:
        if ACTIVITY:
            save_activity(ACTIVITY)
    except Exception:
        pass


def maybe_flush_activity():
    global _last_activity_save
    now = time.time()
    if now - _last_activity_save >= SAVE_ACTIVITY_INTERVAL:
        save_activity(ACTIVITY)
        _last_activity_save = now


def _get_stats(member: discord.Member) -> dict:
    user_key = str(member.id)
    stats = ACTIVITY.get(user_key)
    if stats is None:
        stats = {"chat_msgs": 0, "wins": 0, "gmv": 0}
        ACTIVITY[user_key] = stats
    stats.setdefault("chat_msgs", 0)
    stats.setdefault("wins", 0)
    stats.setdefault("gmv", 0)
    return stats


def _member_tier_roles(member: discord.Member):
    tier_role_ids = set(TIER_ROLE_IDS.values())
    return [r for r in member.roles if r.id in tier_role_ids]


def _member_badge_roles(member: discord.Member):
    badge_role_ids = set(BADGE_ROLE_IDS.values())
    return [r for r in member.roles if r.id in badge_role_ids]


async def assign_tier(member: discord.Member, tier: int):
    guild = member.guild
    role_id = TIER_ROLE_IDS.get(tier)
    if not role_id:
        raise ValueError(f"Unknown tier {tier}")
    role = guild.get_role(role_id)
    if role is None:
        raise RuntimeError(f"Role ID {role_id} not found in this server.")
    old_tiers = _member_tier_roles(member)
    if old_tiers:
        await member.remove_roles(*old_tiers, reason=f"Tier change -> T{tier}")
    await member.add_roles(role, reason=f"Assigned Tier {tier}")


async def assign_badge(member: discord.Member, badge_key: str, reason: str = ""):
    guild = member.guild
    role_id = BADGE_ROLE_IDS.get(badge_key)
    if not role_id:
        raise ValueError(f"Unknown badge key {badge_key} or role ID missing")
    role = guild.get_role(role_id)
    if role is None:
        raise RuntimeError(f"Badge role ID {role_id} not found in this server")
    old_badges = _member_badge_roles(member)
    if old_badges:
        await member.remove_roles(*old_badges, reason=reason or f"Badge change -> {badge_key}")
    await member.add_roles(role, reason=reason or f"Assigned badge {badge_key}")


def _current_badge_key(member: discord.Member) -> str | None:
    badge_by_id = {v: k for k, v in BADGE_ROLE_IDS.items()}
    for r in member.roles:
        key = badge_by_id.get(r.id)
        if key:
            return key
    return None


def _badge_rank_index(badge_key: str | None) -> int:
    order = ["bronze", "silver", "gold", "diamond", "platinum"]
    if badge_key is None:
        return -1
    try:
        return order.index(badge_key)
    except ValueError:
        return -1


async def _check_for_rank_upgrade(member: discord.Member):
    stats = _get_stats(member)
    chat_msgs = stats["chat_msgs"]
    wins = stats["wins"]
    gmv = stats["gmv"]

    current = _current_badge_key(member)
    current_idx = _badge_rank_index(current)
    best = None
    best_idx = current_idx

    if chat_msgs >= GOLD_CHAT_MIN and wins >= GOLD_WINS_MIN:
        if _badge_rank_index("gold") > best_idx:
            best = "gold"
            best_idx = _badge_rank_index("gold")

    if gmv >= DIAMOND_GMV_MIN and chat_msgs >= DIAMOND_CHAT_MIN and wins >= DIAMOND_WINS_MIN:
        if _badge_rank_index("diamond") > best_idx:
            best = "diamond"
            best_idx = _badge_rank_index("diamond")

    if gmv >= PLATINUM_GMV_MIN and chat_msgs >= PLATINUM_CHAT_MIN and wins >= PLATINUM_WINS_MIN:
        if _badge_rank_index("platinum") > best_idx:
            best = "platinum"
            best_idx = _badge_rank_index("platinum")

    if best and best_idx > current_idx:
        await assign_badge(member, best, reason="Auto badge upgrade from activity")
        maybe_flush_activity()


class BadgesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content or ""
        lowered = content.lower()

        if isinstance(message.channel, discord.DMChannel):
            await message.reply(_DM_REPLY)
            return

        if isinstance(message.channel, discord.TextChannel):
            member = message.author
            channel_id = message.channel.id
            stats = _get_stats(member)

            if MAIN_CHAT_ID and channel_id == MAIN_CHAT_ID:
                stats["chat_msgs"] += 1

                if self.bot.user and self.bot.user in message.mentions:
                    if re.search(r"\bintro\b", lowered):
                        try:
                            await assign_badge(member, "bronze", reason="Bronze intro trigger")
                            try:
                                await member.send(
                                    "You have unlocked the **Bronze** badge in THC "
                                    "for introducing yourself in the main chat. 🎉"
                                )
                            except discord.Forbidden:
                                await message.channel.send(
                                    f"{member.mention} you have unlocked the **Bronze** badge.",
                                    allowed_mentions=discord.AllowedMentions(users=[member]),
                                )
                            maybe_flush_activity()
                        except Exception:
                            logger.exception("Failed to assign Bronze badge to %s", member)

            if WINS_CHANNEL_ID and channel_id == WINS_CHANNEL_ID:
                if self.bot.user and self.bot.user in message.mentions:
                    if re.search(r"\bwin\b", lowered):
                        stats["wins"] += 1
                        try:
                            await assign_badge(member, "silver", reason="Silver win trigger")
                            try:
                                await member.send(
                                    "You have unlocked the **Silver** badge in THC "
                                    "for sharing your win in the server. 🎉"
                                )
                            except discord.Forbidden:
                                await message.channel.send(
                                    f"{member.mention} you have unlocked the **Silver** badge.",
                                    allowed_mentions=discord.AllowedMentions(users=[member]),
                                )
                            maybe_flush_activity()
                        except Exception:
                            logger.exception("Failed to assign Silver badge to %s", member)
                    else:
                        stats["wins"] += 1
                else:
                    stats["wins"] += 1

            maybe_flush_activity()

            try:
                await _check_for_rank_upgrade(member)
            except Exception:
                logger.exception("Rank upgrade check failed for %s", member)

        if self.bot.user and self.bot.user in message.mentions and not re.search(
            r"\b(intro|win)\b", lowered
        ):
            from cogs.help_menu import HelpMenu  # lazy to avoid circular import

            view = HelpMenu()
            await message.channel.send("Hi! 👋 Please choose an option below:", view=view)
            return

        await self.bot.process_commands(message)

    # -------------------------------------------------------------------------
    # Slash commands
    # -------------------------------------------------------------------------

    @app_commands.command(
        name="setgmv", description="Set GMV for a user for badge ranking (staff only)."
    )
    @app_commands.describe(user="User to set GMV for", amount="Total GMV for this user")
    @app_commands.default_permissions(manage_messages=True)
    async def setgmv(
        self, interaction: discord.Interaction, user: discord.Member, amount: int
    ):
        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        stats = _get_stats(user)
        stats["gmv"] = max(0, int(amount))
        maybe_flush_activity()
        await _check_for_rank_upgrade(user)

        logger.info("GMV for %s set to %d by %s", user, stats["gmv"], interaction.user)
        await interaction.response.send_message(
            f"Set GMV for {user.mention} to **{stats['gmv']}**. Badge has been rechecked.",
            allowed_mentions=discord.AllowedMentions(users=[user]),
            ephemeral=True,
        )

    @app_commands.command(
        name="stats",
        description="Check your stats (or another member's with manage_roles).",
    )
    @app_commands.describe(user="Member to look up (staff only when checking others)")
    @app_commands.default_permissions(manage_messages=True)
    async def stats(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ):
        invoker = interaction.user
        if not isinstance(invoker, discord.Member):
            await interaction.response.send_message(
                "This command only works in a server.", ephemeral=True
            )
            return

        if user is None:
            user = invoker

        if user.id != invoker.id and not is_staff(invoker):
            await interaction.response.send_message(
                "You need `manage_roles` to view another member's stats.", ephemeral=True
            )
            return

        s = _get_stats(user)
        badge_key = _current_badge_key(user)
        badge_label = BADGE_DISPLAY.get(badge_key, "—") if badge_key else "—"

        tier_label = "—"
        for r in user.roles:
            for num, rid in TIER_ROLE_IDS.items():
                if rid == r.id:
                    tier_label = f"Tier {num}"
                    break

        await interaction.response.send_message(
            f"**Stats for {user.mention}**\n"
            f"Chat msgs: **{s['chat_msgs']}**  |  Wins: **{s['wins']}**  |  "
            f"GMV: **${s['gmv']:,}**  |  Badge: **{badge_label}**  |  Tier: **{tier_label}**",
            allowed_mentions=discord.AllowedMentions(users=[user]),
            ephemeral=True,
        )

    @app_commands.command(name="leaderboard", description="Top 10 members by GMV.")
    @app_commands.default_permissions(manage_messages=True)
    async def leaderboard(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command only works in a server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        entries = []
        for uid_str, s in ACTIVITY.items():
            gmv = s.get("gmv", 0)
            if gmv <= 0:
                continue
            member = interaction.guild.get_member(int(uid_str))
            name = member.display_name if member else f"<@{uid_str}>"
            badge_key = _current_badge_key(member) if member else None
            badge_label = BADGE_DISPLAY.get(badge_key, "") if badge_key else ""
            entries.append((gmv, name, badge_label))

        entries.sort(key=lambda x: x[0], reverse=True)
        top = entries[:10]

        if not top:
            await interaction.followup.send("No GMV data recorded yet.", ephemeral=True)
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = ["**🏆 Top Creators (by GMV)**\n"]
        for i, (gmv, name, badge) in enumerate(top, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} {name} — **${gmv:,}** {badge}")

        await interaction.followup.send("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BadgesCog(bot))
