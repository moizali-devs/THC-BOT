from pathlib import Path
import json
import tempfile
import os

PATH = Path("data/activity.json")
WEEKLY_PATH = Path("data/weekly_snapshot.json")


def _safe_write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=str(path.parent), delete=False, suffix=".tmp", encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2)
        tmp = f.name
    os.replace(tmp, str(path))


def _read():
    if PATH.exists():
        try:
            return json.loads(PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    # default structure: map of str(user_id) -> stats dict
    return {}


def _write(data: dict):
    _safe_write(PATH, data)


def load_activity() -> dict:
    """
    Returns a dict of:
    {
      "1234567890123": {"chat_msgs": int, "wins": int, "gmv": int}
    }
    """
    return _read()


def save_activity(activity: dict):
    _write(activity)


def load_weekly_snapshot() -> dict:
    """
    Returns:
    {
      "wins_snapshot": {"user_id": int, ...},
      "members_joined": [{"id": int, "name": str, "joined_at": str}, ...],
      "snapshot_at": str | None
    }
    """
    if WEEKLY_PATH.exists():
        try:
            return json.loads(WEEKLY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"wins_snapshot": {}, "members_joined": [], "snapshot_at": None}


def save_weekly_snapshot(data: dict):
    _safe_write(WEEKLY_PATH, data)
