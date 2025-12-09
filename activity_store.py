from pathlib import Path
import json

PATH = Path("data/activity.json")


def _read():
    if PATH.exists():
        try:
            return json.loads(PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    # default structure: map of str(user_id) -> stats dict
    return {}


def _write(data: dict):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
