# PRD: Welcome Message Embed Redesign

## Problem Statement

When a new member joins the THC (The Hustlers Club) Discord server, they receive a plain-text welcome message. Plain text is visually unimpressive, hard to scan, and does not reflect the hype and energy of the THC brand. New members may miss key CTAs or disengage before taking any action.

## Solution

Replace the plain-text welcome message with a rich Discord embed. The embed will be visually striking, use brand colors, include the new member's avatar, and surface exactly two high-value CTAs in a clean, scannable format.

## User Stories

1. As a new server member, I want to see a visually appealing welcome message, so that I feel excited about joining the community.
2. As a new server member, I want the welcome message to address me by name, so that it feels personal rather than generic.
3. As a new server member, I want to see my own avatar in the welcome message, so that it feels directed at me specifically.
4. As a new server member, I want to immediately know where to find high-commission products, so that I can start earning quickly.
5. As a new server member, I want a direct link to the onboarding call, so that I can attend and get oriented in the community.
6. As a new server member, I want to know how many members are in the server, so that I feel I am joining a large, active community.
7. As a server admin, I want the embed to use THC brand colors, so that the welcome experience is consistent with the brand identity.
8. As a server admin, I want the onboarding call link to always be valid, so that new members are never sent to a dead link.
9. As a server admin, I want the member count displayed in the footer, so that growing community size is visible to every new joiner.
10. As a server admin, I want the embed to mention the server name, so that new members immediately associate the message with THC.
11. As a server admin, I want the welcome message to still ping the new member on send, so that they receive a notification and see the message.
12. As a server admin, I want the ping to be replaced with a safe non-pinging mention after a short delay, so that the notification fires once but the embed is not permanently pinging.

## Implementation Decisions

### Modules to modify

- **Welcome cog** — The `_send_welcome` method needs to be updated to construct and send a `discord.Embed` instead of raw text. The embed is built inline within this method; no separate builder module is needed given its single use.
- **Config module** — The `WELCOME_MESSAGE` string constant becomes obsolete and should be removed. No new config values are needed since the onboarding call will link to the guild's events page (a dynamic URL derived from the guild ID at runtime, not a hardcoded config value).

### Embed specification

- **Color:** Gold (`#FFD700`)
- **Title:** `Welcome to The Hustlers Club, {name}!` with a fire emoji prefix
- **Description:** A single hype line — `Your journey to financial freedom starts right here. Let's get it.` with an energy emoji
- **Thumbnail:** The joining member's avatar URL
- **Fields (inline or stacked):**
  1. Products & Commissions — label + link to `https://thc-product-showcase.vercel.app/`
  2. Onboarding Call — label + link to the guild's Discord events page (`https://discord.com/events/{guild_id}`)
- **Footer:** Server name + current member count, e.g. `The Hustlers Club · 1,234 members`
- **Timestamp:** Omitted (keeps the embed clean)

### Ping behaviour (unchanged)

The existing two-step pattern is preserved: send with a live `member.mention` to trigger a notification, then edit after 2 seconds to a safe backtick mention. The embed is attached to both sends; only the `content` field (the mention) changes between the initial send and the edit.

### Member count

Derived at runtime from `member.guild.member_count`. No caching or store changes needed.

### Guild events page URL

Constructed at runtime as `https://discord.com/events/{member.guild.id}`. This is always valid and never goes stale, unlike a specific event link.

## Testing Decisions

**What makes a good test here:** Test the observable output — the embed object's attributes (color, title, description, field names/values, footer text) — not the internal construction details. Do not assert on the exact Discord API call signature.

**Modules to test:**

- `_send_welcome` — unit test using a mocked `discord.Member`, `discord.Guild`, and `discord.TextChannel`. Assert that:
  - `channel.send` is called with an embed whose color equals `0xFFD700`
  - The embed title contains the member's display name
  - The embed thumbnail URL matches the member's avatar URL
  - The embed contains exactly 2 fields with the correct names and URLs
  - The embed footer text contains the guild name and member count
  - `msg.edit` is called after the sleep with `allowed_mentions=discord.AllowedMentions.none()`

**Prior art:** No existing test suite found in the repo. This would be the first test file. Use `pytest` with `unittest.mock.AsyncMock` for async Discord methods.

## Out of Scope

- Changing the delayed form DM (`_send_delayed_form`) — this is unaffected.
- Adding images or banners to the embed (no static asset hosting configured).
- Making the embed fields configurable via a dashboard or slash command.
- Localisation or multilingual support.
- Any changes to the badge, payment, or reaction cogs.

## Further Notes

- `WELCOME_MESSAGE` in `config.py` can be fully removed once the embed is live; it is no longer referenced.
- The gold color `#FFD700` (`0xFFD700` as an integer) should be defined as a named constant (e.g. `EMBED_COLOR_GOLD`) rather than a magic number inline.
- The guild events page (`discord.com/events/{guild_id}`) shows all upcoming events; members can pick the relevant onboarding call themselves, which avoids the stale-link problem of hardcoding a specific event URL.
