import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Load .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HUB_JSON_PATH = os.getenv("HUB_JSON_PATH")  # can be path or raw JSON

# Safety check
if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN is missing! Set it in your .env file.")

# Load hubs JSON
try:
    if os.path.exists(HUB_JSON_PATH):
        # If it exists as a file locally
        with open(HUB_JSON_PATH, "r") as f:
            hubs_data = json.load(f)
    else:
        # If it's raw JSON (from .env)
        hubs_data = json.loads(HUB_JSON_PATH)
except Exception as e:
    raise ValueError(f"Failed to load HUB_JSON_PATH: {e}")

# ----------------- Bot commands -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Lapu_All_Server Bot started successfully!\nUse /hubs to see hub data.\nOr type any alias (like h5pc2) to get its IP."
    )

async def hubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = json.dumps(hubs_data, indent=2)
    if len(text) > 4000:
        await update.message.reply_text("Hub data is too large to display!")
    else:
        await update.message.reply_text(f"<pre>{text}</pre>", parse_mode="HTML")

# ----------------- Alias lookup -----------------

async def alias_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip().lower()  # user message

    def search_hubs(data):
        if isinstance(data, dict):
            # Check current dict
            if "alias" in data and data["alias"].lower() == user_msg:
                return data
            if "connector_alias" in data and data["connector_alias"].lower() == user_msg:
                return {"alias": data["connector_alias"], "ip": data.get("connector_ip")}
            if "engine_ip" in data and "alias" in data and data["alias"].lower() == user_msg:
                return {"alias": data["alias"], "ip": data["engine_ip"]}
            # Recurse into values
            for v in data.values():
                result = search_hubs(v)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = search_hubs(item)
                if result:
                    return result
        return None

    found = search_hubs(hubs_data)

    if found:
        ip = found.get("ip") or found.get("engine_ip") or found.get("connector_ip")
        await update.message.reply_text(f"✅ Alias `{user_msg}` found:\nIP: {ip}")
    else:
        await update.message.reply_text(f"❌ Alias `{user_msg}` not found.")

# ----------------- Main -----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hubs", hubs))

    # Any text message is checked for alias
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, alias_lookup))

    print("🤖 Lapu_All_Server Bot started successfully...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
