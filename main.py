import os, asyncio, textwrap, random
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

RANDOM_WORD_URL = "https://random-word-api.vercel.app/api?words=1"
DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

def format_entry(word: str, entry: dict) -> str:
    phon = ""
    try:
        # pick first non-empty phonetic text if present
        for ph in entry.get("phonetics", []):
            if ph.get("text"):
                phon = f" {ph['text']}"
                break
    except Exception:
        pass

    lines = [f"🟦 *{word}*{phon}"]
    defs_added = 0
    for meaning in entry.get("meanings", []):
        pos = meaning.get("partOfSpeech", "")
        for d in meaning.get("definitions", []):
            defi = d.get("definition", "").strip()
            if not defi:
                continue
            defs_added += 1
            prefix = f"{defs_added}. _{pos}_ – " if pos else f"{defs_added}. "
            lines.append(prefix + defi)
            ex = d.get("example")
            if ex:
                lines.append(f"   • _{ex}_")
            if defs_added >= 3:  # keep replies concise
                break
        if defs_added >= 3:
            break

    if defs_added == 0:
        lines.append("No definitions found.")
    return "\n".join(lines)

async def get_random_word(client: httpx.AsyncClient) -> str:
    r = await client.get(RANDOM_WORD_URL, timeout=10)
    r.raise_for_status()
    data = r.json()
    # API returns ["word"]; fall back to a safe default on odd responses
    if isinstance(data, list) and data:
        return str(data[0]).strip()
    return "example"

async def get_dictionary_entries(client: httpx.AsyncClient, word: str):
    r = await client.get(DICT_URL.format(word=word), timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send /word to get a random English word with a quick meaning."
    )

async def word_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    async with httpx.AsyncClient() as client:
        try:
            word = await get_random_word(client)
            entries = await get_dictionary_entries(client, word)
            # If the random word has no dictionary entry, try a few more times.
            retries = 0
            while (not entries) and retries < 3:
                word = await get_random_word(client)
                entries = await get_dictionary_entries(client, word)
                retries += 1

            if not entries:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="Couldn't find a definition right now—try /word again."
                )
                return

            entry = entries[0] if isinstance(entries, list) else entries
            text = format_entry(word, entry)
            await context.bot.send_message(chat_id=chat.id, text=text, parse_mode="Markdown")
        except httpx.HTTPError:
            await context.bot.send_message(chat_id=chat.id, text="Network error. Please try again.")
        except Exception:
            await context.bot.send_message(chat_id=chat.id, text="Something went wrong. Try /word again.")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_TOKEN env var")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("word", word_cmd))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
