from dataclasses import dataclass
from datetime import date
from operator import itemgetter
from pathlib import Path
from typing import Callable

from aiogram.types import CallbackQuery, FSInputFile, User
from aiogram_dialog import Dialog, DialogManager, ShowMode, StartMode, Window
from aiogram_dialog.widgets.kbd import (
    Back, Calendar, Cancel, Column, CurrentPage, FirstPage, Group,
    LastPage, ManagedCalendar, NumberedPager, Next, NextPage, PrevPage,
    Row, ScrollingGroup, Start, Select, SwitchTo
    )
from aiogram_dialog.widgets.text import Case, Const, Format
from dateutil.relativedelta import relativedelta
import pandas
from sqlalchemy.ext.asyncio import AsyncSession

from db.requests import (
    get_daily_results, get_full_real_name, get_interval_results,
    xlsx_all_results, xlsx_interval_results
    )
from .filters import is_admin
from fsm.fsm_dialogs import StartState, StatsState, TaskState
from .utils import str_date

FILEPATH = Path(__file__).resolve().parent.parent


@dataclass
class DateChoise:
    id: str
    name: str
    start_date: date
    function: Callable


DAY = DateChoise(
    'today',
    'За сегодня',
    date.today(),
    get_daily_results,
)
WEEK = DateChoise(
    'week',
    'За неделю',
    date.today() - relativedelta(weeks=1),
    get_interval_results,
)
MONTH = DateChoise(
    'month',
    'За месяц',
    date.today() - relativedelta(months=1),
    get_interval_results,
)
MONTH_XSLX = DateChoise(
    'month_xslx',
    'За месяц',
    date.today() - relativedelta(months=1),
    xlsx_interval_results,
)
ALL_XLSX = DateChoise(
    'all',
    'За все время',
    None,
    xlsx_all_results,
)

DATECHOICE_LIST = [DAY, WEEK, MONTH]
XLSX_DATECHOICE_LIST = [MONTH_XSLX, ALL_XLSX]


async def name_getter(
    dialog_manager: DialogManager,
    event_from_user: User,
    session: AsyncSession,
    **kwargs
):
    real_names = await get_full_real_name(session)
    students = []
    for real_name in real_names:
        if real_name[1] is not None:
            students.append([f'{real_name[1]} {real_name[0]}', real_name[4]])
        else:
            students.append([f'{real_name[3]} {real_name[2]}', real_name[4]])
    dialog_manager.dialog_data['students'] = students
    getter_data = {'students': students}
    return getter_data


async def on_name_clicked(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_item: str,
):
    students = dialog_manager.dialog_data['students']
    name = next((
            student[0] for student in students if str(
                student[1]) == selected_item
        ), None)
    dialog_manager.dialog_data['name'] = name
    dialog_manager.dialog_data['user_id'] = int(selected_item)
    await dialog_manager.next()


async def xlsx_getter(dialog_manager: DialogManager,
                      event_from_user: User,
                      **kwargs):
    getter_data = {'xlsx_datechoice_list': XLSX_DATECHOICE_LIST}
    return getter_data


async def on_xlsx_datechoice_clicked(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_item: str,
):
    datechoice = next((
            choice for choice in XLSX_DATECHOICE_LIST if choice.id == selected_item
        ), None)
    session = dialog_manager.middleware_data['session']
    try:
        user_id = dialog_manager.dialog_data['user_id']
        name = dialog_manager.dialog_data['name']
    except KeyError:
        await callback.message.answer(
            text='Вы не выбрали пользователя, по которому '
                 'хотите получить статистику'
        )
        await dialog_manager.switch_to(
            StatsState.student, show_mode=ShowMode.SEND
            )
        return
    selected_date = datechoice.start_date
    func = datechoice.function
    task_record = await func(session, user_id, selected_date)
    # если не очистить это поле, будет ошибка сериализации json
    dialog_manager.dialog_data['datechoice'] = None
    if task_record:
        filename = (f'{date.today()} - {name}.xlsx')
        filepath = FILEPATH / f'statistic_files/{filename}'
        df = pandas.DataFrame(task_record, columns=[
            'Дата',
            'Взвешивание фруктов',
            'Сбор фруктов',
            'Уравнения',
            'Площадь и периметр',
            'Всего',
            'Количество ошибок'
            ])
        df.to_excel(filepath, index=False)
        with pandas.ExcelWriter(
            filepath, engine='openpyxl', mode='a'
        ) as writer:
            worksheet = writer.sheets['Sheet1']
            worksheet.title = 'Лист1'

            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[
                    column_cells[0].column_letter].width = length + 2
        await callback.message.answer_document(
                FSInputFile(filepath, filename=filename)
            )
        filepath.unlink()
    else:
        await callback.message.answer(
            text=f'Нет данных по пользователю {name} '
                 f'за этот период.'
                )
    await dialog_manager.next(show_mode=ShowMode.SEND)


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
        Const('В каком формате вы хотите получить статистику?'),
        SwitchTo(Const('Вывести на экран'), id='on_screen',
                 state=StatsState.period),
        Next(Const('Скачать в файл'), id='to_xslx'),
        Group(
            Row(
                Back(Const('Назад'), id='back'),
                Cancel(Const('Отмена'), id='cancel'),
            ),
            width=2,
        ),
        state=StatsState.format,
    ),
    Window(
        Const('За какой период вы хотите посмотреть статистику?'),
        Select(
            Format("{item.name}"),
            id="xlsx_datechoice_id",
            items="xlsx_datechoice_list",
            item_id_getter=lambda x: x.id,
            on_click=on_xlsx_datechoice_clicked
                ),
        Group(
            Row(
                Back(Const('Назад'), id='back'),
                Cancel(Const('Отмена'), id='cancel'),
            ),
            width=2,
        ),
        getter=xlsx_getter,
        state=StatsState.xlsx,
    ),
    Window(
        Const('Что дальше?'),
        Group(
            Column(
                SwitchTo(Const('Другой человек'), id='another_preson',
                         state=StatsState.student),
                SwitchTo(Const('Другой период'), id='another_period',
                         state=StatsState.xlsx),
                SwitchTo(Const('Другой формат'), id='another_format',
                         state=StatsState.format),
                Start(Const('На старт'), id='start', state=StartState.start,
                      mode=StartMode.RESET_STACK),
            ),
            width=2
        ),
        state=StatsState.what_next,
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
        SwitchTo(Const('Статистика в файле'), id='file_stats',
                 state=StatsState.xlsx, when=is_admin),
        SwitchTo(Const('Статистика по другому человеку'), id='another_preson',
                 state=StatsState.student, when=is_admin),
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
    ),
)
