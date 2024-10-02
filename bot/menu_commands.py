from aiogram import Bot
from aiogram.types import BotCommand


async def set_main_menu(bot: Bot):

    main_menu_commands = [
        BotCommand(command='/start',
                   description='Начало работы'),
        BotCommand(command='/task',
                   description='Решать задачи'),
        BotCommand(command='/questionary',
                   description='Обновить информацию о себе'),
        BotCommand(command='/stats',
                   description='Посмотреть статистику'),
        BotCommand(command='/help',
                   description='Справка'),
    ]
    await bot.set_my_commands(main_menu_commands)
