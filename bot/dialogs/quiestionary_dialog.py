from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Row, Start
from aiogram_dialog.widgets.text import Const, Format

from db.requests import update_user
from fsm.fsm_dialogs import StartState, TaskState, QuestionnaireState


async def first_name_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager):
    if message.text.isalpha():
        dialog_manager.dialog_data["first_name"] = message.text
        print(dialog_manager.middleware_data)
        await dialog_manager.next()
    else:
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        await message.answer(text='Пожалуйста, напишите только имя')


async def last_name_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager):
    if message.text.isalpha():
        dialog_manager.dialog_data["last_name"] = message.text
        await dialog_manager.next()
    else:
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        await message.answer(text='Пожалуйста, напишите только фамилию')


async def class_handler(
        message: Message,
        widget: MessageInput,
        dialog_manager: DialogManager,
) -> None:
    if message.text.isdigit() and 0 <= int(message.text) <= 11:
        dialog_manager.dialog_data["class_number"] = message.text
        session = dialog_manager.middleware_data.get('session')
        await update_user(
            session, message.from_user.id,
            *dialog_manager.dialog_data.values()
            )
        await dialog_manager.next()
    else:
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        await message.answer(
            text='Пожалуйста, напишите только номер класса от 1 до 11\n'
                 'Или поставьте 0, если вы не учитесь в школе'
                 )


questionnaire_dialog = Dialog(
    Window(
        Const('Пожалуйста, ответьте всего на 3 вопроса'),
        Const('1. Напишите ваше настоящее имя'),
        Cancel(Const('Отмена'), id='cancel'),
        MessageInput(
            func=first_name_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireState.real_first_name,
    ),
    Window(
        Const('2. Напишите вашу фамилию'),
        Row(
            Cancel(Const('Отмена'), id='cancel'),
            Back(Const('Назад'), id='back'),
        ),
        MessageInput(
            func=last_name_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireState.real_last_name,
    ),
    Window(
        Const('3. Напишите в каком классе вы учитесь'),
        Const('Если вы не учитесь в школе, поставьте 0'),
        Row(
            Cancel(Const('Отмена'), id='cancel'),
            Back(Const('Назад'), id='back'),
        ),
        MessageInput(
            func=class_handler,
            content_types=ContentType.TEXT,
        ),
        state=QuestionnaireState.class_number,
    ),
    Window(
        Format('Спасибо, {dialog_data[first_name]} {dialog_data[last_name]}'),
        Const('Если вы указали что-то неправильно,\n'
              'или просто захотите обновить информацию,\n'
              'анкета всегда доступна в стартовом меню.\n'),
        Const('Теперь вы можете вернуться перейти к решению задач'),
        Start(Const('На старт'), id='start', state=StartState.start,
              mode=StartMode.RESET_STACK),
        Start(Const('Задачи'), id='tasks', state=TaskState.task),
        state=QuestionnaireState.save,
    ),
)
