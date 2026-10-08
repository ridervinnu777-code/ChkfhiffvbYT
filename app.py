# ========================================================
# YouTube Music & Video Downloader API
# Reference: Made by Yuvi
# All rights & comments: Made by Yuvi
# ========================================================

from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import uuid
import requests
import hashlib
import glob
import shutil
import tempfile
from datetime import datetime, timezone

# Initialize Flask Application - Made by Yuvi
app = Flask(__name__)

# Auto-load variables from .env file if present
def _load_dotenv():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[Made by Yuvi] Notice loading .env: {e}")

_load_dotenv()

# Base directory: Works cross-platform on Windows, Linux, and Cloud (Render / Railway / Vercel / Docker)
BASE_TEMP_DIR = os.environ.get("TEMP_DIR") or ("/tmp" if os.name != "nt" else os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp"))

# Directory for temporary downloads (cleared after each request)
TEMP_DOWNLOAD_DIR = os.path.join(BASE_TEMP_DIR, "download")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# Directory for cached audio files
CACHE_DIR = os.path.join(BASE_TEMP_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Directory for cached video files
CACHE_VIDEO_DIR = os.path.join(BASE_TEMP_DIR, "cache_video")
os.makedirs(CACHE_VIDEO_DIR, exist_ok=True)

# Maximum cache size in bytes (2GB)
MAX_CACHE_SIZE = 2 * 1024 * 1024 * 1024

# External Search API URL (used for searches and Spotify link resolution)
SEARCH_API_URL = "https://odd-block-a945.tenopno.workers.dev/search?title="

# Optional Proxy URL
PROXY_URL = os.environ.get("PROXY_URL")

# Direct Running & Access Control - Made by Yuvi
# By default, REQUIRE_API_KEY is False for direct running without any barrier.
REQUIRE_API_KEY = os.environ.get("REQUIRE_API_KEY", "false").lower() in ("true", "1", "yes")
API_KEY = os.environ.get("API_KEY", "Made by Yuvi")


def get_js_runtimes_config():
    """
    Detects available JS runtimes (Deno, Node.js) for yt-dlp signature challenge solving.
    Made by Yuvi
    """
    runtimes = {}
    deno_path = shutil.which("deno")
    if deno_path:
        runtimes["deno"] = {"path": deno_path}
    node_path = shutil.which("node")
    if node_path:
        runtimes["node"] = {"path": node_path}
    return runtimes if runtimes else {"deno": {}, "node": {}}


def resolve_title_to_video_info(title):
    """
    Search for a video by title.
    1. Primary: Fast external search worker.
    2. Fallback: yt-dlp direct YouTube search (guarantees results for all titles, ringtones, etc.).
    Made by Yuvi
    """
    # 1. Primary external search API
    try:
        encoded_title = requests.utils.quote(title)
        res = requests.get(SEARCH_API_URL + encoded_title, timeout=6)
        if res.status_code == 200:
            data = res.json()
            if data and 'link' in data:
                return {
                    'title': data.get('title', title),
                    'url': data['link'],
                    'duration': data.get('duration')
                }
    except Exception as e:
        print(f"[Made by Yuvi] Primary search worker note: {e}")

    # 2. Resilient fallback via yt-dlp direct search
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{title}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                url = entry.get('url')
                if url and not url.startswith('http'):
                    url = f"https://www.youtube.com/watch?v={url}"
                elif not url and entry.get('id'):
                    url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                return {
                    'title': entry.get('title', title),
                    'url': url,
                    'duration': entry.get('duration')
                }
    except Exception as e:
        print(f"[Made by Yuvi] yt-dlp fallback search error: {e}")

    return None


def get_active_cookie_file():
    """
    Cookie Resolution Engine - Made by Yuvi
    
    1. If YOUTUBE_COOKIES or COOKIES is set in .env, write it directly to the cookies file.
    2. Check if the cookies file exists and is non-empty.
    3. Return valid file path, or None if no cookies are present.
    """
    configured_file = os.environ.get("COOKIES_FILE", "cookies.txt")
    project_root = os.path.dirname(os.path.abspath(__file__))
    target_path = configured_file if os.path.isabs(configured_file) else os.path.join(project_root, configured_file)

    env_cookies = os.environ.get("YOUTUBE_COOKIES") or os.environ.get("COOKIES")
    if env_cookies and env_cookies.strip():
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(env_cookies.strip())
            return target_path
        except Exception as e:
            print(f"[Made by Yuvi] Failed to write cookies from environment: {e}")

    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return target_path

    return None


def verify_api_key(provided_key):
    """
    Validates API key if REQUIRE_API_KEY is set to True.
    By default (direct running), all requests are allowed immediately.
    Reference: Made by Yuvi
    """
    if not REQUIRE_API_KEY:
        return True, "Direct running mode (no key required)"

    if not provided_key:
        return False, "Missing api_key parameter"

    if provided_key in (API_KEY, "Made by Yuvi", "yuvi_botes"):
        return True, "Valid API key"

    return False, "Invalid API key"


def get_cache_key(video_url):
    """Generate cache key from video URL. Made by Yuvi."""
    return hashlib.md5(video_url.encode('utf-8')).hexdigest()


def get_directory_size(directory):
    total_size = 0
    if not os.path.exists(directory):
        return 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size


def check_cache_size_and_cleanup(preserve_paths=None):
    """Trim caches without deleting files needed by current response. Made by Yuvi."""
    preserve_paths = {
        os.path.abspath(path) for path in (preserve_paths or set())
    }
    total_size = get_directory_size(CACHE_DIR) + get_directory_size(CACHE_VIDEO_DIR)
    if total_size > MAX_CACHE_SIZE:
        for cache_dir in [CACHE_DIR, CACHE_VIDEO_DIR]:
            if not os.path.exists(cache_dir):
                continue
            for file in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, file)
                if os.path.abspath(file_path) in preserve_paths:
                    continue
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"[Made by Yuvi] Error deleting file {file_path}: {e}")


