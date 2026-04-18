import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    PAYMENTS_REQUEST_CHANNEL_ID,
    PAYMENTS_STAFF_ROLE_IDS,
    PAYMENTS_TICKETS_CATEGORY_NAME,
)
from util import is_staff, sanitize_channel_slug

logger = logging.getLogger("thcbot")


def _is_payments_staff(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if is_staff(member):
        return True
    staff_ids = {int(x) for x in PAYMENTS_STAFF_ROLE_IDS if int(x) != 0}
    return any(r.id in staff_ids for r in member.roles)


async def _get_or_create_payments_category(
    guild: discord.Guild,
) -> discord.CategoryChannel | None:
    name = (PAYMENTS_TICKETS_CATEGORY_NAME or "").strip()
    if not name:
        return None
    cat = discord.utils.get(guild.categories, name=name)
    if cat:
        return cat
    return await guild.create_category(name, reason="Create payments tickets category")


async def _unique_channel_name_in_category(
    category: discord.CategoryChannel | None, base_name: str
) -> str:
    base = base_name[:90]
    existing = {c.name for c in category.text_channels} if category else set()
    if base not in existing:
        return base
    i = 2
    while True:
        candidate = f"{base}-{i}"[:90]
        if candidate not in existing:
            return candidate
        i += 1


class ClosePaymentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔴 Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="thc:payments_close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        if not isinstance(member, discord.Member):
            return await interaction.response.send_message("⛔ Not allowed.", ephemeral=True)

        if not _is_payments_staff(member):
            return await interaction.response.send_message(
                "⛔ Only payments staff can close this ticket.", ephemeral=True
            )

        await interaction.response.send_message("✅ Closing ticket…", ephemeral=True)
        try:
            await interaction.channel.delete(reason=f"Payments ticket closed by {member}")
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I lack permission to delete this channel (need Manage Channels).",
                ephemeral=True,
            )


async def create_payment_ticket(
    guild: discord.Guild, opener: discord.Member
) -> discord.TextChannel:
    staff_role_ids = [int(x) for x in PAYMENTS_STAFF_ROLE_IDS if int(x) != 0]
    staff_roles = [r for rid in staff_role_ids if (r := guild.get_role(rid))]

    if not staff_roles:
        raise RuntimeError("No valid PAYMENTS_STAFF_ROLE_IDS found. Add role IDs in config.py.")

    bot_member: discord.Member | None = guild.me

    overwrites: dict = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        opener: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            manage_messages=True,
        )

    category = await _get_or_create_payments_category(guild)
    base_slug = sanitize_channel_slug(opener.display_name)
    channel_name = await _unique_channel_name_in_category(category, f"payment-{base_slug}")

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        topic=f"PAYMENT | Opened by {opener} ({opener.id})",
        overwrites=overwrites,
        category=category,
        reason=f"Payment ticket opened by {opener}",
    )

    welcome = (
        f"✅ **Payment Ticket Created**\n\n"
        f"Hi {opener.mention}, please share the details below so we can process this faster:\n\n"
        f"1) **Brand name**\n"
        f"2) **Amount requested**\n"
        f"3) **Payment method** (Wise, PayPal, Bank, etc)\n"
        f"4) **Proof / screenshots** (required)\n"
        f"5) **Any links or invoice details** (optional)\n\n"
        f"Once everything is verified, the payments team will proceed.\n\n"
        f"Payments staff can close this ticket using the button below."
    )
    await ticket_channel.send(welcome, view=ClosePaymentTicketView())
    return ticket_channel


class PaymentRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="💳 Request Payment",
        style=discord.ButtonStyle.primary,
        custom_id="thc:payments_request_payment",
    )
    async def request_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "⛔ This only works in the server.", ephemeral=True
            )

        if (
            PAYMENTS_REQUEST_CHANNEL_ID
            and interaction.channel
            and interaction.channel.id != PAYMENTS_REQUEST_CHANNEL_ID
        ):
            return await interaction.response.send_message(
                "Please use the payment request panel in the correct channel.", ephemeral=True
            )

        await interaction.response.send_message("✅ Creating your payment ticket…", ephemeral=True)
        try:
            ch = await create_payment_ticket(interaction.guild, interaction.user)
            await interaction.followup.send(f"✅ Ticket created: {ch.mention}", ephemeral=True)
        except Exception as e:
            logger.exception("Failed to create payment ticket for %s", interaction.user)
            await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)


class PaymentsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ClosePaymentTicketView())
        self.bot.add_view(PaymentRequestView())

    @app_commands.command(
        name="post_payment_panel",
        description="Post the payment request panel with a button (payments staff only).",
    )
    @app_commands.describe(channel="Channel where the panel should be posted")
    @app_commands.default_permissions(manage_messages=True)
    async def post_payment_panel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        if not isinstance(interaction.user, discord.Member) or not _is_payments_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        if PAYMENTS_REQUEST_CHANNEL_ID and channel.id != PAYMENTS_REQUEST_CHANNEL_ID:
            await interaction.response.send_message(
                "This panel must be posted in the configured payment request channel.",
                ephemeral=True,
            )
            return

        panel_text = (
            "**Payment Requests**\n\n"
            "Click the button below to open a private payment ticket with the team.\n"
            "Please only open a ticket when you are ready to provide proof and details."
        )
        await channel.send(panel_text, view=PaymentRequestView())
        await interaction.response.send_message(
            f"✅ Payment panel posted in {channel.mention}.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PaymentsCog(bot))
