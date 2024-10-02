from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lexicon import LEXICON

button_1 = InlineKeyboardButton(
    text=LEXICON['scales_and_fruis'],
    callback_data='scales_and_fruis'
)

button_2 = InlineKeyboardButton(
    text=LEXICON['fruit_picking'],
    callback_data='fruit_picking'
)

button_3 = InlineKeyboardButton(
    text=LEXICON['linear_equasion'],
    callback_data='linear_equasion'
)

button_4 = InlineKeyboardButton(
    text=LEXICON['area_and_perimeter'],
    callback_data='area_and_perimeter'
)

button_5 = InlineKeyboardButton(
    text=LEXICON['random_task'],
    callback_data='random_task'
)

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[button_1, button_2],
                     [button_3, button_4],
                     [button_5]]
)
