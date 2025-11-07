import os
import time
import requests

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]  # set in Render → Environment
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---- Telegram helpers ----
def tg_get_updates(offset=None, timeout=50):
    try:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        r = requests.get(f"{TG_API}/getUpdates", params=params, timeout=timeout+5)
        r.raise_for_status()
        return r.json()
    except Exception:
        # On any network error, just return empty results to continue polling
        return {"ok": True, "result": []}

def tg_send(chat_id, text):
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass  # ignore send failures and keep looping

# ---- Random word source ----
def fetch_random_word():
    """
    Uses a free public endpoint. If it fails, fall back to a small local list.
    Docs: https://random-word-api.vercel.app/
    """
    try:
        r = requests.get("https://random-word-api.vercel.app/api?words=1", timeout=8)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return str(data[0])
    except Exception:
        pass
    # Fallback list (never blocks your bot)
    fallback = [
        "serendipity", "quasar", "luminous", "verdant", "mellifluous",
        "ephemeral", "zenith", "halcyon", "equinox", "solstice"
    ]
    import random
    return random.choice(fallback)

def handle_update(upd):
    message = upd.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return

    text = (message.get("text") or "").strip()

    # commands
    if text.startswith("/start"):
        tg_send(chat_id, "Hi! Send /word to get a random word.")
        return

    if text.startswith("/word"):
        w = fetch_random_word()
        tg_send(chat_id, w)
        return

    # optional: light help
    if text.startswith("/help"):
        tg_send(chat_id, "Commands:\n/word — get a random word")
        return

def main():
    update_offset = None
    while True:
        data = tg_get_updates(update_offset, timeout=50)  # long-polling
        for upd in data.get("result", []):
            update_offset = upd["update_id"] + 1  # advance cursor first
            try:
                handle_update(upd)
            except Exception:
                # never crash the loop on a bad update
                pass
        # short pause between polls (Telegram long-poll already waits up to 50s)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
