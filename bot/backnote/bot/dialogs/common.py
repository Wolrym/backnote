"""Shared helpers and widgets for dialogs."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.enums import ButtonStyle
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from aiogram_dialog import DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, SwitchTo
from aiogram_dialog.widgets.link_preview import LinkPreviewBase
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Const, Format

from backnote.ai import GeminiSummarizer
from backnote.bot.notifier import Notifier
from backnote.config import Settings
from backnote.formatting import h, normalize_url
from backnote.services import Services

PRIMARY = Style(ButtonStyle.PRIMARY)
SUCCESS = Style(ButtonStyle.SUCCESS)
DANGER = Style(ButtonStyle.DANGER)

BACK = Const("⬅️ Back")
CANCEL = Const("✖️ Cancel")


def svc(m: DialogManager) -> Services:
    return m.middleware_data["svc"]


def settings(m: DialogManager) -> Settings:
    return m.middleware_data["settings"]


def notifier(m: DialogManager) -> Notifier:
    return m.middleware_data["notifier"]


def summarizer(m: DialogManager) -> GeminiSummarizer | None:
    return m.middleware_data.get("summarizer")


def uid(m: DialogManager) -> int:
    return m.event.from_user.id


def is_admin(m: DialogManager) -> bool:
    return uid(m) == settings(m).admin_id


def can_delete(m: DialogManager, created_by: int | None) -> bool:
    return is_admin(m) or created_by == uid(m)


def deep_link(m: DialogManager, payload: str) -> str:
    return f"https://t.me/{m.middleware_data.get('bot_username', 'bot')}?start={payload}"


def data_id(m: DialogManager, key: str) -> int | None:
    value = m.dialog_data.get(key)
    return int(value) if value is not None else None


async def copy_start_data(start_data: Any, manager: DialogManager) -> None:
    if isinstance(start_data, dict):
        manager.dialog_data.update(start_data)


class DynamicPreview(LinkPreviewBase):
    """Shows a large preview for `preview_url` (e.g. a YouTube lecture) or disables previews."""

    async def _render_link_preview(self, data: dict, manager: DialogManager):
        url = data.get("preview_url")
        if not url:
            return LinkPreviewOptions(is_disabled=True)
        return LinkPreviewOptions(url=url, prefer_large_media=True, show_above_text=True)


# ---------------------------------------------------------------------------
# Generic single-field editor: a window asks for one value and stores it.


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    prompt: str
    kind: str = "text"  # text | longtext | int | url
    optional: bool = True
    max_len: int = 256
    min_value: int | None = None
    max_value: int | None = None

    def parse(self, raw: str) -> Any:
        raw = raw.strip()
        if not raw:
            raise ValueError("The value cannot be empty.")
        if self.kind == "int":
            if not raw.lstrip("-").isdigit():
                raise ValueError("Please send a whole number.")
            value = int(raw)
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"The number must be at least {self.min_value}.")
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"The number must be at most {self.max_value}.")
            return value
        if self.kind == "url":
            url = normalize_url(raw)
            if not url:
                raise ValueError("That doesn't look like a link. Example: https://example.com")
            return url
        limit = 4000 if self.kind == "longtext" else self.max_len
        if len(raw) > limit:
            raise ValueError(f"Too long: {len(raw)} characters, the limit is {limit}.")
        return raw

    def show(self, value: Any) -> str:
        if value is None or value == "":
            return "<i>not set</i>"
        if self.kind == "longtext":
            return f"<blockquote expandable>{h(value)}</blockquote>"
        return f"<code>{h(value)}</code>" if self.kind == "url" else f"<b>{h(value)}</b>"


SaveField = Callable[[DialogManager, str, Any], Awaitable[None]]
LoadField = Callable[[DialogManager, str], Awaitable[Any]]


def field_editor_window(
    state,
    back_state,
    fields: dict[str, Field],
    load: LoadField,
    save: SaveField,
) -> Window:
    """Window that edits `dialog_data["field"]` from `fields` and returns to `back_state`."""

    async def getter(dialog_manager: DialogManager, **_):
        field = fields[dialog_manager.dialog_data["field"]]
        current = await load(dialog_manager, field.key)
        return {
            "text": (
                f"✏️ <b>{h(field.label)}</b>\n\nCurrent: {field.show(current)}\n\n"
                f"<i>{h(field.prompt)}</i>"
            ),
            "optional": field.optional and current not in (None, ""),
        }

    async def on_input(message: Message, _w, manager: DialogManager) -> None:
        field = fields[manager.dialog_data["field"]]
        try:
            value = field.parse(message.text or "")
        except ValueError as exc:
            await message.answer(f"⚠️ {h(exc)}")
            return
        await save(manager, field.key, value)
        await manager.switch_to(back_state)

    async def on_clear(_c: CallbackQuery, _b, manager: DialogManager) -> None:
        await save(manager, manager.dialog_data["field"], None)
        await manager.switch_to(back_state)

    return Window(
        Format("{text}"),
        MessageInput(on_input, content_types=["text"]),
        Button(Const("🧹 Clear"), id="clear", on_click=on_clear, when="optional"),
        SwitchTo(BACK, id="back", state=back_state),
        state=state,
        getter=getter,
    )


def field_buttons(fields: dict[str, Field], edit_state, *, when=None) -> Group:
    async def pick(_c: CallbackQuery, button: Button, manager: DialogManager) -> None:
        manager.dialog_data["field"] = button.widget_id.removeprefix("f_")
        await manager.switch_to(edit_state)

    return Group(
        *[Button(Const(f.label), id=f"f_{f.key}", on_click=pick) for f in fields.values()],
        width=2,
        when=when,
    )


def resend(manager: DialogManager) -> None:
    """Re-render the dialog as a new message below something we just sent."""
    manager.show_mode = ShowMode.SEND
