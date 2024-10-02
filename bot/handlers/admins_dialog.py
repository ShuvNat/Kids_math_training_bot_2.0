from aiogram import Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, StartMode, Window, setup_dialogs
from aiogram_dialog.widgets.text import Calendar, Format, List
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.fsm import FSMSolveTask
from keyboards import keyboard
from lexicon import LEXICON

admin_router = Router()
