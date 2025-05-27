import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI
import uvicorn
from urllib.parse import urlparse
from pathlib import Path

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-telegram-bot-token")  # Add BOT_TOKEN in Render Environment Variables

# === TELEGRAM BOT ===
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a direct download link. I’ll fetch and send the file.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Validate link
    if not url.startswith("http"):
        await update.message.reply_text("Please send a valid direct download link.")
        return

    await update.message.reply_text("Downloading file...")

    try:
        filename = Path(urlparse(url).path).name
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://utkarshapp.com"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    await update.message.reply_text(f"Download failed: HTTP {resp.status}")
                    return
                data = await resp.read()
                with open(filename, "wb") as f:
                    f.write(data)

        await update.message.reply_document(document=open(filename, "rb"), filename=filename)
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# === HANDLERS ===
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === FASTAPI SERVER ===
web_app = FastAPI()

@web_app.get("/")
def home():
    return {"status": "Bot is running on Render!"}

# === ENTRY POINT ===
async def main():
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()
    await app_bot.updater.idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    uvicorn.run(web_app, host="0.0.0.0", port=10000)
