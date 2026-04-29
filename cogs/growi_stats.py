import os
from datetime import datetime, timedelta

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from util import is_staff

GROWI_API_KEY = os.getenv("GROWI_API_KEY", "")
GROWI_HEADERS = {
    "Authorization": f"Bearer {GROWI_API_KEY}",
    "Content-Type": "application/json",
}
TOP_CREATORS_URL = "https://api.growi.io/api/public/v1/stats/top_creators_by_gmv"


def _date_range(days: int):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end, start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")


class GrowiStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------ #
    #  /top_creators  — top creators by GMV                               #
    # ------------------------------------------------------------------ #

    @app_commands.command(
        name="top_creators",
        description="Show the top creators by GMV (Growi data).",
    )
    @app_commands.describe(
        days="How many days back to look (default 30)",
        limit="How many creators to show (default 5, max 20)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def top_creators(
        self,
        interaction: discord.Interaction,
        days: int = 30,
        limit: int = 5,
    ):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "You don't have permission to use this.", ephemeral=True
            )

        limit = max(1, min(limit, 20))
        days = max(1, min(days, 365))
        start, end, start_str, end_str = _date_range(days)

        params = {
            "start_date": start_str,
            "end_date": end_str,
            "limit": limit,
            "include_discord": "true",
        }

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TOP_CREATORS_URL,
                    params=params,
                    headers=GROWI_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return await interaction.followup.send(
                            f"API error {resp.status}: {text[:300]}", ephemeral=True
                        )
                    data = await resp.json()

            creators = data.get("data", {}).get("top_creators_by_gmv", [])
            if not creators:
                return await interaction.followup.send(
                    "No creators found for that date range.", ephemeral=True
                )

            embed = discord.Embed(
                title=f"Top {len(creators)} Creators by GMV",
                description=f"{start.strftime('%b %d, %Y')} — {end.strftime('%b %d, %Y')}",
                color=discord.Color.gold(),
            )

            for i, creator in enumerate(creators, 1):
                name = creator.get("name") or creator.get("username") or "Unknown"
                gmv = creator.get("gmv") or creator.get("total_gmv") or 0

                display = name if len(name) <= 200 else name[:197] + "..."
                field_name = f"{i}. {display}"
                if len(field_name) > 256:
                    field_name = field_name[:253] + "..."

                value = f"GMV: **${gmv:,.2f}**"

                # Social accounts
                socials = creator.get("social_accounts") or []
                handles = []
                for s in socials:
                    platform = (s.get("platform") or "").capitalize()
                    handle = s.get("handle") or s.get("username") or ""
                    if platform and handle:
                        handles.append(f"{platform}: @{handle}")
                if handles:
                    value += "\n" + " | ".join(handles)

                # Discord
                discord_info = creator.get("discord") or {}
                discord_tag = discord_info.get("username") or discord_info.get("tag") or ""
                if discord_tag:
                    value += f"\nDiscord: {discord_tag}"

                embed.add_field(name=field_name, value=value, inline=False)

            embed.set_footer(text="Powered by Growi")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GrowiStats(bot))
