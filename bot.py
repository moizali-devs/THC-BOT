import os
import asyncio
import discord
import time
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from store import find_binding

# One DM per (message_id, user_id) per cooldown window
COOLDOWN_SECONDS = 24 * 60 * 60  # 24h; change as you like
_SENT_CACHE: dict[tuple[int, int], float] = {}

# --- Ticket config for growi---
# <-- replace with your Growi person's Discord user ID
GROWI_USER_ID = 1363412581137780911
# auto-creates this category; set "" to disable
TICKETS_CATEGORY_NAME = "Growi Ticket"

# on_raw_reaction_add gives us payload even if message isn't cached
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Applu channel id
APPLY_CHANNEL_ID = 1282723291618082836

# --- Welcome config ---
WELCOME_CHANNEL_ID = 1282010168015716536  # set in .env
WELCOME_MESSAGE = (
    "Hey {mention} — welcome to **THC**! 🎉\n\n"
    "Here we will guide you on how to make your first 10k/m online.\n\n"
    "Follow the steps below to achieve financial freedom (Free Course Below):\n"
    "https://docs.google.com/presentation/d/1F_k8P0lX3eizRbb87Q8FQzTNJYq1ufimxLUikOCDxao/edit?usp=sharing\n\n"
    "Be sure to check out the brand deals section to start making your first bit of online money.\n\n"
    # Examples if you want them visible too:
    # "Name: {name}\nUser ID: {id}\n"
)


# optional but recommended for fast slash command sync
GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_reactions = True
intents.dm_messages = True  # not strictly required to send DMs, but fine to keep
intents.members = True


class SonOfAndOn(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # load cog
        await self.load_extension("cogs.admin")
        # fast sync to a single guild if provided

        # IMPORTANT: register persistent views once on boot
        self.add_view(CloseTicketView())

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
        else:
            synced = await self.tree.sync()
            print(
                f"✅ Synced {len(synced)} global commands (can take ~1h to appear)")


bot = SonOfAndOn()


DM_REPLY_TEMPLATE = (
    "# 🎉 Welcome to the THC Server 🎉\n"

    "Here at THC, we:\n"
    "- Work with TikTok Shop creators.\n"
    "- Provide opportunities and retainers.\n"
    "- Support your growth as a creator.\n"

    "💬 If you have any questions, please reach out to <@563044854792323082>.\n"

)


async def send_welcome(member: discord.Member):
    if member.bot:
        return

    # Get your welcome channel (by ID from config)
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID) or await bot.fetch_channel(WELCOME_CHANNEL_ID)

    # --- STEP 1: Send live ping so they get the notification ---
    live_text = WELCOME_MESSAGE.format(
        mention=member.mention,               # Real ping
        name=member.display_name,
        id=member.id,
        guild=member.guild.name,
    )

    msg = await channel.send(
        live_text,
        allowed_mentions=discord.AllowedMentions(
            users=True, roles=False, everyone=False)
    )

    # --- STEP 2: Wait a bit, then make it unclickable ---
    await asyncio.sleep(2)

    # Option A: Show escaped mention (looks like <@1234> but not clickable)
    # safe_mention = f"\\<@{member.id}>"

    # Option B: OR show name only (you can comment/uncomment depending on preference)
    safe_mention = f"`@{member.display_name}`"

    safe_text = WELCOME_MESSAGE.format(
        mention=safe_mention,
        name=member.display_name,
        id=member.id,
        guild=member.guild.name,
    )

    await msg.edit(
        content=safe_text,
        allowed_mentions=discord.AllowedMentions.none()
    )


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# new code
# ---------- Tickets: helpers ----------


async def _get_or_create_tickets_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    name = TICKETS_CATEGORY_NAME.strip()
    if not name:
        return None
    cat = discord.utils.get(guild.categories, name=name)
    if cat:
        return cat
    return await guild.create_category(name, reason="Create tickets category")


