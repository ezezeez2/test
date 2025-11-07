import os, requests
from flask import Flask, request, jsonify

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]         # set in Render dashboard
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "ok", 200

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")

    if chat_id:
        text = (msg.get("text") or "").strip() or "Hi!"
        # Example: call ANY external API (replace with what you need)
        # Here we hit a public test API:
        r = requests.get("https://api.github.com/rate_limit", timeout=10)
        summary = r.json().get("rate", {})
        reply = f"You said: {text}\nGitHub remaining: {summary.get('remaining')}"
        requests.post(f"{TELEGRAM_API}/sendMessage",
                      json={"chat_id": chat_id, "text": reply}, timeout=10)
    return jsonify(ok=True)
