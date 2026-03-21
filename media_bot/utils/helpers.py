from datetime import datetime


def fmt_duration(sec: float) -> str:
    if not sec: return "—"
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def fmt_size(mb: float) -> str:
    if mb < 1: return f"{mb*1024:.0f} KB"
    if mb < 1024: return f"{mb:.1f} MB"
    return f"{mb/1024:.2f} GB"


def platform_emoji(p: str) -> str:
    return {"youtube": "▶️", "instagram": "📸", "tiktok": "🎵"}.get(p.lower(), "🌐")


def fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso or "—"


def success_caption(info: dict) -> str:
    emoji = platform_emoji(info.get("platform", ""))
    title = (info.get("title") or "Media")[:60]
    dur = fmt_duration(info.get("duration", 0))
    size = fmt_size(info.get("file_size", 0))
    return (
        f"{emoji} <b>{title}</b>\n\n"
        f"⏱ <code>{dur}</code>  💾 <code>{size}</code>\n"
        f"✅ Muvaffaqiyatli yuklandi!"
    )