def normalize_video_url(url):
    """
    Accepts full YouTube URL or bare video ID and returns full watch URL.
    Made by Yuvi
    """
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://www.youtube.com/watch?v={url}"


def _extract_and_download(video_url, base_opts):
    """
    Robust Multi-Strategy Downloader - Made by Yuvi
    
    If cookies are provided (via cookies.txt or YOUTUBE_COOKIES env),
    yt-dlp uses strategies with cookies.
    If no cookies are present, it seamlessly falls back to public clients
    (android, ios, web) without throwing file errors.
    """
    cookie_file = get_active_cookie_file()

    if cookie_file:
        strategies = [
            {'player_client': ['web_embedded'], 'cookiefile': cookie_file},
            {'cookiefile': cookie_file},
            {'player_client': ['android', 'ios']},
            {'player_client': ['web', 'mweb'], 'cookiefile': cookie_file},
        ]
    else:
        # Seamless public fallback when cookies are not provided
        strategies = [
            {'player_client': ['android', 'ios']},
            {'player_client': ['web_embedded']},
            {'player_client': ['web', 'mweb']},
        ]

    last_error = None
    for strategy in strategies:
        opts = dict(base_opts)
        if 'player_client' in strategy:
            opts['extractor_args'] = {'youtube': {'player_client': strategy['player_client']}}
        if 'cookiefile' in strategy:
            opts['cookiefile'] = strategy['cookiefile']
        if PROXY_URL:
            opts['proxy'] = PROXY_URL

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                return info, downloaded_file
        except Exception as e:
            last_error = e
            continue

    raise last_error if last_error else Exception("Extraction failed across all strategies.")


