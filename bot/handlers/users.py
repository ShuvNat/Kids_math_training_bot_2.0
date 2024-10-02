from aiogram import Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.requests import add_or_update_task, get_daily_results, get_weekly_results
from bot.fsm.fsm import FSMSolveTask
from keyboards import keyboard
from lexicon import LEXICON
from tasks import Tasks

user_router = Router()


# обработчик команды start
@user_router.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: Message):
    await message.answer(text=LEXICON['/start'])


# обработчик команды task в основном режиме выдает клавиатуру в выбором задачи
@user_router.message(Command(commands='task'), StateFilter(default_state))
async def cmd_task(message: Message):
    await message.answer(
        text=LEXICON['/task'],
        reply_markup=keyboard
    )


# обработчик команды task в режиме решения
@user_router.callback_query(~StateFilter(default_state))
async def get_task_state(callback: CallbackQuery):
    await callback.message.answer(text=LEXICON['/task_state'])
    await callback.answer()


# обработчик команды cancel в основном режиме
@user_router.message(Command('cancel'), StateFilter(default_state))
async def cmd_cancel(message: Message):
    await message.answer(text=LEXICON['/cancel'],
                         reply_markup=keyboard)


# обработчик команды calcel в режиме задачи
@user_router.message(Command('cancel'), StateFilter(FSMSolveTask.get_answer))
async def cmd_cancel_state(message: Message, state: FSMContext):
    await message.answer(text=LEXICON['/cancel_state'],
                         reply_markup=keyboard)
    await state.clear()


# обработчик команды repeat в основном режиме
@user_router.message(Command('repeat'), StateFilter(default_state))
async def cmd_repeat(message: Message):
    await message.answer(text=LEXICON['/repeat'],
                         reply_markup=keyboard)


# обработчик команды repeat в режиме задачи
@user_router.message(Command('repeat'), StateFilter(FSMSolveTask.get_answer))
async def cmd_repeat_state(message: Message, state: FSMContext):
    data = await state.get_data()
    question = data.get('question')
    await message.answer(text=f'{question}')


# обработчик выдающий задачу
@user_router.callback_query(StateFilter(default_state))
async def get_task(callback: CallbackQuery, state: FSMContext):
    task = Tasks()
    func = getattr(task, callback.data)
    func()
    await state.update_data(
        question=task.question, answer=task.answer, task_type=task.name
    )
    await callback.message.answer(
            text=f'{task.question}'
        )
    await state.set_state(FSMSolveTask.get_answer)
    await callback.answer()


# обработчик проверяющий ответ и отправляющий результат в бд
@user_router.message(StateFilter(FSMSolveTask.get_answer))
async def check_answer(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    correct_answer = data.get('answer')
    task_type = data.get('task_type')
    user_answer = message.text
    mistakes = data.get('mistakes', 0)

    if user_answer.isdigit() and int(user_answer) == correct_answer:
        await add_or_update_task(session, message.from_user.id, task_type, mistakes)
        await message.answer(text=LEXICON['right'])
        await message.answer(text=LEXICON['one_more'],
                             reply_markup=keyboard)
        await state.clear()
    else:
        mistakes += 1
        await state.update_data(mistakes=mistakes)
        if mistakes <= 3:
            await message.answer(text=LEXICON['wrong'])
        else:
            await message.answer(text=LEXICON['wrong_3'])


# обработчик выдающий статистику за текущий день
@user_router.message(Command('stats_daily'))
async def cmd_daily_stats(
    message: Message,
    session: AsyncSession,
):
    task_record: int = await get_daily_results(
        session, message.from_user.id
    )
    if not task_record:
        await message.answer(text=LEXICON['no_stats'],
                             reply_markup=keyboard)
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n"
            f"Сегодня решено задач: {task_record.total}\n\n"
            f'Из них\n'
            f'Взвешивание фруктов: {task_record.scales_and_fruis}\n'
            f'Сбор фруктов: {task_record.fruit_picking}\n'
            f'Линейных уравнений: {task_record.linear_equasion}\n'
            f'Площадь и периметр: {task_record.area_and_perimeter}\n\n'
            f'Сделано ошибок: {task_record.mistakes}\n'
        )
        await message.answer(text=LEXICON['one_more'],
                             reply_markup=keyboard)


# обработчик выдающий статистику за текущий день
@user_router.message(Command('stats_weekly'))
async def cmd_weekly_stats(
    message: Message,
    session: AsyncSession,
):
    weekly_record: int = await get_weekly_results(
        session, message.from_user.id
    )
    if not weekly_record:
        await message.answer(text=LEXICON['no_stats'],
                             reply_markup=keyboard)
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n"
            f"За прошедшую неделю решено задач: {weekly_record.total}\n\n"
            f'Из них\n'
            f'Взвешивание фруктов: {weekly_record.scales_and_fruis}\n'
            f'Сбор фруктов: {weekly_record.fruit_picking}\n'
            f'Линейных уравнений: {weekly_record.linear_equasion}\n'
            f'Площадь и периметр: {weekly_record.area_and_perimeter}\n\n'
            f'Сделано ошибок: {weekly_record.mistakes}\n'
        )
        await message.answer(text=LEXICON['one_more'],
                             reply_markup=keyboard)


# обработчик команды cancel в основном режиме
@user_router.message(StateFilter(default_state))
async def any_message(message: Message):
    await message.answer(text=LEXICON['anything_else'],
                         reply_markup=keyboard)
