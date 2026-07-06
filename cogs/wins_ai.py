import json
import logging
import os
import time

import discord
from discord.ext import commands
from openai import AsyncOpenAI

from config import BIG_WIN_THRESHOLD_USD, BIG_WINS_CHANNEL_ID, WINS_CHANNEL_ID

logger = logging.getLogger("thcbot")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

COOLDOWN_SECONDS = 60  # seconds between AI classification calls per user

_LAST_CALL_CACHE: dict[tuple[int], float] = {}

_SYSTEM_PROMPT = (
    "You are a classifier for a Discord community's #wins channel. Members post "
    "screenshots or photos showing earnings, payouts, sales, or other wins. Your job "
    "is to decide whether the image(s) and caption show a 'big win': a screenshot or "
    "photo clearly displaying a dollar amount greater than ${threshold} USD. If the "
    "image does not clearly show a dollar amount greater than the threshold, or the "
    "image is irrelevant/unclear, classify it as not a big win. "
    "Respond with strict JSON only, no markdown formatting, no code fences, in "
    "exactly this shape: {{\"is_big_win\": true or false, \"reasoning\": \"short "
    "explanation of what you saw and why\"}}"
).format(threshold=BIG_WIN_THRESHOLD_USD)


class WinsAICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def _get_image_attachments(self, message: discord.Message) -> list[discord.Attachment]:
        images = []
        for attachment in message.attachments:
            filename = (attachment.filename or "").lower()
            content_type = (attachment.content_type or "").lower()
            if filename.endswith(IMAGE_EXTENSIONS) or content_type in (
                "image/png",
                "image/jpeg",
                "image/webp",
            ):
                images.append(attachment)
        return images

    def _on_cooldown(self, user_id: int) -> bool:
        key = (user_id,)
        now = time.time()
        if now - _LAST_CALL_CACHE.get(key, 0) < COOLDOWN_SECONDS:
            return True
        _LAST_CALL_CACHE[key] = now
        return False

    async def _classify_images(
        self, image_urls: list[str], caption: str
    ) -> dict | None:
        if not self._client:
            logger.error("OPENAI_API_KEY not configured; skipping win classification.")
            return None

        content = [
            {
                "type": "text",
                "text": f"Caption text: {caption!r}" if caption else "Caption text: (none)",
            }
        ]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=300,
                timeout=30,
            )
        except Exception:
            logger.exception("OpenAI API call failed during win classification.")
            return None

        try:
            raw_text = response.choices[0].message.content.strip()
        except Exception:
            logger.exception("Malformed OpenAI response during win classification.")
            return None

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        try:
            parsed = json.loads(raw_text)
            is_big_win = bool(parsed["is_big_win"])
            reasoning = str(parsed.get("reasoning", ""))
        except Exception:
            logger.error(
                "Failed to parse OpenAI classification JSON. Raw response: %r", raw_text
            )
            return None

        return {"is_big_win": is_big_win, "reasoning": reasoning}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        if not WINS_CHANNEL_ID or message.channel.id != WINS_CHANNEL_ID:
            return

        images = self._get_image_attachments(message)
        if not images:
            return

        if self._on_cooldown(message.author.id):
            logger.debug(
                "Skipping win classification for user %d due to cooldown.",
                message.author.id,
            )
            return

        caption = message.content or ""
        image_urls = [a.url for a in images]

        result = await self._classify_images(image_urls, caption)
        if result is None:
            return

        is_big_win = result["is_big_win"]
        reasoning = result["reasoning"]

        logger.info(
            "Win classification for message %d by %s: verdict=%s reasoning=%s",
            message.id,
            message.author,
            "big" if is_big_win else "small",
            reasoning,
        )

        if not is_big_win:
            return

        try:
            await message.add_reaction("🔥")
        except Exception:
            logger.exception(
                "Failed to react to big win message %d in #wins.", message.id
            )

        if not BIG_WINS_CHANNEL_ID:
            return

        big_wins_channel = message.guild.get_channel(BIG_WINS_CHANNEL_ID) if message.guild else None
        if not isinstance(big_wins_channel, discord.TextChannel):
            logger.error(
                "BIG_WINS_CHANNEL_ID=%d not found or not a text channel.",
                BIG_WINS_CHANNEL_ID,
            )
            return

        embed = discord.Embed(
            title="🔥 Big Win!",
            description=caption if caption else None,
            color=discord.Color.gold(),
            url=message.jump_url,
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url,
        )
        embed.set_image(url=images[0].url)
        embed.add_field(name="Original message", value=f"[Jump to message]({message.jump_url})")

        try:
            await big_wins_channel.send(embed=embed)
            if len(images) > 1:
                for attachment in images[1:]:
                    extra_embed = discord.Embed(color=discord.Color.gold())
                    extra_embed.set_image(url=attachment.url)
                    await big_wins_channel.send(embed=extra_embed)
        except Exception:
            logger.exception(
                "Failed to post big win embed for message %d in big wins channel.",
                message.id,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(WinsAICog(bot))
