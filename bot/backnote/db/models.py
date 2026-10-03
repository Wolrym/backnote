from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Stores UTC datetime. In SQLite, supports both integer unix timestamps and ISO strings."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(Integer())

    def process_bind_param(self, value: datetime | int | float | None, dialect):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("Naive datetimes are not allowed")
            return int(value.timestamp())
        raise ValueError(f"Unexpected datetime type: {type(value)}")

    def process_result_value(self, value: datetime | int | float | str | None, dialect):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, UTC)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except ValueError:
                return datetime.fromtimestamp(float(value), UTC)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        return value


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class SubjectKind(StrEnum):
    SUBJECT = "subject"
    COURSE = "course"


class LessonKind(StrEnum):
    LECTURE = "lecture"
    SEMINAR = "seminar"
    PRACTICE = "practice"
    LAB = "lab"
    VIDEO = "video"
    READING = "reading"
    OTHER = "other"


class MaterialKind(StrEnum):
    LINK = "link"
    DOCUMENT = "document"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"


class SummarySource(StrEnum):
    MANUAL = "manual"
    AI = "ai"


NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime(), date: Date()}  # noqa: RUF012


def _user_fk() -> ForeignKey:
    return ForeignKey("users.id", ondelete="SET NULL")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default=UserStatus.PENDING)
    notify_new_content: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime | None]
    login: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.username:
            return f"@{self.username}"
        return str(self.id)


class WebSession(Base):
    __tablename__ = "web_sessions"
    __table_args__ = (Index("ix_web_sessions_user", "user_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())


class Subject(Base):
    """A university subject or an online course; both hold ordered lessons."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), default=SubjectKind.SUBJECT, index=True)
    title: Mapped[str] = mapped_column(String(256))
    code: Mapped[str | None] = mapped_column(String(32))
    instructor: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    term: Mapped[int | None] = mapped_column(Integer)
    ects: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(String(1024))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, _user_fk())
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default=LessonKind.LECTURE)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(1024))
    held_on: Mapped[date | None]
    summary: Mapped[str | None] = mapped_column(Text)
    summary_source: Mapped[str | None] = mapped_column(String(16))
    summary_updated_at: Mapped[datetime | None]
    summary_by: Mapped[int | None] = mapped_column(BigInteger, _user_fk())
    created_by: Mapped[int | None] = mapped_column(BigInteger, _user_fk())
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Material(Base):
    """A link or Telegram file attached to a subject or a lesson."""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(256))
    url: Mapped[str | None] = mapped_column(String(1024))
    file_id: Mapped[str | None] = mapped_column(String(256))
    created_by: Mapped[int | None] = mapped_column(BigInteger, _user_fk())
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    completed_at: Mapped[datetime] = mapped_column(default=utcnow)


class LessonNote(Base):
    """Private per-user note for a lesson."""

    __tablename__ = "lesson_notes"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Task(Base):
    """A .py / .md / .html task attached to a subject or (optionally) a lesson."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(16))  # python | markdown | html
    content: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(String(256))
    created_by: Mapped[int | None] = mapped_column(BigInteger, _user_fk())
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class TaskWork(Base):
    """A user's personal copy of a task. No row = the user works with the base version."""

    __tablename__ = "task_work"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