@bot.event
async def on_member_join(member: discord.Member):
    await send_welcome(member)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(
        label="🔴 Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="thc:close_ticket"  # <-- stable id
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # recover opener from channel topic so we don't need in-memory state
        opener_id = None
        topic = getattr(interaction.channel, "topic", "") or ""
        if "TICKET:" in topic:
            try:
                opener_id = int(topic.split("TICKET:")[
                                1].split()[0].strip("| "))
            except Exception:
                pass

        user = interaction.user
        allowed = (
            (opener_id and user.id == opener_id) or
            user.id == GROWI_USER_ID or
            (isinstance(user, discord.Member)
             and user.guild_permissions.manage_channels)
        )
        if not allowed:
            return await interaction.response.send_message("⛔ You’re not allowed to close this ticket.", ephemeral=True)

        await interaction.response.send_message("✅ Closing ticket…", ephemeral=True)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {user}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I lack permission to delete this channel (need **Manage Channels**).", ephemeral=True)


async def create_ticket(guild: discord.Guild, opener: discord.Member, growi_user_id: int) -> discord.TextChannel:
    """Create a private ticket channel for opener + growi user + bot. Prevents duplicates."""
    growi_member: discord.Member | None = guild.get_member(growi_user_id)
    bot_member: discord.Member | None = guild.me

    if growi_member is None:
        raise RuntimeError("Configured Growi user not found in this server.")

    # Prevent duplicates by tagging topic
    ticket_tag = f"TICKET:{opener.id}"
    for ch in guild.text_channels:
        if ch.topic and ticket_tag in ch.topic:
            return ch  # return existing channel

    # Build overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        opener: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True
        ),
        growi_member: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True
        ),
    }
    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True, manage_messages=True
        )

    category = await _get_or_create_tickets_category(guild)
    channel_name = f"ticket-{opener.name}".lower().replace(" ", "-")[:90]

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        topic=f"{ticket_tag} | Opened by {opener} ({opener.id})",
        overwrites=overwrites,
        category=category,
        reason=f"Ticket opened by {opener}",
    )

    # Drop close button
    view = CloseTicketView()
    await ticket_channel.send(
        f"Hello {opener.mention}! This is your private support channel.\n"
        f"{growi_member.mention} and <@{bot_member.id}> are here.\n"
        f"Click **Close Ticket** when you’re done.",
        view=view,
    )
    return ticket_channel


class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)  # menu expires after 60s

    @discord.ui.button(label="1️⃣ Growi Help", style=discord.ButtonStyle.primary)
    async def button_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ch = await create_ticket(interaction.guild, interaction.user, GROWI_USER_ID)
            await interaction.response.send_message(f"✅ Ticket ready: {ch.mention}", ephemeral=True)
        except RuntimeError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ Couldn’t create the ticket.", ephemeral=True)

    # @discord.ui.button(label="2️⃣ Apply to brands", style=discord.ButtonStyle.success)
    # async def button_guidance(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.send_message("You chose **Guidance** 🧭", ephemeral=True)

    @discord.ui.button(label="2️⃣ Apply to Brand", style=discord.ButtonStyle.success, custom_id="apply_btn")
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_mention = f"<#{APPLY_CHANNEL_ID}>"
        await interaction.response.send_message(
            f"All brand deals can be found in {channel_mention}.\n"
            f"React ✅ to receive the application form in your DMs.",
            ephemeral=True
        )

    @discord.ui.button(label="3️⃣ Talk with frhan", style=discord.ButtonStyle.secondary)
    async def button_droid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose **Droid Help** 🤖", ephemeral=True)

    @discord.ui.button(label="4️⃣ Server suggestions", style=discord.ButtonStyle.danger)
    async def button_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose **Other** ⚡", ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    # ignore bots (including ourselves)
    if message.author.bot:
        return

    # 1) Reply to **DMs to the bot**
    if isinstance(message.channel, discord.DMChannel):
        await message.reply(DM_REPLY_TEMPLATE)
        return

    # 2) If bot is mentioned → show interactive menu
    if bot.user and bot.user in message.mentions:
        view = HelpMenu()
        await message.channel.send("Hi! 👋 Please choose an option below:", view=view)
        return  # stop here so it doesn’t also send DM_REPLY_TEMPLATE

    # 3) (Optional) Reply in servers if message starts with "A"
    starts_with_A = message.content.strip().lower().startswith("a")
    if starts_with_A:
        try:
            await message.reply(DM_REPLY_TEMPLATE, mention_author=True)
        except discord.Forbidden:
            pass

    # keep commands working
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    try:
        # ignore bot's own reaction
        if payload.user_id == bot.user.id:
            return

        # Is this message bound?
        binding = find_binding(payload.message_id)
        if not binding:
            return

        # Require ✅ (either because it's stored, or force it if binding was ANY)
        target_emoji = binding.get("emoji") or "ANY"
        if target_emoji != "ANY":
            if payload.emoji.name != target_emoji and str(payload.emoji) != target_emoji:
                return
        else:
            # force ✅ for old ANY bindings
            if payload.emoji.name != "✅" and str(payload.emoji) != "✅":
                return

        # One DM per user per message (with cooldown)
        key = (payload.message_id, payload.user_id)
        now = time.time()
        if now - _SENT_CACHE.get(key, 0) < COOLDOWN_SECONDS:
            return

        # Fetch user and DM
        user = bot.get_user(payload.user_id) or await bot.fetch_user(payload.user_id)
        try:
            # here is what the user will receive
            await user.send(f"Here is your **{binding['brand']}** onboarding form:\n{binding['form']}")
            _SENT_CACHE[key] = now
        except Exception:
            # Fallback: notify in channel (public)
            try:
                channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
                await channel.send(
                    f"<@{payload.user_id}>, I couldn't DM you. Please enable **Allow DMs from server members** "
                    f"or ask an admin for the **{binding['brand']}** form."
                )
                _SENT_CACHE[key] = now
            except Exception:
                pass

    except Exception as e:
        print("Reaction handler error:", e)


def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing in .env")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
