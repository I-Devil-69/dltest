import os
import asyncio
import aiohttp
import io
import logging
from urllib.parse import urlparse
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI
import uvicorn
from werkzeug.utils import secure_filename

# === CONFIG ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")
PORT = int(os.getenv("PORT", 10000))

# === TELEGRAM BOT ===
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a direct download link. I’ll fetch and send the file.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"Processing URL: {url}")

    # Validate URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        await update.message.reply_text("Please send a valid direct download link.")
        return

    filename = secure_filename(Path(parsed.path).name)
    if not filename:
        await update.message.reply_text("Invalid filename in URL.")
        return

    await update.message.reply_text("Downloading file...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://utkarshapp.com"
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    await update.message.reply_text(f"Download failed: HTTP {resp.status}")
                    return
                content_length = int(resp.headers.get("Content-Length", 0))
                if content_length > 50_000_000:  # 50 MB limit
                    await update.message.reply_text("File too large for Telegram (max 50 MB).")
                    return
                data = io.BytesIO(await resp.read())
                data.name = filename
                await update.message.reply_document(document=data, filename=filename)

    except aiohttp.ClientError as e:
        logger.error(f"Network error for {url}: {e}")
        await update.message.reply_text(f"Network error: {e}")
    except telegram.error.TelegramError as e:
        logger.error(f"Telegram error for {url}: {e}")
        await update.message.reply_text(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error for {url}: {e}")
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
    config = uvicorn.Config(web_app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
