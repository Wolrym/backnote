from dataclasses import dataclass

from sqlalchemy import and_, delete, func, select

from backnote.db.models import Lesson, LessonNote, LessonProgress, Subject
from backnote.services.base import BaseService


@dataclass(frozen=True)
class SubjectProgress:
    subject: Subject
    total: int
    done: int


class ProgressService(BaseService):
    async def is_completed(self, lesson_id: int, user_id: int) -> bool:
        async with self._sm() as s:
            return await s.get(LessonProgress, (user_id, lesson_id)) is not None

    async def toggle_lesson(self, lesson_id: int, user_id: int) -> bool:
        """Flip the personal completion mark; returns the new state."""
        async with self._sm() as s:
            row = await s.get(LessonProgress, (user_id, lesson_id))
            if row:
                await s.delete(row)
            else:
                s.add(LessonProgress(user_id=user_id, lesson_id=lesson_id))
            await s.commit()
            return row is None

    async def completed_count(self, user_id: int) -> int:
        async with self._sm() as s:
            return await s.scalar(
                select(func.count())
                .select_from(LessonProgress)
                .where(LessonProgress.user_id == user_id)
            )

    async def overview(self, user_id: int) -> list[SubjectProgress]:
        """Per-subject progress for active subjects that have at least one lesson."""
        total = func.count(Lesson.id)
        done = func.count(LessonProgress.lesson_id)
        query = (
            select(Subject, total, done)
            .join(Lesson, Lesson.subject_id == Subject.id)
            .outerjoin(
                LessonProgress,
                and_(LessonProgress.lesson_id == Lesson.id, LessonProgress.user_id == user_id),
            )
            .where(Subject.is_archived.is_(False))
            .group_by(Subject.id)
            .order_by(Subject.kind.desc(), func.lower(Subject.title))
        )
        async with self._sm() as s:
            return [SubjectProgress(subj, t, d) for subj, t, d in await s.execute(query)]

    async def continue_lesson(self, user_id: int) -> tuple[Lesson, Subject] | None:
        """The first unfinished lesson in the subject the user completed something in last."""
        async with self._sm() as s:
            last_subject_id = await s.scalar(
                select(Lesson.subject_id)
                .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
                .join(Subject, Subject.id == Lesson.subject_id)
                .where(LessonProgress.user_id == user_id, Subject.is_archived.is_(False))
                .order_by(LessonProgress.completed_at.desc())
                .limit(1)
            )
            if last_subject_id is None:
                return None
            row = (
                await s.execute(
                    select(Lesson, Subject)
                    .join(Subject, Subject.id == Lesson.subject_id)
                    .outerjoin(
                        LessonProgress,
                        and_(
                            LessonProgress.lesson_id == Lesson.id,
                            LessonProgress.user_id == user_id,
                        ),
                    )
                    .where(Lesson.subject_id == last_subject_id, LessonProgress.lesson_id.is_(None))
                    .order_by(Lesson.number, Lesson.id)
                    .limit(1)
                )
            ).first()
            return (row[0], row[1]) if row else None

    async def get_note(self, lesson_id: int, user_id: int) -> str | None:
        async with self._sm() as s:
            note = await s.get(LessonNote, (user_id, lesson_id))
            return note.text if note else None

    async def set_note(self, lesson_id: int, user_id: int, text: str | None) -> None:
        async with self._sm() as s:
            if not text:
                await s.execute(
                    delete(LessonNote).where(
                        LessonNote.user_id == user_id, LessonNote.lesson_id == lesson_id
                    )
                )
            else:
                await s.merge(LessonNote(user_id=user_id, lesson_id=lesson_id, text=text))
            await s.commit()
