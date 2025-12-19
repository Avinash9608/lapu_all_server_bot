import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
        # If it's raw JSON (Render)
        hubs_data = json.loads(HUB_JSON_PATH)
except Exception as e:
    raise ValueError(f"Failed to load HUB_JSON_PATH: {e}")

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Lapu_All_Server Bot started successfully!\nUse /hubs to see hub data."
    )

async def hubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = json.dumps(hubs_data, indent=2)
    if len(text) > 4000:
        await update.message.reply_text("Hub data is too large to display!")
    else:
        await update.message.reply_text(f"<pre>{text}</pre>", parse_mode="HTML")

# Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hubs", hubs))

    print("🤖 Lapu_All_Server Bot started successfully...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
