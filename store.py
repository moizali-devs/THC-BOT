from pathlib import Path
import json
import tempfile
import os

PATH = Path("data/bindings.json")
_BINDINGS_CACHE: list[dict] | None = None
_BINDINGS_BY_MESSAGE: dict[str, dict] = {}


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
    return {"bindings": []}


def _write(data):
    _safe_write(PATH, data)


def _set_bindings_cache(bindings):
    global _BINDINGS_CACHE, _BINDINGS_BY_MESSAGE
    _BINDINGS_CACHE = list(bindings)
    _BINDINGS_BY_MESSAGE = {b["message_id"]: b for b in _BINDINGS_CACHE}


def _get_bindings_cache():
    global _BINDINGS_CACHE
    if _BINDINGS_CACHE is None:
        _set_bindings_cache(_read().get("bindings", []))
    return _BINDINGS_CACHE


def load_bindings():
    return list(_get_bindings_cache())


def save_bindings(bindings):
    _set_bindings_cache(bindings)
    _write({"bindings": bindings})

# old working code 
# def upsert_binding(message_id: int, brand: str, form: str, guild_id: int | None, channel_id: int | None, emoji: str = "ANY"):
#     bindings = load_bindings()
#     for i, b in enumerate(bindings):
#         if b["message_id"] == str(message_id):
#             bindings[i] = {
#                 "message_id": str(message_id),
#                 "brand": brand,
#                 "form": form,
#                 "guild_id": str(guild_id) if guild_id else None,
#                 "channel_id": str(channel_id) if channel_id else None,
#                 "emoji": emoji
#             }
#             save_bindings(bindings)
#             return
#     bindings.append({
#         "message_id": str(message_id),
#         "brand": brand,
#         "form": form,
#         "guild_id": str(guild_id) if guild_id else None,
#         "channel_id": str(channel_id) if channel_id else None,
#         "emoji": emoji
#     })
#     save_bindings(bindings)

# NEW CODE: 
def upsert_binding(
    message_id: int,
    brand: str,
    form: str,
    guild_id: int | None,
    channel_id: int | None,
    emoji: str = "ANY",
    kind: str = "form",
    role_id: int | None = None,
):
    bindings = load_bindings()
    for i, b in enumerate(bindings):
        if b["message_id"] == str(message_id):
            bindings[i] = {
                "message_id": str(message_id),
                "brand": brand,
                "form": form,
                "guild_id": str(guild_id) if guild_id else None,
                "channel_id": str(channel_id) if channel_id else None,
                "emoji": emoji,
                "kind": kind,
                "role_id": str(role_id) if role_id else None,
            }
            save_bindings(bindings)
            return

    bindings.append({
        "message_id": str(message_id),
        "brand": brand,
        "form": form,
        "guild_id": str(guild_id) if guild_id else None,
        "channel_id": str(channel_id) if channel_id else None,
        "emoji": emoji,
        "kind": kind,
        "role_id": str(role_id) if role_id else None,
    })
    save_bindings(bindings)



def remove_binding(message_id: int | str):
    ms = str(message_id)
    bindings = [b for b in load_bindings() if b["message_id"] != ms]
    save_bindings(bindings)


def find_binding(message_id: int | str):
    ms = str(message_id)
    _get_bindings_cache()
    return _BINDINGS_BY_MESSAGE.get(ms)


def list_bindings_for_guild(guild_id: int | str):
    gid = str(guild_id)
    return [b for b in load_bindings() if (b.get("guild_id") == gid or b.get("guild_id") is None)]
