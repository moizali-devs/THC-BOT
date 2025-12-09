import os
import atexit
import asyncio
import discord
import time
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from store import find_binding
import re
from activity_store import load_activity, save_activity

# One DM per (message_id, user_id) per cooldown window
COOLDOWN_SECONDS = 24 * 60 * 60  # 24h; change as you like
_SENT_CACHE: dict[tuple[int, int], float] = {}

# --- Ticket config for growi---
# <-- replace with your Growi person's Discord user ID
GROWI_USER_ID = 1427318529622933736
# auto-creates this category; set "" to disable
TICKETS_CATEGORY_NAME = "Growi Ticket"

# on_raw_reaction_add gives us payload even if message isn't cached
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Applu channel id
APPLY_CHANNEL_ID = 1282723291618082836

TIER_ROLE_IDS = {
    1: 1425403368817426543,  # Tier 1
    2: 1425403496387186770,  # Tier 2
    3: 1425403540775370833,  # Tier 3
    4: 1425403620139991061,  # Tier 4
}

#NEW CODE DEC5#----------------------------------------------------------
# - Badge roles for Bronze - Platinum
# TODO: replace these with real role IDs from your server
BADGE_ROLE_IDS = {
    "bronze": 1447644206897303765,      # e.g. 123456789012345678
    "silver": 1447644686134153286,
    "gold": 1447644808943370484,
    "diamond": 1447645001789083839,
    "platinum": 1447645453259636847,
}

# - Channel IDs for main chat and wins channel
# TODO: replace with your actual channel IDs
MAIN_CHAT_ID = 1291049360473456651      # e.g. 1282010168015716536 or your main chat
WINS_CHANNEL_ID = 1292975300740644936   # e.g. ID of #wins channel

# - Rank thresholds (example values, tune as you like)
GOLD_CHAT_MIN = 50
GOLD_WINS_MIN = 6

DIAMOND_GMV_MIN = 100_000
DIAMOND_CHAT_MIN = 60
DIAMOND_WINS_MIN = 5

PLATINUM_GMV_MIN = 250_000
PLATINUM_CHAT_MIN = 150
PLATINUM_WINS_MIN = 10

# - Load activity data at startup
# activity: dict[str(user_id)] -> {"chat_msgs": int, "wins": int, "gmv": int}
ACTIVITY = load_activity()

#something 
@atexit.register
def _flush_activity_on_exit():
    try:
        if ACTIVITY:
            save_activity(ACTIVITY)
    except Exception:
        pass


# Save to disk at most once every 10 minutes
SAVE_ACTIVITY_INTERVAL = 10 * 60  # 10 minutes
_last_activity_save = time.time()


def maybe_flush_activity():
    """
    Save ACTIVITY to disk at most once per SAVE_ACTIVITY_INTERVAL.
    Call this after you change ACTIVITY.
    """
    global _last_activity_save
    now = time.time()
    if now - _last_activity_save >= SAVE_ACTIVITY_INTERVAL:
        save_activity(ACTIVITY)
        _last_activity_save = now


# --- Welcome config ---
WELCOME_CHANNEL_ID = 1282010168015716536  # set in .env
WELCOME_MESSAGE = (
    "Hey {mention} — welcome to **THC**! 🎉\n\n"
    "Here we will guide you on how to make your first 10k/m online.\n\n"
    "Follow the steps below to achieve financial freedom (Free Course Below):\n"
    "https://docs.google.com/presentation/d/1F_k8P0lX3eizRbb87Q8FQzTNJYq1ufimxLUikOCDxao/edit?usp=sharing\n\n"
    "Be sure to check out the brand deals section to start making your first bit of online money.\n\n"
    # "Here is the link to our onboarding call! 📞:\n"
    # "https://discord.gg/PZP9e9Ex?event=1442642136485986375\n\n"
    # Examples if you want them visible too:
    # "Name: {name}\nUser ID: {id}\n"
)
# New Code 15th nov (remove if the code works)

# --- Form config for new members ---
FORM_DELAY_SECONDS = 5 * 60  # 5 minutes

# --- This is the form link below
FORM_LINK = "https://forms.gle/YV4PnCjfcMLZk7j48"

