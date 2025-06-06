import os
import asyncio
import aiohttp
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import secure_filename
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI
import uvicorn
import logging
import io
from pathlib import Path

# === CONFIG ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")
PORT = int(os.getenv("PORT", 10000))  # Use Render's PORT or default to 10000

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

    await update.message.reply_text("Downloading file via proxy...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://utkarshapp.com",
            "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://utkarshapp.com",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site"
        }
        # List of provided proxies
        proxies = [
            "http://219.65.73.81:80",
            "http://103.249.121.11:80",
            "http://103.117.15.10:8080"
        ]
        for proxy in proxies:
            try:
                logger.info(f"Trying proxy: {proxy}")
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(url, headers=headers, proxy=proxy, allow_redirects=True) as resp:
                        logger.info(f"Response URL: {resp.url}")
                        if resp.status == 200:
                            content_length = int(resp.headers.get("Content-Length", 0))
                            if content_length > 50_000_000:
                                await update.message.reply_text("File too large for Telegram (max 50 MB).")
                                return
                            data = io.BytesIO(await resp.read())
                            data.name = filename
                            await update.message.reply_document(document=data, filename=filename)
                            return
                        else:
                            error_text = await resp.text()
                            logger.error(f"Proxy {proxy} failed: HTTP {resp.status}, Response: {error_text}")
            except aiohttp.ClientError as e:
                logger.error(f"Proxy {proxy} error: {e}")
                continue
        await update.message.reply_text("Download failed: All proxies returned HTTP 403 or errors. The server restricts access based on location.")

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
    try:
        # Ensure no webhook is active
        await app_bot.bot.delete_webhook(drop_pending_updates=True)
        # Clear any pending updates to avoid conflicts
        await app_bot.bot.get_updates(offset=-1)
        # Start the bot
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling(drop_pending_updates=True)
        # Start FastAPI server
        config = uvicorn.Config(web_app, host="0.0.0.0", port=PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except telegram.error.Conflict as e:
        logger.error(f"Conflict error during startup: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
