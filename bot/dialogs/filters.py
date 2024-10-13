from typing import Dict
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable


def is_admin(
        data: Dict,
        widget: Whenable,
        dialog_manager: DialogManager):
    is_admin = data.get('user_id') in dialog_manager.middleware_data[
                    'admin_ids'
                    ]
    return is_admin
