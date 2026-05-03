# =============================================================================
# THC Bot — Central Configuration
# Edit values here to configure the bot for your server.
# All IDs are Discord snowflake integers (right-click → Copy ID).
# =============================================================================

# -----------------------------------------------------------------------------
# TRUSTED USERS
# These user IDs can use all staff/admin bot commands regardless of their
# Discord role permissions.
# -----------------------------------------------------------------------------
TRUSTED_USER_IDS = [
    1427318529622933736,  # Main admin / helper
]

# -----------------------------------------------------------------------------
# STAFF ROLES
# Members with any of these roles can use all staff/admin bot commands.
# Add role IDs here (right-click role → Copy ID with Developer Mode on).
# -----------------------------------------------------------------------------
STAFF_ROLE_IDS = [
    0,  # Replace with your staff role ID
]

# -----------------------------------------------------------------------------
# REACTION COOLDOWN
# How long (in seconds) before the same user can get another DM from the same
# bound message reaction. Default is 24 hours.
# -----------------------------------------------------------------------------
COOLDOWN_SECONDS = 24 * 60 * 60  # 24 hours

# -----------------------------------------------------------------------------
# ACTIVITY AUTO-SAVE INTERVAL
# How often (in seconds) the bot saves activity data to disk.
# Data is always saved on bot shutdown regardless of this setting.
# -----------------------------------------------------------------------------
SAVE_ACTIVITY_INTERVAL = 10 * 60  # 10 minutes

# -----------------------------------------------------------------------------
# GROWI TICKET CONFIG
# GROWI_USER_ID       — Discord user ID of the person who handles Growi tickets.
#                       They will be added to every Growi/Referral ticket channel.
# TICKETS_CATEGORY_NAME — Name of the Discord category where ticket channels
#                         are created. Set to "" to place tickets at root level.
# -----------------------------------------------------------------------------
GROWI_USER_ID = 1427318529622933736
TICKETS_CATEGORY_NAME = "Growi Ticket"

# -----------------------------------------------------------------------------
# PAYMENT TICKET CONFIG
# PAYMENTS_REQUEST_CHANNEL_ID    — ID of the public channel that contains the
#                                  payment panel message. Users click the button
#                                  here to open a private payment ticket.
# PAYMENTS_TICKETS_CATEGORY_NAME — Name of the Discord category where payment
#                                  ticket channels will be created.
# PAYMENTS_STAFF_ROLE_IDS        — List of role IDs whose members can view and
#                                  close payment ticket channels. Also any member
#                                  with Manage Channels or Administrator can close.
# -----------------------------------------------------------------------------
PAYMENTS_REQUEST_CHANNEL_ID = 1454840634450903308
PAYMENTS_TICKETS_CATEGORY_NAME = "💫 PAYMENTS 💫"
PAYMENTS_STAFF_ROLE_IDS = [
    1350197846963654687,  # Payments Manager role
    1291054567491895387,  # Payments Staff role
    1282014675932020736,  # Admin role
]

# -----------------------------------------------------------------------------
# APPLY CHANNEL
# The channel where brand deal applications are posted. Shown to users who
# click "Apply to Brand" in the help menu.
# -----------------------------------------------------------------------------
APPLY_CHANNEL_ID = 1282723291618082836

# -----------------------------------------------------------------------------
# TIER ROLES
# Role IDs for each creator tier. Assigned via the /setgmv command or the
# "Tier / Roles" button in the help menu.
#   Tier 1 → 0–50k GMV
#   Tier 2 → 50k–100k GMV
#   Tier 3 → 100k–200k GMV
#   Tier 4 → 200k+ GMV
# -----------------------------------------------------------------------------
TIER_ROLE_IDS = {
    1: 1425403368817426543,  # Tier 1 role
    2: 1425403496387186770,  # Tier 2 role
    3: 1425403540775370833,  # Tier 3 role
    4: 1425403620139991061,  # Tier 4 role
}

# -----------------------------------------------------------------------------
# BADGE ROLES
# Role IDs for each activity/achievement badge. Assigned automatically when
# members hit the thresholds defined in the RANK THRESHOLDS section below.
# -----------------------------------------------------------------------------
BADGE_ROLE_IDS = {
    "bronze":   1447644206897303765,  # Bronze  — awarded for intro in main chat
    "silver":   1447644686134153286,  # Silver  — awarded for posting a win
    "gold":     1447644808943370484,  # Gold    — 50+ messages + 6+ wins
    "diamond":  1447645001789083839,  # Diamond — $100k GMV + 60 msgs + 5 wins
    "platinum": 1447645453259636847,  # Platinum— $250k GMV + 150 msgs + 10 wins
}

