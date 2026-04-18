import logging

import discord
from discord.ext import commands

from config import APPLY_CHANNEL_ID, GROWI_USER_ID
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


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpMenuCog(bot))
