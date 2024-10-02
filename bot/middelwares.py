from typing import Callable, Awaitable, Dict, Any, cast

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.requests import add_user


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)


class TrackAllUsersMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.cache = TTLCache(
            maxsize=1000,
            ttl=60 * 60 * 24,
        )

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        event = cast(Message, event)
        user_id = event.from_user.id

        if user_id not in self.cache:
            session: AsyncSession = data["session"]
            await add_user(
                session=session,
                telegram_id=event.from_user.id,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
            )
            self.cache[user_id] = None
        return await handler(event, data)
