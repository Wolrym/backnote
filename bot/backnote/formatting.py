"""Pure helpers that turn domain objects into Telegram HTML / Rich Markdown."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from aiogram.types import Message

from backnote.db.models import Lesson, LessonKind, MaterialKind, Subject, SubjectKind


def h(value: object | None) -> str:
    return escape(str(value)) if value is not None else ""


@dataclass(frozen=True)
class KindMeta:
    emoji: str
    label: str
    short: str


LESSON_KINDS: dict[str, KindMeta] = {
    LessonKind.LECTURE: KindMeta("🎓", "Lecture", "L"),
    LessonKind.SEMINAR: KindMeta("💬", "Seminar", "S"),
    LessonKind.PRACTICE: KindMeta("🛠", "Practice", "P"),
    LessonKind.LAB: KindMeta("🧪", "Lab", "Lab"),
    LessonKind.VIDEO: KindMeta("🎬", "Video", "V"),
    LessonKind.READING: KindMeta("📖", "Reading", "R"),
    LessonKind.OTHER: KindMeta("📌", "Other", "#"),
}

SUBJECT_KINDS: dict[str, KindMeta] = {
    SubjectKind.SUBJECT: KindMeta("📘", "Subject", "Subjects"),
    SubjectKind.COURSE: KindMeta("🎯", "Course", "Courses"),
}

MATERIAL_EMOJI: dict[str, str] = {
    MaterialKind.LINK: "🔗",
    MaterialKind.DOCUMENT: "📄",
    MaterialKind.PHOTO: "🖼",
    MaterialKind.VIDEO: "🎞",
    MaterialKind.AUDIO: "🎧",
    MaterialKind.VOICE: "🎙",
}


def lesson_kind(kind: str) -> KindMeta:
    return LESSON_KINDS.get(kind, LESSON_KINDS[LessonKind.OTHER])


def lesson_code(lesson: Lesson) -> str:
    meta = lesson_kind(lesson.kind)
    return f"{meta.short}{lesson.number}"


def lesson_heading(lesson: Lesson) -> str:
    """Plain text such as "Lecture 3 · Supply and demand"."""
    return f"{lesson_kind(lesson.kind).label} {lesson.number} · {lesson.title}"


def lesson_button(lesson: Lesson, done: bool) -> str:
    mark = "✅ " if done else ""
    return f"{mark}{lesson_code(lesson)} · {lesson.title}"


def term_label(year: int | None, term: int | None) -> str | None:
    parts = []
    if year:
        parts.append(f"Year {year}")
    if term:
        parts.append(f"Term {term}")
    return " · ".join(parts) or None


def term_short(year: int | None, term: int | None) -> str:
    if year and term:
        return f"Y{year}T{term}"
    if year:
        return f"Y{year}"
    if term:
        return f"T{term}"
    return ""


def progress_bar(done: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "▱" * width
    filled = round(width * done / total)
    return "▰" * filled + "▱" * (width - filled)


def percent(done: int, total: int) -> int:
    return round(100 * done / total) if total else 0


def progress_line(done: int, total: int) -> str:
    return f"{progress_bar(done, total)} {done}/{total} · {percent(done, total)}%"


def subject_button(subject: Subject, total: int, done: int) -> str:
    tag = term_short(subject.year, subject.term)
    prefix = f"[{tag}] " if tag else ""
    status = "done ✓" if total and done == total else f"{done}/{total}"
    return f"{prefix}{subject.title} · {status}"


_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_id(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    candidate: str | None = None
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in _YT_HOSTS:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in {"live", "shorts", "embed", "v"}:
                candidate = parts[1]
    return candidate if candidate and _YT_ID.match(candidate) else None


def youtube_watch_url(url: str | None) -> str | None:
    vid = youtube_id(url)
    return f"https://www.youtube.com/watch?v={vid}" if vid else None


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def normalize_url(text: str) -> str | None:
    text = text.strip()
    if not text or " " in text:
        return None
    if not re.match(r"^https?://", text, re.IGNORECASE):
        if "." not in text:
            return None
        text = f"https://{text}"
    parsed = urlparse(text)
    return text if parsed.hostname and "." in parsed.hostname else None


def extract_url(message: Message) -> str | None:
    """First link in a message: entities first (handles hidden text links), then plain text."""
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == "text_link" and entity.url:
            return entity.url
        if entity.type == "url":
            return entity.extract_from(text)
    match = _URL_RE.search(text)
    if match:
        return match.group(0).rstrip(").,;!?")
    return normalize_url(text)


def local(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt.astimezone(tz)


def fmt_datetime(dt: datetime, tz: ZoneInfo) -> str:
    return local(dt, tz).strftime("%a, %d %b · %H:%M")


def fmt_date(d: date) -> str:
    return d.strftime("%a, %d %b %Y")


def quote(text: str, *, expandable: bool | None = None) -> str:
    """HTML block quote; long texts collapse automatically."""
    if expandable is None:
        expandable = len(text) > 300 or text.count("\n") > 4
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{h(text)}</blockquote>"


def summary_markdown(lesson: Lesson, subject: Subject, *, source_line: str | None = None) -> str:
    """Rich Markdown document for sendRichMessage (headings, tables, formulas…)."""
    header = [
        f"# {lesson_kind(lesson.kind).emoji} {_md_escape(lesson_heading(lesson))}",
        f"*{_md_escape(subject.title)}*",
    ]
    if lesson.video_url:
        header.append(f"[▶️ Watch the recording]({lesson.video_url})")
    parts = ["\n\n".join(header), "---", (lesson.summary or "").strip()]
    if source_line:
        parts += ["---", f"_{_md_escape(source_line)}_"]
    return "\n\n".join(parts)


_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>#|~=$])")


def _md_escape(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Split on paragraph/line boundaries so each chunk fits a Telegram message."""
    chunks: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip("\n")
    if rest.strip():
        chunks.append(rest)
    return chunks
