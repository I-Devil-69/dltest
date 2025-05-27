import os
import aiohttp
import asyncio
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from fastapi import FastAPI
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Dummy FastAPI web app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Bot is running."}

# Custom headers for 403 bypass
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/112 Firefox/112"
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /get <url> to download and receive the file.")

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a valid URL.")
        return

    url = context.args[0]
    filename = url.split("/")[-1]

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await update.message.reply_text(f"Failed to download: {resp.status}")
                    return
                data = await resp.read()

                with open(filename, "wb") as f:
                    f.write(data)

        await update.message.reply_document(document=open(filename, "rb"))
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start_command))
    app_bot.add_handler(CommandHandler("get", get_command))
    print("Bot started...")
    app_bot.run_polling()

# Start bot in background thread
threading.Thread(target=run_bot).start()

# Start FastAPI (Render will call this)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
