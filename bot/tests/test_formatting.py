import pytest

from backnote.bot.dialogs.common import Field
from backnote.db.models import Lesson, Subject
from backnote.formatting import (
    normalize_url,
    progress_bar,
    split_text,
    subject_button,
    summary_markdown,
    youtube_id,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
        ("youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/playlist?list=PL123", None),
        ("https://vimeo.com/123", None),
        (None, None),
    ],
)
def test_youtube_id(url, expected):
    assert youtube_id(url) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.com/a", "https://example.com/a"),
        ("example.com", "https://example.com"),
        ("not a link", None),
        ("hello", None),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


def test_progress_bar():
    assert progress_bar(0, 0, 4) == "▱▱▱▱"
    assert progress_bar(1, 2, 4) == "▰▰▱▱"
    assert progress_bar(3, 3, 4) == "▰▰▰▰"


def test_subject_button_marks_finished():
    subject = Subject(title="Micro", year=1, term=3)
    assert subject_button(subject, 4, 2) == "[Y1T3] Micro · 2/4"
    assert subject_button(subject, 4, 4) == "[Y1T3] Micro · done ✓"


def test_split_text_respects_limit():
    text = "\n\n".join("x" * 900 for _ in range(10))
    chunks = split_text(text, 4000)
    assert all(len(c) <= 4000 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_summary_markdown_escapes_titles():
    lesson = Lesson(number=2, kind="lecture", title="Costs *and* [profit]", summary="## Body")
    md = summary_markdown(lesson, Subject(title="Micro_1"), source_line="Written")
    assert "# 🎓 Lecture 2 · Costs \\*and\\* \\[profit\\]" in md
    assert "*Micro\\_1*" in md
    assert md.rstrip().endswith("_Written_")
    assert "## Body" in md


def test_field_parse():
    assert Field("n", "N", "", "int", min_value=0, max_value=10).parse(" 7 ") == 7
    with pytest.raises(ValueError):
        Field("n", "N", "", "int", max_value=10).parse("11")
    assert Field("u", "U", "", "url").parse("kse.ua") == "https://kse.ua"
    with pytest.raises(ValueError):
        Field("t", "T", "", max_len=3).parse("long")


async def test_dynamic_preview():
    from backnote.bot.dialogs.common import DynamicPreview

    widget = DynamicPreview()
    shown = await widget._render_link_preview({"preview_url": "https://youtu.be/x"}, None)
    assert shown.url == "https://youtu.be/x" and shown.prefer_large_media and shown.show_above_text
    hidden = await widget._render_link_preview({"preview_url": None}, None)
    assert hidden.is_disabled
