import asyncio
import logging
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    EMBED_COLOR_GOLD,
    FORM_DELAY_SECONDS,
    FORM_DM_TEMPLATE,
    FORM_LINK,
    HELPER_USER_ID,
    ONBOARDING_CALL_1_URL,
    ONBOARDING_CALL_2_URL,
    PRODUCTS_URL,
    WELCOME_CHANNEL_ID,
)
from util import is_staff

logger = logging.getLogger("thcbot")

_WAVE_GIF_DIR = "welcome_gifs"

_FREE_COURSE_URL = "https://docs.google.com/presentation/d/1F_k8P0lX3eizRbb87Q8FQzTNJYq1ufimxLUikOCDxao/edit?usp=sharing"
_JOBS_URL = "https://www.thehustlersclub.net/jobs"


def _random_gif_path() -> str | None:
    try:
        files = [f for f in os.listdir(_WAVE_GIF_DIR) if f.lower().endswith(".gif")]
        return os.path.join(_WAVE_GIF_DIR, random.choice(files)) if files else None
    except Exception:
        return None


class WelcomeLinks(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="📖 Free Course",
            style=discord.ButtonStyle.link,
            url=_FREE_COURSE_URL,
        ))
        self.add_item(discord.ui.Button(
            label="💰 Products",
            style=discord.ButtonStyle.link,
            url=PRODUCTS_URL,
        ))
        self.add_item(discord.ui.Button(
            label="💼 Jobs & Opportunities",
            style=discord.ButtonStyle.link,
            url=_JOBS_URL,
        ))


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

        embed = self._build_embed(member)
        gif_path = _random_gif_path()

        if gif_path:
            file = discord.File(gif_path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            msg = await channel.send(
                member.mention,
                embed=embed,
                file=file,
                view=WelcomeLinks(),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        else:
            msg = await channel.send(
                member.mention,
                embed=embed,
                view=WelcomeLinks(),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )

        await asyncio.sleep(2)
        await msg.edit(
            content=f"`@{member.display_name}`",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    def _build_embed(self, member: discord.Member) -> discord.Embed:
        guild = member.guild
        member_count = guild.member_count

        embed = discord.Embed(
            title=f"🔥 {member.display_name} — Welcome to The Hustlers Club!",
            description=(
                f"{member.mention} Your journey to financial freedom starts right here. "
                f"Let's get it. 💪"
            ),
            color=EMBED_COLOR_GOLD,
        )

        embed.add_field(
            name="📖 Free Course",
            value="Step-by-step guide from zero to $10k/month online.",
            inline=False,
        )
        embed.add_field(
            name="💰 Products & Commissions",
            value="Browse high-commission products and start earning today.",
            inline=False,
        )
        embed.add_field(
            name="💼 Jobs & Opportunities",
            value="Live roles and brand opportunities, applications reviewed regularly.",
            inline=False,
        )
        embed.add_field(
            name="📅 Onboarding Calls",
            value=f"[Onboarding Call #1]({ONBOARDING_CALL_1_URL}) · [Onboarding Call #2]({ONBOARDING_CALL_2_URL})",
            inline=False,
        )
        embed.add_field(
            name="👋 Introduce Yourself",
            value=f"Drop a quick intro in <#1499136008480886924> and say hello!",
            inline=False,
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        if member_count:
            embed.set_footer(text=f"Welcome to the server, {member.display_name}!  ·  {member_count:,} members")
        else:
            embed.set_footer(text=f"Welcome to the server, {member.display_name}!")
        return embed

    @app_commands.command(name="testwelcome", description="Preview the welcome embed for a member.")
    @app_commands.describe(member="Member to preview the welcome for (defaults to you)")
    async def testwelcome(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if not is_staff(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        target = member or interaction.user
        embed = self._build_embed(target)
        gif_path = _random_gif_path()

        if gif_path:
            file = discord.File(gif_path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await interaction.response.send_message(embed=embed, file=file, view=WelcomeLinks(), ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=WelcomeLinks(), ephemeral=True)

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
