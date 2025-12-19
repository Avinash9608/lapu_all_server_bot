# bot.py
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from services.responder import generate_response

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in .env file")

# -------- Start Command --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm your Infra Bot.\n"
        "Send me an IP, 'alias <name>' or 'hub <name>' to get details.\n"
        "Example:\n"
        "10.241.177.22\n"
        "alias pweb1\n"
        "hub hub-1"
    )

# -------- Message Handler --------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    response = generate_response(text)
    await update.message.reply_text(response)

# -------- Main Function --------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Infra Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
