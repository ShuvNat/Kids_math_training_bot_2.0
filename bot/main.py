import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionTypeFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, Message, ReplyKeyboardRemove
from aiogram_dialog import DialogManager, setup_dialogs, ShowMode, StartMode
from aiogram_dialog.api.exceptions import UnknownIntent
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import Config, load_config
from dialogs.quiestionary_dialog import questionnaire_dialog
from dialogs.start_dialog import start_dialog
from dialogs.statistic_dialog import stats_dialog
from dialogs.tasks_dialog import task_dialog
from fsm.fsm_dialogs import storage, StartState
from middelwares import DbSessionMiddleware, TrackAllUsersMiddleware

logger = logging.getLogger(__name__)


async def start(
        message: Message,
        dialog_manager: DialogManager
        ):
    await dialog_manager.start(
        StartState.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


async def on_unknown_intent(event: ErrorEvent, dialog_manager: DialogManager):
    logging.error("Restarting dialog: %s", event.exception)
    if event.update.callback_query:
        await event.update.callback_query.answer(
            'Бот был перезагружен в ходе обслуживния'
            'или непредвиденной ошибки\n'
            'Вы будете пренаправлены в главное меню',
        )
        if event.update.callback_query.message:
            try:
                await event.update.callback_query.message.delete()
            except TelegramBadRequest:
                pass  # whatever
    elif event.update.message:
        await event.update.message.answer(
            'Бот был перезагружен в ходе обслуживния'
            'или непредвиденной ошибки\n'
            'Вы будете пренаправлены в главное меню',
            reply_markup=ReplyKeyboardRemove(),
        )
    await dialog_manager.start(
        StartState.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


dialog_router = Router()
dialog_router.include_routers(
    questionnaire_dialog,
    start_dialog,
    stats_dialog,
    task_dialog,
)


def setup_dp():
    config: Config = load_config()
    dp = Dispatcher(storage=storage, admin_ids=config.tg_bot.admin_ids)
    dp.message.register(start, F.text == "/start")
    dp.business_message.register(start, F.text == "/start")
    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.include_router(dialog_router)
    setup_dialogs(dp)
    return dp


async def main():

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    logger.info('Starting bot')

    config: Config = load_config()

    engine = create_async_engine(
        url=str(config.db.dns),
        echo=config.db.is_echo
    )

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    dp = setup_dp()

    Sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    dp.update.outer_middleware(DbSessionMiddleware(Sessionmaker))
    dp.message.outer_middleware(TrackAllUsersMiddleware())

    bot = Bot(token=config.tg_bot.token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.run(main())
