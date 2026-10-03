from aiogram.types import User as TgUser

from backnote.db.models import LessonKind, SubjectKind
from tests.conftest import ADMIN_ID


async def test_tasks_attach_to_lessons_and_subjects(svc):
    await svc.users.touch(TgUser(id=ADMIN_ID, is_bot=False, first_name="Admin"))
    subject = await svc.subjects.create(
        kind=SubjectKind.SUBJECT, title="Algorithms", created_by=ADMIN_ID
    )
    lesson = await svc.lessons.create(
        subject_id=subject.id,
        number=1,
        kind=LessonKind.LECTURE,
        title="Intro",
        created_by=ADMIN_ID,
    )

    on_lesson = await svc.tasks.create(
        subject_id=subject.id,
        lesson_id=lesson.id,
        kind="python",
        title="Binary search",
        content="print(1)",
        created_by=ADMIN_ID,
    )
    await svc.tasks.create(
        subject_id=subject.id, kind="markdown", title="Reading", content="# Hi", created_by=ADMIN_ID
    )

    listed = await svc.tasks.list_for(subject_id=subject.id, lesson_id=lesson.id)
    assert [t.id for t in listed] == [on_lesson.id]
    assert len(await svc.tasks.list_for(subject_id=subject.id)) == 1  # subject-level only
    assert await svc.tasks.count_for_lesson(lesson.id) == 1

    await svc.lessons.delete(lesson.id)  # tasks follow their lesson
    assert await svc.tasks.get(on_lesson.id) is None
