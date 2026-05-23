import discord
from discord import app_commands
from discord.ext import commands

from util import is_staff

_OPTIONS = [
    discord.SelectOption(
        label="Welcome Message",
        value="welcome",
        description="Preview the welcome embed for yourself",
        emoji="👋",
    ),
    discord.SelectOption(
        label="Help Embed",
        value="help",
        description="Show the /help embed",
        emoji="❓",
    ),
    discord.SelectOption(
        label="Tier Info",
        value="tierinfo",
        description="Show the /tierinfo embed",
        emoji="🏆",
    ),
    discord.SelectOption(
        label="Leaderboard",
        value="leaderboard",
        description="Show top 10 members by GMV",
        emoji="💰",
    ),
    discord.SelectOption(
        label="Weekly Summary",
        value="weekly",
        description="Actually posts the weekly summary to the channel",
        emoji="📊",
    ),
]


class TestSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self._bot = bot
        super().__init__(placeholder="Choose a command to test...", options=_OPTIONS)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]

        if val == "welcome":
            from cogs.welcome import WelcomeLinks
            cog = self._bot.cogs.get("WelcomeCog")
            if not cog:
                return await interaction.response.send_message("WelcomeCog not loaded.", ephemeral=True)
            embed = cog._build_embed(interaction.user)
            await interaction.response.send_message(embed=embed, view=WelcomeLinks(), ephemeral=True)

        elif val == "help":
            cog = self._bot.cogs.get("HelpMenuCog")
            if not cog:
                return await interaction.response.send_message("HelpMenuCog not loaded.", ephemeral=True)
            await cog.help_command.callback(cog, interaction)

        elif val == "tierinfo":
            cog = self._bot.cogs.get("HelpMenuCog")
            if not cog:
                return await interaction.response.send_message("HelpMenuCog not loaded.", ephemeral=True)
            await cog.tierinfo.callback(cog, interaction)

        elif val == "leaderboard":
            cog = self._bot.cogs.get("BadgesCog")
            if not cog:
                return await interaction.response.send_message("BadgesCog not loaded.", ephemeral=True)
            await cog.leaderboard.callback(cog, interaction)

        elif val == "weekly":
            cog = self._bot.cogs.get("WeeklySummaryCog")
            if not cog:
                return await interaction.response.send_message("WeeklySummaryCog not loaded.", ephemeral=True)
            await cog.post_weekly_summary.callback(cog, interaction)


class TestSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.add_item(TestSelect(bot))


class TestPanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="test", description="Open the test panel to preview bot commands (staff only).")
    async def test(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Select a command to test:",
            view=TestSelectView(self.bot),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TestPanelCog(bot))
