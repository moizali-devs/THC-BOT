import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    APPLY_CHANNEL_ID,
    DIAMOND_CHAT_MIN,
    DIAMOND_GMV_MIN,
    DIAMOND_WINS_MIN,
    GOLD_CHAT_MIN,
    GOLD_WINS_MIN,
    GROWI_USER_ID,
    PLATINUM_CHAT_MIN,
    PLATINUM_GMV_MIN,
    PLATINUM_WINS_MIN,
)
from cogs.badges import assign_tier
from cogs.tickets import create_ticket

logger = logging.getLogger("thcbot")


class TierButtons(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self._member = member
        self.add_item(self._make_button(1, "Tier 1 • 0–50k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(2, "Tier 2 • 50k–100k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(3, "Tier 3 • 100k–200k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(4, "Tier 4 • 200k+ GMV", discord.ButtonStyle.success))

    def _make_button(self, tier: int, label: str, style: discord.ButtonStyle):
        async def _callback(interaction: discord.Interaction):
            if interaction.user.id != self._member.id:
                return await interaction.response.send_message(
                    "Only the requester can use these buttons.", ephemeral=True
                )
            try:
                await assign_tier(self._member, tier)
                await interaction.response.send_message(
                    f"✅ Assigned **Tier {tier}**. Previous tier removed.", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)

        btn = discord.ui.Button(label=label, style=style)
        btn.callback = _callback
        return btn


class GetHelpButtons(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=120)
        self._member = member
        self.add_item(
            self._make_button(key="THC_Academy_msg", label="THC Academy", style=discord.ButtonStyle.green)
        )
        self.add_item(
            self._make_button(key="THC_Premium_msg", label="THC Premium", style=discord.ButtonStyle.green)
        )

    def _make_button(self, key: str, label: str, style: discord.ButtonStyle):
        async def _callback(interaction: discord.Interaction):
            if interaction.user.id != self._member.id:
                return await interaction.response.send_message(
                    "Only the requester can use these buttons.", ephemeral=True
                )

            if key == "THC_Academy_msg":
                msg = (
                    "**THC Academy**\n"
                    "THC Academy is something we recommend every affiliate goes through. No matter the level.\n\n"
                    "It's an **intensive step-by-step walkthrough** showing you how to go from sitting at home lazy 🛋️ "
                    "to making your first **$10K/month online 💸**.\n\n"
                    "The goal: start the Academy with zero knowledge and leave feeling like a **top-tier affiliate.**\n\n"
                    "__**THC Academy Offers:**__\n"
                    "• Walkthrough from start to finish\n"
                    "• Intense course (~10 hours of knowledge)\n"
                    "• Sales psychology fundamentals\n"
                    "• The mindset of a successful creator\n"
                    "• Pre-recorded interview calls with **7-figure creators**\n\n"
                )
            elif key == "THC_Premium_msg":
                msg = (
                    "**THC Premium**\n"
                    "THC Premium is for creators who are serious about taking their content to the next level. 🚀\n"
                    "It's a step up from THC Free — a close-knit, experienced community built to help you grow faster and smarter.\n\n"
                    "__**THC Premium Offers:**__\n"
                    "• Exclusive Brand Deals 💼\n"
                    "• 1-on-1 Feedback from top coaches 🧠\n"
                    "• A network of the best creators in the space 🌎\n"
                    "• A closer, more supportive community 🤝\n"
                    "• Intensive TikTok Shop strategy & growth courses 🎥\n"
                    "• Live calls and real-time advice 🔥\n"
                    "• 1-on-1 access to 8-figure brand owners 💰\n\n"
                )
            else:
                msg = "Coming soon."

            await interaction.response.send_message(msg, ephemeral=True)

        btn = discord.ui.Button(label=label, style=style)
        btn.callback = _callback
        return btn


class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="1️⃣ Growi Help", style=discord.ButtonStyle.primary)
    async def button_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ch = await create_ticket(interaction.guild, interaction.user, GROWI_USER_ID)
            await interaction.response.send_message(f"✅ Ticket ready: {ch.mention}", ephemeral=True)
        except RuntimeError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
        except Exception:
            logger.exception("Failed to create Growi ticket for %s", interaction.user)
            await interaction.response.send_message("❌ Couldn't create the ticket.", ephemeral=True)

    @discord.ui.button(
        label="2️⃣ Apply to Brand", style=discord.ButtonStyle.secondary, custom_id="apply_btn"
    )
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"All brand deals can be found in <#{APPLY_CHANNEL_ID}>.\n"
            f"React ✅ to receive the application form in your DMs.",
            ephemeral=True,
        )

    @discord.ui.button(label="3️⃣ Tier / Roles", style=discord.ButtonStyle.success)
    async def button_tiers(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Choose your tier based on your GMV:",
            view=TierButtons(interaction.user),
            ephemeral=True,
        )

    @discord.ui.button(label="4️⃣ Get Started", style=discord.ButtonStyle.primary)
    async def button_get_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Pick a help topic:",
            view=GetHelpButtons(interaction.user),
            ephemeral=True,
        )

    @discord.ui.button(label="5️⃣ Select Referral", style=discord.ButtonStyle.primary)
    async def button_referral(self, interaction: discord.Interaction, button: discord.ui.Button):
        referral_msg = (
            f"{interaction.user.mention} please answer the questions below:\n\n"
            "1) Creator or brand owner?\n"
            "2) Brand name?\n"
            "3) Brand owner contact?\n"
            "4) Platform and niche?\n"
            "5) Estimated budget?\n\n"
            "Share as much detail as you can so we can move fast."
        )
        try:
            ch = await create_ticket(
                interaction.guild,
                interaction.user,
                GROWI_USER_ID,
                ticket_type="referral",
                channel_prefix="referral",
                intro_message=referral_msg,
            )
            await interaction.response.send_message(
                f"✅ Referral ticket ready: {ch.mention}", ephemeral=True
            )
        except RuntimeError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
        except Exception:
            logger.exception("Failed to create referral ticket for %s", interaction.user)
            await interaction.response.send_message(
                "❌ Couldn't create the referral ticket.", ephemeral=True
            )


class HelpMenuCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="tierinfo",
        description="Show the tier and badge rules for THC members.",
    )
    async def tierinfo(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="THC Tier & Badge System",
            color=0xFFD700,
        )

        embed.add_field(
            name="Creator Tiers (GMV-based)",
            value=(
                "Tiers are based on your total GMV (Gross Merchandise Value).\n"
                "Select your tier via the **Tier / Roles** button when you mention the bot.\n\n"
                "**Tier 1** — $0 – $50k GMV\n"
                "**Tier 2** — $50k – $100k GMV\n"
                "**Tier 3** — $100k – $200k GMV\n"
                "**Tier 4** — $200k+ GMV"
            ),
            inline=False,
        )

        embed.add_field(
            name="Activity Badges",
            value=(
                "Badges are earned automatically based on your activity.\n\n"
                "🥉 **Bronze** — Introduce yourself in main chat by mentioning the bot with the word `intro`\n"
                "🥈 **Silver** — Post a win in the wins channel mentioning the bot with the word `win`\n"
                f"🥇 **Gold** — {GOLD_CHAT_MIN}+ chat messages AND {GOLD_WINS_MIN}+ wins\n"
                f"💎 **Diamond** — ${DIAMOND_GMV_MIN:,}+ GMV AND {DIAMOND_CHAT_MIN}+ chat messages AND {DIAMOND_WINS_MIN}+ wins\n"
                f"🏆 **Platinum** — ${PLATINUM_GMV_MIN:,}+ GMV AND {PLATINUM_CHAT_MIN}+ chat messages AND {PLATINUM_WINS_MIN}+ wins"
            ),
            inline=False,
        )

        embed.set_footer(text="Badges upgrade automatically when you hit the thresholds. GMV is set by staff.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="help",
        description="Show all available bot commands and what they do.",
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="THC Bot — Commands",
            color=0xFFD700,
        )

        embed.add_field(
            name="General Commands",
            value=(
                "**/help** — Show this list of commands\n"
                "**/tierinfo** — Show tier and badge rules\n"
                "**/stats** — View your stats (chat messages, wins, GMV, badge, tier)\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="Staff Commands",
            value=(
                "**/setgmv** `<user> <amount>` — Set a member's GMV and recheck their badge\n"
                "**/setbadge** `<user> <badge>` — Manually assign a badge to a member\n"
                "**/stats** `<user>` — View another member's stats\n"
                "**/leaderboard** — Top 10 members by GMV\n"
                "**/bind** `<message> <brand> <form>` — Bind a message so reactions DM the form\n"
                "**/unbind** `<message>` — Remove a message binding\n"
                "**/list_binds** — List all active message bindings\n"
                "**/newbrand** `<channel>` — Post & bind a new brand announcement via a form\n"
                "**/post_onboard** `<channel> <brand> <form>` — Post an onboarding message and auto-bind it\n"
                "**/bind_role_react** `<message_id> <role> <channel>` — Assign a role when a message is reacted to\n"
                "**/post_payment_panel** `<channel>` — Post the payment request panel\n"
            ),
            inline=False,
        )

        embed.add_field(
            name="Interactive Menu",
            value=(
                "Mention the bot in any channel to open the help menu with these options:\n"
                "1️⃣ **Growi Help** — Open a private support ticket\n"
                "2️⃣ **Apply to Brand** — Find and apply for brand deals\n"
                "3️⃣ **Tier / Roles** — Self-assign your creator tier\n"
                "4️⃣ **Get Started** — Learn about THC Academy & THC Premium\n"
                "5️⃣ **Select Referral** — Open a referral ticket\n"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpMenuCog(bot))
