from aiogram.types import User
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Column, Start
from aiogram_dialog.widgets.text import Const, Format
from sqlalchemy.ext.asyncio import AsyncSession

from db.requests import get_real_name
from .filters import is_admin
from fsm.fsm_dialogs import (
    StartState, StatsState, TaskState, QuestionnaireState
    )


async def username_getter(
        dialog_manager: DialogManager,
        event_from_user: User,
        session: AsyncSession,
        **kwargs
):
    real_name: str = await get_real_name(
        session, event_from_user.id
    )
    if real_name:
        getter_data = {
            'username': real_name,
            'first_show': False,
            'second_show': True,
            'user_id': event_from_user.id
            }
    else:
        getter_data = {
            'username': event_from_user.first_name or 'Stranger',
            'first_show': True,
            'second_show': False,
            'user_id': event_from_user.id
            }
    return getter_data

start_dialog = Dialog(
    Window(
        Format('<b>Приветствую, {username}</b>\n'),
        Const('Это тренировчный бот, в котором можно решать '
              'задачи по математике\n'),
        Const('Кажется вы здесь в первый раз. Пожалуйста, '
              'ответьте на пару вопросов себе\n'
              'перед тем, как продолжить.\nЭто нужно только для правильного '
              'отображения статистики у администратора\n'
              'Для этого нажмите на кнопку "Анкета"\n', when='first_show'),
        Column(
            Start(Const('Задачи'), id='tasks', state=TaskState.task,
                  when='second_show'),
            Start(Const('Анкета'), id='questionnaire',
                  state=QuestionnaireState.real_first_name),
            Start(Const('Статистика'), id='stats', state=StatsState.period,
                  when='second_show'),
            Start(Const('Статистика для администратора'), id='admin_stats',
                  state=StatsState.student,
                  when=is_admin),
        ),
        getter=username_getter,
        state=StartState.start
    )
)
