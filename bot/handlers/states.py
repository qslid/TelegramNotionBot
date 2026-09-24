"""FSM states for Notion connection wizard."""

from aiogram.fsm.state import State, StatesGroup


class NotionConnectFSM(StatesGroup):
    waiting_token = State()
    waiting_database_id = State()
