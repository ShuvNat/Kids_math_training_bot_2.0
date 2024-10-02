import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram_dialog import setup_dialogs
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import Config, load_config
from fsm.fsm_user_dialogs import storage
from handlers.users_dialog import start_dialog, stats_dialog, task_dialog, questionnaire_dialog, user_router
from menu_commands import set_main_menu
from middelwares import DbSessionMiddleware, TrackAllUsersMiddleware


async def main():

    config: Config = load_config()

    engine = create_async_engine(
        url=str(config.db.dns),
        echo=config.db.is_echo
    )

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    dp = Dispatcher(storage=storage)

    Sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    dp.update.outer_middleware(DbSessionMiddleware(Sessionmaker))
    dp.message.outer_middleware(TrackAllUsersMiddleware())

    bot = Bot(token=config.tg_bot.token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.include_routers(start_dialog, stats_dialog, task_dialog, questionnaire_dialog, user_router)
    setup_dialogs(dp)
    dp.startup.register(set_main_menu)

    print("Starting polling...")
    await dp.start_polling(bot)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.run(main())
