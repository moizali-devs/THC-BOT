from pathlib import Path
import json

PATH = Path("data/bindings.json")


def _read():
    if PATH.exists():
        try:
            return json.loads(PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"bindings": []}


def _write(data):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_bindings():
    return _read().get("bindings", [])


def save_bindings(bindings):
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
    for b in load_bindings():
        if b["message_id"] == ms:
            return b
    return None


def list_bindings_for_guild(guild_id: int | str):
    gid = str(guild_id)
    return [b for b in load_bindings() if (b.get("guild_id") == gid or b.get("guild_id") is None)]