# -----------------------------------------------------------------------------
# TRACKED CHANNELS
# MAIN_CHAT_ID    — Channel where chat messages are counted toward badge progress
#                   and where users say their intro to earn Bronze.
# WINS_CHANNEL_ID — Channel where win posts are counted. Mentioning the bot with
#                   the word "win" triggers the Silver badge.
# -----------------------------------------------------------------------------
MAIN_CHAT_ID = 1291049360473456651
WINS_CHANNEL_ID = 1292975300740644936

# -----------------------------------------------------------------------------
# RANK THRESHOLDS
# Minimum stats required to be upgraded to each badge tier automatically.
# Bronze and Silver are event-triggered (intro / win post), not threshold-based.
# -----------------------------------------------------------------------------
# Gold
GOLD_CHAT_MIN = 50   # minimum chat messages in main chat
GOLD_WINS_MIN = 6    # minimum wins posted

# Diamond
DIAMOND_GMV_MIN = 100_000  # minimum GMV in dollars
DIAMOND_CHAT_MIN = 60      # minimum chat messages
DIAMOND_WINS_MIN = 5       # minimum wins posted

# Platinum
PLATINUM_GMV_MIN = 250_000  # minimum GMV in dollars
PLATINUM_CHAT_MIN = 150     # minimum chat messages
PLATINUM_WINS_MIN = 10      # minimum wins posted

# -----------------------------------------------------------------------------
# WEEKLY SUMMARY
# WEEKLY_SUMMARY_CHANNEL_ID — Channel where the weekly summary embed is posted.
# WEEKLY_SUMMARY_DAY        — Day of week to post (0=Monday … 6=Sunday).
# WEEKLY_SUMMARY_HOUR       — Hour (UTC, 24h) to post. Default: 9am UTC Monday.
# -----------------------------------------------------------------------------
WEEKLY_SUMMARY_CHANNEL_ID = 0  # Replace with your summary channel ID
WEEKLY_SUMMARY_DAY = 0   # Monday
WEEKLY_SUMMARY_HOUR = 9  # 9:00 UTC

# -----------------------------------------------------------------------------
# WELCOME CONFIG
# WELCOME_CHANNEL_ID — Channel where new member welcome messages are posted.
# EMBED_COLOR_GOLD   — Accent color for the welcome embed (THC brand gold).
# PRODUCTS_URL       — Link shown in the welcome embed's products field.
# -----------------------------------------------------------------------------
WELCOME_CHANNEL_ID = 1282010168015716536
EMBED_COLOR_GOLD = 0xFFD700
PRODUCTS_URL = "https://thc-product-showcase.vercel.app/"
ONBOARDING_CALL_1_URL = "https://discord.com/events/1282010167507943444/1501282330214400000"
ONBOARDING_CALL_2_URL = "https://discord.com/events/1282010167507943444/1502067503923200000"

# -----------------------------------------------------------------------------
# NEW MEMBER FORM
# FORM_DELAY_SECONDS — How long (seconds) to wait after a member joins before
#                      sending them the onboarding form DM.
# FORM_LINK          — URL of the Google Form (or any form) to DM new members.
# HELPER_USER_ID     — Discord user ID who is mentioned in the form DM as the
#                      person to contact if the member has trouble filling it out.
# FORM_DM_TEMPLATE   — Template for the DM. Supports {name}, {form_link},
#                      {helper_mention} placeholders.
# -----------------------------------------------------------------------------
FORM_DELAY_SECONDS = 5 * 60  # 5 minutes
FORM_LINK = "https://forms.gle/YV4PnCjfcMLZk7j48"
HELPER_USER_ID = 1427318529622933736  # Person to contact if form issues arise

FORM_DM_TEMPLATE = (
    "Hey {name}, welcome to **The Hustlers Club** 🎉\n\n"
    "To be considered for current and future brand deals inside The Hustlers Club, "
    "Please fill out this short form:\n"
    "{form_link}\n\n"
    "If you face any issues while filling it out, please message {helper_mention}."
)
