import logging
from datetime import datetime, time as dt_time, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from activity_store import load_activity, load_weekly_snapshot, save_weekly_snapshot
from config import EMBED_COLOR_GOLD, WEEKLY_SUMMARY_CHANNEL_ID, WEEKLY_SUMMARY_DAY, WEEKLY_SUMMARY_HOUR
from util import is_staff

logger = logging.getLogger("thcbot")


class WeeklySummaryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._snapshot = load_weekly_snapshot()

    async def cog_load(self):
        self.weekly_post.start()

    async def cog_unload(self):
        self.weekly_post.cancel()

    # ------------------------------------------------------------------ #
    #  Track new member joins                                             #
    # ------------------------------------------------------------------ #

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        self._snapshot["members_joined"].append({
            "id": member.id,
            "name": member.display_name,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        })
        save_weekly_snapshot(self._snapshot)

    # ------------------------------------------------------------------ #
    #  Scheduled weekly task                                              #
    # ------------------------------------------------------------------ #

    @tasks.loop(time=dt_time(hour=WEEKLY_SUMMARY_HOUR, minute=0, tzinfo=timezone.utc))
    async def weekly_post(self):
        if datetime.now(timezone.utc).weekday() != WEEKLY_SUMMARY_DAY:
            return
        await self._post_summary()

    @weekly_post.before_loop
    async def before_weekly_post(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------------ #
    #  Core summary builder                                               #
    # ------------------------------------------------------------------ #

    async def _post_summary(self):
        if not WEEKLY_SUMMARY_CHANNEL_ID:
            logger.warning("WEEKLY_SUMMARY_CHANNEL_ID not set — skipping weekly summary")
            return

        channel = self.bot.get_channel(WEEKLY_SUMMARY_CHANNEL_ID)
        if channel is None:
            logger.error("Weekly summary channel %d not found", WEEKLY_SUMMARY_CHANNEL_ID)
            return

        activity = load_activity()
        old_wins: dict = self._snapshot.get("wins_snapshot", {})

        # Calculate per-user win delta
        wins_this_week: list[tuple[str, int]] = []
        for uid, stats in activity.items():
            delta = stats.get("wins", 0) - old_wins.get(uid, 0)
            if delta > 0:
                wins_this_week.append((uid, delta))
        wins_this_week.sort(key=lambda x: x[1], reverse=True)
        total_wins = sum(d for _, d in wins_this_week)

        new_members: list[dict] = self._snapshot.get("members_joined", [])

        embed = discord.Embed(
            title="Weekly Server Summary",
            color=EMBED_COLOR_GOLD,
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(name="New Members", value=str(len(new_members)), inline=True)
        embed.add_field(name="Wins Posted", value=str(total_wins), inline=True)

        if wins_this_week:
            top = wins_this_week[:5]
            lines = []
            for uid, delta in top:
                member = channel.guild.get_member(int(uid))
                name = member.display_name if member else f"<@{uid}>"
                lines.append(f"• {name} — {delta} win{'s' if delta != 1 else ''}")
            embed.add_field(name="Top Winners This Week", value="\n".join(lines), inline=False)

        if new_members:
            names = [m["name"] for m in new_members[:10]]
            suffix = f" (+{len(new_members) - 10} more)" if len(new_members) > 10 else ""
            embed.add_field(name="Who Joined", value=", ".join(names) + suffix, inline=False)

        await channel.send(embed=embed)
        logger.info("Posted weekly summary to channel %d", WEEKLY_SUMMARY_CHANNEL_ID)

        # Reset snapshot — capture current wins as new baseline
        new_snapshot = {
            "wins_snapshot": {uid: s.get("wins", 0) for uid, s in activity.items()},
            "members_joined": [],
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }
        self._snapshot = new_snapshot
        save_weekly_snapshot(new_snapshot)

    # ------------------------------------------------------------------ #
    #  Staff command — manual trigger                                     #
    # ------------------------------------------------------------------ #

    @app_commands.command(
        name="post_weekly_summary",
        description="Manually post this week's summary now (staff only).",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def post_weekly_summary(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "You don't have permission to use this.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        await self._post_summary()
        await interaction.followup.send("Weekly summary posted.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklySummaryCog(bot))
