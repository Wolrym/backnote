from sqlalchemy import delete, func, select

from backnote.db.models import Task
from backnote.services.base import BaseService


class TaskService(BaseService):
    async def create(
        self,
        *,
        subject_id: int,
        kind: str,
        title: str,
        content: str,
        created_by: int,
        lesson_id: int | None = None,
        file_name: str | None = None,
    ) -> Task:
        task = Task(
            subject_id=subject_id,
            lesson_id=lesson_id,
            kind=kind,
            title=title,
            content=content,
            file_name=file_name,
            created_by=created_by,
        )
        async with self._sm() as s:
            s.add(task)
            await s.commit()
            return task

    async def get(self, task_id: int) -> Task | None:
        async with self._sm() as s:
            return await s.get(Task, task_id)

    async def delete(self, task_id: int) -> None:
        async with self._sm() as s:
            await s.execute(delete(Task).where(Task.id == task_id))
            await s.commit()

    async def list_for(self, *, subject_id: int, lesson_id: int | None = None) -> list[Task]:
        """Tasks of a lesson, or the subject-level ones (no lesson) when lesson_id is None."""
        query = select(Task).where(Task.subject_id == subject_id)
        if lesson_id is not None:
            query = query.where(Task.lesson_id == lesson_id)
        else:
            query = query.where(Task.lesson_id.is_(None))
        async with self._sm() as s:
            return list(await s.scalars(query.order_by(Task.created_at, Task.id)))

    async def count_for_lesson(self, lesson_id: int) -> int:
        async with self._sm() as s:
            return await s.scalar(select(func.count(Task.id)).where(Task.lesson_id == lesson_id))
