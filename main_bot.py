import os
import aiohttp
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Custom headers to bypass 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/112 Firefox/112"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /get <url> to download a file and receive it.")

async def get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a valid URL.")
        return

    url = context.args[0]
    filename = url.split("/")[-1]

    try:
        # Download with custom headers
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await update.message.reply_text(f"Failed to download: {resp.status}")
                    return

                data = await resp.read()

                # Save file locally
                with open(filename, "wb") as f:
                    f.write(data)

        # Send the file to user
        await update.message.reply_document(document=open(filename, "rb"))
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get))
    print("Bot running...")
    app.run_polling()
  
