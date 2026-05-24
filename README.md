# 🎬 Telegram Video Downloader Bot

Download videos from **YouTube**, **Instagram**, and **TikTok** directly via Telegram.

---

## ✨ Features

- 📸 Instagram — Reels, Posts, Stories
- 🎵 TikTok — Videos
- 🎬 YouTube — Videos, Shorts
- 🎵 MP3 audio extraction
- 📦 Inline format picker (Video / Audio)
- 🔒 Cookie support for private/age-restricted content
- 🐳 Docker-ready

---

## 🚀 Quick Start

### 1. Get a Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy your **Bot Token**

---

### 2. Configure

Edit the `.env` file:

```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxYZ
```

---

### 3. Install & Run (Local)

**Prerequisites:** Python 3.10+, ffmpeg

```bash
# Install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: https://ffmpeg.org/download.html

# Install Python dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

---

### 4. Run with Docker (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🍪 Cookies (Private / Age-Restricted Content)

Some content requires authentication. To enable:

1. Install the **Get cookies.txt LOCALLY** browser extension
2. Log in to Instagram / YouTube in your browser
3. Export cookies as `cookies.txt` (Netscape format)
4. Place `cookies.txt` in the same folder as `bot.py`

---

## ☁️ Deployment

### Railway (Free Tier)
1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add `BOT_TOKEN` as an environment variable

### VPS (DigitalOcean / Hetzner / Linode)
```bash
# Clone your repo, then:
docker-compose up -d
```

### Systemd Service (without Docker)
```ini
# /etc/systemd/system/videobot.service
[Unit]
Description=Telegram Video Downloader Bot
After=network.target

[Service]
WorkingDirectory=/path/to/video-downloader-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
EnvironmentFile=/path/to/video-downloader-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable videobot
sudo systemctl start videobot
```

---

## 📁 Project Structure

```
video-downloader-bot/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── .env                # Your bot token (keep secret!)
├── Dockerfile          # Docker build file
├── docker-compose.yml  # Docker Compose config
├── cookies.txt         # Optional: for private content
├── downloads/          # Temp folder (auto-cleaned)
└── README.md
```

---

## ⚠️ Notes

- Telegram bots have a **50MB file size limit**
- Large YouTube videos may exceed this limit — try audio-only
- Keep your `.env` file **private** — never share your bot token

---

## 📜 License

MIT — use freely, modify as needed.
