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


# on_raw_reaction_add gives us payload even if message isn't cached
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# optional but recommended for fast slash command sync
GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_reactions = True
intents.dm_messages = True  # not strictly required to send DMs, but fine to keep


class SonOfAndOn(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # load cog
        await self.load_extension("cogs.admin")
        # fast sync to a single guild if provided
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


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
# async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
#     try:
#         # ignores bots own reaction
#         if payload.user_id == bot.user.id:
#             return
#         # Is this message bound?
#         binding = find_binding(payload.message_id)
#         if not binding:
#             return
#         # Optional: restrict to a specific emoji
#         target_emoji = binding.get("✅") or "ANY"
#         if target_emoji != "ANY":
#             # payload.emoji.name works for unicode; for custom emojis use payload.emoji.id or str(payload.emoji)
#             if payload.emoji.name != target_emoji and str(payload.emoji) != target_emoji:
#                 return
#         # Fetch user
#         user = bot.get_user(payload.user_id) or await bot.fetch_user(payload.user_id)
#         # DM them the form
#         try:
#             await user.send(f"Here is your **{binding['brand']}** onboarding form:\n{binding['form']}")
#         except Exception:
#             # Fallback: notify in channel (public, because reaction events aren't interactions)
#             try:
#                 channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
#                 await channel.send(f"<@{payload.user_id}>, I couldn't DM you. Please enable **Allow DMs from server members** or ask an admin for the **{binding['brand']}** form.")
#             except Exception:
#                 pass
#         # Optional: remove the user's reaction to keep message tidy (requires Manage Messages)
#         try:
#             if payload.guild_id:
#                 guild = bot.get_guild(payload.guild_id) or await bot.fetch_guild(payload.guild_id)
#                 member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
#             else:
#                 member = None
#             channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
#             message = await channel.fetch_message(payload.message_id)
#             if member:
#                 await message.remove_reaction(payload.emoji, member)
#         except Exception:
#             pass
#     except Exception as e:
#         print("Reaction handler error:", e)
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
            await user.send(f"Here is your **{binding['brand']}** onboarding nigga form:\n{binding['form']}")
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

        # Optional: remove user's reaction to keep message tidy (needs Manage Messages)
        try:
            channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if payload.guild_id:
                guild = bot.get_guild(payload.guild_id) or await bot.fetch_guild(payload.guild_id)
                member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
            else:
                member = None
            if member:
                await message.remove_reaction(payload.emoji, member)
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
