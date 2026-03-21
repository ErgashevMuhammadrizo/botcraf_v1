"""yt-dlp downloader — YouTube, Instagram, TikTok"""

import os
import re
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

import yt_dlp

from config.settings import DOWNLOADS_DIR, MAX_FILE_SIZE_MB, FFMPEG_AVAILABLE

logger = logging.getLogger(__name__)


def detect_platform(url: str) -> Optional[str]:
    url_l = url.lower()
    if any(x in url_l for x in ["youtube.com", "youtu.be"]):
        return "youtube"
    if any(x in url_l for x in ["instagram.com", "instagr.am"]):
        return "instagram"
    if any(x in url_l for x in ["tiktok.com", "vm.tiktok.com"]):
        return "tiktok"
    return None


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if "&list=" in url:
        url = url.split("&list=", 1)[0]
    if "?si=" in url and "youtu" in url:
        url = url.split("?si=", 1)[0]
    return url


def is_valid_url(url: str) -> bool:
    url = normalize_url(url)
    return url.startswith("http://") or url.startswith("https://")


def _build_ydl_opts(output_dir: str, fmt: str, is_audio: bool, platform: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(output_dir, "%(title).80s.%(ext)s"),
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "concurrent_fragment_downloads": 4,
        "nopart": True,
        "format_sort": ["ext:mp4:m4a", "res", "fps"],
        "ignoreerrors": False,
        "noplaylist": True,
        # FFMPEG yokligida merge qilmaslik
        "merge_output_format": "mp4" if FFMPEG_AVAILABLE else None,
    }

    if not FFMPEG_AVAILABLE:
        opts["postprocessors"] = []

    if is_audio:
        if FFMPEG_AVAILABLE:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            # ffmpeg yo'q — m4a yoki webm to'g'ridan yuklab olamiz
            opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
    else:
        opts["format"] = fmt

    # Instagram uchun maxsus sozlamalar
    if platform == "instagram":
        opts["http_headers"] = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        }
        # Cookie fayl bor bo'lsa qo'shamiz
        cookies = os.getenv("INSTAGRAM_COOKIES_FILE", "")
        if cookies and os.path.exists(cookies):
            opts["cookiefile"] = cookies

    if platform == "youtube":
        opts["extractor_args"] = {"youtube": {"player_client": ["android", "web"]}}
    return opts


def _find_file(directory: str) -> Optional[str]:
    exts = {".mp4", ".mp3", ".mkv", ".webm", ".m4a", ".opus",
            ".jpg", ".jpeg", ".png", ".gif"}
    try:
        for f in Path(directory).iterdir():
            if f.suffix.lower() in exts:
                return str(f)
    except Exception:
        pass
    return None


def _cleanup(directory: str):
    try:
        import shutil
        shutil.rmtree(directory, ignore_errors=True)
    except Exception:
        pass


def cleanup_file(file_path: str):
    try:
        p = Path(file_path)
        if p.exists():
            p.unlink()
        parent = p.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except Exception as e:
        logger.warning(f"cleanup xatosi: {e}")


async def download_media(url: str, quality_key: str = "720p") -> dict:
    from config.settings import QUALITY_OPTIONS
    url = normalize_url(url)
    quality = QUALITY_OPTIONS.get(quality_key, QUALITY_OPTIONS["720p"])
    is_audio = quality_key == "audio"
    platform = detect_platform(url) or "unknown"

    session_id = str(uuid.uuid4())[:8]
    output_dir = os.path.join(DOWNLOADS_DIR, session_id)
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = _build_ydl_opts(output_dir, quality["format"], is_audio, platform)

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _do_download, url, ydl_opts)

        file_path = _find_file(output_dir)
        if not file_path:
            _cleanup(output_dir)
            return {"success": False, "error": "❌ Fayl yuklab olinmadi. Boshqa sifat tanlang.", "platform": platform}

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > MAX_FILE_SIZE_MB:
            _cleanup(output_dir)
            return {"success": False,
                    "error": f"❌ Fayl juda katta ({file_size:.1f} MB). Pastroq sifat tanlang.",
                    "platform": platform}

        return {
            "success": True,
            "file_path": file_path,
            "title": (info.get("title") or "Media")[:100],
            "platform": platform,
            "duration": info.get("duration") or 0,
            "file_size": round(file_size, 2),
            "is_audio": is_audio,
            "session_dir": output_dir,
            "error": None,
        }

    except yt_dlp.utils.DownloadError as e:
        _cleanup(output_dir)
        err = str(e)
        if "Private" in err or "Login" in err or "login" in err:
            msg = "❌ Bu post xususiy. Login talab qiladi."
        elif "not available" in err or "unavailable" in err or "video unavailable" in err.lower():
            msg = "❌ Video ochilmadi. Havola noto'g'ri, video yashirin, region blok yoki vaqtincha cheklangan bo'lishi mumkin."
        elif "Too many requests" in err or "429" in err:
            msg = "⏳ Juda ko'p so'rov. Biroz kuting."
        elif "ffmpeg" in err.lower() or "ffprobe" in err.lower():
            msg = "⚠️ ffmpeg topilmadi. Pastroq sifat (720p/480p) tanlang."
        elif "Unsupported URL" in err:
            msg = "❌ Bu havola qo'llab-quvvatlanmaydi."
        else:
            msg = f"❌ Xato: {err[:150]}"
        logger.error(f"DownloadError [{url}]: {err[:200]}")
        return {"success": False, "error": msg, "platform": platform}

    except Exception as e:
        _cleanup(output_dir)
        logger.exception(f"Kutilmagan xato [{url}]: {e}")
        return {"success": False, "error": "❌ Noma'lum xato. Keyinroq urinib ko'ring.", "platform": platform}


def _do_download(url: str, opts: dict) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)