# User who will help with the form issue
HELPER_USER_ID = 1427318529622933736  # TODO: replace with your Discord user ID

FORM_DM_TEMPLATE = (
    "Hey {name}, welcome to **The Hustlers Club** 🎉\n\n"
    "To be considered for current and future brand deals inside The Hustlers Club, "
    "Please fill out this short form:\n"
    "{form_link}\n\n"
    "If you face any issues while filling it out, please message {helper_mention}."
)

# optional but recommended for fast slash command sync
GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_reactions = True
intents.dm_messages = True  # not strictly required to send DMs, but fine to keep
intents.members = True
intents.message_content = True


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


async def send_delayed_form(member: discord.Member):
    # Wait 5 minutes before sending
    await asyncio.sleep(FORM_DELAY_SECONDS)

    # If the member left during the delay, do nothing
    if member.guild.get_member(member.id) is None:
        return

    helper_mention = f"<@{HELPER_USER_ID}>"

    try:
        # Try sending them a DM
        await member.send(
            FORM_DM_TEMPLATE.format(
                name=member.display_name,
                form_link=FORM_LINK,
                helper_mention=helper_mention,
            )
        )
    except Exception:
        # DMs closed or blocked — silently ignore
        pass


# This is fallback code, if the person cannot be dmed the bot (if allowed below will send the message in the welcome channel)
    # except discord.Forbidden:
    #     # DMs are closed, fall back to welcome channel
    #     try:
    #         channel = member.guild.get_channel(WELCOME_CHANNEL_ID) or await bot.fetch_channel(WELCOME_CHANNEL_ID)
    #         await channel.send(
    #             f"{member.mention} to be considered for brand deals in **DaHustlersClub**, "
    #             f"please fill out this form:\n{FORM_LINK}\n\n"
    #             f"If you face any issues, please message {helper_mention}."
    #         )


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
    asyncio.create_task(send_delayed_form(member))


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

# -----------------------new code----------------------
# ---- Tier helpers ----


def _member_tier_roles(member: discord.Member):
    tier_role_ids = set(TIER_ROLE_IDS.values())
    return [r for r in member.roles if r.id in tier_role_ids]


async def assign_tier(member: discord.Member, tier: int):
    guild = member.guild
    role_id = TIER_ROLE_IDS.get(tier)
    if not role_id:
        raise ValueError(f"Unknown tier {tier}")
    role = guild.get_role(role_id)
    if role is None:
        raise RuntimeError(f"Role ID {role_id} not found in this server.")

    # remove any existing tier roles
    old_tiers = _member_tier_roles(member)
    if old_tiers:
        await member.remove_roles(*old_tiers, reason=f"Tier change -> T{tier}")

    # add the new tier
    await member.add_roles(role, reason=f"Assigned Tier {tier}")

# ---- Badge helpers ----

def _member_badge_roles(member: discord.Member):
    badge_role_ids = set(BADGE_ROLE_IDS.values())
    return [r for r in member.roles if r.id in badge_role_ids]


async def assign_badge(member: discord.Member, badge_key: str, reason: str = ""):
    guild = member.guild
    role_id = BADGE_ROLE_IDS.get(badge_key)
    if not role_id:
        raise ValueError(f"Unknown badge key {badge_key} or role ID missing")

    role = guild.get_role(role_id)
    if role is None:
        raise RuntimeError(f"Badge role ID {role_id} not found in this server")

    # remove any existing badge roles
    old_badges = _member_badge_roles(member)
    if old_badges:
        await member.remove_roles(*old_badges, reason=reason or f"Badge change -> {badge_key}")

    # add the new badge
    await member.add_roles(role, reason=reason or f"Assigned badge {badge_key}")


# ---- Activity helpers ----

def _get_stats(member: discord.Member) -> dict:
    user_key = str(member.id)
    stats = ACTIVITY.get(user_key)
    if stats is None:
        stats = {"chat_msgs": 0, "wins": 0, "gmv": 0}
        ACTIVITY[user_key] = stats
    # ensure fields exist even if file is old
    stats.setdefault("chat_msgs", 0)
    stats.setdefault("wins", 0)
    stats.setdefault("gmv", 0)
    return stats


