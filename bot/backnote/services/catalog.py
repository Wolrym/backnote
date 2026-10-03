from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, delete, func, or_, select

from backnote.db.models import (
    Lesson,
    LessonKind,
    LessonProgress,
    Material,
    Subject,
    SubjectKind,
    SummarySource,
    utcnow,
)
from backnote.services.base import BaseService, apply_fields


@dataclass(frozen=True)
class SubjectRow:
    subject: Subject
    total: int
    done: int


@dataclass(frozen=True)
class LessonRow:
    lesson: Lesson
    done: bool


def _like(query: str) -> str:
    escaped = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SubjectService(BaseService):
    EDITABLE = frozenset(
        {
            "title",
            "code",
            "instructor",
            "description",
            "year",
            "term",
            "ects",
            "provider",
            "url",
            "is_archived",
        }
    )

    async def create(self, *, kind: SubjectKind, title: str, created_by: int, **fields) -> Subject:
        subject = Subject(kind=kind, title=title, created_by=created_by)
        apply_fields(subject, fields, set(self.EDITABLE))
        async with self._sm() as s:
            s.add(subject)
            await s.commit()
            return subject

    async def get(self, subject_id: int) -> Subject | None:
        async with self._sm() as s:
            return await s.get(Subject, subject_id)

    async def update(self, subject_id: int, **fields: Any) -> Subject:
        async with self._sm() as s:
            subject = await s.get(Subject, subject_id)
            if subject is None:
                raise LookupError(subject_id)
            apply_fields(subject, fields, set(self.EDITABLE))
            await s.commit()
            return subject

    async def delete(self, subject_id: int) -> None:
        async with self._sm() as s:
            await s.execute(delete(Subject).where(Subject.id == subject_id))
            await s.commit()

    async def list_with_progress(
        self, kind: SubjectKind, user_id: int, *, archived: bool = False
    ) -> list[SubjectRow]:
        total = func.count(Lesson.id)
        done = func.count(LessonProgress.lesson_id)
        query = (
            select(Subject, total, done)
            .outerjoin(Lesson, Lesson.subject_id == Subject.id)
            .outerjoin(
                LessonProgress,
                and_(LessonProgress.lesson_id == Lesson.id, LessonProgress.user_id == user_id),
            )
            .where(Subject.kind == kind, Subject.is_archived.is_(archived))
            .group_by(Subject.id)
            # Most recent study period first, undated subjects last.
            .order_by(
                Subject.year.is_(None),
                Subject.year.desc(),
                Subject.term.desc(),
                func.lower(Subject.title),
            )
        )
        async with self._sm() as s:
            rows = await s.execute(query)
            return [SubjectRow(subject, t, d) for subject, t, d in rows]

    async def count(self, kind: SubjectKind, *, archived: bool = False) -> int:
        async with self._sm() as s:
            return await s.scalar(
                select(func.count(Subject.id)).where(
                    Subject.kind == kind, Subject.is_archived.is_(archived)
                )
            )

    async def search(self, query: str, limit: int = 20) -> list[Subject]:
        pattern = _like(query)
        async with self._sm() as s:
            return list(
                await s.scalars(
                    select(Subject)
                    .where(
                        or_(
                            func.lower(Subject.title).like(pattern, escape="\\"),
                            func.lower(Subject.code).like(pattern, escape="\\"),
                            func.lower(Subject.instructor).like(pattern, escape="\\"),
                        )
                    )
                    .order_by(Subject.is_archived, func.lower(Subject.title))
                    .limit(limit)
                )
            )