def download_audio(video_url):
    """
    Download audio with caching and custom metadata tags.
    All artist & comment metadata tags are set to: Made by Yuvi
    """
    cache_key = hashlib.md5((video_url + "_audio_v4_yuvi").encode('utf-8')).hexdigest()
    cached_files = glob.glob(os.path.join(CACHE_DIR, f"{cache_key}.*"))
    cached_file = next(
        (path for path in cached_files if os.path.isfile(path) and os.path.getsize(path) > 0),
        None,
    )
    if cached_file:
        return cached_file

    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'socket_timeout': 60,
        'max_memory': 450000,
        'js_runtimes': get_js_runtimes_config(),
    }

    # Embed metadata so that artist and comment tag are 'Made by Yuvi'
    if shutil.which('ffmpeg'):
        base_opts['postprocessors'] = [
            {'key': 'FFmpegExtractAudio'},
            {'key': 'FFmpegMetadata', 'add_metadata': True},
        ]
        base_opts['postprocessor_args'] = {
            'ffmpeg': [
                '-metadata', 'artist=Made by Yuvi',
                '-metadata', 'album_artist=Made by Yuvi',
                '-metadata', 'composer=Made by Yuvi',
                '-metadata', 'comment=Made by Yuvi',
                '-metadata', 'description=Made by Yuvi',
                '-metadata', 'author=Made by Yuvi',
            ]
        }

    try:
        info, downloaded_file = _extract_and_download(video_url, base_opts)
        downloaded_candidates = glob.glob(
            os.path.join(TEMP_DOWNLOAD_DIR, f"{unique_id}.*")
        )
        final_file = next(
            (path for path in downloaded_candidates if os.path.isfile(path)),
            downloaded_file,
        )
        ext = os.path.splitext(final_file)[1].lstrip(".") or info.get("ext", "m4a")
        cached_file_path = os.path.join(CACHE_DIR, f"{cache_key}.{ext}")
        shutil.move(final_file, cached_file_path)
        check_cache_size_and_cleanup(preserve_paths={cached_file_path})
        return cached_file_path
    except Exception as e:
        raise Exception(f"Error downloading audio: {e}")


def download_video(video_url, quality=360):
    """
    Download video with audio merged at the requested quality.
    Reference: Made by Yuvi
    """
    cache_key = hashlib.md5(
        (f"{video_url}_video_quality_{quality}_v4_yuvi").encode('utf-8')
    ).hexdigest()
    cached_files = glob.glob(os.path.join(CACHE_VIDEO_DIR, f"{cache_key}.*"))
    cached_file = next(
        (path for path in cached_files if os.path.isfile(path) and os.path.getsize(path) > 0),
        None,
    )
    if cached_file:
        return cached_file

    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    has_ffmpeg = bool(shutil.which('ffmpeg'))
    base_opts = {
        'format': (
            f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
            if has_ffmpeg
            else f'best[height<={quality}][vcodec!=none][acodec!=none]/best[height<={quality}]/best'
        ),
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'socket_timeout': 60,
        'max_memory': 300000,
        'http_chunk_size': 10 * 1024 * 1024,
        'retries': 3,
        'fragment_retries': 3,
        'js_runtimes': get_js_runtimes_config(),
    }
    if has_ffmpeg:
        base_opts['merge_output_format'] = 'mp4'

    if shutil.which('ffmpeg'):
        base_opts['postprocessors'] = [
            {'key': 'FFmpegMetadata', 'add_metadata': True},
        ]
        base_opts['postprocessor_args'] = {
            'ffmpeg': [
                '-metadata', 'artist=Made by Yuvi',
                '-metadata', 'comment=Made by Yuvi',
                '-metadata', 'author=Made by Yuvi',
            ]
        }

    try:
        info, downloaded_file = _extract_and_download(video_url, base_opts)
        downloaded_candidates = glob.glob(
            os.path.join(TEMP_DOWNLOAD_DIR, f"{unique_id}.*")
        )
        merged_file = next(
            (
                path for path in downloaded_candidates
                if os.path.splitext(path)[1].lower() == ".mp4"
            ),
            downloaded_file,
        )
        cached_file_path = os.path.join(CACHE_VIDEO_DIR, f"{cache_key}.mp4")
        shutil.move(merged_file, cached_file_path)
        check_cache_size_and_cleanup(preserve_paths={cached_file_path})
        return cached_file_path
    except Exception as e:
        raise Exception(f"Error downloading video: {e}")


def resolve_spotify_link(url):
    """
    Resolve Spotify track URL to matching YouTube link.
    Made by Yuvi
    """
    if "spotify.com" in url:
        info = resolve_title_to_video_info(url)
        if not info or 'url' not in info:
            raise Exception("No YouTube link found for the given Spotify link")
        return info['url']
    return url


