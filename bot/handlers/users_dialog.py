from datetime import date
from dateutil.relativedelta import relativedelta

from aiogram import Router
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, User
from aiogram_dialog import ChatEvent, Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Button, Calendar, Column, Group, ManagedCalendar, Row, Start, SwitchTo
from aiogram_dialog.widgets.text import Case, Const, Format
from sqlalchemy.ext.asyncio import AsyncSession

from db.requests import get_daily_results, get_interval_results, get_real_name, add_or_update_task, add_user, update_user
from fsm.fsm_user_dialogs import StartUD, StatsUD, TaskUD, QuestionnaireUD
from tasks import Tasks
from utils import str_date


user_router = Router()


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
        getter_data = {'username': real_name, 'first_show': False}
    else:
        getter_data = {'username': event_from_user.first_name or 'Stranger', 'first_show': True}
    return getter_data

start_dialog = Dialog(
    Window(
        Format('<b>Приветствую, {username}</b>\n'),
        Const('Это тренировчный бот, в котором можно решать задачи по математике\n'),
        Const('Кажется вы здесь в первый раз. Пожалуйста, ответьте на пару вопросов себе\n'
              'перед тем, как продолжить.\nЭто нужно для правильного отображения статистики\n'
              'Для этого нажмите на кнопку "Анкета"\n', when='first_show'),
        Column(
            Start(Const('Задачи'), id='tasks', state=TaskUD.task),
            Start(Const('Анкета'), id='questionnaire', state=QuestionnaireUD.real_first_name),
            Start(Const('Статистика'), id='stats', state=StatsUD.choice),
        ),
        getter=username_getter,
        state=StartUD.start
    )
)


async def first_name_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager):
    if message.text.isalpha():
        dialog_manager.dialog_data["first_name"] = message.text
        print(dialog_manager.middleware_data)
        await dialog_manager.next()
    else:
        await message.answer(text='Пожалуйста, напишите только имя')


async def last_name_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager):
    if message.text.isalpha():
        dialog_manager.dialog_data["last_name"] = message.text
        await dialog_manager.next()
    else:
        await message.answer(text='Пожалуйста, напишите только фамилию')


async def class_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager,
) -> None:
    if message.text.isdigit() and 0 <= int(message.text) <= 11:
        dialog_manager.dialog_data["class_number"] = message.text
        session = dialog_manager.middleware_data.get('session')
        await update_user(session, message.from_user.id, *dialog_manager.dialog_data.values())
        await dialog_manager.next()
    else:
        await message.answer(text='Пожалуйста, напишите только номер класса от 1 до 11\n'
                                  'Или поставьте 0, если вы не учитесь в школе')


