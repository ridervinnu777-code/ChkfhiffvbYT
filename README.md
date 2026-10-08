# 🎶 YouTube Music API

> **Reference:** Made by Yuvi  
> **Direct Running Mode** • **Zero Database / Supabase** • **Plug & Play Cookies**

A high-performance Flask API to **search YouTube** and **download audio & video** from YouTube (and Spotify links, resolved via search) — powered by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.

---

## ✨ Features

- ⚡ **Direct Running**: No database, no Supabase, and no login required. Instant out-of-the-box operation.
- 🍪 **Plug & Play Cookies**: Safely share the repository without cookies. Simply add your own `cookies.txt` or set `YOUTUBE_COOKIES` in `.env` to work instantly.
- 🔍 **Search**: Search YouTube videos by song title.
- 🎧 **Audio Download**: Extracts audio with custom metadata tags (`artist: Made by Yuvi`, `comment: Made by Yuvi`).
- 🎬 **Video Download**: Configurable max quality (`144p`–`1080p`/`2160p`), auto-merged with audio via FFmpeg.
- 🎵 **Spotify Support**: Spotify track links are automatically resolved to YouTube matches.
- 🌐 **Multi-Strategy Fallback**: Gracefully falls back across YouTube clients (`web_embedded`, `android`, `ios`, `web`) if blocked.
- ⚡ **Disk Caching**: Previously downloaded audio and video files are cached and served instantly.

---

## 🍪 How to Add Cookies (1-Step Setup)

When sharing or receiving this codebase, YouTube cookies can be added in either of two easy ways:

### Method 1: Drop `cookies.txt` (Recommended for Local & Docker)
1. Export your YouTube cookies in Netscape format using browser extensions like **Get cookies.txt LOCALLY**.
2. Save the file as `cookies.txt` in the root folder of the project.

### Method 2: Set `YOUTUBE_COOKIES` in `.env` (Recommended for Cloud / Vercel / Render)
Open `.env` and paste your raw cookies content directly:
```env
YOUTUBE_COOKIES="your_raw_netscape_cookies_here"
```
The server will automatically detect and load your cookies! If no cookies are provided, it seamlessly operates using public clients (`android`, `ios`).

---

## 📡 API Endpoints

### 1. `GET /search`
Search for a YouTube video by song title.

| Param | Required | Description |
|---|---|---|
| `title` | ✅ | Search query (e.g. `Shape of You`) |

```bash
GET /search?title=Shape%20of%20You
```

**Response:**
```json
{
  "title": "Ed Sheeran - Shape of You",
  "url": "https://www.youtube.com/watch?v=...",
  "duration": 233,
  "artist": "Made by Yuvi",
  "made_by": "Made by Yuvi"
}
```

---

### 2. `GET /download`
Download audio or video for any YouTube URL, video ID, or Spotify link.

| Param | Required | Default | Description |
|---|---|---|---|
| `url` | one of `url`/`title` | — | Full YouTube/Spotify URL, or bare YouTube video ID |
| `title` | one of `url`/`title` | — | Search song by title directly |
| `type` | ❌ | `audio` | `audio` or `video` |
| `stream` | ❌ | `0` | Set `1` for inline streaming (ideal for Telegram voice chat / PyTgCalls & apps) |
| `quality` | ❌ | `360` | Max video height (`144`, `360`, `720`, `1080`, `2160`) |

**Examples:**
```bash
# Direct audio stream URL for Telegram Music Bots & PyTgCalls
GET /download?title=Shape%20of%20You&type=audio&stream=1

# Download audio file as attachment
GET /download?url=dQw4w9WgXcQ&type=audio

# Download 720p HD video
GET /download?url=dQw4w9WgXcQ&type=video&quality=720

# Download from Spotify link
GET /download?url=https://open.spotify.com/track/xxxx&type=audio
```

---

### 3. `GET /health`
Returns service status, cookie status, and configuration details.

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "YouTube Music API",
  "made_by": "Made by Yuvi",
  "direct_running": true,
  "cookies_loaded": true
}
```

---

## 💻 Integration Examples

### Telegram Music Bot (PyTgCalls Assistant Stream)
```python
# Telegram Music Bot Stream - Made by Yuvi
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped

async def play_music(chat_id, song_name):
    # Pass stream URL directly to PyTgCalls (Zero local downloading needed)
    stream_url = f"http://localhost:5000/download?title={song_name}&type=audio&stream=1"
    
    await pytgcalls.join_group_call(
        chat_id,
        AudioPiped(stream_url)
    )
```

### Python (Download & Send Audio in Telegram)
```python
import requests

# Made by Yuvi - Music Downloader
api_url = "http://localhost:5000/download"
params = {"title": "Ram Siya Ram", "type": "audio"}

response = requests.get(api_url, params=params)
with open("song.mp3", "wb") as f:
    f.write(response.content)

print("Downloaded! Made by Yuvi")
```

### Node.js
```javascript
const axios = require('axios');
const fs = require('fs');

async function downloadMusic(query) {
    const res = await axios.get('http://localhost:5000/download', {
        params: { title: query, type: 'audio' },
        responseType: 'arraybuffer'
    });
    fs.writeFileSync('track.mp3', res.data);
    console.log('Saved! Made by Yuvi');
}
```

---

## 🧑‍💻 Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env (optional)
cp .env.example .env

# 3. Add your cookies.txt (optional but recommended)

# 4. Run the server
python app.py
```
Open `http://localhost:5000` to access the live playground.

---

## 💬 Credits & Reference

- **Author / Reference**: Made by Yuvi
- **Telegram Support**: [t.me/yuvi_botes](https://t.me/yuvi_botes)