def _current_badge_key(member: discord.Member) -> str | None:
    badge_by_id = {v: k for k, v in BADGE_ROLE_IDS.items()}
    for r in member.roles:
        key = badge_by_id.get(r.id)
        if key:
            return key
    return None


def _badge_rank_index(badge_key: str | None) -> int:
    order = ["bronze", "silver", "gold", "diamond", "platinum"]
    if badge_key is None:
        return -1
    try:
        return order.index(badge_key)
    except ValueError:
        return -1

#newcode#
async def _check_for_rank_upgrade(member: discord.Member):
    """
    Called every time we update stats or GMV.
    Decides if user should be upgraded based on thresholds.
    """
    stats = _get_stats(member)
    chat_msgs = stats["chat_msgs"]
    wins = stats["wins"]
    gmv = stats["gmv"]

    current = _current_badge_key(member)
    current_idx = _badge_rank_index(current)

    best = None
    best_idx = current_idx

    # Bronze and Silver are normally triggered by specific actions,
    # but we still treat them in the order chain
    # Gold
    if chat_msgs >= GOLD_CHAT_MIN and wins >= GOLD_WINS_MIN:
        if _badge_rank_index("gold") > best_idx:
            best = "gold"
            best_idx = _badge_rank_index("gold")

    # Diamond
    if gmv >= DIAMOND_GMV_MIN and chat_msgs >= DIAMOND_CHAT_MIN and wins >= DIAMOND_WINS_MIN:
        if _badge_rank_index("diamond") > best_idx:
            best = "diamond"
            best_idx = _badge_rank_index("diamond")

    # Platinum
    if gmv >= PLATINUM_GMV_MIN and chat_msgs >= PLATINUM_CHAT_MIN and wins >= PLATINUM_WINS_MIN:
        if _badge_rank_index("platinum") > best_idx:
            best = "platinum"
            best_idx = _badge_rank_index("platinum")

    if best and best_idx > current_idx:
        await assign_badge(member, best, reason="Auto badge upgrade from activity")
        maybe_flush_activity()