questionnaire_dialog = Dialog(
    Window(
        Const('Пожалуйста, ответьте всего на 3 вопроса'),
        Const('1. Напишите ваше настоящее имя'),
        MessageInput(
            func=first_name_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireUD.real_first_name,
    ),
    Window(
        Const('2. Напишите вашу фамилию'),
        MessageInput(
            func=last_name_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireUD.real_last_name,
    ),
    Window(
        Const('3. Напишите в каком классе вы учитесь'),
        Const('Если вы не учитесь в школе, поставьте 0'),
        MessageInput(
            func=class_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireUD.class_number,
    ),
    Window(
        Format('Спасибо, {dialog_data[first_name]} {dialog_data[last_name]}'),
        Const('В стартовом окне эта анкета больше не появится\n'
              'Если вы указали что-то неправильно,\n'
              'или просто захотите обновить информацию,\n'
              'воспользуйтесь меню бота'),
        Const('Теперь вы можете вернуться на старт\n'
              'Или перейти к решению задач\n'),
        Row(
            Start(Const('На старт'), id='start', state=StartUD.start, mode=StartMode.RESET_STACK),
            Start(Const('Задачи'), id='tasks', state=TaskUD.task),
        ),
        state=QuestionnaireUD.save,
    ),
)


async def get_task(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    task = Tasks()
    func = getattr(task, button.widget_id)
    func()
    dialog_manager.dialog_data['question'] = task.question
    dialog_manager.dialog_data['answer'] = task.answer
    dialog_manager.dialog_data['task_type'] = task.name
    print(task.answer)
    await dialog_manager.next()


async def answer_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager,
):
    correct_answer = dialog_manager.dialog_data.get('answer')
    task_type = dialog_manager.dialog_data.get('task_type')
    user_answer = message.text
    mistakes = dialog_manager.dialog_data.get('mistakes', 0)
    if user_answer.isdigit() and int(user_answer) == correct_answer:
        dialog_manager.dialog_data['again'] = True
        session = dialog_manager.middleware_data.get('session')
        await add_or_update_task(session, message.from_user.id, task_type, mistakes)
        await dialog_manager.back()
    else:
        mistakes += 1
        dialog_manager.dialog_data['mistakes'] = mistakes
        await message.answer(text='Неправильно. Попробуйте еще раз.')


async def get_text_task(dialog_manager: DialogManager, **kwargs):
    if not dialog_manager.dialog_data.get('again'):
        return {'number': 1}
    else:
        return {'number': 2}

task_dialog = Dialog(
    Window(
        Case(
            texts={
                1: Const('Пожалуйста, выберите задачу'),
                2: Const('Правильно! Молодец!\n'
                         'Может быть еще одну?'),
            },
            selector='number',
        ),
        Group(
            Column(
                Button(Const("Взвешивание фруктов"), id="scales_and_fruis", on_click=get_task),
                Button(Const("Сбор фруктов"), id="fruit_picking", on_click=get_task),
                Button(Const("Уравнение"), id="linear_equasion", on_click=get_task),
                Button(Const("Площадь и периметр"), id="area_and_perimeter", on_click=get_task),
                Button(Const("Случайная"), id="area_and_perimeter", on_click=get_task),
            ),
            width=2
        ),
        Row(
            Start(Const('На старт'), id='start', state=StartUD.start, mode=StartMode.RESET_STACK),
            ),
        getter=get_text_task,
        state=TaskUD.task,
    ),
    Window(
        Format('{dialog_data[question]}'),
        MessageInput(
            func=answer_handler,
            content_types=ContentType.TEXT,
        ),
        Back(Const('Сдаться'), id='back'),
        state=TaskUD.answer,
    ),
)


async def on_date_clicked(
    callback: ChatEvent,
    widget: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: date, /,
):
    dialog_manager.dialog_data['selected_date'] = selected_date
    dialog_manager.dialog_data['function'] = get_daily_results
    await call_database(dialog_manager)
    await dialog_manager.back()


async def get_stats(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    if button.widget_id == 'today':
        selected_date = date.today()
        dialog_manager.dialog_data['function'] = get_daily_results
    elif button.widget_id == 'week':
        selected_date = date.today() - relativedelta(weeks=1)
        dialog_manager.dialog_data['function'] = get_interval_results
    else:
        selected_date = date.today() - relativedelta(months=1)
        dialog_manager.dialog_data['function'] = get_interval_results
    dialog_manager.dialog_data['selected_date'] = selected_date
    await call_database(dialog_manager)
    await dialog_manager.next()


async def call_database(dialog_manager: DialogManager):
    session = dialog_manager.middleware_data.get('session')
    user_id = dialog_manager.event.from_user.id
    function = dialog_manager.dialog_data['function']
    selected_date = dialog_manager.dialog_data['selected_date']
    task_record = await function(session, user_id, selected_date)
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['start_date'] = str_date(selected_date)
    dialog_manager.dialog_data['end_date'] = str_date(date.today())
    dialog_manager.dialog_data['func_name'] = function.__name__
    if task_record:
        dialog_manager.dialog_data['total'] = task_record.total
        dialog_manager.dialog_data['scales_and_fruis'] = task_record.scales_and_fruis
        dialog_manager.dialog_data['fruit_picking'] = task_record.fruit_picking
        dialog_manager.dialog_data['linear_equasion'] = task_record.linear_equasion
        dialog_manager.dialog_data['area_and_perimeter'] = task_record.area_and_perimeter
        dialog_manager.dialog_data['mistakes'] = task_record.mistakes


async def get_text_stats(dialog_manager: DialogManager, **kwargs):
    if not dialog_manager.dialog_data.get('total'):
        return {'text': 1}
    else:
        return {'text': 2}


async def get_date_stats(dialog_manager: DialogManager, **kwargs):
    if dialog_manager.dialog_data['func_name'] == 'get_daily_results':
        return {'date': 1}
    else:
        return {'date': 2}


stats_dialog = Dialog(
    Window(
        Const('За какой период вы хотите посмотреть статистику?'),
        Group(
            Column(
                Button(Const("За сегодня"), id="today", on_click=get_stats),
                SwitchTo(Const("За другой день"), id="any_day", state=StatsUD.calendar),
                Button(Const("За неделю"), id="week", on_click=get_stats),
                Button(Const("За месяц"), id="month", on_click=get_stats),
                ),
            width=2,
        ),
        Row(
            Start(Const('На старт'), id='start', state=StartUD.start, mode=StartMode.RESET_STACK),
        ),
        state=StatsUD.choice,
    ),
    Window(
        Case(
            texts={
                1: Format('{dialog_data[start_date]}\n'),
                2: Format('В период с {dialog_data[start_date]} по '
                          '{dialog_data[end_date]}\n'),
            },
            selector='date'
        ),
        Case(
            texts={
                1: Const('Hе было решено ни одной задачи\n'
                         'Может быть стоит решить парочку?'),
                2: Format('Всего решено задач: {dialog_data[total]}\n\n'
                          'Из них\n'
                          'Взвешивание фруктов: {dialog_data[scales_and_fruis]}\n'
                          'Сбор фруктов: {dialog_data[fruit_picking]}\n'
                          'Линейных уравнений: {dialog_data[linear_equasion]}\n'
                          'Площадь и периметр: {dialog_data[area_and_perimeter]}\n\n'
                          'Сделано ошибок: {dialog_data[mistakes]}\n')
            },
            selector='text',
        ),
        Column(
            Back(Const('Другая статистика'), id='stats'),
            Start(Const('На старт'), id='start', state=StartUD.start, mode=StartMode.RESET_STACK),
            Start(Const('Задачи'), id='tasks', state=TaskUD.task),
            ),
        getter=(get_text_stats, get_date_stats),
        state=StatsUD.stats,
    ),
    Window(
        Const('Выберите день, за который хотите увидеть статистику'),
        Calendar(
            id="pick_any_day",
            on_click=on_date_clicked,
        ),
        state=StatsUD.calendar,
    ))


@user_router.message(CommandStart())
async def command_start_process(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(
        state=StartUD.start,
        mode=StartMode.RESET_STACK,
    )


@user_router.message(Command('questionary'))
async def command_questionary_process(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(
        state=QuestionnaireUD.real_first_name,
    )
