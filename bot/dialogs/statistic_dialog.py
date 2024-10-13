from dataclasses import dataclass
from datetime import date
from operator import itemgetter
from typing import Callable

from aiogram.types import CallbackQuery, User
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import (
    Back, Calendar, Cancel, Column, CurrentPage, FirstPage, Group,
    LastPage, ManagedCalendar, NumberedPager, NextPage, PrevPage,
    Row, ScrollingGroup, Start, Select, SwitchTo
    )
from aiogram_dialog.widgets.text import Case, Const, Format
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from db.requests import (
    get_daily_results, get_full_real_name, get_interval_results
    )
from .filters import is_admin
from fsm.fsm_dialogs import StartState, StatsState, TaskState
from .utils import str_date


@dataclass
class DateChoise:
    id: str
    name: str
    start_date: date
    function: Callable


DATECHOICE_LIST = [
            DateChoise(
                'today',
                'За сегодня',
                date.today(),
                get_daily_results,
            ),
            DateChoise(
                'week',
                'За неделю',
                date.today() - relativedelta(weeks=1),
                get_interval_results,
            ),
            DateChoise(
                'month',
                'За месяц',
                date.today() - relativedelta(months=1),
                get_interval_results,
            )
        ]


async def name_getter(
    dialog_manager: DialogManager,
    event_from_user: User,
    session: AsyncSession,
    **kwargs
):
    real_names = await get_full_real_name(session)
    students = []
    for real_name in real_names:
        students.append([f'{real_name[1]} {real_name[0]}', real_name[2]])
    getter_data = {'students': students}
    return getter_data


async def on_name_clicked(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_item: str,
):
    dialog_manager.dialog_data['user_id'] = int(selected_item)
    await dialog_manager.next()


async def date_getter(dialog_manager: DialogManager,
                      event_from_user: User,
                      **kwargs):
    getter_data = {'datechoice_list': DATECHOICE_LIST,
                   'user_id': event_from_user.id}
    return getter_data


async def on_datechoice_clicked(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_item: str,
):
    datechoice = next((
            choice for choice in DATECHOICE_LIST if choice.id == selected_item
        ), None)
    dialog_manager.dialog_data['datechoice'] = datechoice
    await dialog_manager.next()


async def on_date_clicked(
    callback: CallbackQuery,
    widget: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: date, /,
):
    datechoice = DateChoise(
        'any_day',
        'За другой день',
        selected_date,
        get_daily_results,
    )
    dialog_manager.dialog_data['datechoice'] = datechoice
    await dialog_manager.back()


async def stats_getter(
        dialog_manager: DialogManager,
        event_from_user: User,
        session: AsyncSession,
        **kwargs):
    try:
        user_id = dialog_manager.dialog_data['user_id']
    except KeyError:
        user_id = dialog_manager.event.from_user.id
    datechoice = dialog_manager.dialog_data['datechoice']
    selected_date = datechoice.start_date
    func = datechoice.function
    task_record = await func(session, user_id, selected_date)
    # если не очистить это поле, будет ошибка сериализации json
    dialog_manager.dialog_data['datechoice'] = None
    if task_record and task_record.total is not None:
        data = {
            'total': task_record.total,
            'scales_and_fruis': task_record.scales_and_fruis,
            'fruit_picking': task_record.fruit_picking,
            'linear_equasion': task_record.linear_equasion,
            'area_and_perimeter': task_record.area_and_perimeter,
            'mistakes': task_record.mistakes,
            'start_date': str_date(selected_date),
            'end_date': str_date(date.today()),
            'text': 2,
            'date': func.__name__ == 'get_daily_results'
        }
    else:
        data = {
            'start_date': str_date(selected_date),
            'end_date': str_date(date.today()),
            'text': 1,
            'date': func.__name__ == 'get_daily_results'
            }
    return data


stats_dialog = Dialog(
    Window(
        Const('По какому ученику вы хотите посмотреть статистику?'),
        NumberedPager(
            scroll="scroll_no_pager",
            page_text=Format("{target_page1}\uFE0F\u20E3"),
            current_page_text=Format("{current_page1}"),
        ),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),
                id="select_student",
                items="students",
                item_id_getter=itemgetter(1),
                on_click=on_name_clicked
            ),
            width=1,
            height=5,
            hide_pager=True,
            id="scroll_no_pager",
        ),
        Row(
            FirstPage(
                scroll="scroll_no_pager", text=Format("⏮️ {target_page1}"),
            ),
            PrevPage(
                scroll="scroll_no_pager", text=Format("◀️"),
            ),
            CurrentPage(
                scroll="scroll_no_pager", text=Format("{current_page1}"),
            ),
            NextPage(
                scroll="scroll_no_pager", text=Format("▶️"),
            ),
            LastPage(
                scroll="scroll_no_pager", text=Format("{target_page1} ⏭️"),
            ),
        ),
        Cancel(Const('Отмена'), id='cancel'),
        getter=name_getter,
        state=StatsState.student,
        ),
    Window(
        Const('За какой период вы хотите посмотреть статистику?'),
        Group(
            Row(
                Select(
                    Format("{item.name}"),
                    id="datechoice_id",
                    items="datechoice_list",
                    item_id_getter=lambda x: x.id,
                    on_click=on_datechoice_clicked
                ),
                SwitchTo(Const('За другой день'), id='calendar',
                         state=StatsState.calendar),
            ),
            width=2,
        ),
        Back(Const('Назад'), id='back', when=is_admin),
        Start(Const('На старт'), id='start', state=StartState.start,
              mode=StartMode.RESET_STACK),
        getter=date_getter,
        state=StatsState.period,
    ),
    Window(
        Case(
            texts={
                True: Format('{start_date}\n'),
                False: Format('В период с {start_date} по '
                              '{end_date}\n'),
            },
            selector='date'
        ),
        Case(
            texts={
                1: Const('Hе было решено ни одной задачи\n'
                         'Может быть стоит решить парочку?'),
                2: Format(
                    'Всего решено задач: {total}\n\n'
                    'Из них\n'
                    'Взвешивание фруктов: {scales_and_fruis}\n'
                    'Сбор фруктов: {fruit_picking}\n'
                    'Линейных уравнений: {linear_equasion}\n'
                    'Площадь и периметр: {area_and_perimeter}\n\n'
                    'Сделано ошибок: {mistakes}\n'
                    )
            },
            selector='text',
        ),
        Column(
            SwitchTo(Const('Статистика за другой период'), id='stats',
                     state=StatsState.period),
            Start(Const('На старт'), id='start', state=StartState.start,
                  mode=StartMode.RESET_STACK),
            Start(Const('Задачи'), id='tasks', state=TaskState.task),
            ),
        getter=stats_getter,
        state=StatsState.stats,
    ),
    Window(
        Const('Выберите день, за который хотите увидеть статистику'),
        Calendar(
            id="pick_any_day",
            on_click=on_date_clicked,
        ),
        state=StatsState.calendar,
    ))
