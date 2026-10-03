from aiogram.filters.callback_data import CallbackData


class AccessCb(CallbackData, prefix="acc"):
    action: str  # "allow" | "block"
    user_id: int


class OpenCb(CallbackData, prefix="open"):
    target: str  # "lesson" | "summary"
    id: int
