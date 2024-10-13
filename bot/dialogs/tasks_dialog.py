from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message, User
from aiogram_dialog import Dialog, DialogManager, ShowMode, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Group, Row, Select, Start
from aiogram_dialog.widgets.text import Case, Const, Format
from operator import itemgetter

from db.requests import add_or_update_task
from fsm.fsm_dialogs import StartState, TaskState
from .filters import is_admin
from tasks import Tasks


async def tasks_getter(
    dialog_manager: DialogManager,
    **kwargs
):
    tasks = [
        ['scales_and_fruis', 'Взвешивание фруктов'],
        ['fruit_picking', 'Сбор фруктов'],
        ['linear_equasion', 'Уравнение'],
        ['area_and_perimeter', 'Площадь и периметр'],
        ['random_task', 'Случайная']
    ]
    if not dialog_manager.dialog_data.get('again'):
        return {'tasks': tasks, 'number': 1}
    else:
        return {'tasks': tasks, 'number': 2}


async def on_task_clicked(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_item: str,
):
    task = Tasks()
    func = getattr(task, selected_item)
    func()
    dialog_manager.dialog_data['question'] = task.question
    dialog_manager.dialog_data['answer'] = task.answer
    dialog_manager.dialog_data['task_type'] = task.name
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
        await add_or_update_task(session, message.from_user.id,
                                 task_type, mistakes)
        await dialog_manager.back()
    else:
        mistakes += 1
        dialog_manager.dialog_data['mistakes'] = mistakes
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        await message.answer(text='Неправильно. Попробуйте еще раз.')


async def is_admin_getter(
        dialog_manager: DialogManager,
        event_from_user: User,
        **kwargs):
    return {'user_id': event_from_user.id}

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
            Select(
                Format("{item[1]}"),
                id="select_task",
                items="tasks",
                item_id_getter=itemgetter(0),
                on_click=on_task_clicked
            ),
            width=2
        ),
        Row(
            Start(Const('На старт'),
                  id='start',
                  state=StartState.start,
                  mode=StartMode.RESET_STACK),
            ),
        getter=tasks_getter,
        state=TaskState.task,
    ),
    Window(
        Format('{dialog_data[question]}'),
        Format('Ответ: {dialog_data[answer]}', when=is_admin),
        MessageInput(
            func=answer_handler,
            content_types=ContentType.TEXT,
        ),
        Back(Const('Сдаться'), id='back'),
        getter=is_admin_getter,
        state=TaskState.answer,
    ),
)
