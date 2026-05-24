import os
import re
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the same directory as bot.py
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE_MB = 50


def detect_platform(url: str) -> tuple[str, str]:
    """Returns (platform_name, emoji)"""
    if "instagram.com" in url:
        return "Instagram", "📸"
    elif "tiktok.com" in url:
        return "TikTok", "🎵"
    elif "youtube.com" in url or "youtu.be" in url:
        return "YouTube", "🎬"
    return "Unknown", "🌐"


def extract_urls(text: str) -> list:
    pattern = r"https?://[^\s]+"
    return re.findall(pattern, text)


def sync_download(url: str, output_dir: Path, audio_only: bool = False) -> dict:
    """Synchronous yt-dlp download. Returns info dict with filename and title."""
    if audio_only:
        ydl_opts = {
            "outtmpl": str(output_dir / "%(title).60s.%(ext)s"),
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
        }
    else:
        ydl_opts = {
            "outtmpl": str(output_dir / "%(title).60s.%(ext)s"),
            "format": (
                "bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/"
                "best[ext=mp4][filesize<45M]/"
                "best[filesize<45M]/"
                "best"
            ),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }

    cookies_file = Path("cookies.txt")
    if cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        if audio_only:
            filename = str(Path(filename).with_suffix(".mp3"))
        elif not Path(filename).exists():
            filename = str(Path(filename).with_suffix(".mp4"))

        return {
            "filename": filename,
            "title": info.get("title", "Video"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "thumbnail": info.get("thumbnail", ""),
        }


def sync_get_info(url: str) -> dict:
    """Get video info without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    cookies_file = Path("cookies.txt")
    if cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Video"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "filesize": info.get("filesize_approx", 0),
        }


# ── Command Handlers ──────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"👋 Hey *{name}*! Welcome to the Video Downloader Bot.\n\n"
        "Just send me a video link and I'll download it for you.\n\n"
        "*Supported Platforms:*\n"
        "📸 Instagram — Reels, Posts, Stories\n"
        "🎵 TikTok — Videos\n"
        "🎬 YouTube — Videos, Shorts\n\n"
        "📎 Paste a link to get started!\n\n"
        "Use /help for more info.",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*📖 How to use:*\n"
        "1. Copy a video URL\n"
        "2. Paste it here\n"
        "3. Choose Video or Audio (MP3)\n"
        "4. Receive your file!\n\n"
        "*⚙️ Commands:*\n"
        "/start — Welcome message\n"
        "/help — This help message\n\n"
        "*⚠️ Limits:*\n"
        "• Max file size: 50MB\n"
        "• Private content requires cookies\n\n"
        "*🍪 Cookies (for private content):*\n"
        "If you need to download private or age-restricted content, "
        "place a `cookies.txt` file (Netscape format) in the bot directory.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "❌ No valid URL detected.\nPlease send a YouTube, Instagram, or TikTok link."
        )
        return

    url = urls[0]
    platform, emoji = detect_platform(url)

    # Store URL in context for callback use
    context.user_data["pending_url"] = url

    # Fetch info first
    status = await update.message.reply_text(f"{emoji} Fetching info from *{platform}*...", parse_mode="Markdown")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: sync_get_info(url))

        title = info["title"][:60]
        duration = info["duration"]
        uploader = info["uploader"]

        dur_str = ""
        if duration:
            mins, secs = divmod(int(duration), 60)
            dur_str = f"⏱ Duration: {mins}:{secs:02d}\n"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Video (MP4)", callback_data=f"dl_video"),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"dl_audio"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="dl_cancel")]
        ])

        await status.edit_text(
            f"{emoji} *{title}*\n"
            f"👤 {uploader}\n"
            f"{dur_str}\n"
            "Choose download format:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        err = str(e)
        logger.error(f"Info fetch error: {err}")
        if "private" in err.lower() or "login" in err.lower():
            msg = "🔒 This content is private or requires login.\nAdd a `cookies.txt` file to the bot directory."
        elif "unavailable" in err.lower() or "removed" in err.lower():
            msg = "❌ This video is unavailable or has been removed."
        else:
            msg = f"❌ Could not fetch video info.\n`{err[:200]}`"
        await status.edit_text(msg, parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    url = context.user_data.get("pending_url")

    if action == "dl_cancel" or not url:
        await query.edit_message_text("❌ Download cancelled.")
        return

    audio_only = action == "dl_audio"
    mode_label = "audio (MP3)" if audio_only else "video (MP4)"
    platform, emoji = detect_platform(url)

    await query.edit_message_text(
        f"{emoji} Downloading *{mode_label}* from *{platform}*...\n\nThis may take a moment ⏳",
        parse_mode="Markdown"
    )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: sync_download(url, DOWNLOAD_DIR, audio_only=audio_only)
        )

        filepath = Path(result["filename"])
        title = result["title"]

        if not filepath.exists():
            await query.edit_message_text("❌ Download failed. File not found after download.")
            return

        file_size_mb = filepath.stat().st_size / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            filepath.unlink(missing_ok=True)
            await query.edit_message_text(
                f"⚠️ File is *{file_size_mb:.1f}MB* — exceeds Telegram's 50MB limit.\n\n"
                "Try a shorter video or use audio-only download.",
                parse_mode="Markdown"
            )
            return

        await query.edit_message_text(f"📤 Uploading *{title[:50]}*...", parse_mode="Markdown")

        caption = f"{'🎵' if audio_only else '🎬'} *{title[:80]}*\n_via {platform} Downloader Bot_"

        with open(filepath, "rb") as f:
            if audio_only:
                await query.message.reply_audio(
                    audio=f,
                    caption=caption,
                    parse_mode="Markdown",
                    title=title[:64],
                )
            else:
                await query.message.reply_video(
                    video=f,
                    caption=caption,
                    parse_mode="Markdown",
                    supports_streaming=True,
                )

        await query.delete_message()
        filepath.unlink(missing_ok=True)
        context.user_data.pop("pending_url", None)

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        logger.error(f"Download error: {err}")
        if "private" in err.lower() or "login" in err.lower():
            msg = "🔒 This content is private or requires login."
        elif "unavailable" in err.lower():
            msg = "❌ Video is unavailable or has been removed."
        elif "copyright" in err.lower():
            msg = "⚖️ This video is blocked due to copyright restrictions."
        else:
            msg = f"❌ Download failed:\n`{err[:300]}`"
        await query.edit_message_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Unexpected error during download")
        await query.edit_message_text(
            f"❌ Unexpected error: `{str(e)[:200]}`", parse_mode="Markdown"
        )


# ── Main ──────────────────────────────────────────────────

async def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your BOT_TOKEN in the .env file or environment variable.")
        print("   Edit .env and set: BOT_TOKEN=your_actual_token_here")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 Bot is running! Press Ctrl+C to stop.")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        print("✅ Polling started. Waiting for messages...")
        await asyncio.Event().wait()  # run forever


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
