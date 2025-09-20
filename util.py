import re
from urllib.parse import urlparse

LINK_RX = re.compile(r"discord\.com\/channels\/(\d+)\/(\d+)\/(\d+)")


def parse_message_ref(s: str):
    """Accept a raw message ID or a message link. Returns dict with possible keys: guild_id, channel_id, message_id."""
    s = s.strip().strip("<>")
    if s.isdigit():
        return {"message_id": int(s)}
    m = LINK_RX.search(s)
    if m:
        return {"guild_id": int(m.group(1)), "channel_id": int(m.group(2)), "message_id": int(m.group(3))}
    raise ValueError("Provide a valid message ID or a full message link.")


def is_valid_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False
