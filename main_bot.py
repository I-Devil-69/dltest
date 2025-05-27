from urllib.parse import urlparse, parse_qs
from werkzeug.utils import secure_filename
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes, filters
import logging
import io
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    # Check for pre-signed URL
    query_params = parse_qs(parsed.query)
    if "X-Amz-Expires" in query_params:
        await update.message.reply_text("This appears to be a pre-signed URL. It may have expired. Please provide a fresh link.")
        return

    await update.message.reply_text("Downloading file...")

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
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                logger.info(f"Response URL: {resp.url}")
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Download failed: HTTP {resp.status}, Response: {error_text}, Final URL: {resp.url}")
                    await update.message.reply_text(f"Download failed: HTTP {resp.status}. The server may require specific headers or restrict bot access.")
                    return
                content_length = int(resp.headers.get("Content-Length", 0))
                if content_length > 50_000_000:
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
