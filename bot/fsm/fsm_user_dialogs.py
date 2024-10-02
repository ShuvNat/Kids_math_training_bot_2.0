from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage, Redis

redis = Redis(host='localhost', port=6379, db=1)

storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))


class StartUD(StatesGroup):
    start = State()


class QuestionnaireUD(StatesGroup):
    real_first_name = State()
    real_last_name = State()
    class_number = State()
    save = State()


class TaskUD(StatesGroup):
    task = State()
    answer = State()


class StatsUD(StatesGroup):
    choice = State()
    calendar = State()
    stats = State()