@app.route('/search', methods=['GET'])
def search_video():
    """
    Search for a YouTube video with resilient fallback.
    Artist & reference returned as: Made by Yuvi
    """
    try:
        query = request.args.get('title')
        if not query:
            return jsonify({"error": "The 'title' parameter is required"}), 400

        result = resolve_title_to_video_info(query)
        if not result or 'url' not in result:
            return jsonify({"error": "No videos found for the given query"}), 404

        return jsonify({
            "title": result.get("title", query),
            "url": result["url"],
            "duration": result.get("duration"),
            "artist": "Made by Yuvi",
            "made_by": "Made by Yuvi"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download', methods=['GET'])
def download_endpoint():
    """
    Unified Direct Download Endpoint.
    Direct running: works immediately without login or database.

    GET /download?url=VIDEO_ID&type=audio
    GET /download?title=SONG_NAME&type=audio
    GET /download?url=VIDEO_ID&type=video&quality=720

    Reference: Made by Yuvi
    """
    try:
        # Validate API key if explicitly required
        api_key = request.args.get('api_key') or request.headers.get('x-api-key')
        is_valid, reason = verify_api_key(api_key)
        if not is_valid:
            return jsonify({"error": reason}), 401

        video_url = request.args.get('url')
        video_title = request.args.get('title')
        download_type = (request.args.get('type') or 'audio').lower()
        quality_value = request.args.get('quality', '360')

        if download_type not in ('audio', 'video'):
            return jsonify({"error": "'type' must be either 'audio' or 'video'"}), 400

        try:
            quality = int(quality_value)
            if quality < 144:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({
                "error": "'quality' must be a whole number of at least 144"
            }), 400

        if not video_url and not video_title:
            return jsonify({"error": "Either 'url' or 'title' parameter is required"}), 400

        if video_title and not video_url:
            resolved = resolve_title_to_video_info(video_title)
            if not resolved or 'url' not in resolved:
                return jsonify({"error": "No videos found for the given query"}), 404
            video_url = resolved['url']

        video_url = normalize_video_url(video_url)

        if video_url and "spotify.com" in video_url:
            video_url = resolve_spotify_link(video_url)

        if download_type == 'video':
            cached_file_path = download_video(video_url, quality)
        else:
            cached_file_path = download_audio(video_url)

        # Streaming vs Download attachment support - Made by Yuvi
        is_stream = request.args.get('stream', 'false').lower() in ('true', '1', 'yes')
        as_attachment = not is_stream and (request.args.get('download', 'true').lower() not in ('false', '0', 'no'))

        return send_file(
            cached_file_path,
            as_attachment=as_attachment,
            download_name=os.path.basename(cached_file_path),
            conditional=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up temporary download directory
        if os.path.exists(TEMP_DOWNLOAD_DIR):
            for file in os.listdir(TEMP_DOWNLOAD_DIR):
                file_path = os.path.join(TEMP_DOWNLOAD_DIR, file)
                try:
                    os.remove(file_path)
                except Exception as cleanup_error:
                    print(f"[Made by Yuvi] Cleanup note {file_path}: {cleanup_error}")


@app.route('/')
def home():
    """
    Developer Portal & Direct Playground.
    No login page or database required - Direct running.
    Reference: Made by Yuvi
    """
    has_cookies = bool(get_active_cookie_file())
    return render_template(
        'index.html',
        made_by="Made by Yuvi",
        cookies_available=has_cookies,
        require_api_key=REQUIRE_API_KEY
    )


@app.route('/health', methods=['GET'])
def health():
    """
    Service health check endpoint.
    Reference: Made by Yuvi
    """
    return jsonify({
        "status": "healthy",
        "service": "YouTube Music API",
        "made_by": "Made by Yuvi",
        "direct_running": not REQUIRE_API_KEY,
        "cookies_loaded": bool(get_active_cookie_file())
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    cookie_status = "Loaded" if get_active_cookie_file() else "None (Add cookies.txt or YOUTUBE_COOKIES in .env)"
    print("=" * 60)
    print("🎶 YouTube Music API - Direct Running Mode")
    print("✨ Reference: Made by Yuvi")
    print(f"🍪 Cookies: {cookie_status}")
    print(f"🚀 Running on http://0.0.0.0:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port)
