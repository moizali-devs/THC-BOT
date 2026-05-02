import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from discord import TextStyle
from util import is_staff, is_valid_url, parse_message_ref
from store import upsert_binding, remove_binding, list_bindings_for_guild

DEFAULT_EMOJI = "ANY"


class NewBrandModal(Modal, title="New Brand Onboarding"):
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.target_channel = target_channel

        self.message_input = TextInput(
            label="Message to post (essay)",
            style=TextStyle.paragraph,
            required=True,
            max_length=1900,  # Discord hard limit ~2000 chars per message
            placeholder="Paste the full announcement text that should appear in the channel…"
        )
        self.brand_input = TextInput(
            label="Brand name",
            style=TextStyle.short,
            required=True,
            placeholder="e.g., Crypto Wallet X"
        )
        self.form_input = TextInput(
            label="Form link (URL)",
            style=TextStyle.short,
            required=True,
            placeholder="https://…"
        )

        self.add_item(self.message_input)
        self.add_item(self.brand_input)
        self.add_item(self.form_input)

    async def on_submit(self, interaction: discord.Interaction):
        essay = str(self.message_input.value).strip()
        brand = str(self.brand_input.value).strip()
        form = str(self.form_input.value).strip()

        if not is_valid_url(form):
            return await interaction.response.send_message("❌ Invalid form URL.", ephemeral=True)

        # 1) Post the essay
        try:
            msg = await self.target_channel.send(essay)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Couldn't post in {self.target_channel.mention}: {e}", ephemeral=True)

        # 2) Bind the message so reactions DM the standardized onboarding text
        upsert_binding(
            message_id=msg.id,
            brand=brand,
            form=form,
            guild_id=interaction.guild_id,
            channel_id=self.target_channel.id,
            emoji="✅"
            # change this to change the emoji
        )

        await interaction.response.send_message(
            f"✅ Posted and bound message **{msg.id}** in {self.target_channel.mention} for **{brand}**.",
            ephemeral=True
        )


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    # --- /bind ---

    @app_commands.command(name="bind", description="Bind an existing message to a brand & form URL. Reactions on that message will DM the form.")
    @app_commands.describe(message="Message link or ID", brand="Brand name", form="Form URL", emoji="Optional: limit to a specific emoji (default: ANY)")
    @app_commands.default_permissions(manage_messages=True)
    async def bind(self, interaction: discord.Interaction, message: str, brand: str, form: str, emoji: str | None = None):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        if not is_valid_url(form):
            return await interaction.response.send_message("❌ Invalid URL.", ephemeral=True)
        try:
            ref = parse_message_ref(message)
        except ValueError as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)

        em = emoji or DEFAULT_EMOJI
        upsert_binding(
            message_id=ref["message_id"],
            brand=brand,
            form=form,
            guild_id=(ref.get("guild_id") or interaction.guild_id),
            channel_id=ref.get("channel_id"),
            emoji=em
        )
        await interaction.response.send_message(
            f"✅ Bound message **{ref['message_id']}** → **{brand}** ({form}){'' if em == 'ANY' else f' [emoji: {em}]'}",
            ephemeral=True
        )

    # --- /unbind ---
    @app_commands.command(name="unbind", description="Remove a binding by message link or ID.")
    @app_commands.describe(message="Message link or ID")
    @app_commands.default_permissions(manage_messages=True)
    async def unbind(self, interaction: discord.Interaction, message: str):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        try:
            ref = parse_message_ref(message)
        except ValueError as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        remove_binding(ref["message_id"])
        await interaction.response.send_message(f"🗑️ Unbound **{ref['message_id']}**", ephemeral=True)

    # --- /list_binds ---
    @app_commands.command(name="list_binds", description="List all current message → form bindings.")
    @app_commands.default_permissions(manage_messages=True)
    async def list_binds(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        binds = list_bindings_for_guild(interaction.guild_id)
        if not binds:
            return await interaction.response.send_message("_No bindings yet._", ephemeral=True)
        lines = [
            f"• `{b['message_id']}` → **{b['brand']}** ({b['form']})"
            + (f" [emoji: {b['emoji']}]" if b.get('emoji')
               and b['emoji'] != 'ANY' else "")
            for b in binds
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
    # --- /adding ---

    @app_commands.command(
        name="newbrand",
        description="Open a form: paste the message to post, then provide brand name and form link. I’ll post & bind it."
    )
    @app_commands.describe(channel="Where to post the announcement")
    @app_commands.default_permissions(manage_messages=True)
    async def newbrand(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don’t have permission to use this.", ephemeral=True)
        modal = NewBrandModal(target_channel=channel)
        await interaction.response.send_modal(modal)

    # --- /post_onboard ---

    @app_commands.command(name="post_onboard", description="Post an onboarding message and auto-bind it.")
    @app_commands.describe(channel="Target text channel", brand="Brand name", form="Form URL", emoji="Optional emoji to pre-react with")
    @app_commands.default_permissions(manage_messages=True)
    async def post_onboard(self, interaction: discord.Interaction, channel: discord.TextChannel, brand: str, form: str, emoji: str | None = None):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        if not is_valid_url(form):
            return await interaction.response.send_message("❌ Invalid URL.", ephemeral=True)

        msg = await channel.send(f"**{brand} Onboarding**\nReact to this message to receive the form via DM.")
        if emoji:
            try:
                await msg.add_reaction(emoji)
            except Exception:
                pass

        upsert_binding(
            message_id=msg.id,
            brand=brand,
            form=form,
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            emoji="✅"  # allow any emoji by default
        )
        await interaction.response.send_message(f"✅ Posted & bound message **{msg.id}** for **{brand}**.", ephemeral=True)


    # --- /setbadge ---

    @app_commands.command(
        name="setbadge",
        description="Manually assign a badge to a member (staff only).",
    )
    @app_commands.describe(
        user="Member to assign the badge to",
        badge="Badge key: bronze / silver / gold / diamond / platinum",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def setbadge(
        self, interaction: discord.Interaction, user: discord.Member, badge: str
    ):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        badge = badge.strip().lower()
        valid = {"bronze", "silver", "gold", "diamond", "platinum"}
        if badge not in valid:
            return await interaction.response.send_message(
                f"❌ Invalid badge. Choose from: {', '.join(sorted(valid))}",
                ephemeral=True,
            )

        from cogs.badges import assign_badge  # lazy import — badges cog loaded after admin

        try:
            await assign_badge(user, badge, reason=f"Manual override by {interaction.user}")
            await interaction.response.send_message(
                f"✅ Assigned **{badge}** badge to {user.mention}.",
                allowed_mentions=discord.AllowedMentions(users=[user]),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    # --- /bind_role_react ---

    @app_commands.command(
        name="bind_role_react",
        description="Bind a message reaction to a role assignment.",
    )
    @app_commands.describe(
        message_id="Message ID to bind",
        role="Role to assign on reaction",
        channel="Channel where the message lives",
        brand="Label for this deal",
        emoji="Emoji to accept (default ✅)",
    )
    @app_commands.default_permissions(manage_messages=True)
    async def bind_role_react(
        self,
        interaction: discord.Interaction,
        message_id: str,
        role: discord.Role,
        channel: discord.TextChannel,
        brand: str = "Deal",
        emoji: str = "✅",
    ):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("⛔ You don't have permission to use this.", ephemeral=True)
        upsert_binding(
            message_id=int(message_id),
            brand=brand,
            form="",
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            emoji=emoji,
            kind="role",
            role_id=role.id,
        )
        await interaction.response.send_message(
            f"Bound message {message_id} to role {role.mention} on emoji {emoji}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
