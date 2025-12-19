from telegram.ext import ApplicationBuilder, MessageHandler, filters
from config import BOT_TOKEN
from services.responder import generate_response

async def handle_message(update, context):
    reply = generate_response(update.message.text)
    await update.message.reply_text(reply)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