class TierButtons(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self._member = member

        # Define buttons inline (no separate label dict)
        self.add_item(self._make_button(
            1, "Tier 1 • 0–50k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(
            2, "Tier 2 • 50k–100k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(
            3, "Tier 3 • 100k–200k GMV", discord.ButtonStyle.success))
        self.add_item(self._make_button(
            4, "Tier 4 • 200k+ GMV", discord.ButtonStyle.success))

    def _make_button(self, tier: int, label: str, style: discord.ButtonStyle):
        async def _callback(interaction: discord.Interaction):
            # only the requester can use these
            if interaction.user.id != self._member.id:
                return await interaction.response.send_message(
                    "Only the requester can use these buttons.", ephemeral=True
                )
            try:
                await assign_tier(self._member, tier)
                await interaction.response.send_message(
                    f"✅ Assigned **Tier {tier}**. Previous tier removed.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)

        btn = discord.ui.Button(label=label, style=style)
        btn.callback = _callback
        return btn
# new code on Sunday 19th of oct


class GetHelpButtons(discord.ui.View):
    """Second-layer help topics, only clickable by the requester."""

    def __init__(self, member: discord.Member):
        super().__init__(timeout=120)
        self._member = member

        # Add as many help topics as you want here:
        # button 1
        self.add_item(self._make_button(
            key="THC_Academy_msg",  # start_no_tts
            label="THC Academy",
            style=discord.ButtonStyle.green
        ))
        # button 2
        self.add_item(self._make_button(
            key="THC_Premium_msg",
            label="THC Premium",
            style=discord.ButtonStyle.green
        ))
        # # button 3
        # self.add_item(self._make_button(
        #     key="content_ideas",
        #     label="THC Premium",
        #     style=discord.ButtonStyle.secondary
        # ))

    def _make_button(self, key: str, label: str, style: discord.ButtonStyle):
        async def _callback(interaction: discord.Interaction):
            # Only the person who opened the submenu can use it
            if interaction.user.id != self._member.id:
                return await interaction.response.send_message(
                    "Only the requester can use these buttons.", ephemeral=True
                )

            # Respond per-topic (edit these texts as you like)
            if key == "THC_Academy_msg":
                msg = (
                    "**THC Academy**\n"
                    "THC Academy is something we recommend every affiliate goes through. No matter the level.\n\n"
                    "It’s an **intensive step-by-step walkthrough** showing you how to go from sitting at home lazy 🛋️ "
                    "to making your first **$10K/month online 💸**.\n\n"
                    "The goal: start the Academy with zero knowledge and leave feeling like a **top-tier affiliate.**\n\n"
                    "__**THC Academy Offers:**__\n"
                    "• Walkthrough from start to finish\n"
                    "• Intense course (~10 hours of knowledge)\n"
                    "• Sales psychology fundamentals\n"
                    "• The mindset of a successful creator\n"
                    "• Pre-recorded interview calls with **7-figure creators**\n\n"
                    # "**Join now → [WHOP LINK](https://your.whop.link/here)**"
                )
            elif key == "THC_Premium_msg":
                msg = (
                    "**THC Premium**\n"
                    "THC Premium is for creators who are serious about taking their content to the next level. 🚀\n"
                    "It’s a step up from THC Free — a close-knit, experienced community built to help you grow faster and smarter.\n\n"
                    "__**THC Premium Offers:**__\n"
                    "• Exclusive Brand Deals 💼\n"
                    "• 1-on-1 Feedback from top coaches 🧠\n"
                    "• A network of the best creators in the space 🌎\n"
                    "• A closer, more supportive community 🤝\n"
                    "• Intensive TikTok Shop strategy & growth courses 🎥\n"
                    "• Live calls and real-time advice 🔥\n"
                    "• 1-on-1 access to 8-figure brand owners 💰\n\n"
                    # "**Join now → [WHOP LINK](https://your.whop.link/here)**"
                )

            elif key == "content_ideas":
                msg = (
                    "**Content Ideas / Hooks**\n"
                    "• “I tried X for 7 days—results shocked me”\n"
                    "• “3 mistakes killing your Y”\n"
                    "• “Do this before you buy Z”"
                )
            else:
                msg = "Coming soon."

            await interaction.response.send_message(msg, ephemeral=True)

        btn = discord.ui.Button(label=label, style=style)
        btn.callback = _callback
        return btn


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

    @discord.ui.button(label="2️⃣ Apply to Brand", style=discord.ButtonStyle.secondary, custom_id="apply_btn")
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_mention = f"<#{APPLY_CHANNEL_ID}>"
        await interaction.response.send_message(
            f"All brand deals can be found in {channel_mention}.\n"
            f"React ✅ to receive the application form in your DMs.",
            ephemeral=True
        )

    # @discord.ui.button(label="3️⃣4️⃣ Talk with frhan", style=discord.ButtonStyle.primary)
    # async def button_droid(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.send_message("You chose **Droid Help** 🤖", ephemeral=True)

    @discord.ui.button(label="3️⃣ Tier / Roles", style=discord.ButtonStyle.success)
    async def button_tiers(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Choose your tier based on your GMV:",
            view=TierButtons(interaction.user),
            ephemeral=True
        )

# 👉 NEW BUTTON code on 19th of oct
    @discord.ui.button(label="4️⃣ Get Started", style=discord.ButtonStyle.primary)
    async def button_get_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Pick a help topic:",
            view=GetHelpButtons(interaction.user),
            ephemeral=True
        )



@bot.event
async def on_message(message: discord.Message):
    # ignore bots (including ourselves)
    if message.author.bot:
        return
        
    content = message.content or ""
    lowered = content.lower()

    # 1) Reply to DMs to the bot
    if isinstance(message.channel, discord.DMChannel):
        await message.reply(DM_REPLY_TEMPLATE)
        return

    # 2) Activity tracking and Bronze/Silver triggers in guild channels
    if isinstance(message.channel, discord.TextChannel):
        member = message.author
        channel_id = message.channel.id
        # content = message.content or ""
        # lowered = content.lower()

        # Only track users who talk (this call creates stats entry)
        stats = _get_stats(member)

   
        # Count main chat messages
        if MAIN_CHAT_ID and channel_id == MAIN_CHAT_ID:
            stats["chat_msgs"] += 1

            # Bronze trigger: in main chat, message contains intro and mentions bot
            if bot.user and bot.user in message.mentions:
                if re.search(r"\bintro\b", lowered):
                    try:
                        await assign_badge(member, "bronze", reason="Bronze intro trigger")

                        # Try to DM the user privately about the badge
                        try:
                            await member.send(
                                "You have unlocked the **Bronze** badge in THC "
                                "for introducing yourself in the main chat. 🎉"
                            )
                        except discord.Forbidden:
                            # If their DMs are closed, fall back to a short public confirmation
                            await message.channel.send(
                                f"{member.mention} you have unlocked the **Bronze** badge.",
                                allowed_mentions=discord.AllowedMentions(users=[member])
                            )

                        maybe_flush_activity()
                    except Exception as e:
                        print("Bronze assign error:", e)



        # Count wins in wins channel
        # Count wins in wins channel
        if WINS_CHANNEL_ID and channel_id == WINS_CHANNEL_ID:

            # Detection: must mention bot AND contain the word "win"
            if bot.user and bot.user in message.mentions:
                if re.search(r"\bwin\b", lowered):
                    stats["wins"] += 1

                    # Silver trigger: bump to Silver immediately
                    try:
                        await assign_badge(member, "silver", reason="Silver win trigger")

                        # Try to DM the user privately
                        try:
                            await member.send(
                                "You have unlocked the **Silver** badge in THC "
                                "for sharing your win in the server. 🎉"
                            )
                        except discord.Forbidden:
                            # If their DMs are closed, fall back to short public confirmation
                            await message.channel.send(
                                f"{member.mention} you have unlocked the **Silver** badge.",
                                allowed_mentions=discord.AllowedMentions(users=[member])
                            )

                        maybe_flush_activity()

                    except Exception as e:
                        print("Silver assign error:", e)

                else:
                    # still count as a win activity even if 'win' wasn't matched perfectly
                    stats["wins"] += 1

            else:
                # message in wins channel without bot mention still counts as activity
                stats["wins"] += 1

        
        # After updating stats, maybe flush to disk every 10 minutes
        maybe_flush_activity()

        # After updating stats, check for rank upgrades (Gold / Diamond / Platinum)
        try:
            await _check_for_rank_upgrade(member)
        except Exception as e:
            print("Rank upgrade check error:", e)

    # 3) If bot is mentioned → show interactive menu
    # but do NOT show it for intro/win messages that are used for badges
    if bot.user and bot.user in message.mentions and not re.search(r"\b(intro|win)\b", lowered):
        view = HelpMenu()
        await message.channel.send("Hi! 👋 Please choose an option below:", view=view)
        return

    # # 4) Optional reply in servers if message starts with "A"
    # starts_with_A = message.content.strip().lower().startswith("a")
    # if starts_with_A:
    #     try:
    #         await message.reply(DM_REPLY_TEMPLATE, mention_author=True)
    #     except discord.Forbidden:
    #         pass

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

#newcode#
# ---- GMV management command ----

@bot.tree.command(name="setgmv", description="Set GMV for a user for badge ranking (staff only).")
@app_commands.describe(user="User to set GMV for", amount="Total GMV for this user")
async def setgmv(interaction: discord.Interaction, user: discord.Member, amount: int):
    # Only allow admins or manage_roles to use this
    if not isinstance(interaction.user, discord.Member) or not (
        interaction.user.guild_permissions.manage_roles or
        interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    stats = _get_stats(user)
    stats["gmv"] = max(0, int(amount))
    maybe_flush_activity()

    # Reevaluate their rank based on new GMV
    await _check_for_rank_upgrade(user)

    await interaction.response.send_message(
        f"Set GMV for {user.mention} to **{stats['gmv']}**. Badge has been rechecked.",
        allowed_mentions=discord.AllowedMentions(users=[user]),
        ephemeral=True
    )



def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing in .env")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
