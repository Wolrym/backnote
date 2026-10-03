import pytest
from aiogram.types import User as TgUser

from backnote.db.models import LessonKind, SubjectKind, UserStatus
from tests.conftest import ADMIN_ID

FRIEND = 2000


async def make_members(svc):
    await svc.users.touch(TgUser(id=ADMIN_ID, is_bot=False, first_name="Admin"))
    await svc.users.allow(FRIEND)


async def test_touch_creates_pending_and_admin_active(svc):
    admin, created = await svc.users.touch(TgUser(id=ADMIN_ID, is_bot=False, first_name="A"))
    assert created and admin.status == UserStatus.ACTIVE
    stranger, created = await svc.users.touch(TgUser(id=5, is_bot=False, first_name="S"))
    assert created and stranger.status == UserStatus.PENDING
    _, created = await svc.users.touch(TgUser(id=5, is_bot=False, first_name="S"))
    assert not created
    with pytest.raises(PermissionError):
        await svc.users.set_status(ADMIN_ID, UserStatus.BLOCKED)
    with pytest.raises(PermissionError):
        await svc.users.remove(ADMIN_ID)


async def test_progress_is_personal(svc):
    await make_members(svc)
    subject = await svc.subjects.create(
        kind=SubjectKind.SUBJECT, title="Micro", created_by=FRIEND, year=1, term=2
    )
    l1 = await svc.lessons.create(
        subject_id=subject.id, number=1, kind=LessonKind.LECTURE, title="Intro", created_by=FRIEND
    )
    l2 = await svc.lessons.create(
        subject_id=subject.id, number=2, kind=LessonKind.LECTURE, title="Demand", created_by=FRIEND
    )
    assert await svc.lessons.next_number(subject.id, LessonKind.LECTURE) == 3
    assert await svc.lessons.next_number(subject.id, LessonKind.SEMINAR) == 1

    assert await svc.progress.toggle_lesson(l1.id, ADMIN_ID) is True
    rows = await svc.subjects.list_with_progress(SubjectKind.SUBJECT, ADMIN_ID)
    assert [(r.total, r.done) for r in rows] == [(2, 1)]
    rows = await svc.subjects.list_with_progress(SubjectKind.SUBJECT, FRIEND)
    assert [(r.total, r.done) for r in rows] == [(2, 0)]

    lesson, subj = await svc.progress.continue_lesson(ADMIN_ID)
    assert (lesson.id, subj.id) == (l2.id, subject.id)
    assert await svc.progress.continue_lesson(FRIEND) is None
    assert await svc.lessons.neighbours(l1) == (None, l2.id)

    assert await svc.progress.toggle_lesson(l1.id, ADMIN_ID) is False
    assert await svc.progress.completed_count(ADMIN_ID) == 0


async def test_delete_subject_cascades(svc):
    await make_members(svc)
    subject = await svc.subjects.create(kind=SubjectKind.COURSE, title="ML", created_by=FRIEND)
    lesson = await svc.lessons.create(
        subject_id=subject.id, number=1, kind=LessonKind.VIDEO, title="W1", created_by=FRIEND
    )
    await svc.materials.create(
        subject_id=subject.id,
        lesson_id=lesson.id,
        kind="link",
        title="x",
        created_by=FRIEND,
        url="https://x.io",
    )
    await svc.progress.toggle_lesson(lesson.id, FRIEND)
    await svc.progress.set_note(lesson.id, FRIEND, "remember this")
    await svc.subjects.delete(subject.id)
    assert await svc.lessons.get(lesson.id) is None
    assert await svc.progress.completed_count(FRIEND) == 0
    assert await svc.progress.get_note(lesson.id, FRIEND) is None


async def test_materials_are_scoped_to_target(svc):
    await make_members(svc)
    subject = await svc.subjects.create(kind=SubjectKind.SUBJECT, title="S", created_by=FRIEND)
    lesson = await svc.lessons.create(
        subject_id=subject.id, number=1, kind=LessonKind.LECTURE, title="L", created_by=FRIEND
    )
    common = dict(subject_id=subject.id, kind="document", created_by=FRIEND, file_id="f")
    await svc.materials.create(**common, title="syllabus")
    await svc.materials.create(**common, title="slides", lesson_id=lesson.id)
    assert [m.title for m in await svc.materials.list_for(subject_id=subject.id)] == ["syllabus"]
    assert [
        m.title for m in await svc.materials.list_for(subject_id=subject.id, lesson_id=lesson.id)
    ] == ["slides"]


async def test_search(svc):
    await make_members(svc)
    subject = await svc.subjects.create(
        kind=SubjectKind.SUBJECT, title="Microeconomics", created_by=FRIEND
    )
    lesson = await svc.lessons.create(
        subject_id=subject.id,
        number=1,
        kind=LessonKind.LECTURE,
        title="Elasticity",
        created_by=FRIEND,
    )
    await svc.lessons.set_summary(lesson.id, "Price 100% elasticity", "manual", FRIEND)
    assert [s.id for s in await svc.subjects.search("micro")] == [subject.id]
    assert [lesson.id for lesson, _ in await svc.lessons.search("ELAST")] == [lesson.id]
    assert [lesson.id for lesson, _ in await svc.lessons.search("100%")] == [lesson.id]
    assert await svc.lessons.search("50%") == []