class LessonService(BaseService):
    EDITABLE = frozenset({"number", "kind", "title", "description", "video_url", "held_on"})

    async def create(
        self,
        *,
        subject_id: int,
        number: int,
        kind: LessonKind,
        title: str,
        created_by: int,
        **fields: Any,
    ) -> Lesson:
        lesson = Lesson(
            subject_id=subject_id, number=number, kind=kind, title=title, created_by=created_by
        )
        apply_fields(lesson, fields, set(self.EDITABLE))
        async with self._sm() as s:
            s.add(lesson)
            await s.commit()
            return lesson

    async def get(self, lesson_id: int) -> Lesson | None:
        async with self._sm() as s:
            return await s.get(Lesson, lesson_id)

    async def update(self, lesson_id: int, **fields: Any) -> Lesson:
        async with self._sm() as s:
            lesson = await s.get(Lesson, lesson_id)
            if lesson is None:
                raise LookupError(lesson_id)
            apply_fields(lesson, fields, set(self.EDITABLE))
            await s.commit()
            return lesson

    async def set_summary(
        self, lesson_id: int, text: str | None, source: SummarySource | None, user_id: int | None
    ) -> Lesson:
        async with self._sm() as s:
            lesson = await s.get(Lesson, lesson_id)
            if lesson is None:
                raise LookupError(lesson_id)
            lesson.summary = text
            lesson.summary_source = source if text else None
            lesson.summary_by = user_id if text else None
            lesson.summary_updated_at = utcnow() if text else None
            await s.commit()
            return lesson

    async def delete(self, lesson_id: int) -> None:
        async with self._sm() as s:
            await s.execute(delete(Lesson).where(Lesson.id == lesson_id))
            await s.commit()

    async def list_with_progress(self, subject_id: int, user_id: int) -> list[LessonRow]:
        query = (
            select(Lesson, LessonProgress.lesson_id.is_not(None))
            .outerjoin(
                LessonProgress,
                and_(LessonProgress.lesson_id == Lesson.id, LessonProgress.user_id == user_id),
            )
            .where(Lesson.subject_id == subject_id)
            .order_by(Lesson.number, Lesson.id)
        )
        async with self._sm() as s:
            return [LessonRow(lesson, bool(done)) for lesson, done in await s.execute(query)]

    async def next_number(self, subject_id: int, kind: LessonKind) -> int:
        async with self._sm() as s:
            current = await s.scalar(
                select(func.max(Lesson.number)).where(
                    Lesson.subject_id == subject_id, Lesson.kind == kind
                )
            )
            return (current or 0) + 1

    async def neighbours(self, lesson: Lesson) -> tuple[int | None, int | None]:
        async with self._sm() as s:
            ids = list(
                await s.scalars(
                    select(Lesson.id)
                    .where(Lesson.subject_id == lesson.subject_id)
                    .order_by(Lesson.number, Lesson.id)
                )
            )
        idx = ids.index(lesson.id)
        prev_id = ids[idx - 1] if idx > 0 else None
        next_id = ids[idx + 1] if idx + 1 < len(ids) else None
        return prev_id, next_id

    async def count(self) -> int:
        async with self._sm() as s:
            return await s.scalar(select(func.count(Lesson.id)))

    async def search(self, query: str, limit: int = 30) -> list[tuple[Lesson, Subject]]:
        pattern = _like(query)
        async with self._sm() as s:
            rows = await s.execute(
                select(Lesson, Subject)
                .join(Subject, Subject.id == Lesson.subject_id)
                .where(
                    or_(
                        func.lower(Lesson.title).like(pattern, escape="\\"),
                        func.lower(Lesson.description).like(pattern, escape="\\"),
                        func.lower(Lesson.summary).like(pattern, escape="\\"),
                    )
                )
                .order_by(
                    # Title matches first.
                    case((func.lower(Lesson.title).like(pattern, escape="\\"), 0), else_=1),
                    Subject.title,
                    Lesson.number,
                )
                .limit(limit)
            )
            return [(lesson, subject) for lesson, subject in rows]


class MaterialService(BaseService):
    async def create(
        self,
        *,
        subject_id: int,
        kind: str,
        title: str,
        created_by: int,
        lesson_id: int | None = None,
        url: str | None = None,
        file_id: str | None = None,
    ) -> Material:
        material = Material(
            subject_id=subject_id,
            lesson_id=lesson_id,
            kind=kind,
            title=title,
            url=url,
            file_id=file_id,
            created_by=created_by,
        )
        async with self._sm() as s:
            s.add(material)
            await s.commit()
            return material

    async def get(self, material_id: int) -> Material | None:
        async with self._sm() as s:
            return await s.get(Material, material_id)

    async def rename(self, material_id: int, title: str) -> None:
        async with self._sm() as s:
            material = await s.get(Material, material_id)
            if material:
                material.title = title
                await s.commit()

    async def delete(self, material_id: int) -> None:
        async with self._sm() as s:
            await s.execute(delete(Material).where(Material.id == material_id))
            await s.commit()

    async def list_for(
        self,
        *,
        subject_id: int,
        lesson_id: int | None = None,
    ) -> list[Material]:
        """Materials of a lesson, or of the subject itself when lesson_id is None."""
        query = select(Material).where(Material.subject_id == subject_id)
        if lesson_id is not None:
            query = query.where(Material.lesson_id == lesson_id)
        else:
            query = query.where(Material.lesson_id.is_(None))
        async with self._sm() as s:
            return list(await s.scalars(query.order_by(Material.created_at, Material.id)))

    async def count_for_lesson(self, lesson_id: int) -> int:
        async with self._sm() as s:
            return await s.scalar(
                select(func.count(Material.id)).where(Material.lesson_id == lesson_id)
            )
