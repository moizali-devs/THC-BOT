import logging

import discord
from discord.ext import commands

from config import GROWI_USER_ID, TICKETS_CATEGORY_NAME

logger = logging.getLogger("thcbot")


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔴 Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="thc:close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        opener_id = None
        topic = getattr(interaction.channel, "topic", "") or ""
        if "TICKET:" in topic:
            try:
                opener_id = int(topic.split("TICKET:")[1].split()[0].strip("| "))
            except Exception:
                pass

        user = interaction.user
        allowed = (
            (opener_id and user.id == opener_id)
            or user.id == GROWI_USER_ID
            or (isinstance(user, discord.Member) and user.guild_permissions.manage_channels)
        )
        if not allowed:
            return await interaction.response.send_message(
                "⛔ You're not allowed to close this ticket.", ephemeral=True
            )

        await interaction.response.send_message("✅ Closing ticket…", ephemeral=True)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I lack permission to delete this channel (need **Manage Channels**).",
                ephemeral=True,
            )


async def _get_or_create_tickets_category(
    guild: discord.Guild,
) -> discord.CategoryChannel | None:
    name = TICKETS_CATEGORY_NAME.strip()
    if not name:
        return None
    cat = discord.utils.get(guild.categories, name=name)
    if cat:
        return cat
    return await guild.create_category(name, reason="Create tickets category")


async def create_ticket(
    guild: discord.Guild,
    opener: discord.Member,
    growi_user_id: int,
    *,
    ticket_type: str = "growi",
    channel_prefix: str = "ticket",
    intro_message: str | None = None,
) -> discord.TextChannel:
    """Create a private ticket channel. Prevents duplicate tickets per ticket_type per user."""
    growi_member: discord.Member | None = guild.get_member(growi_user_id)
    bot_member: discord.Member | None = guild.me

    if growi_member is None:
        raise RuntimeError("Configured Growi user not found in this server.")

    ticket_tag = f"TICKET:{ticket_type}:{opener.id}"
    for ch in guild.text_channels:
        if ch.topic and ticket_tag in ch.topic:
            return ch

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        opener: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        growi_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }
    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            manage_messages=True,
        )

    category = await _get_or_create_tickets_category(guild)
    safe_name = opener.name.lower().replace(" ", "-")
    channel_name = f"{channel_prefix}-{safe_name}"[:90]

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        topic=f"{ticket_tag} | Opened by {opener} ({opener.id})",
        overwrites=overwrites,
        category=category,
        reason=f"{ticket_type} ticket opened by {opener}",
    )

    if intro_message is None:
        intro_message = (
            f"Hello {opener.mention}! This is your private support channel.\n"
            f"{growi_member.mention} and <@{bot_member.id}> are here.\n"
            f"Click **Close Ticket** when you're done."
        )

    await ticket_channel.send(intro_message, view=CloseTicketView())
    return ticket_channel


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(CloseTicketView())


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
