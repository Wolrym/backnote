from aiogram_dialog import Dialog

from backnote.bot.dialogs.admin import admin_dialog
from backnote.bot.dialogs.lessons import lesson_create_dialog, lessons_dialog
from backnote.bot.dialogs.main_menu import main_dialog
from backnote.bot.dialogs.materials import materials_dialog
from backnote.bot.dialogs.search import search_dialog
from backnote.bot.dialogs.subjects import subject_create_dialog, subjects_dialog
from backnote.bot.dialogs.summary import summary_dialog
from backnote.bot.dialogs.tasks import tasks_dialog


def all_dialogs() -> list[Dialog]:
    return [
        main_dialog(),
        search_dialog(),
        subjects_dialog(),
        subject_create_dialog(),
        lessons_dialog(),
        lesson_create_dialog(),
        summary_dialog(),
        materials_dialog(),
        tasks_dialog(),
        admin_dialog(),
    ]
